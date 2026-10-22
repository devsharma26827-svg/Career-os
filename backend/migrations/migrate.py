"""
JobPulse AI - Database Migration Runner
Applies schema migrations to target SQLite database.
Preserves existing data and adds missing columns safely.
"""
import os
import sys

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import create_engine
from app.core.database import Base, engine
from app.core.migrations import apply_migrations
import app.models  # Populate Base.metadata

def run_migrations(target_engine=None):
    eng = target_engine or engine
    print(f"[*] Applying schema migrations to: {eng.url}")
    # 1. Ensure all defined tables exist
    Base.metadata.create_all(bind=eng)
    # 2. Add any missing columns to existing tables safely
    changes = apply_migrations(eng)
    if changes:
        print("[*] Migration changes applied:")
        for table, cols in changes.items():
            print(f"    - Table '{table}':")
            for c in cols:
                print(f"        * {c}")
    else:
        print("[*] Database schema is already up to date. No changes needed.")
    return changes

if __name__ == "__main__":
    run_migrations()
