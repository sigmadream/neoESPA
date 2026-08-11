from sqlmodel import SQLModel

VERSION = "0012_contests"


def upgrade(engine) -> None:
    SQLModel.metadata.create_all(engine)
