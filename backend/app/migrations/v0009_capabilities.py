from sqlalchemy import text
from sqlmodel import SQLModel

from ..services.authorization_service import DEFAULT_ROLE_CAPABILITIES

VERSION = "0009_capabilities"


def upgrade(engine) -> None:
    SQLModel.metadata.create_all(engine)
    with engine.begin() as connection:
        for role_name, capabilities in DEFAULT_ROLE_CAPABILITIES.items():
            for capability in capabilities:
                connection.execute(
                    text(
                        """
                        INSERT OR IGNORE INTO role_capabilities (role_name, capability)
                        VALUES (:role_name, :capability)
                        """
                    ),
                    {"role_name": role_name, "capability": capability},
                )
