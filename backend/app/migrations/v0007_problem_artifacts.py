from sqlmodel import SQLModel

VERSION = "0007_problem_artifacts"


def upgrade(engine) -> None:
    SQLModel.metadata.create_all(engine)
