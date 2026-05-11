import os, psycopg2, uvicorn, webbrowser

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join('..', '.env'))

app = FastAPI()


DB_CONFIG = {
    'dbname': os.getenv('DB_SLAVE_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_SLAVE_HOST'),
    'port': os.getenv('DB_SLAVE_PORT')
}


def get_db():
    conn = psycopg2.connect(**DB_CONFIG)
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


@app.get('/api/stats')
def get_stats():
    conn = get_db()
    cur = conn.cursor()

    cur.execute('SELECT COUNT(*) FROM "user"')
    total_users = cur.fetchone()[0]

    cur.execute('SELECT COUNT(*) FROM item')
    total_items = cur.fetchone()[0]

    cur.execute('SELECT COUNT(*) FROM orders')
    total_orders = cur.fetchone()[0]

    conn.close()

    return JSONResponse({
        "total_users": total_users,
        "total_items": total_items,
        "total_orders": total_orders
    })


@app.get('/api/users')
def get_users():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT id, username, email, is_admin, created_at FROM "user"')
    rows = fetchall(cur)
    conn.close()
    return JSONResponse(rows)


@app.get('/api/orders')
def get_orders():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        'SELECT orders.id, "user".username, item.title, orders.status, orders.created_at FROM orders JOIN "user" ON orders.user_id = "user".id JOIN item ON orders.item_id = item.id'
    )
    rows = fetchall(cur)
    conn.close()
    return JSONResponse(rows)


if __name__ == '__main__':
    webbrowser.open('http://127.0.0.1:8000/api/stats')
    uvicorn.run(app, host='127.0.0.1', port=8000)