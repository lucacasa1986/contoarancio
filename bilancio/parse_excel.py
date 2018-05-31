import xlrd
import xlrd.sheet
from xlrd.xldate import xldate_as_datetime
from xlrd.biffh import XLRDError
import os
import hashlib
from flask import Flask, jsonify, request, flash, redirect, g
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from flask_jwt import JWT, JWTError, jwt_required, current_identity
from flask_cors import CORS
import pandas as pd

ALLOWED_EXTENSIONS = {'xls', 'xlsx'}

app = Flask(__name__)
app.config.from_object('bilancio.contoarancioapp.config_app.DevelopmentConfig')

app.config.update(dict(
    SECRET_KEY='asdkasdkasdkkAKAKK(((AMcsdkasd?Zasdk2230fksadlcmSJfdk:à',
    UPLOAD_FOLDER=os.path.join(app.root_path, 'uploads'),
    BCRYPT_LOG_ROUNDS=13,
    JWT_AUTH_URL_RULE=None,
    JWT_AUTH_HEADER_PREFIX="Bearer",
    JWT_EXPIRATION_DELTA=timedelta(seconds=3600)
))
app.config.from_envvar('CONTOARANCIO_SETTINGS', silent=True)

mysql = MySQL(app)
bcrypt = Bcrypt(app)
CORS(app)

class User(object):
    def __init__(self, id, password):
        self.id = id
        self.password = password

    def __str__(self):
        return "User(id='%s')" % self.id


def authenticate(username, password):
    cursor = mysql.connection.cursor()
    cursor.execute(""" select id, username, password from utenti where
                          username = %s
        """, [username])

    user = cursor.fetchone()
    if user and bcrypt.check_password_hash(user["password"], password):
        return User(user["username"], user["password"])
    else:
        return None


def identify(payload):
    cursor = mysql.connection.cursor()
    cursor.execute(""" select username from utenti where
                              username = %s
            """, [payload['identity']])

    user = cursor.fetchone()
    return user


def jwt_response_callback(access_token, identity):
    return jsonify({'token': access_token.decode('utf-8')})


jwt = JWT(app, authenticate, identify)
jwt.auth_response_handler(jwt_response_callback)


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
        self.sottocategoria_id = None
        self.ignored = False
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
        m.update(repr(self.date).encode('utf-8'))
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
            i = i + 1
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


def generated_hash(password):
    return bcrypt.generate_password_hash(
        password, app.config.get('BCRYPT_LOG_ROUNDS')
    ).decode()


@app.route("/api/login", methods=['POST'])
def do_login():
    username = request.form.get("email")
    password = request.form.get("password")

    identity = jwt.authentication_callback(username, password)

    if identity:
        access_token = jwt.jwt_encode_callback(identity)
        return jwt.auth_response_callback(access_token, identity)
    else:
        raise JWTError('Bad Request', 'Invalid credentials')


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


def assign_category(movimento):
    cursor = mysql.connection.cursor()
    cursor.execute('select id, category_id, subcategory_id from regole order by priority')
    rules = cursor.fetchall()
    found_category_id = None
    found_subcat_id = None
    for rule in rules:
        cursor.execute('select field, operator, value from regole_condizione '
                       'where regola_id = %s', [rule["id"]])
        conditions = cursor.fetchall()
        conditions_match = True
        for condition in conditions:
            value = condition['value']
            field = condition['field']
            operatore = condition['operator']
            movimento_column = None
            if field == 'CAUSALE':
                movimento_column = "type"
            elif field == 'DESCRIZIONE':
                movimento_column = 'description'
            elif field == 'IMPORTO':
                movimento_column = 'amount'
            column_value = getattr(movimento, movimento_column)

            if operatore == 'EQUALS':
                if column_value.upper() != value.upper():
                    conditions_match = False
            elif operatore == 'CONTAINS':
                if value.upper() not in column_value.upper():
                    conditions_match = False
        if conditions_match:
            found_category_id = rule['category_id']
            found_subcat_id = rule['subcategory_id']
            break
    cursor.close()
    return found_category_id, found_subcat_id


