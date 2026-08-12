from sqlmodel import SQLModel

VERSION = "0003_platform_extensions"


def upgrade(engine) -> None:
    SQLModel.metadata.create_all(engine)
