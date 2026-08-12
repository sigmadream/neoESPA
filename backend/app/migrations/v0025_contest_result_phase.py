from sqlalchemy import inspect, text
from sqlmodel import SQLModel

VERSION = "0025_contest_result_phase"


def upgrade(engine) -> None:
    if inspect(engine).has_table("users"):
        user_columns = {item["name"] for item in inspect(engine).get_columns("users")}
        if "organization_id" not in user_columns:
            with engine.begin() as connection:
                connection.execute(text(
                    "ALTER TABLE users ADD COLUMN organization_id VARCHAR(80)"
                ))
                connection.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_users_organization_id ON users (organization_id)"
                ))
    if inspect(engine).has_table("contests"):
        contest_columns = {item["name"] for item in inspect(engine).get_columns("contests")}
        if "allowed_organizations_json" not in contest_columns:
            with engine.begin() as connection:
                connection.execute(text(
                    "ALTER TABLE contests ADD COLUMN allowed_organizations_json "
                    "TEXT NOT NULL DEFAULT '[]'"
                ))
    if inspect(engine).has_table("contest_result_events"):
        columns = {
            item["name"] for item in inspect(engine).get_columns("contest_result_events")
        }
        if "result_phase" not in columns:
            with engine.begin() as connection:
                connection.execute(text(
                    "ALTER TABLE contest_result_events ADD COLUMN result_phase "
                    "VARCHAR(20) NOT NULL DEFAULT 'live'"
                ))
                connection.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_contest_result_events_result_phase "
                    "ON contest_result_events (result_phase)"
                ))
    SQLModel.metadata.create_all(engine)