def parse_amount(value):
    if value:
        value_str = value.split(" ")
        if len(value_str) > 1:
            value_str = value_str[1]
        else:
            value_str = value_str[0]
        return float(value_str.replace('.','').replace(',','.'))
    return value


def convert_html_to_xls(filename, tipo):
    tmp_filename = os.path.join(app.config['UPLOAD_FOLDER'], 'tmp_output.xlsx')

    writer = pd.ExcelWriter(tmp_filename)

    if not tipo or tipo == 'CONTO':

        frames = pd.read_html(os.path.join(app.config['UPLOAD_FOLDER'], filename),
                              flavor="bs4",
                              header=0,
                              index_col=0,
                              thousands="",
                              decimal=",",
                              converters={
                                  4: parse_amount
                              }
                              )
    else:
        frames = pd.read_html(
            os.path.join(app.config['UPLOAD_FOLDER'], filename),
            flavor="bs4",
            header=0,
            index_col=0,
            thousands="",
            decimal=","
            )
    if frames:
        df = frames[0]
        df.to_excel(writer,'Sheet1')
    writer.save()

    return tmp_filename


def parse_movimenti_conto_mps(conto_id, sheet):
    movimenti = []
    cursor = mysql.connection.cursor()
    # find beignning of file
    for rowindex in range(0, sheet.nrows):
        check_val = sheet.cell_value(rowindex, 1)
        if check_val == 'DATA CONT.':
            starting_row_index = rowindex
            break

    if starting_row_index:
        for rowindex in range(starting_row_index+1, sheet.nrows):
            check_val = sheet.cell_value(rowindex, 1)
            if not check_val:
                break
            movimento = Movimento()
            try:
                movimento.date = xldate_as_datetime(sheet.cell_value(rowindex, 2),
                                                    datemode=0)
            except:
                date_str = sheet.cell_value(rowindex, 2)
                movimento.date = datetime.strptime(date_str, '%d/%m/%Y')

            try:
                movimento.data_contabile = xldate_as_datetime(
                    sheet.cell_value(rowindex, 1),
                    datemode=0)
            except:
                date_str = sheet.cell_value(rowindex, 1)
                movimento.data_contabile = datetime.strptime(date_str, '%d/%m/%Y')

            movimento.type = sheet.cell_value(rowindex, 3)
            if movimento.type == 'CARTA CREDITO ING DIRECT':
                continue
            movimento.description = sheet.cell_value(rowindex, 4)
            movimento.amount = sheet.cell_value(rowindex, 6)

            movimento.compute_hash()

            cursor.execute('select id from movimenti where row_hash = %s',
                           [movimento.row_hash])
            rec = cursor.fetchone()
            if not rec:
                movimento.categoria_id, movimento.sottocategoria_id = assign_category(
                    movimento)
                cursor.execute("""
                              INSERT INTO movimenti (tipo,
                               descrizione, 
                               data_movimento,
                               importo,
                               row_hash,
                               categoria_id,
                               sottocategoria_id,
                               conto_id) 
                              VALUES (%s, %s, %s, %s, %s, %s,%s, %s)
                              """,
                               [movimento.type, movimento.description,
                                movimento.date, movimento.amount,
                                movimento.row_hash, movimento.categoria_id,
                                movimento.sottocategoria_id,
                                conto_id])
                movimento.id = cursor.lastrowid
                movimenti.append(movimento)
            else:
                print('Movimento già caricato')
    mysql.connection.commit()
    cursor.close()
    return movimenti


