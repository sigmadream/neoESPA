from sqlmodel import SQLModel

VERSION = "0016_admin_auth_assurance"


def upgrade(engine) -> None:
    SQLModel.metadata.create_all(engine)
