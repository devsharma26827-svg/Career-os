import sqlite3
import os

db_paths = [
    os.path.abspath("backend/sql_app.db"),
    os.path.abspath("sql_app.db")
]

for db_path in db_paths:
    print(f"\n==========================================")
    print(f"DATABASE: {db_path}")
    print(f"==========================================")
    if not os.path.exists(db_path):
        print("Does not exist.")
        continue
    print(f"Size: {os.path.getsize(db_path)} bytes")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cur.fetchall()]
    print(f"Tables ({len(tables)}): {tables}")
    
    for table in tables:
        if table.startswith("sqlite_"):
            continue
        cur.execute(f"PRAGMA table_info({table});")
        cols = cur.fetchall()
        cur.execute(f"SELECT count(*) FROM {table};")
        count = cur.fetchone()[0]
        col_names = [c[1] for c in cols]
        print(f"Table: {table} -> {count} rows")
        if table == "users":
            print(f"  Columns: {col_names}")
            cur.execute("SELECT id, email, full_name, is_active FROM users LIMIT 5;")
            user_rows = cur.fetchall()
            print(f"  Sample users: {user_rows}")

    conn.close()
