from pathlib import Path
from sqlalchemy import text

from ..migrations import MIGRATIONS



def resolve_sqlite_url_for_alembic(
    database_url,
    *,
    base_dir,
    database_mount_exists,
):
    if database_url == "sqlite:////database/database.sqlite" and not database_mount_exists:
        return f"sqlite:///{base_dir / 'database' / 'database.sqlite'}"
    return database_url
def _ensure_migration_table(engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
                """
            )
        )


def get_applied_versions(engine) -> set[str]:
    _ensure_migration_table(engine)

    with engine.connect() as connection:
        rows = connection.execute(text("SELECT version FROM schema_migrations")).all()
    return {row[0] for row in rows}


def apply_migrations(engine) -> None:
    _ensure_migration_table(engine)
    applied_versions = get_applied_versions(engine)

    for version, upgrade in MIGRATIONS:
        if version in applied_versions:
            continue

        upgrade(engine)
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO schema_migrations (version, applied_at)
                    VALUES (:version, CURRENT_TIMESTAMP)
                    """
                ),
                {"version": version},
            )


if __name__ == "__main__":
    from .db import engine

    apply_migrations(engine)
