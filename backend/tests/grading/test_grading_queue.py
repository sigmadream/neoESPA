from datetime import UTC, datetime, timedelta

from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.models.schemas import Homework, Submission, SubmissionResult, User
from app.services.auth_service import AuthService
from app.services.grading_queue import GradingQueueService


engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)


class ExplodingGradingService:
    def grade_submission(self, session: Session, submission: Submission, homework: Homework):
        raise RuntimeError("runner crashed")


def _dt_string(offset_days: int) -> str:
    return (datetime.now(UTC) + timedelta(days=offset_days)).strftime("%Y-%m-%d %H:%M:%S")


def setup_function():
    SQLModel.metadata.create_all(engine)


def teardown_function():
    SQLModel.metadata.drop_all(engine)


def _create_submission(session: Session) -> Submission:
    session.add(
        User(
            id="queue-student",
            sid=20246001,
            ps=AuthService.get_password_hash("student-pass"),
            name="queue-student",
            phone="010-0000-0000",
            email="queue-student@example.com",
            user_group="student",
        )
    )
    session.add(
        Homework(
            num=1,
            title="Queue Homework",
            intro="Queue grading",
            starttime=_dt_string(-1),
            deadline=_dt_string(1),
            codeName="answer",
            sec=2,
        )
    )
    submission = Submission(
        homework_num=1,
        user_id="queue-student",
        submission_mode="official",
        attempt_no=1,
        language="python",
        status="pending",
        code_text="print('queue')\n",
        original_filename="answer.py",
    )
    session.add(submission)
    session.commit()
    session.refresh(submission)
    session.add(SubmissionResult(submission_id=submission.id or 0))
    session.commit()
    return submission


def test_submission_enters_pending_state_before_grading():
    with Session(engine) as session:
        submission = _create_submission(session)
        queue_service = GradingQueueService()

        queued_submission = queue_service.enqueue(session, submission.id or 0)
        result = session.exec(
            select(SubmissionResult).where(
                SubmissionResult.submission_id == queued_submission.id
            )
        ).first()

    assert queued_submission.status == "pending"
    assert result is not None
    assert result.status == "pending"
    assert result.grader_summary == "Submission queued for grading."


def test_failed_job_is_marked_retryable():
    with Session(engine) as session:
        submission = _create_submission(session)
        queue_service = GradingQueueService(grading_service=ExplodingGradingService())

        queue_service.enqueue(session, submission.id or 0)
        processed_submission = queue_service.process_next(session)
        result = session.exec(
            select(SubmissionResult).where(
                SubmissionResult.submission_id == submission.id
            )
        ).first()

    assert processed_submission is not None
    assert processed_submission.status == "retryable"
    assert result is not None
    assert result.status == "retryable"
    assert result.grader_summary == "Queue processing failed: runner crashed"
