from sqlmodel import SQLModel

VERSION = "0014_analytics_consent"


def upgrade(engine) -> None:
    SQLModel.metadata.create_all(engine)
