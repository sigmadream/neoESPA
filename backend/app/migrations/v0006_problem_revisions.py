from sqlalchemy import inspect, text
from sqlmodel import SQLModel

VERSION = "0006_problem_revisions"


def upgrade(engine) -> None:
    inspector = inspect(engine)
    if inspector.has_table("submissions"):
        submission_columns = {
            column["name"] for column in inspector.get_columns("submissions")
        }
        if "problem_revision_id" not in submission_columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE submissions "
                        "ADD COLUMN problem_revision_id INTEGER "
                        "REFERENCES problem_revisions(id)"
                    )
                )

    SQLModel.metadata.create_all(engine)

    # Existing Homework rows become published revision 1 records. INSERT OR
    # IGNORE plus stable homework-{num} codes makes this safe to resume.
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO problems
                    (code, title, owner_id, is_active, created_at, updated_at)
                SELECT
                    'homework-' || num,
                    title,
                    NULL,
                    1,
                    COALESCE(created_at, CURRENT_TIMESTAMP),
                    COALESCE(updated_at, CURRENT_TIMESTAMP)
                FROM homework
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO problem_revisions
                    (problem_id, revision_no, statement, input_description,
                     output_description, time_limit_ms, memory_limit_mb,
                     output_limit_kb, process_limit, source_limit_kb,
                     checker_type, problem_mode, checker_config_json, language_multipliers_json,
                     allowed_languages_json, status,
                     validation_report, created_by, created_at, published_at)
                SELECT
                    p.id,
                    1,
                    h.intro,
                    '',
                    '',
                    CASE WHEN h.sec > 0 THEN h.sec * 1000 ELSE 1000 END,
                    256,
                    1024,
                    1,
                    1024,
                    'token',
                    'standard',
                    '{}',
                    '{}',
                    '["c", "cpp", "python", "java"]',
                    'published',
                    '{"source":"homework_backfill"}',
                    NULL,
                    COALESCE(h.created_at, CURRENT_TIMESTAMP),
                    COALESCE(h.updated_at, CURRENT_TIMESTAMP)
                FROM homework h
                JOIN problems p ON p.code = 'homework-' || h.num
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO assignment_problems
                    (homework_num, revision_id, position, created_at)
                SELECT h.num, pr.id, 1, CURRENT_TIMESTAMP
                FROM homework h
                JOIN problems p ON p.code = 'homework-' || h.num
                JOIN problem_revisions pr
                  ON pr.problem_id = p.id AND pr.revision_no = 1
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE submissions
                SET problem_revision_id = (
                    SELECT ap.revision_id
                    FROM assignment_problems ap
                    WHERE ap.homework_num = submissions.homework_num
                      AND ap.position = 1
                )
                WHERE problem_revision_id IS NULL
                  AND EXISTS (
                    SELECT 1 FROM assignment_problems ap
                    WHERE ap.homework_num = submissions.homework_num
                      AND ap.position = 1
                  )
                """
            )
        )
