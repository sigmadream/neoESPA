from sqlalchemy import text

VERSION = "0002_submission_adjustments"

SUBMISSION_RESULT_COLUMNS = {
    "manual_total_score": "REAL",
    "adjustment_note": "TEXT",
    "adjusted_at": "TEXT",
    "adjusted_by": "TEXT",
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


def upgrade(engine) -> None:
    with engine.begin() as connection:
        if not _table_exists(connection, "submission_results"):
            return

        existing_columns = _existing_columns(connection, "submission_results")
        for column_name, definition in SUBMISSION_RESULT_COLUMNS.items():
            if column_name in existing_columns:
                continue
            connection.execute(
                text(
                    f"ALTER TABLE submission_results ADD COLUMN {column_name} {definition}"
                )
            )
