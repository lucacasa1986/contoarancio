import xlrd
import xlrd.sheet
from xlrd.xldate import xldate_as_datetime
import os
import hashlib
from flask import Flask, jsonify, request, flash, redirect, g
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import jwt, sys, traceback
from functools import wraps
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt

ALLOWED_EXTENSIONS = set(['xls', 'xlsx'])

app = Flask(__name__)
app.config.from_object('bilancio.contoarancioapp.config_app.DevelopmentConfig')

app.config.update(dict(
    SECRET_KEY='asdkasdkasdkkAKAKK(((AMcsdkasd?Zasdk2230fksadlcmSJfdk:à',
    UPLOAD_FOLDER=os.path.join(app.root_path, 'uploads'),
    BCRYPT_LOG_ROUNDS=13
))
app.config.from_envvar('CONTOARANCIO_SETTINGS', silent=True)

mysql = MySQL(app)
bcrypt = Bcrypt(app)


class Movimento(object):
    def __init__(self):
        self.id = None
        self.type = None
        self.amount = None
        self.description = None
        self.date = None
        self.data_contabile = None
        self.row_hash = None
        self.categoria_id = None
        self.tags = []

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
        m.update(repr(self.data_contabile).encode('utf-8'))
        self.row_hash = m.hexdigest()


def connect_db():
    """Connects to sqlite database."""
    conn = mysql.connect()
    return conn


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'mysql_db'):
        g.mysql_db = connect_db()
    return g.mysql_db


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'mysql_db'):
        g.mysql_db.close()


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


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def encode_auth_token(user_id):
    """
    Generates the Auth Token
    :return: string
    """
    try:
        payload = {
            'exp': datetime.utcnow() + timedelta(days=0, minutes=15),
            'iat': datetime.utcnow(),
            'sub': user_id
        }
        return jwt.encode(
            payload,
            app.config.get('SECRET_KEY'),
            algorithm='HS256'
        )
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return e


def decode_auth_token(auth_token):
    """
    Decodes the auth token
    :param auth_token:
    :return: integer|string
    """
    payload = jwt.decode(auth_token, app.config.get('SECRET_KEY'))
    return payload['sub']


def generated_hash(password):
    return bcrypt.generate_password_hash(
        password, app.config.get('BCRYPT_LOG_ROUNDS')
    ).decode()


@app.route("/api/login", methods=['POST'])
def do_login():
    username = request.form.get("email")
    password = request.form.get("password")

    cursor = mysql.connection.cursor()
    cursor.execute(""" select username, password from utenti where
                      username = %s
    """, [username])

    user = cursor.fetchone()
    cursor.close()
    if user and bcrypt.check_password_hash(user["password"], password):
        token = encode_auth_token(username)
        return jsonify({
            "token": token.decode('utf-8')
        })
    else:
        return "Unauthorized", 401


@app.route("/api/register", methods=['POST'])
def do_register():
    username = request.form.get("email")
    password = request.form.get("password")

    cursor = mysql.connection.cursor()
    cursor.execute(""" select username, password from utenti where
                      username = %s
    """, [username])

    user = cursor.fetchone()
    if user:
        cursor.close()
        return "User already exists", 500
    else:
        cursor.execute(""" insert into utenti(username, password) 
                          VALUES (%s,%s)""",
                       [username, generated_hash(password)]
                       )
        mysql.connection.commit()
        cursor.close()
        return username, 200


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_token = request.headers.get('Authorization')

        if not auth_token:
            return "Unauthorized", 401
        try:
            auth_token = auth_token.split(" ")[1]
            sub = decode_auth_token(auth_token)
            request.username = sub
        except jwt.ExpiredSignatureError:
            return 'Signature expired. Please log in again.', 401
        except jwt.InvalidTokenError:
            return 'Invalid token. Please log in again.', 401
        except Exception:
            return "Unauthorized", 401
        else:
            return f(*args, **kwargs)
    return decorated


