"""
Unit tests for JobPulse AI SQLite schema migration engine.
Verifies that:
1. Missing columns (reduced_motion, application_destination, etc.) are added safely.
2. Existing rows are preserved without data corruption or loss.
3. Migrations are idempotent (can be run repeatedly without errors).
"""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from app.core.migrations import apply_migrations, get_table_columns

def test_migration_adds_reduced_motion_and_preserves_data():
    # 1. Create a simulated legacy SQLite database lacking reduced_motion
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                email VARCHAR NOT NULL UNIQUE,
                hashed_password VARCHAR NOT NULL,
                full_name VARCHAR,
                is_active BOOLEAN DEFAULT 1,
                font_size VARCHAR DEFAULT 'normal',
                display_mode VARCHAR DEFAULT 'simple'
            );
        """))
        # Seed an existing user
        conn.execute(text("""
            INSERT INTO users (id, email, hashed_password, full_name, is_active)
            VALUES (1, 'legacy_user@example.com', 'hashed_pass_xyz', 'Legacy User', 1);
        """))

    # 2. Run migration
    changes = apply_migrations(engine)
    assert "users" in changes
    assert any("reduced_motion" in c for c in changes["users"])

    # 3. Verify columns and data integrity
    with engine.begin() as conn:
        cols = get_table_columns(conn, "users")
        assert "reduced_motion" in cols
        assert cols["reduced_motion"]["notnull"] == 1
        assert cols["reduced_motion"]["default"] == "0"

        # Verify existing user is preserved with default reduced_motion = 0
        user_row = conn.execute(text("SELECT id, email, full_name, reduced_motion FROM users WHERE id = 1;")).fetchone()
        assert user_row is not None
        assert user_row[0] == 1
        assert user_row[1] == "legacy_user@example.com"
        assert user_row[2] == "Legacy User"
        assert user_row[3] == 0  # Default value applied to existing row

    # 4. Verify idempotency: running migration a second time produces no changes and no errors
    second_run_changes = apply_migrations(engine)
    assert "users" not in second_run_changes or len(second_run_changes["users"]) == 0


def test_migration_adds_user_profiles_confidence_columns():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE user_profiles (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE,
                full_name VARCHAR,
                skills TEXT DEFAULT '[]',
                experiences TEXT DEFAULT '[]',
                education TEXT DEFAULT '[]'
            );
        """))
        conn.execute(text("""
            INSERT INTO user_profiles (id, user_id, full_name)
            VALUES (1, 10, 'Existing Engineer');
        """))

    changes = apply_migrations(engine)
    assert "user_profiles" in changes
    assert any("confidence_scores" in c for c in changes["user_profiles"])
    assert any("uncertain_fields" in c for c in changes["user_profiles"])
    assert any("field_evidence" in c for c in changes["user_profiles"])

    with engine.begin() as conn:
        cols = get_table_columns(conn, "user_profiles")
        assert "confidence_scores" in cols
        assert "uncertain_fields" in cols
        assert "field_evidence" in cols

        # Check existing row preserved
        row = conn.execute(text("SELECT id, full_name, confidence_scores FROM user_profiles WHERE id = 1;")).fetchone()
        assert row is not None
        assert row[0] == 1
        assert row[1] == "Existing Engineer"

