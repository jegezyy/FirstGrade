import uuid, os, json, re, jwt, psycopg2, psycopg2.extras

from flask import Flask, render_template, request, redirect, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from flask import jsonify
from datetime import datetime, timedelta, timezone
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
JWT_SECRET = os.getenv("JWT_SECRET")


DB_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}


def get_db():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    return conn


def fetchone(cur):
    row = cur.fetchone()
    if row is None:
        return None
    cols = [desc[0] for desc in cur.description]
    return dict(zip(cols, row))


def fetchall(cur):
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    return [dict(zip(cols, row)) for row in rows]


def get_current_user():
    token = request.cookies.get('jwt_token')
    if not token:
        return None
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT * FROM "user" WHERE id = %s', (data['user_id'],))
        row = fetchone(cur)
        conn.close()
        return row
    except:
        return None


def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return redirect('/login')
        if user['is_admin'] != 1:
            return redirect('/index')
        return f(*args, **kwargs)
    return decorated


def create_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.now(timezone.utc) + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')


def validate_password(password):
    errors = []
    if len(password) < 8:
        errors.append('• минимум 8 символов')
    if not re.search(r'[A-Z]', password):
        errors.append('• хотя бы одна заглавная буква')
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>/?]', password):
        errors.append('• хотя бы один специальный символ')
    if errors:
        return 'Пароль должен содержать:\n' + '\n'.join(errors)
    return None


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS item (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            price INTEGER NOT NULL,
            type TEXT,
            condition TEXT,
            description TEXT NOT NULL,
            number TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active'
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS "user" (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            is_admin INTEGER NOT NULL DEFAULT 0,
            uuid TEXT UNIQUE,
            created_at TEXT NOT NULL
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES "user"(id),
            FOREIGN KEY (item_id) REFERENCES item(id)
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS hash_log (
            id SERIAL PRIMARY KEY,
            request TEXT NOT NULL,
            result TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


@app.route('/')
@app.route('/index')
def index():
    type_filter = request.args.get('type')
    condition_filter = request.args.get('condition')
    sort = request.args.get('sort')

    sql = "SELECT * FROM item WHERE status = 'active'"
    params = []

    if type_filter:
        sql += " AND type = %s"
        params.append(type_filter)
    if condition_filter:
        sql += " AND condition = %s"
        params.append(condition_filter)
    if sort == 'price_asc':
        sql += " ORDER BY price ASC"
    elif sort == 'price_desc':
        sql += " ORDER BY price DESC"

    conn = get_db()
    cur = conn.cursor()
    cur.execute(sql, params)
    data = fetchall(cur)
    conn.close()

    return render_template('index.html', data=data)


@app.route('/state')
def state():
    return render_template('state.html')


@app.route('/api/about')
def api_about():
    with open('instance/about.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(data)


@app.route('/create', methods=['POST', 'GET'])
@admin_required
def create():
    if request.method == 'POST':
        title = request.form['title'].strip()
        price = request.form['price'].strip()
        type_ = request.form['type']
        condition = request.form['condition']
        description = request.form['description'].strip()
        number = request.form['number'].strip()

        if not title or not price or not description or not number:
            return render_template('create.html', error='Все поля должны быть заполнены')

        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO item (title, price, type, condition, description, number) VALUES (%s, %s, %s, %s, %s, %s)",
                (title, price, type_, condition, description, number)
            )
            conn.commit()
            conn.close()
            return redirect('/index')
        except Exception as e:
            return f"Ошибка: {e}"
    else:
        return render_template('create.html')


@app.route('/edit/<int:id>', methods=['POST', 'GET'])
@admin_required
def edit(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM item WHERE id = %s", (id,))
    item = fetchone(cur)
    conn.close()

    if request.method == 'POST':
        title = request.form['title'].strip()
        price = request.form['price'].strip()
        type_ = request.form['type']
        condition = request.form['condition']
        description = request.form['description'].strip()
        number = request.form['number'].strip()

        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                "UPDATE item SET title=%s, price=%s, type=%s, condition=%s, description=%s, number=%s WHERE id=%s",
                (title, price, type_, condition, description, number, id)
            )
            conn.commit()
            conn.close()
            return redirect('/index')
        except Exception as e:
            return f"Ошибка: {e}"
    else:
        return render_template('edit.html', item=item)


@app.route('/delete/<int:id>')
@admin_required
def delete(id):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM item WHERE id = %s", (id,))
        conn.commit()
        conn.close()
        return redirect('/index')
    except Exception as e:
        return f"Ошибка: {e}"


@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password2 = request.form['password2']

        if password != password2:
            return render_template('register.html', error='Пароли не совпадают')

        error = validate_password(password)
        if error:
            return render_template('register.html', error=error)

        hashed_password = generate_password_hash(password)
        user_uuid = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                'INSERT INTO "user" (username, email, password, is_admin, uuid, created_at) VALUES (%s, %s, %s, %s, %s, %s)',
                (username, email, hashed_password, 0, user_uuid, created_at)
            )
            conn.commit()
            conn.close()
            return redirect('/login')
        except Exception:
            return render_template('register.html', error='Логин или Email уже занят')
    else:
        return render_template('register.html')


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        login_input = request.form['login']
        password = request.form['password']

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            'SELECT * FROM "user" WHERE email = %s OR username = %s',
            (login_input, login_input)
        )
        row = fetchone(cur)
        conn.close()

        if row and check_password_hash(row['password'], password):
            token = create_token(row['id'])
            response = make_response(redirect('/index'))
            response.set_cookie('jwt_token', token, httponly=True, max_age=7*24*60*60)
            return response
        else:
            return render_template('login.html', error='Неверный логин или пароль')
    else:
        return render_template('login.html')


@app.route('/logout')
def logout():
    response = make_response(redirect('/index'))
    response.delete_cookie('jwt_token')
    return response


@app.route('/api/hash/<string:text>')
def hash_string(text):
    hashed = generate_password_hash(text)
    created_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO hash_log (request, result, created_at) VALUES (%s, %s, %s)",
        (text, hashed, created_at)
    )
    conn.commit()
    conn.close()

    return jsonify({"request": text, "result": hashed})