def parse_movimenti_conto(conto_id, sheet):
    movimenti = []
    cursor = mysql.connection.cursor()
    for rowindex in range(1, sheet.nrows):
        check_val = sheet.cell_value(rowindex, 0)
        if not check_val:
            break
        movimento = Movimento()
        try:
            movimento.date = xldate_as_datetime(sheet.cell_value(rowindex, 1),
                                                datemode=0)
        except:
            date_str = sheet.cell_value(rowindex, 1)
            movimento.date = datetime.strptime(date_str, '%d/%m/%Y')

        try:
            movimento.data_contabile = xldate_as_datetime(
                sheet.cell_value(rowindex, 0),
                datemode=0)
        except:
            date_str = sheet.cell_value(rowindex, 0)
            movimento.data_contabile = datetime.strptime(date_str, '%d/%m/%Y')

        movimento.type = sheet.cell_value(rowindex, 2)
        if movimento.type == 'CARTA CREDITO ING DIRECT':
            continue
        movimento.description = sheet.cell_value(rowindex, 3)
        movimento.amount = sheet.cell_value(rowindex, 4)

        movimento.compute_hash()

        cursor.execute('select id from movimenti where row_hash = %s',
                       [movimento.row_hash])
        rec = cursor.fetchone()
        if not rec:
            movimento.categoria_id, movimento.sottocategoria_id = assign_category(movimento)
            cursor.execute("""
                      INSERT INTO movimenti (tipo,
                       descrizione,
                       data_movimento,
                       importo,
                       row_hash,
                       categoria_id,
                       sottocategoria_id,
                       conto_id)
                      VALUES (%s, %s, %s, %s, %s, %s,%s, %s)
                      """,
                           [movimento.type, movimento.description,
                            movimento.date, movimento.amount,
                            movimento.row_hash, movimento.categoria_id,
                            movimento.sottocategoria_id,
                            conto_id])
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
    for rowindex in range(1, sheet.nrows):
        check_val = sheet.cell_value(rowindex, 3)
        if not check_val:
            break
        movimento = Movimento()

        try:
            movimento.date = xldate_as_datetime(sheet.cell_value(rowindex, 0),
                                                datemode=0)
        except:
            date_str = sheet.cell_value(rowindex, 0)
            movimento.date = datetime.strptime(date_str, '%d/%m/%Y')

        try:
            movimento.data_contabile = xldate_as_datetime(sheet.cell_value(rowindex, 1),
                                                datemode=0)
        except:
            date_str = sheet.cell_value(rowindex, 1)
            movimento.data_contabile = datetime.strptime(date_str,'%d/%m/%Y')

        movimento.type = 'PAGAMENTO CARTA DI CREDITO'
        movimento.description = sheet.cell_value(rowindex, 2)
        movimento.amount = sheet.cell_value(rowindex, 4) * -1

        movimento.compute_hash()
        cursor.execute('select id from movimenti where row_hash = %s',
                       [movimento.row_hash])
        rec = cursor.fetchone()
        if not rec:
            movimento.categoria_id , movimento.sottocategoria_id= assign_category(movimento)
            cursor.execute("""
                          INSERT INTO movimenti (tipo,
                           descrizione,
                           data_movimento,
                           importo,
                           row_hash,
                           categoria_id,
                           sottocategoria_id,
                           conto_id)
                          VALUES (%s, %s, %s, %s, %s, %s,%s, %s)
                          """,
                           [movimento.type, movimento.description,
                            movimento.date, movimento.amount,
                            movimento.row_hash, movimento.categoria_id,
                            movimento.sottocategoria_id,
                            conto_id])
            movimento.id = cursor.lastrowid
            movimenti.append(movimento)
        else:
            print('Movimento già caricato')
    mysql.connection.commit()
    cursor.close()
    return movimenti


@app.route("/api/parse/<conto_id>", methods=['POST'])
@jwt_required()
def parse_file(conto_id):
    movimenti = []
    tipo_movimenti = request.form.get('type')
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

        try:
            res = xlrd.open_workbook(
                filename=os.path.join(app.config['UPLOAD_FOLDER'], filename))
            sheet = res.sheet_by_index(0)
        except XLRDError:
            # not a valid excel , maybe it's an html table
            tmp_filename = convert_html_to_xls(filename=filename,
                                               tipo=tipo_movimenti)
            res = xlrd.open_workbook(filename=tmp_filename)
            sheet = res.sheet_by_index(0)

        if not tipo_movimenti or tipo_movimenti == 'CONTO':
            movimenti = parse_movimenti_conto(conto_id, sheet)
        elif tipo_movimenti == 'CONTO_MPS':
            moviment = parse_movimenti_conto_mps(conto_id, sheet)
        elif tipo_movimenti == 'CARTA':
            movimenti = parse_movimenti_carta(conto_id, sheet)

        return jsonify([m.__dict__ for m in movimenti])


