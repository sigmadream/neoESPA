from sqlalchemy import text

VERSION = "0004_user_timestamp_backfill"


def upgrade(engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("""
                UPDATE users
                SET created_at = CURRENT_TIMESTAMP
                WHERE created_at IS NULL
                """))
        connection.execute(text("""
                UPDATE users
                SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)
                WHERE updated_at IS NULL
                """))
