from sqlalchemy import inspect, text
from sqlmodel import SQLModel

VERSION = "0013_selected_grading_run"


def upgrade(engine) -> None:
    inspector = inspect(engine)
    if inspector.has_table("submissions"):
        columns = {
            column["name"] for column in inspector.get_columns("submissions")
        }
        if "selected_grading_run_id" not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE submissions ADD COLUMN selected_grading_run_id INTEGER"
                    )
                )
    SQLModel.metadata.create_all(engine)
