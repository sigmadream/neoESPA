from sqlmodel import SQLModel

VERSION = "0019_revision_approvals"


def upgrade(engine) -> None:
    SQLModel.metadata.create_all(engine)
