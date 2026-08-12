from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

from .config import settings


def configure_sqlite_foreign_keys(engine: Engine) -> Engine:
    if engine.url.get_backend_name() != "sqlite":
        return engine
    if getattr(engine, "_neoespa_sqlite_foreign_keys_enabled", False):
        return engine

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    setattr(engine, "_neoespa_sqlite_foreign_keys_enabled", True)
    return engine


engine = configure_sqlite_foreign_keys(
    create_engine(settings.SQLITE_URL, echo=settings.SQL_ECHO)
)


def get_session():
    with Session(engine) as session:
        yield session