def parse_movimenti_conto(conto_id, sheet):
    movimenti = []
    cursor = mysql.connection.cursor()
    for rowindex in range(1, sheet.nrows):
        check_val = sheet.cell_value(rowindex, 0)
        if not check_val:
            break
        movimento = Movimento()
        movimento.date = xldate_as_datetime(sheet.cell_value(rowindex, 1),
                                            datemode=0)
        movimento.data_contabile = xldate_as_datetime(sheet.cell_value(rowindex, 0),
                                            datemode=0)

        movimento.type = sheet.cell_value(rowindex, 2)
        movimento.description = sheet.cell_value(rowindex, 3)
        movimento.amount = sheet.cell_value(rowindex, 4)

        movimento.compute_hash()

        cursor.execute('select id from movimenti where row_hash = %s',
                         [movimento.row_hash])
        rec = cursor.fetchone()
        if not rec:
            cursor.execute("""
                      INSERT INTO movimenti (tipo, descrizione, data_movimento, importo, row_hash, conto_id) 
                      VALUES (%s, %s, %s, %s, %s, %s)
                      """,
                           [movimento.type, movimento.description,
                            movimento.date, movimento.amount,
                            movimento.row_hash, conto_id])
            movimento.id = cursor.lastrowid
            movimenti.append(movimento)
        else:
            print('Movimento già caricato')
    mysql.connection.commit()
    cursor.close()
    return movimenti


def parse_movimenti_carta(conto_id, sheet):
    movimenti = []
    cursor = mysql.connection.cursor()
    for rowindex in range(1, sheet.nrows-1):
        check_val = sheet.cell_value(rowindex, 0)
        if not check_val:
            break
        movimento = Movimento()
        movimento.date = xldate_as_datetime(sheet.cell_value(rowindex, 0),
                                            datemode=0)
        movimento.data_contabile = xldate_as_datetime(
            sheet.cell_value(rowindex, 1),
            datemode=0)
        movimento.type = 'PAGAMENTO CARTA DI CREDITO'
        movimento.description = sheet.cell_value(rowindex, 2)
        movimento.amount = sheet.cell_value(rowindex, 4) * -1

        movimento.compute_hash()
        print('new movimento hash is ' + movimento.row_hash)
        cursor.execute('select id from movimenti where row_hash = %s',
                         [movimento.row_hash])
        rec = cursor.fetchone()
        if not rec:
            cursor.execute("""
                          INSERT INTO movimenti (tipo, descrizione, data_movimento, importo, row_hash, conto_id)
                          VALUES (%s, %s, %s, %s, %s, %s)
                          """,
                           [movimento.type, movimento.description,
                            movimento.date, movimento.amount,
                            movimento.row_hash, conto_id])
            movimento.id = cursor.lastrowid
            movimenti.append(movimento)
        else:
            print('Movimento già caricato')
    mysql.connection.commit()
    cursor.close()
    return movimenti


@app.route("/api/parse/<conto_id>", methods=['POST'])
@requires_auth
def parse_file(conto_id):

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

        tipo_movimenti = request.form.get('type')

        if not tipo_movimenti or tipo_movimenti == 'CONTO':
            movimenti = parse_movimenti_conto(conto_id, sheet)
        elif tipo_movimenti == 'CARTA':
            movimenti = parse_movimenti_carta(conto_id, sheet)

        return jsonify([ m.__dict__ for m in movimenti])


@app.route("/api/conti", methods=['GET'])
@requires_auth
def get_lista_conti():
    cursor = mysql.connection.cursor()
    username = request.username
    select = """
        select conti.id,
        titolare,
        descrizione
        from conti inner join utenti u ON conti.user_id = u.id
        where u.username = %s
    """
    cursor.execute(select, [username])
    entries = cursor.fetchall()
    return jsonify([e for e in entries])


@app.route('/api/conto', methods=['POST'])
@requires_auth
def crea_conto():
    conto = request.get_json(force=True)
    username = request.username

    cursor = mysql.connection.cursor()
    cursor.execute(" select id from utenti where username = %s", [username])
    utente = cursor.fetchone()

    cursor.execute("""
                  INSERT INTO conti(titolare,descrizione, user_id) VALUES (%s,%s)
                        """,
                   [conto["titolare"], conto["descrizione"], utente["id"]])
    mysql.connection.commit()
    cursor.close()
    return str(cursor.lastrowid)

