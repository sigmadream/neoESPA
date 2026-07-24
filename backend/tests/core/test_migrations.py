from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from app.core.migrations import (
    apply_migrations,
    get_applied_versions,
)
from app.migrations import MIGRATIONS

EXPECTED_TABLES = {
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
    "code_snapshots",
    "exams",
    "exam_submissions",
    "collab_sessions",
    "collab_participants",
    "collab_messages",
    "collab_code_snapshots",
    "lecture_materials",
    "material_comments",
    "qa_posts",
    "qa_answers",
}


def assert_latest_tables(engine) -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    assert EXPECTED_TABLES.issubset(table_names)


def assert_all_migrations_applied(engine) -> None:
    applied_versions = get_applied_versions(engine)
    assert applied_versions == {version for version, _ in MIGRATIONS}



def test_upgrade_creates_expected_tables(tmp_path: Path):
    database_path = tmp_path / "migration-test.sqlite"
    engine = create_engine(f"sqlite:///{database_path}")

    apply_migrations(engine)

    assert_latest_tables(engine)
    assert "0001_submission_core" in get_applied_versions(engine)
    assert "0003_platform_extensions" in get_applied_versions(engine)



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



def test_upgrade_is_idempotent(tmp_path: Path):
    database_path = tmp_path / "migration-idempotent.sqlite"
    engine = create_engine(f"sqlite:///{database_path}")

    apply_migrations(engine)
    first_versions = get_applied_versions(engine)

    apply_migrations(engine)
    second_versions = get_applied_versions(engine)

    with engine.connect() as connection:
        migration_rows = connection.execute(
            text("SELECT version FROM schema_migrations ORDER BY version")
        ).all()

    assert first_versions == second_versions
    assert len(migration_rows) == len(MIGRATIONS)
    assert {row[0] for row in migration_rows} == {version for version, _ in MIGRATIONS}
    assert_all_migrations_applied(engine)



def test_upgrade_adds_board_columns_to_legacy_lecture_materials(tmp_path: Path):
    database_path = tmp_path / "legacy-materials.sqlite"
    engine = create_engine(f"sqlite:///{database_path}")

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE lecture_materials (
                    id INTEGER PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    description TEXT NOT NULL,
                    url VARCHAR(500) NOT NULL,
                    is_published INTEGER NOT NULL DEFAULT 1,
                    created_by TEXT NOT NULL,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
        )

    apply_migrations(engine)

    inspector = inspect(engine)
    material_columns = {
        column["name"] for column in inspector.get_columns("lecture_materials")
    }
    table_names = set(inspector.get_table_names())

    assert {"content", "attachment_name", "attachment_relpath"}.issubset(material_columns)
    assert {"material_comments", "qa_posts", "qa_answers"}.issubset(table_names)
    assert "0005_materials_board_and_qa" in get_applied_versions(engine)