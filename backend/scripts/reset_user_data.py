"""
JobPulse AI - User Data Reset Script
Safely purges all user accounts, profiles, preferences, uploaded resumes,
saved jobs, applications, and audit logs while preserving public job listings
and database schema.

Requires `--confirm` flag to execute destructive actions.
"""

import os
import sys
import argparse
import shutil
from typing import Dict

# Ensure backend root is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import text
from app.core.database import engine, SessionLocal


# Tables to be cleared in dependency order (children first)
USER_DATA_TABLES = [
    "application_audit_logs",
    "application_workspaces",
    "batch_application_sessions",
    "recruiter_contacts",
    "saved_jobs",
    "notifications",
    "notification_preferences",
    "search_preferences",
    "resumes",
    "user_profiles",
    "users",
]

PRESERVED_TABLES = [
    "job_listings",
]


def get_table_counts() -> Dict[str, int]:
    """Retrieve row counts for all application tables."""
    counts = {}
    with SessionLocal() as db:
        all_tables = USER_DATA_TABLES + PRESERVED_TABLES
        for table in all_tables:
            try:
                res = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                counts[table] = int(res) if res is not None else 0
            except Exception:
                counts[table] = 0
    return counts


def purge_user_upload_files(uploads_dir: str, dry_run: bool = False) -> int:
    """
    Remove all user resume subdirectories in backend/uploads/resumes
    while preserving the base directory and leaving a .gitkeep.
    """
    resumes_dir = os.path.join(uploads_dir, "resumes")
    removed_count = 0

    if not os.path.exists(resumes_dir):
        os.makedirs(resumes_dir, exist_ok=True)
        gitkeep_path = os.path.join(resumes_dir, ".gitkeep")
        if not os.path.exists(gitkeep_path) and not dry_run:
            with open(gitkeep_path, "w") as f:
                f.write("")
        return 0

    for item in os.listdir(resumes_dir):
        if item == ".gitkeep":
            continue
        item_path = os.path.join(resumes_dir, item)
        if dry_run:
            print(f"[DRY-RUN] Would remove upload artifact: {item_path}")
            removed_count += 1
        else:
            if os.path.isdir(item_path):
                shutil.rmtree(item_path, ignore_errors=True)
                removed_count += 1
            else:
                os.remove(item_path)
                removed_count += 1

    if not dry_run:
        gitkeep_path = os.path.join(resumes_dir, ".gitkeep")
        if not os.path.exists(gitkeep_path):
            with open(gitkeep_path, "w") as f:
                f.write("")

    return removed_count


def execute_reset(dry_run: bool = False) -> None:
    print("=" * 60)
    print("   JobPulse AI - User Data Reset Utility")
    print("=" * 60)
    print(f"Target Database Engine: {engine.name}")
    print(f"Target Database URL:    {engine.url}")
    print(f"Execution Mode:         {'DRY-RUN' if dry_run else 'DESTRUCTIVE RESET'}")
    print("-" * 60)

    # 1. Inspect initial state
    before_counts = get_table_counts()
    print("\n[Current Table Counts]")
    for table, count in before_counts.items():
        tag = "[PRESERVE]" if table in PRESERVED_TABLES else "[PURGE]"
        print(f"  {tag:<12} {table:<30}: {count} rows")

    uploads_dir = os.path.join(BACKEND_DIR, "uploads")
    print(f"\nUploads Directory: {uploads_dir}")

    if dry_run:
        print("\n[DRY-RUN] Simulated cleanup:")
        for table in USER_DATA_TABLES:
            print(f"  Would execute: DELETE FROM {table};")
        purge_user_upload_files(uploads_dir, dry_run=True)
        print("\nDry run completed. No data was deleted.")
        return

    # 2. Execute deletion
    print("\nExecuting purge of user tables...")
    with SessionLocal() as db:
        # For SQLite, enable foreign keys or handle explicitly
        if engine.name == "sqlite":
            db.execute(text("PRAGMA foreign_keys = OFF;"))

        for table in USER_DATA_TABLES:
            deleted = db.execute(text(f"DELETE FROM {table}"))
            print(f"  Cleaned {table:<28} (deleted {deleted.rowcount if hasattr(deleted, 'rowcount') else 'all'} rows)")

        if engine.name == "sqlite":
            db.execute(text("PRAGMA foreign_keys = ON;"))

        db.commit()

    # 3. Clean uploaded resume files
    print("\nPurging user uploaded resume files...")
    removed_files = purge_user_upload_files(uploads_dir, dry_run=False)
    print(f"  Removed {removed_files} user upload items. .gitkeep preserved.")

    # 4. Verify post-reset state
    after_counts = get_table_counts()
    print("\n[Post-Reset Table Counts]")
    all_zero = True
    for table in USER_DATA_TABLES:
        count = after_counts.get(table, 0)
        status = "OK (0)" if count == 0 else f"FAILED ({count})"
        if count != 0:
            all_zero = False
        print(f"  {table:<30}: {status}")

    print("\n[Preserved Tables]")
    for table in PRESERVED_TABLES:
        print(f"  {table:<30}: {after_counts.get(table, 0)} rows (Retained)")

    print("-" * 60)
    if all_zero:
        print("SUCCESS: All user data successfully purged. Fresh state established.")
    else:
        print("WARNING: Some user tables still have records. Review foreign keys.")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Purge all user accounts, profiles, resumes, and application records from JobPulse AI."
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Explicitly confirm destructive deletion of all user records.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without modifying data.",
    )

    args = parser.parse_args()

    if not args.confirm and not args.dry_run:
        print("\nERROR: Destructive operation requires explicit confirmation.")
        print("Usage: python backend/scripts/reset_user_data.py --confirm")
        print("       python backend/scripts/reset_user_data.py --dry-run\n")
        sys.exit(1)

    execute_reset(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
