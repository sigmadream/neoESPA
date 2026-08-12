from sqlalchemy import inspect, text
from sqlmodel import SQLModel

VERSION = "0005_materials_board_and_qa"

LECTURE_MATERIAL_COLUMNS = {
    "content": "TEXT",
    "attachment_name": "VARCHAR(255)",
    "attachment_relpath": "VARCHAR(500)",
}


def upgrade(engine) -> None:
    # Register QA tables (declared in the domain router) on SQLModel.metadata
    # before create_all so fresh and legacy databases both receive them.
    from ..domains.qa.router import QAAnswer, QAPost  # noqa: F401

    inspector = inspect(engine)
    if inspector.has_table("lecture_materials"):
        existing_columns = {
            column["name"]
            for column in inspector.get_columns("lecture_materials")
        }
        with engine.begin() as connection:
            for column_name, definition in LECTURE_MATERIAL_COLUMNS.items():
                if column_name in existing_columns:
                    continue
                connection.execute(
                    text(
                        f"ALTER TABLE lecture_materials ADD COLUMN {column_name} {definition}"
                    )
                )

    SQLModel.metadata.create_all(engine)
