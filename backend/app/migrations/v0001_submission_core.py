from sqlalchemy import text
from sqlmodel import SQLModel

VERSION = "0001_submission_core"

EXISTING_TABLE_COLUMNS = {
    "users": {
        "is_active": "INTEGER NOT NULL DEFAULT 1",
        "created_at": "TEXT",
        "updated_at": "TEXT",
    },
    "homework": {
        "filename": "TEXT",
        "ratedatanum": "INTEGER NOT NULL DEFAULT 0",
        "sec": "INTEGER NOT NULL DEFAULT 1",
        "sbnum": "INTEGER NOT NULL DEFAULT 10",
        "starttime": "TEXT",
        "isDetected": "INTEGER NOT NULL DEFAULT 0",
        "vitalSpace": "INTEGER NOT NULL DEFAULT 0",
        "disorderedOutput": "INTEGER NOT NULL DEFAULT 0",
        "isLint": "INTEGER NOT NULL DEFAULT 0",
        "created_at": "TEXT",
        "updated_at": "TEXT",
    },
    "notice": {
        "is_pinned": "INTEGER NOT NULL DEFAULT 0",
        "is_published": "INTEGER NOT NULL DEFAULT 1",
        "updated_at": "TEXT",
    },
}


def _table_exists(connection, table_name: str) -> bool:
    row = connection.execute(
        text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = :table_name"
        ),
        {"table_name": table_name},
    ).first()
    return row is not None


def _existing_columns(connection, table_name: str) -> set[str]:
    if not _table_exists(connection, table_name):
        return set()

    rows = connection.execute(text(f"PRAGMA table_info('{table_name}')")).all()
    return {row[1] for row in rows}


def _ensure_columns(
    connection, table_name: str, columns: dict[str, str]
) -> None:
    if not _table_exists(connection, table_name):
        return

    existing = _existing_columns(connection, table_name)
    for column_name, definition in columns.items():
        if column_name in existing:
            continue
        connection.execute(
            text(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
            )
        )


def upgrade(engine) -> None:
    with engine.begin() as connection:
        for table_name, columns in EXISTING_TABLE_COLUMNS.items():
            _ensure_columns(connection, table_name, columns)

    SQLModel.metadata.create_all(engine)
