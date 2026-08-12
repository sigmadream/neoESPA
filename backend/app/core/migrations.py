from sqlalchemy import text

from ..migrations import MIGRATIONS


def _ensure_migration_table(engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
                """))


def get_applied_versions(engine) -> set[str]:
    _ensure_migration_table(engine)

    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT version FROM schema_migrations")
        ).all()
    return {row[0] for row in rows}


def apply_migrations(engine) -> None:
    _ensure_migration_table(engine)
    applied_versions = get_applied_versions(engine)
    pending = [
        version
        for version, _upgrade in MIGRATIONS
        if version not in applied_versions
    ]
    if pending:
        _create_production_pre_migration_snapshot(engine, applied_versions)

    for version, upgrade in MIGRATIONS:
        if version in applied_versions:
            continue

        upgrade(engine)
        with engine.begin() as connection:
            connection.execute(
                text("""
                    INSERT INTO schema_migrations (version, applied_at)
                    VALUES (:version, CURRENT_TIMESTAMP)
                    """),
                {"version": version},
            )


def _create_production_pre_migration_snapshot(
    engine, applied_versions: set[str]
) -> None:
    from pathlib import Path

    from .config import settings

    if (
        settings.ENVIRONMENT != "production"
        or engine.url.get_backend_name() != "sqlite"
    ):
        return
    database_name = engine.url.database
    if not database_name:
        return
    with engine.connect() as connection:
        user_table_count = connection.execute(
            text(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' AND name != 'schema_migrations'"
            )
        ).scalar_one()
    if user_table_count == 0:
        return
    from ..services.course_bundle import CourseBundleService

    CourseBundleService().create_snapshot(
        Path(database_name),
        course_id=settings.COURSE_ID,
        term=settings.COURSE_TERM,
        schema_version=(
            max(applied_versions) if applied_versions else "legacy-unversioned"
        ),
    )


if __name__ == "__main__":
    from .db import engine

    apply_migrations(engine)
