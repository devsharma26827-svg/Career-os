"""
JobPulse AI - Database Schema Migration System
Safely applies missing column migrations to existing SQLite databases
without dropping tables, recreating schemas, or losing existing user data.
"""
import logging
from sqlalchemy import text, Engine
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

def get_table_columns(connection, table_name: str) -> Dict[str, Dict[str, Any]]:
    """Retrieve column metadata for a given table in SQLite."""
    result = connection.execute(text(f"PRAGMA table_info({table_name});"))
    columns = {}
    for row in result.fetchall():
        # row: (cid, name, type, notnull, dflt_value, pk)
        columns[row[1]] = {
            "cid": row[0],
            "name": row[1],
            "type": row[2],
            "notnull": row[3],
            "default": row[4],
            "pk": row[5]
        }
    return columns

def table_exists(connection, table_name: str) -> bool:
    """Check if a table exists in the database."""
    res = connection.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name;"),
        {"table_name": table_name}
    ).fetchone()
    return res is not None

def apply_migrations(engine: Engine) -> Dict[str, List[str]]:
    """
    Applies required schema migrations idempotently.
    Adds missing columns with safe defaults while preserving all existing data.
    """
    changes_applied: Dict[str, List[str]] = {}

    with engine.begin() as conn:
        # 1. Migrate `users` table
        if table_exists(conn, "users"):
            user_cols = get_table_columns(conn, "users")
            user_changes = []

            # Check `reduced_motion`
            if "reduced_motion" not in user_cols:
                logger.info("Migrating users table: Adding missing column 'reduced_motion' (BOOLEAN NOT NULL DEFAULT 0)...")
                conn.execute(text("ALTER TABLE users ADD COLUMN reduced_motion BOOLEAN NOT NULL DEFAULT 0;"))
                user_changes.append("added reduced_motion BOOLEAN NOT NULL DEFAULT 0")

            # Check `font_size`
            if "font_size" not in user_cols:
                logger.info("Migrating users table: Adding missing column 'font_size'...")
                conn.execute(text("ALTER TABLE users ADD COLUMN font_size VARCHAR DEFAULT 'normal';"))
                user_changes.append("added font_size VARCHAR DEFAULT 'normal'")

            # Check `display_mode`
            if "display_mode" not in user_cols:
                logger.info("Migrating users table: Adding missing column 'display_mode'...")
                conn.execute(text("ALTER TABLE users ADD COLUMN display_mode VARCHAR DEFAULT 'simple';"))
                user_changes.append("added display_mode VARCHAR DEFAULT 'simple'")

            if user_changes:
                changes_applied["users"] = user_changes

        # 2. Migrate `application_workspaces` table (Module 4 columns)
        if table_exists(conn, "application_workspaces"):
            app_cols = get_table_columns(conn, "application_workspaces")
            app_changes = []

            workspace_columns_to_check = [
                ("application_destination", "VARCHAR DEFAULT 'manual_portal'"),
                ("application_status", "VARCHAR DEFAULT 'not_started'"),
                ("application_confirmation_id", "VARCHAR"),
                ("application_confirmation_message", "TEXT"),
                ("application_submitted_at", "DATETIME"),
                ("application_error", "TEXT"),
                ("email_outreach_status", "VARCHAR DEFAULT 'not_started'"),
                ("email_sent_at", "DATETIME"),
                ("email_error", "TEXT"),
                ("screening_answers", "TEXT DEFAULT '{}'"),
                ("idempotency_key", "VARCHAR"),
                ("user_consent_granted", "BOOLEAN DEFAULT 0"),
                ("consent_timestamp", "DATETIME")
            ]

            for col_name, col_def in workspace_columns_to_check:
                if col_name not in app_cols:
                    logger.info(f"Migrating application_workspaces table: Adding column '{col_name}'...")
                    conn.execute(text(f"ALTER TABLE application_workspaces ADD COLUMN {col_name} {col_def};"))
                    app_changes.append(f"added {col_name} {col_def}")

            if app_changes:
                changes_applied["application_workspaces"] = app_changes

        # 3. Migrate `user_profiles` table (confidence & evidence tracking)
        if table_exists(conn, "user_profiles"):
            profile_cols = get_table_columns(conn, "user_profiles")
            profile_changes = []

            profile_columns_to_check = [
                ("confidence_scores", "TEXT DEFAULT '{}'"),
                ("uncertain_fields", "TEXT DEFAULT '[]'"),
                ("field_evidence", "TEXT DEFAULT '{}'")
            ]

            for col_name, col_def in profile_columns_to_check:
                if col_name not in profile_cols:
                    logger.info(f"Migrating user_profiles table: Adding column '{col_name}'...")
                    conn.execute(text(f"ALTER TABLE user_profiles ADD COLUMN {col_name} {col_def};"))
                    profile_changes.append(f"added {col_name} {col_def}")

            if profile_changes:
                changes_applied["user_profiles"] = profile_changes

        # 4. Migrate and re-normalize existing cached job listings
        if table_exists(conn, "job_listings"):
            job_cols = get_table_columns(conn, "job_listings")
            job_changes = []

            job_columns_to_check = [
                ("source_listing_url", "VARCHAR"),
                ("application_url", "VARCHAR"),
                ("company_website_url", "VARCHAR"),
                ("last_verified_at", "DATETIME")
            ]

            for col_name, col_def in job_columns_to_check:
                if col_name not in job_cols:
                    logger.info(f"Migrating job_listings table: Adding column '{col_name}'...")
                    conn.execute(text(f"ALTER TABLE job_listings ADD COLUMN {col_name} {col_def};"))
                    job_changes.append(f"added {col_name} {col_def}")

            # Backfill source_listing_url & application_url from url where null
            conn.execute(text("UPDATE job_listings SET source_listing_url = url WHERE source_listing_url IS NULL;"))
            conn.execute(text("UPDATE job_listings SET application_url = url WHERE application_url IS NULL AND source_name != 'jobicy';"))

            from app.core.locations import normalize_job_location
            jobs_result = conn.execute(text("SELECT id, location, country, is_remote FROM job_listings;")).fetchall()
            normalized_count = 0
            for row in jobs_result:
                j_id, j_loc, j_country, j_is_remote = row
                norm = normalize_job_location(raw_location=j_loc or "", raw_country=j_country, raw_is_remote=bool(j_is_remote))
                if norm["country"] != j_country or norm["state"] or norm["city"]:
                    conn.execute(
                        text("UPDATE job_listings SET country=:country, state=:state, city=:city WHERE id=:id;"),
                        {"country": norm["country"], "state": norm["state"], "city": norm["city"], "id": j_id}
                    )
                    normalized_count += 1
            if normalized_count > 0:
                changes_applied["job_listings"] = [f"re-normalized {normalized_count} job locations"]

            # Ensure mock/demo records are deactivated from live search without deleting application history
            conn.execute(text("UPDATE job_listings SET is_active=0 WHERE source_name='official_feed' OR url LIKE '%example.com%';"))

        # 5. Create indices if needed
        if table_exists(conn, "application_workspaces"):
            app_cols = get_table_columns(conn, "application_workspaces")
            if "application_status" in app_cols:
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_app_workspaces_app_status ON application_workspaces (application_status);"))
            if "email_outreach_status" in app_cols:
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_app_workspaces_email_status ON application_workspaces (email_outreach_status);"))

    return changes_applied