@app.route("/api/<conto_id>/andamento", methods=['GET'])
@requires_auth
def get_andamento(conto_id):
    cursor = mysql.connection.cursor()
    from_date_param = request.args.get('from_date')
    to_date_param = request.args.get('to_date')
    if from_date_param:
        from_date = datetime.strptime(from_date_param, '%Y-%m-%d').date()
    else:
        from_date = datetime.now() - timedelta(days=30)
        from_date = from_date.date()

    if to_date_param:
        to_date = datetime.strptime(to_date_param, '%Y-%m-%d').date()
    else:
        to_date = datetime.now().date()


    starting_value_q = """
    select sum(importo) as partenza
    from movimenti
    where conto_id = %s
    and data_movimento <= %s
    """

    cursor.execute(starting_value_q, [conto_id, from_date])
    starting = cursor.fetchone()["partenza"]

    if not starting:
        starting = 0
        date = []
        valori = []
    else:
        date = [from_date.strftime('%d-%m-%Y')]
        valori = [starting]

    select = """
            select data_movimento,sum(importo) as del_giorno
            from movimenti
            where conto_id = %s
            and data_movimento > %s and data_movimento <= %s
            group by data_movimento
        """
    params = [conto_id, from_date, to_date ]
    cursor.execute(select, params)
    entries = cursor.fetchall()

    for row in entries:
        starting = starting + row['del_giorno']
        date.append(row['data_movimento'].strftime('%d-%m-%Y'))
        valori.append(starting)

    if not to_date.strftime('%d-%m-%Y') in date:
        date.append(to_date.strftime('%d-%m-%Y'))
        valori.append(starting)

    andamento = {
        "date": date,
        "valori": valori
    }

    return jsonify(andamento)


@app.route("/api/<conto_id>/parziali", methods=['GET'])
@requires_auth
def get_per_categoria(conto_id):
    cursor = mysql.connection.cursor()
    from_date_param = request.args.get('from_date')
    to_date_param = request.args.get('to_date')
    categories = request.args.getlist('category')
    if from_date_param:
        from_date = datetime.strptime(from_date_param, '%Y-%m-%d').date()
    else:
        from_date = datetime.now() - timedelta(days=30)
        from_date = from_date.date()

    if to_date_param:
        to_date = datetime.strptime(to_date_param, '%Y-%m-%d').date()
    else:
        to_date = datetime.now().date()


    select = """
    select categorie.descrizione, 
    categorie.colore, 
    categorie.id as categoria_id, 
    DATE_FORMAT(data_movimento, '%%Y-%%m-01') as month,
    sum(importo) as importo_tot
    from movimenti inner join categorie on movimenti.categoria_id = categorie.id 
    where categoria_id is not null and movimenti.conto_id = %s
    and movimenti.data_movimento > %s and movimenti.data_movimento <= %s
    """

    params = [conto_id, from_date, to_date]

    group_by = """
    group by categorie.descrizione, categorie.colore, categorie.id, DATE_FORMAT(data_movimento, '%%Y-%%m-01')
    order by categoria_id, month
    """

    if categories:
        select = select + " and categoria_id in ( "
        for category_id in categories:
            select = select + "%s,"
            params.append(category_id)
        select = select[:-1] + ") "
    print(select + " " + group_by)
    print (params)
    cursor.execute(select + " " + group_by, params)
    entries = cursor.fetchall()

    result = []
    category_id = None
    categoria = None
    for row in entries:
        curr_category_id = row["categoria_id"]
        if not category_id or category_id != curr_category_id:
            category_id = curr_category_id
            # nuova categoria
            categoria = {
                "id": curr_category_id,
                "colore": row["colore"],
                "descrizione": row["descrizione"],
                "rilevazioni": []
            }
            result.append(categoria)
        categoria["rilevazioni"].append({
            "month": row["month"],
            "importo": row["importo_tot"]
        })

    return jsonify(result)



