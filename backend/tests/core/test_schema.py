from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.models.schemas import Homework, Submission, User


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
