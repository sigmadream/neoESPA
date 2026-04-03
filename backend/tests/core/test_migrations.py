from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from app.core.migrations import apply_migrations, get_applied_versions


def test_upgrade_creates_expected_tables(tmp_path: Path):
    database_path = tmp_path / "migration-test.sqlite"
    engine = create_engine(f"sqlite:///{database_path}")

    apply_migrations(engine)

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    assert {
        "schema_migrations",
        "users",
        "homework",
        "notice",
        "submissions",
        "submission_files",
        "submission_results",
        "submission_case_results",
        "grading_rules",
        "system_settings",
    }.issubset(table_names)
    assert "0001_submission_core" in get_applied_versions(engine)


def test_upgrade_backfills_missing_user_timestamps(tmp_path: Path):
    database_path = tmp_path / "legacy-users.sqlite"
    engine = create_engine(f"sqlite:///{database_path}")

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE users (
                    id TEXT PRIMARY KEY,
                    sid INTEGER UNIQUE,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    email TEXT NOT NULL,
                    user_group TEXT NOT NULL,
                    ps TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO users (
                    id, sid, name, phone, email, user_group, ps, is_active, created_at, updated_at
                ) VALUES (
                    'legacy-user',
                    20256001,
                    'Legacy User',
                    '010-9999-0001',
                    'legacy-user@example.com',
                    'student',
                    'hashed-password',
                    1,
                    NULL,
                    NULL
                )
                """
            )
        )

    apply_migrations(engine)

    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT created_at, updated_at
                FROM users
                WHERE id = 'legacy-user'
                """
            )
        ).one()

    assert row[0] is not None
    assert row[1] is not None
    assert "0004_user_timestamp_backfill" in get_applied_versions(engine)