@app.route("/api/conti", methods=['GET'])
@jwt_required()
def get_lista_conti():
    cursor = mysql.connection.cursor()
    username = current_identity["username"]
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
@jwt_required()
def crea_conto():
    conto = request.get_json(force=True)
    username = current_identity["username"]

    cursor = mysql.connection.cursor()
    cursor.execute(" select id from utenti where username = %s", [username])
    utente = cursor.fetchone()

    cursor.execute('INSERT INTO conti(titolare,descrizione,user_id) '
                   'VALUES (%s,%s,%s)',
                   [conto["titolare"], conto["descrizione"], utente["id"]])
    mysql.connection.commit()
    cursor.close()
    return str(cursor.lastrowid)


@app.route("/api/<conto_id>/andamento", methods=['GET'])
@jwt_required()
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
    and data_movimento <= %s and ignored is FALSE
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
            and ignored is FALSE
            group by data_movimento
        """
    params = [conto_id, from_date, to_date]
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
@jwt_required()
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
    and movimenti.ignored is FALSE
    """

    params = [conto_id, from_date, to_date]

    group_by = """
    group by categorie.descrizione, categorie.colore,
    categorie.id, DATE_FORMAT(data_movimento, '%%Y-%%m-01')
    order by categoria_id, month
    """

    if categories:
        select = select + " and categoria_id in ( "
        for category_id in categories:
            select = select + "%s,"
            params.append(category_id)
        select = select[:-1] + ") "
    else:
        return jsonify([])
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
@jwt_required()
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
        categoria_id,
        sottocategoria_id
        from movimenti where data_movimento between %s and %s and conto_id = %s
        and ignored is FALSE 
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
        movimento.sottocategoria_id = row["sottocategoria_id"]
        movimento.tags = load_tags_for_movimento(movimento.id)
        movimenti.append(movimento)
    return jsonify([m.__dict__ for m in movimenti])


@app.route("/api/movimento", methods=['PUT'])
@jwt_required()
def update_movimento():
    movimento = request.get_json(force=True)
    if not movimento.get("id"):
        return "Errore, manca id movimento"

    cursor = mysql.connection.cursor()
    cursor.execute("""
                      UPDATE movimenti set categoria_id = %s,
                      sottocategoria_id = %s, ignored=%s where id=%s
                    """,
                   [movimento["categoria_id"],
                    movimento["sottocategoria_id"],
                    movimento.get("ignored", False),
                    movimento["id"]])
    mysql.connection.commit()
    cursor.close()
    return str(movimento.get("id"))


@app.route("/api/movimento", methods=['POST'])
@jwt_required()
def split_movimento():
    """ Splitta il movimento su più cataegoire
    ( di fatto, crea dei nuovi movimenti)"""
    data = request.get_json(force=True)
    movimento = data["movimento"]
    altre_categorie = data["others"]
    if not movimento.get("id"):
        return "Errore, manca id movimento"

    cursor = mysql.connection.cursor()
    cursor.execute("select * from movimenti where id=%s", [movimento["id"]])
    movimento_orig = cursor.fetchone()

    cursor.execute("""
                      UPDATE movimenti set categoria_id = %s,
                      sottocategoria_id = %s, importo=%s where id=%s
                    """,
                   [movimento["categoria_id"],
                    movimento["sottocategoria_id"],
                    movimento["amount"],
                    movimento["id"]])

    for nuovo_movimento in altre_categorie:
        m = Movimento()
        m.amount = nuovo_movimento["amount"]
        m.categoria_id = nuovo_movimento["category"]["id"]
        if nuovo_movimento['subCategory']:
            m.sottocategoria_id = nuovo_movimento["subCategory"]["id"]
        m.date = movimento_orig["data_movimento"]
        m.description = movimento_orig["descrizione"]
        m.type = movimento_orig["tipo"]
        m.data_contabile = movimento_orig["data_movimento"]
        m.compute_hash()
        cursor.execute("""
                              INSERT INTO movimenti (tipo,
                               descrizione,
                               data_movimento,
                               importo,
                               row_hash,
                               categoria_id,
                               sottocategoria_id,
                               conto_id)
                              VALUES (%s, %s, %s, %s, %s, %s,%s, %s)
                              """,
                       [m.type, m.description,
                        m.date, m.amount,
                        m.row_hash, m.categoria_id,
                        m.sottocategoria_id,
                        movimento_orig["conto_id"]])

    mysql.connection.commit()
    cursor.close()
    return "OK"


