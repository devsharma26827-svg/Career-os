import os
import sys
import sqlite3

# Add backend to path so we can import all models
sys.path.insert(0, os.path.abspath("backend"))

from app.core.database import Base
# Import all models to populate Base.metadata
import app.models

print(f"Loaded {len(Base.metadata.tables)} models in Base.metadata:")
for table_name in Base.metadata.tables:
    print(f" - {table_name}")

db_paths = [
    os.path.abspath("backend/sql_app.db"),
    os.path.abspath("sql_app.db")
]

for db_path in db_paths:
    print(f"\n==========================================")
    print(f"COMPARING WITH DB: {db_path}")
    print(f"==========================================")
    if not os.path.exists(db_path):
        print("DB file does not exist.")
        continue
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    existing_tables = set(t[0] for t in cur.fetchall())

    for table_name, table_obj in Base.metadata.tables.items():
        if table_name not in existing_tables:
            print(f"[MISSING TABLE] {table_name} does not exist in DB!")
            continue
        cur.execute(f"PRAGMA table_info({table_name});")
        db_cols = {row[1]: row for row in cur.fetchall()}
        model_cols = {c.name: c for c in table_obj.columns}

        missing_in_db = [c for c in model_cols if c not in db_cols]
        extra_in_db = [c for c in db_cols if c not in model_cols]

        if missing_in_db:
            print(f"[MISSING COLUMNS in {table_name}]: {missing_in_db}")
            for c_name in missing_in_db:
                c_obj = model_cols[c_name]
                print(f"    Column {c_name}: type={c_obj.type}, default={c_obj.default}, nullable={c_obj.nullable}")
        if extra_in_db:
            print(f"[EXTRA COLUMNS in DB for {table_name}]: {extra_in_db}")
        if not missing_in_db and not extra_in_db:
            print(f"[OK] {table_name}: all {len(model_cols)} columns match.")

    conn.close()
