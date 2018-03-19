import xlrd
import xlrd.sheet
from xlrd.xldate import xldate_as_datetime
import os
import sqlite3
import hashlib
from flask import Flask, jsonify, request, flash, redirect, g
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

ALLOWED_EXTENSIONS = set(['xls', 'xlsx'])

app = Flask(__name__)
app.config.from_object(__name__)

app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'flaskr.db'),
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='default',
    UPLOAD_FOLDER=os.path.join(app.root_path, 'uploads')
))
app.config.from_envvar('FLASKR_SETTINGS', silent=True)


class Movimento(object):
    def __init__(self):
        self.id = None
        self.type = None
        self.amount = None
        self.description = None
        self.date = None
        self.row_hash = None
        self.categoria_id = None

    def __str__(self):
        return 'Movimento %s di tipo %s, per un ammontare di %s in data %s' % (
            self.description,
            self.type,
            self.amount,
            self.date
        )

    def compute_hash(self):
        m = hashlib.sha1()
        m.update(repr(self.type).encode('utf-8'))
        m.update(repr(self.amount).encode('utf-8'))
        m.update(repr(self.description).encode('utf-8'))
        m.update(repr(self.date).encode('utf-8'))
        self.row_hash = m.hexdigest()


def connect_db():
    """Connects to sqlite database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


def init_db():
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


def update_db():
    db = get_db()
    i = 1
    check_update = True
    while check_update:
        try:
            with app.open_resource('update%i.sql' % i, mode='r') as f:
                db.cursor().executescript(f.read())
        except Exception as e:
            print('Error executing script %s: %s' % ('update%i.sql' % i, e))
            check_update = False
        else:
            i = i+1
    db.commit()


@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""
    init_db()
    print('Initialized the database.')


@app.cli.command('updatedb')
def updatedb_command():
    """Initializes the database."""
    update_db()
    print('Database updated')


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_movimenti_conto(sheet):
    movimenti = []
    db = get_db()
    for rowindex in range(1, sheet.nrows):
        check_val = sheet.cell_value(rowindex, 0)
        if not check_val:
            break
        movimento = Movimento()
        movimento.date = xldate_as_datetime(sheet.cell_value(rowindex, 0),
                                            datemode=0)
        movimento.type = sheet.cell_value(rowindex, 2)
        movimento.description = sheet.cell_value(rowindex, 3)
        movimento.amount = sheet.cell_value(rowindex, 4)

        movimento.compute_hash()

        cur = db.execute('select id from movimenti where row_hash = ?',
                         [movimento.row_hash])
        rec = cur.fetchone()
        if not rec:
            cursor = db.cursor()
            cursor.execute("""
                      INSERT INTO movimenti (tipo, descrizione, data_movimento, importo, row_hash) VALUES (?, ?, ?, ?, ?)
                      """,
                           [movimento.type, movimento.description,
                            movimento.date, movimento.amount,
                            movimento.row_hash])
            movimento.id = cursor.lastrowid
            movimenti.append(movimento)
        else:
            print('Movimento già caricato')
    db.commit()
    return movimenti


def parse_movimenti_carta(sheet):
    movimenti = []
    db = get_db()
    for rowindex in range(1, sheet.nrows - 1):
        check_val = sheet.cell_value(rowindex, 0)
        if not check_val:
            break
        movimento = Movimento()
        movimento.date = xldate_as_datetime(sheet.cell_value(rowindex, 0),
                                            datemode=0)
        movimento.type = 'PAGAMENTO CARTA DI CREDITO'
        movimento.description = sheet.cell_value(rowindex, 2)
        movimento.amount = sheet.cell_value(rowindex, 4) * -1

        movimento.compute_hash()

        cur = db.execute('select id from movimenti where row_hash = ?',
                         [movimento.row_hash])
        rec = cur.fetchone()
        if not rec:
            cursor = db.cursor()
            cursor.execute("""
                          INSERT INTO movimenti (tipo, descrizione, data_movimento, importo, row_hash) VALUES (?, ?, ?, ?, ?)
                          """,
                           [movimento.type, movimento.description,
                            movimento.date, movimento.amount,
                            movimento.row_hash])
            movimento.id = cursor.lastrowid
            movimenti.append(movimento)
        else:
            print('Movimento già caricato')
    db.commit()
    return movimenti


@app.route("/api/parse", methods=['POST'])
def parse_file():

    if 'excel_file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['excel_file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        res = xlrd.open_workbook(
            filename=os.path.join(app.config['UPLOAD_FOLDER'], filename))
        sheet = res.sheet_by_index(0)

        tipo_movimenti = request.args.get('type')

        if not tipo_movimenti or tipo_movimenti == 'CONTO':
            movimenti = parse_movimenti_conto(sheet)
        elif tipo_movimenti == 'CARTA':
            movimenti = parse_movimenti_carta(sheet)

        return jsonify([ m.__dict__ for m in movimenti])


@app.route("/api", methods=['GET'])
def get_movimenti():
    db = get_db()
    from_date_param = request.args.get('from_date')
    to_date_param = request.args.get('to_date')
    categories = request.args.getlist('category')
    print(categories)
    if from_date_param:
        from_date = datetime.strptime(from_date_param, '%Y-%m-%d')
    else:
        from_date = datetime.now() - timedelta(days=30)

    if to_date_param:
        to_date = datetime.strptime(to_date_param, '%Y-%m-%d')
    else:
        to_date = datetime.now()

    params = [from_date, to_date]

    select = """
        select id,
        tipo,
        descrizione,
        data_movimento,
        importo,
        row_hash,
        categoria_id
        from movimenti where data_movimento between ? and ?
    """

    if categories:
        select = select + " and categoria_id in ( "
        for category_id in categories:
            select = select + "?,"
            params.append(category_id)
        select = select[:-1] + ") "

    select = select + " order by data_movimento desc"

    cur = db.execute(select,params)
    entries = cur.fetchall()
    movimenti = []
    for row in entries:
        movimento = Movimento()
        movimento.id = row["id"],
        movimento.type = row["tipo"]
        movimento.description = row["descrizione"]
        movimento.date = row["data_movimento"]
        movimento.amount = row["importo"]
        movimento.categoria_id = row["categoria_id"]
        movimento.row_hash = row["row_hash"]
        movimenti.append(movimento)
    return jsonify([ m.__dict__ for m in movimenti])

@app.route("/api/movimento", methods=['PUT'])
def update_movimento():
    movimento = request.get_json(force=True)
    if not movimento.get("id"):
        return "Errore, manca id movimento"

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
                      UPDATE movimenti set categoria_id = ? where id=?
                    """,
                   [movimento["categoria_id"], movimento["id"]])
    db.commit()
    return str(movimento.get("id"))