@app.route("/api/categories", methods=['GET'])
def get_all_categories():
    cursor = mysql.connection.cursor()
    cursor.execute("""
select
  categorie.id,
  categorie.descrizione,
  categorie.colore,
  categorie.icon_class,
  categorie.tipo,
  s.id sottocategoria_id,
  s.descrizione sottocategoria_desc
from categorie
  left outer join sottocategorie s on categorie.id = s.categoria_id
order by categorie.id
""")
    cursor.fetchall()
    categorie = []
    current_categoria_id = None
    for e in cursor:
        categoria_id = e["id"]
        if current_categoria_id is None or categoria_id != current_categoria_id:
            current_categoria_id = categoria_id
            # nuova categoria
            categoria = {
                "id": e["id"],
                "descrizione": e["descrizione"],
                "colore": e["colore"],
                "icon_class": e["icon_class"],
                "tipo": e["tipo"],
                "sottocategorie": []
            }
            categorie.append(categoria)
            if e["sottocategoria_id"]:
                sottocategoria = {
                    "id": e["sottocategoria_id"],
                    "categoria_id": e["id"],
                    "descrizione": e["sottocategoria_desc"]
                }
                categoria["sottocategorie"].append(sottocategoria)
        else:
            if e["sottocategoria_id"]:
                sottocategoria = {
                    "id": e["sottocategoria_id"],
                    "categoria_id": e["id"],
                    "descrizione": e["sottocategoria_desc"]
                }
                categoria["sottocategorie"].append(sottocategoria)

    return jsonify(categorie)


@app.route("/api/subcategories", methods=['POST'])
@jwt_required()
def update_subcategory():
    subcategory = request.get_json(force=True)
    cursor = mysql.connection.cursor()
    if subcategory["id"]:
        # update
        cursor.execute("""update sottocategorie set categoria_id=%s,
              descrizione=%s where id=%s
        """, [subcategory["categoria_id"], subcategory["descrizione"],
              subcategory["id"]])
    else:
        # insert
        cursor.execute("""insert into sottocategorie(categoria_id, descrizione)
                      values(%s,%s)
                """, [subcategory["categoria_id"], subcategory["descrizione"]])
        subcategory["id"] = cursor.lastrowid

    mysql.connection.commit()
    cursor.close()
    return jsonify(subcategory)

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
@jwt_required()
def get_tag_for_movimento(movimento_id):
    entries = load_tags_for_movimento(movimento_id)
    return jsonify([e for e in entries])


@app.route('/api/tag/<movimento_id>/<tag_value>', methods=['PUT'])
@jwt_required()
def add_tag(movimento_id, tag_value):
    cursor = mysql.connection.cursor()
    cursor.execute(
        'select id from tags where value = %s',
        [tag_value])
    tags = cursor.fetchall()
    if tags:
        tag_id = tags[0]['id']
    else:
        cursor.execute(
            'insert into tags(value, name) values (%s,%s)',
            [tag_value, tag_value])
        tag_id = cursor.lastrowid
    cursor.execute('insert into movimento_tags(movimento_id, tag_id) '
                   'values (%s,%s)',
                   [movimento_id, tag_id])
    mysql.connection.commit()
    cursor.close()
    return 'OK'


