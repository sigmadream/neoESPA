from sqlalchemy import inspect, text
from sqlmodel import SQLModel

VERSION = "0024_interactive_problem_mode"


def upgrade(engine) -> None:
    if inspect(engine).has_table("problem_revisions"):
        columns = {item["name"] for item in inspect(engine).get_columns("problem_revisions")}
        if "problem_mode" not in columns:
            with engine.begin() as connection:
                connection.execute(text(
                    "ALTER TABLE problem_revisions ADD COLUMN problem_mode "
                    "VARCHAR(20) NOT NULL DEFAULT 'standard'"
                ))
    SQLModel.metadata.create_all(engine)
