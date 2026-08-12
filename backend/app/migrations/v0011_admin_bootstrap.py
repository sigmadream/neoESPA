from sqlmodel import SQLModel

VERSION = "0011_admin_bootstrap"


def upgrade(engine) -> None:
    SQLModel.metadata.create_all(engine)