@app.route('/api/tag/<movimento_id>/<tag_value>', methods=['DELETE'])
@jwt_required()
def remove_tag(movimento_id, tag_value):
    cursor = mysql.connection.cursor()
    cursor.execute(
        'select id from tags where value = %s',
        [tag_value])
    tags = cursor.fetchall()
    if tags:
        tag_id = tags[0]['id']
        cursor.execute('delete from movimento_tags '
                       'where movimento_id = %s and tag_id = %s',
                       [movimento_id, tag_id])
        mysql.connection.commit()
        cursor.close()
    return 'OK'


@app.route('/api/regole', methods=['GET'])
def get_rules():
    cursor = mysql.connection.cursor()
    cursor.execute(
        'select id, category_id, subcategory_id, name from regole')
    rules = cursor.fetchall()
    for rule in rules:
        # get conditions
        cursor.execute(
            'select id, field, operator, value from regole_condizione '
            'where regola_id = %s', [rule["id"]])
        conditions = cursor.fetchall()
        rule["conditions"] = conditions
    return jsonify(rules)


@app.route('/api/regole', methods=['POST'])
@jwt_required()
def save_rule():
    rule = request.get_json(force=True)
    cursor = mysql.connection.cursor()
    if rule["id"]:
        cursor.execute(
            'update regole set category_id=%s, subcategory_id=%s, name=%s  '
            'where id = %s', [rule["category_id"], rule["subcategory_id"],
                              rule["name"], rule["id"]])

        cursor.execute(
            'delete from regole_condizione where regola_id = %s',
            [rule["id"]])

        for condition in rule["conditions"]:
            cursor.execute(
                'insert into '
                'regole_condizione(field, operator, value, regola_id ) '
                'value(%s, %s, %s, %s)', [condition["field"],
                                          condition["operator"],
                                          condition["value"],
                                          rule["id"]
                                          ])
        mysql.connection.commit()

    else:
        cursor.execute(
            'insert into regole(category_id, subcategory_id, name)  '
            'value(%s, %s, %s)', [rule["category_id"], rule["subcategory_id"],
                              rule["name"]])

        rule_id = cursor.lastrowid
        for condition in rule["conditions"]:
            cursor.execute(
                'insert into '
                'regole_condizione(field, operator, value, regola_id ) '
                'value(%s, %s, %s, %s)', [condition["field"],
                                          condition["operator"],
                                          condition["value"],
                                          rule_id
                                          ])
        mysql.connection.commit()
    cursor.close()

    return jsonify('OK')


@app.route('/api/regole/<conto_id>', methods=['PUT'])
@jwt_required()
def apply_rules(conto_id):
    cursor = mysql.connection.cursor()
    query = " select * from movimenti where conto_id = %s and ignored is FALSE"
    cursor.execute(query, [conto_id])
    movimenti_rows = cursor.fetchall()
    for row in movimenti_rows:
        movimento = Movimento()
        movimento.date = row["data_movimento"]
        movimento.type = row["tipo"]
        movimento.id = row["id"]
        movimento.description = row["descrizione"]
        movimento.amount = row["importo"]
        movimento.categoria_id, movimento.sottocategoria_id = assign_category(movimento)
        if movimento.categoria_id and (movimento.categoria_id != row["categoria_id"] or movimento.sottocategoria_id != row['sottocategoria_id']):
            update_q = 'update movimenti set categoria_id = %s, sottocategoria_id=%s where id = %s'
            cursor.execute(update_q, [movimento.categoria_id,movimento.sottocategoria_id, movimento.id])
    mysql.connection.commit()
    cursor.close()
    return jsonify('OK')


@app.route('/api/regole/<id_regola>', methods=['DELETE'])
@jwt_required()
def delete_rule(id_regola):
    if id_regola:
        cursor = mysql.connection.cursor()
        cursor.execute(
            'delete from regole_condizione '
            'where regola_id = %s', [id_regola])
        cursor.execute(
            'delete from regole '
            'where id = %s', [id_regola])
        mysql.connection.commit()
    return jsonify('OK')


if __name__ == "__main__":
    app.run(host='0.0.0.0')
