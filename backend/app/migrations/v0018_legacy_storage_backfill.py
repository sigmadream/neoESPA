from sqlalchemy import inspect, text
from sqlmodel import SQLModel

VERSION = "0018_legacy_storage_backfill"


def upgrade(engine) -> None:
    inspector = inspect(engine)
    additions = {
        "storage_sha256": "VARCHAR(64)",
        "legacy_storage_path": "VARCHAR(500)",
        "legacy_storage_status": "VARCHAR(20)",
    }
    with engine.begin() as connection:
        for table in ("submissions", "submission_files"):
            if not inspector.has_table(table):
                continue
            columns = {item["name"] for item in inspector.get_columns(table)}
            for name, definition in additions.items():
                if name not in columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE {table} ADD COLUMN {name} {definition}"
                        )
                    )
    SQLModel.metadata.create_all(engine)
