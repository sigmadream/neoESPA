from sqlalchemy import inspect, text
from sqlmodel import SQLModel

VERSION = "0026_user_token_version"


def upgrade(engine) -> None:
    if inspect(engine).has_table("users"):
        columns = {
            item["name"] for item in inspect(engine).get_columns("users")
        }
        if "token_version" not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN token_version "
                        "INTEGER NOT NULL DEFAULT 0"
                    )
                )
    SQLModel.metadata.create_all(engine)
