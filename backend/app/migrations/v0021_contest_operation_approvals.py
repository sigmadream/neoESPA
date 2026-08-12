from sqlmodel import SQLModel

VERSION = "0021_contest_operation_approvals"


def upgrade(engine) -> None:
    SQLModel.metadata.create_all(engine)
