from sqlalchemy import text

from ..services.authorization_service import DEFAULT_ROLE_CAPABILITIES

VERSION = "0023_operational_capabilities"


def upgrade(engine) -> None:
    with engine.begin() as connection:
        for role, capabilities in DEFAULT_ROLE_CAPABILITIES.items():
            for capability in capabilities:
                connection.execute(text(
                    "INSERT OR IGNORE INTO role_capabilities (role_name, capability) "
                    "VALUES (:role, :capability)"
                ), {"role": role, "capability": capability})
