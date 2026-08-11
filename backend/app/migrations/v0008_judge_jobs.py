from sqlmodel import SQLModel

VERSION = "0008_judge_jobs"


def upgrade(engine) -> None:
    SQLModel.metadata.create_all(engine)
