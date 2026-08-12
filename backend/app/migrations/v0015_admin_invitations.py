from sqlmodel import SQLModel

VERSION = "0015_admin_invitations"


def upgrade(engine) -> None:
    SQLModel.metadata.create_all(engine)