@app.route("/api/<conto_id>", methods=['GET'])
@requires_auth
def get_movimenti(conto_id):
    cursor = mysql.connection.cursor()
    from_date_param = request.args.get('from_date')
    to_date_param = request.args.get('to_date')
    categories = request.args.getlist('category')
    if from_date_param:
        from_date = datetime.strptime(from_date_param, '%Y-%m-%d').date()
    else:
        from_date = datetime.now() - timedelta(days=30)
        from_date = from_date.date()

    if to_date_param:
        to_date = datetime.strptime(to_date_param, '%Y-%m-%d').date()
    else:
        to_date = datetime.now().date()

    params = [from_date, to_date, conto_id]

    select = """
        select id,
        tipo,
        descrizione,
        data_movimento,
        importo,
        row_hash,
        categoria_id
        from movimenti where data_movimento between %s and %s and conto_id = %s
    """

    if categories:
        select = select + " and categoria_id in ( "
        for category_id in categories:
            select = select + "%s,"
            params.append(category_id)
        select = select[:-1] + ") "

    select = select + " order by data_movimento desc"
    cursor.execute(select, params)
    entries = cursor.fetchall()
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
        movimento.tags = load_tags_for_movimento(movimento.id)
        movimenti.append(movimento)
    return jsonify([ m.__dict__ for m in movimenti])


@app.route("/api/movimento", methods=['PUT'])
@requires_auth
def update_movimento():
    movimento = request.get_json(force=True)
    if not movimento.get("id"):
        return "Errore, manca id movimento"

    cursor = mysql.connection.cursor()
    cursor.execute("""
                      UPDATE movimenti set categoria_id = %s where id=%s
                    """,
                   [movimento["categoria_id"], movimento["id"]])
    mysql.connection.commit()
    cursor.close()
    return str(movimento.get("id"))


@app.route("/api/categories", methods=['GET'])
def get_all_categories():
    cursor = mysql.connection.cursor()
    cursor.execute('select id, descrizione, colore, icon_class, tipo from categorie order by descrizione')
    cursor.fetchall()
    return jsonify([e for e in cursor])


@app.route("/api/tags", methods=['GET'])
def get_all_tags():
    cursor = mysql.connection.cursor()
    cursor.execute('select id, value, name from tags')
    entries = cursor.fetchall()
    return jsonify([e for e in entries])


def load_tags_for_movimento(movimento_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
            select t.value, t.name
            from tags t join movimento_tags mt on mt.tag_id = t.id
            and mt.movimento_id = %s
            """, [movimento_id])
    return cursor.fetchall()


@app.route('/api/tag/<movimento_id>', methods=['GET'])
@requires_auth
def get_tag_for_movimento(movimento_id):
    entries = load_tags_for_movimento(movimento_id)
    return jsonify([e for e in entries])


@app.route('/api/tag/<movimento_id>/<tag_value>', methods=['PUT'])
@requires_auth
def add_tag(movimento_id, tag_value):
    cursor = mysql.connection.cursor()
    cursor.execute(
        'select id from tags where value = %s',
        [tag_value]);
    tags = cursor.fetchall()
    if tags:
        tag_id = tags[0]['id']
    else:
        cursor.execute(
            'insert into tags(value, name) values (%s,%s)',
            [tag_value, tag_value]);
        tag_id=cursor.lastrowid
    cursor.execute('insert into movimento_tags(movimento_id, tag_id) values (%s,%s)', [movimento_id, tag_id]);
    mysql.connection.commit()
    cursor.close()
    return 'OK'


@app.route('/api/tag/<movimento_id>/<tag_value>', methods=['DELETE'])
@requires_auth
def remove_tag(movimento_id, tag_value):
    cursor = mysql.connection.cursor()
    cursor.execute(
        'select id from tags where value = %s',
        [tag_value]);
    tags = cursor.fetchall()
    if tags:
        tag_id = tags[0]['id']
        cursor.execute('delete from movimento_tags where movimento_id = %s and tag_id = %s', [movimento_id, tag_id]);
        mysql.connection.commit()
        cursor.close()
    return 'OK'


if __name__ == "__main__":
    app.run(host='0.0.0.0')