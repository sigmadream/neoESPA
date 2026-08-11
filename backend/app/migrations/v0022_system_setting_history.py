from sqlmodel import SQLModel

VERSION = "0022_system_setting_history"


def upgrade(engine) -> None:
    SQLModel.metadata.create_all(engine)
