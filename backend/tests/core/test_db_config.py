from sqlalchemy import text
from sqlmodel import create_engine

from app.core.db import configure_sqlite_foreign_keys


def test_sqlite_foreign_keys_are_enabled_on_connect():
    engine = configure_sqlite_foreign_keys(
        create_engine("sqlite://", connect_args={"check_same_thread": False})
    )

    with engine.connect() as connection:
        pragma_value = connection.execute(text("PRAGMA foreign_keys")).scalar()

    assert pragma_value == 1
