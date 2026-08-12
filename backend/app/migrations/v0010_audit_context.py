from sqlalchemy import inspect, text
from sqlmodel import SQLModel

VERSION = "0010_audit_context"

COLUMNS = {
    "result": "VARCHAR(20) NOT NULL DEFAULT 'success'",
    "request_id": "VARCHAR(80)",
    "job_id": "INTEGER REFERENCES judge_jobs(id)",
    "before_json": "TEXT",
    "after_json": "TEXT",
}


def upgrade(engine) -> None:
    inspector = inspect(engine)
    if inspector.has_table("audit_logs"):
        existing = {
            column["name"] for column in inspector.get_columns("audit_logs")
        }
        with engine.begin() as connection:
            for name, definition in COLUMNS.items():
                if name not in existing:
                    connection.execute(
                        text(
                            f"ALTER TABLE audit_logs ADD COLUMN {name} {definition}"
                        )
                    )
    SQLModel.metadata.create_all(engine)
