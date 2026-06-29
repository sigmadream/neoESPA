from datetime import UTC, datetime, timedelta

from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.domains.exams.helpers import to_exam_read
from app.domains.homework.helpers import to_homework_read
from app.models.schemas import Exam, Homework, Submission, User


def test_submission_schema_supports_multiple_students_per_homework():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        homework = Homework(
            num=1,
            title="Normalized Submission Test",
            intro="Verify multiple students can submit to the same homework.",
            deadline="2026-12-31 23:59:59",
            codeName="solution",
        )
        student_a = User(
            id="student-a",
            sid=20240011,
            ps="hashed-a",
            name="Student A",
            phone="010-0000-0001",
            email="a@example.com",
            user_group="student",
        )
        student_b = User(
            id="student-b",
            sid=20240012,
            ps="hashed-b",
            name="Student B",
            phone="010-0000-0002",
            email="b@example.com",
            user_group="student",
        )

        session.add(homework)
        session.add(student_a)
        session.add(student_b)
        session.commit()

        submission_a = Submission(
            homework_num=1,
            user_id="student-a",
            submission_mode="official",
            attempt_no=1,
            language="python",
        )
        submission_b = Submission(
            homework_num=1,
            user_id="student-b",
            submission_mode="official",
            attempt_no=1,
            language="python",
        )

        session.add(submission_a)
        session.add(submission_b)
        session.commit()

        submissions = session.exec(
            select(Submission).where(Submission.homework_num == 1)
        ).all()

        assert len(submissions) == 2
        assert {submission.user_id for submission in submissions} == {
            "student-a",
            "student-b",
        }


def test_assignment_base_contract_is_applied_to_homework_and_exam_reads():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    now = datetime.now(UTC)
    starttime = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    deadline = (now + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")

    with Session(engine) as session:
        creator = User(
            id="exam-admin",
            sid=20249999,
            ps="hashed-admin",
            name="Exam Admin",
            phone="010-0000-9999",
            email="exam-admin@example.com",
            user_group="admin",
        )
        homework = Homework(
            num=10,
            title="Shared Contract Homework",
            intro="Homework intro",
            codeName="shared_homework",
            starttime=starttime,
            deadline=deadline,
        )
        exam = Exam(
            title="Shared Contract Exam",
            intro="Exam intro",
            codeName="shared_exam",
            starttime=starttime,
            deadline=deadline,
            allowed_languages_json='["python"]',
            created_by="exam-admin",
        )

        session.add(creator)
        session.add(homework)
        session.add(exam)
        session.commit()
        session.refresh(homework)
        session.refresh(exam)

        homework_read = to_homework_read(session, homework)
        exam_read = to_exam_read(exam)

    assert homework_read.title == "Shared Contract Homework"
    assert homework_read.intro == "Homework intro"
    assert homework_read.codeName == "shared_homework"
    assert homework_read.starttime == starttime
    assert homework_read.deadline == deadline
    assert homework_read.schedule_status == "open"
    assert homework_read.can_submit is True

    assert exam_read.title == "Shared Contract Exam"
    assert exam_read.intro == "Exam intro"
    assert exam_read.codeName == "shared_exam"
    assert exam_read.starttime == starttime
    assert exam_read.deadline == deadline
    assert exam_read.schedule_status == "open"
    assert exam_read.can_submit is True
    assert exam_read.allowed_languages == ["python"]


def test_homework_and_exam_intro_columns_are_independent_text_columns():
    homework_intro_column = Homework.__table__.c.intro
    exam_intro_column = Exam.__table__.c.intro

    assert homework_intro_column is not exam_intro_column
    assert homework_intro_column.nullable is False
    assert exam_intro_column.nullable is False
    assert homework_intro_column.type.__class__.__name__ == "Text"
    assert exam_intro_column.type.__class__.__name__ == "Text"
