from sqlalchemy import text

VERSION = "0020_audit_capability"


def upgrade(engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT OR IGNORE INTO role_capabilities (role_name, capability) "
                "VALUES ('support', 'audit:read')"
            )
        )
