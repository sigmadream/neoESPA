from sqlalchemy import inspect, text
from sqlmodel import SQLModel

VERSION = "0017_revision_judge_policy"


def upgrade(engine) -> None:
    if inspect(engine).has_table("problem_revisions"):
        columns = {
            item["name"]
            for item in inspect(engine).get_columns("problem_revisions")
        }
        additions = {
            "process_limit": "INTEGER NOT NULL DEFAULT 1",
            "source_limit_kb": "INTEGER NOT NULL DEFAULT 1024",
            "checker_type": "VARCHAR(40) NOT NULL DEFAULT 'token'",
            "checker_config_json": "TEXT NOT NULL DEFAULT '{}'",
            "language_multipliers_json": "TEXT NOT NULL DEFAULT '{}'",
        }
        with engine.begin() as connection:
            for name, definition in additions.items():
                if name not in columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE problem_revisions ADD COLUMN {name} {definition}"
                        )
                    )
    SQLModel.metadata.create_all(engine)