@app.route("/api/categories", methods=['GET'])
def get_all_categories():
    db = get_db()
    cur = db.execute('select id, descrizione, colore, icon_class from categorie order by descrizione')
    entries = cur.fetchall()
    return jsonify([dict(e) for e in entries])


@app.route("/api/categories", methods=['POST'])
def add_category():
    category = request.get_json(force=True)
    id = category.get("id")
    db = get_db()
    cursor = db.cursor()
    if id:
        # update
        cursor.execute("""
                      update categorie set descrizione=?, colore = ? where id = ?
                       """,
                       [category["descrizione"], category["colore"], category["id"]])
    else:
        cursor.execute("""
                       INSERT INTO categorie (descrizione, colore) VALUES (?, ?)
                       """,
                       [category["descrizione"], category["colore"]])
    db.commit()
    return id or str(cursor.lastrowid)

@app.route("/api/tags", methods=['GET'])
def get_all_tags():
    db = get_db()
    cur = db.execute('select id, value, name from tags')
    entries = cur.fetchall()
    return jsonify([dict(e) for e in entries])

@app.route('/api/tag/<movimento_id>', methods=['GET'])
def get_tag_for_movimento(movimento_id):
    db = get_db()
    cur = db.execute("""
        select t.value, t.name
        from tags t join movimento_tags mt on mt.tag_id = t.id
        and mt.movimento_id = ?
        """, [movimento_id])
    entries = cur.fetchall()
    return jsonify([dict(e) for e in entries])

@app.route('/api/tag/<movimento_id>/<tag_value>', methods=['PUT'])
def add_tag(movimento_id, tag_value):
    db = get_db()
    cur = db.execute(
        'select id from tags where value = ?',
        [tag_value]);
    tags = cur.fetchall()
    if tags:
        tag_id = tags[0]['id']
    else:
        cur = db.execute(
            'insert into tags(value, name) values (?,?)',
            [tag_value, tag_value]);
        tag_id=cur.lastrowid
    cur = db.execute('insert into movimento_tags(movimento_id, tag_id) values (?,?)', [movimento_id, tag_id]);
    db.commit()
    return 'OK'

@app.route('/api/tag/<movimento_id>/<tag_value>', methods=['DELETE'])
def remove_tag(movimento_id, tag_value):
    db = get_db()
    cur = db.execute(
        'select id from tags where value = ?',
        [tag_value]);
    tags = cur.fetchall()
    if tags:
        tag_id = tags[0]['id']
        cur = db.execute('delete from movimento_tags where movimento_id = ? and tag_id = ?', [movimento_id, tag_id]);
        db.commit()
    return 'OK'