@app.route('/profile/<username>')
@jwt_required
def profile(username):
    token = request.cookies.get('jwt_token')
    data = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])

    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT * FROM "user" WHERE id = %s', (data['user_id'],))
    current = fetchone(cur)
    cur.execute('SELECT * FROM "user" WHERE username = %s', (username,))
    row = fetchone(cur)
    conn.close()

    if not row:
        return "Пользователь не найден", 404
    if current['username'] != username and current['is_admin'] != 1:
        return redirect('/index')

    return render_template('profile.html', user=row)


@app.route('/profile/<username>/refresh_token')
@jwt_required
def refresh_token(username):
    token = request.cookies.get('jwt_token')
    data = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])

    new_token = create_token(data['user_id'])
    response = make_response(redirect(f'/profile/{username}'))
    response.set_cookie('jwt_token', new_token, httponly=True, max_age=7*24*60*60)
    return response


@app.route('/buy/<int:item_id>')
@jwt_required
def buy(item_id):
    token = request.cookies.get('jwt_token')
    data = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM orders WHERE user_id = %s AND item_id = %s",
        (data['user_id'], item_id)
    )
    existing = fetchone(cur)

    if existing:
        conn.close()
        return redirect('/index?error=already_bought')

    created_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    cur.execute(
        "INSERT INTO orders (user_id, item_id, status, created_at) VALUES (%s, %s, %s, %s)",
        (data['user_id'], item_id, 'pending', created_at)
    )
    cur.execute("UPDATE item SET status = 'sold' WHERE id = %s", (item_id,))
    conn.commit()
    conn.close()

    return redirect('/orders')


@app.route('/orders')
@jwt_required
def orders():
    token = request.cookies.get('jwt_token')
    data = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT orders.id, item.title, item.price, orders.status, orders.created_at FROM orders JOIN item ON orders.item_id = item.id WHERE orders.user_id = %s",
        (data['user_id'],)
    )
    data_orders = fetchall(cur)
    conn.close()

    return render_template('orders.html', orders=data_orders)


@app.route('/admin/orders')
@admin_required
def admin_orders():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        'SELECT orders.id, "user".username, item.title, orders.status, orders.created_at FROM orders JOIN "user" ON orders.user_id = "user".id JOIN item ON orders.item_id = item.id'
    )
    data = fetchall(cur)
    conn.close()
    return render_template('admin_orders.html', orders=data)


@app.route('/order/<int:order_id>/status/<string:status>')
@admin_required
def change_order_status(order_id, status):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status = %s WHERE id = %s", (status, order_id))
    conn.commit()
    conn.close()
    return redirect('/admin/orders')


@app.route('/dashboard')
@admin_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/api/dashboard')
@admin_required
def api_dashboard():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT status, COUNT(*) as count FROM orders GROUP BY status")
    orders_by_status = fetchall(cur)

    cur.execute("SELECT type, COUNT(*) as count FROM item GROUP BY type")
    items_by_type = fetchall(cur)

    cur.execute("SELECT DATE(created_at) as date, COUNT(*) as count FROM orders GROUP BY DATE(created_at) ORDER BY date")
    orders_by_date = fetchall(cur)

    conn.close()

    status_map = {'pending': 'В обработке', 'paid': 'Оплачен', 'delivered': 'Доставлен'}
    return app.response_class(
        response=json.dumps({
            'orders_by_status': [{'status': status_map.get(r['status'], r['status']), 'count': r['count']} for r in orders_by_status],
            'items_by_type': [{'type': r['type'], 'count': r['count']} for r in items_by_type],
            'orders_by_date': [{'date': str(r['date']), 'count': r['count']} for r in orders_by_date]
        }, ensure_ascii=False),
        mimetype='application/json'
    )


@app.context_processor
def inject_user():
    user = get_current_user()
    return {'current_user': user}


if __name__ == '__main__':
    init_db()
    app.run(debug=True)