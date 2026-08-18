from datetime import UTC, datetime, timedelta

from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.models.schemas import (
    Homework,
    PlagiarismPair,
    Submission,
    SubmissionResult,
    User,
)
from app.services.auth_service import AuthService
from app.services.plagiarism_service import PlagiarismService
import app.services.plagiarism_service as plagiarism_module

engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)


def _dt_string(offset_days: int) -> str:
    return (datetime.now(UTC) + timedelta(days=offset_days)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def _create_user(session: Session, user_id: str, sid: int) -> None:
    session.add(
        User(
            id=user_id,
            sid=sid,
            ps=AuthService.get_password_hash("password"),
            name=user_id,
            phone="010-0000-0000",
            email=f"{user_id}@example.com",
            user_group="student",
        )
    )
    session.commit()


def _create_submission(
    session: Session, homework_num: int, user_id: str, code_text: str
) -> None:
    submission = Submission(
        homework_num=homework_num,
        user_id=user_id,
        submission_mode="official",
        attempt_no=1,
        language="python",
        status="graded",
        code_text=code_text,
        original_filename="main.py",
    )
    session.add(submission)
    session.flush()
    session.add(
        SubmissionResult(submission_id=submission.id or 0, status="graded")
    )
    session.commit()


def setup_function():
    SQLModel.metadata.create_all(engine)


def teardown_function():
    SQLModel.metadata.drop_all(engine)


def test_identical_submissions_are_flagged():
    with Session(engine) as session:
        session.add(
            Homework(
                num=1,
                title="Plagiarism Homework",
                intro="Compare code",
                starttime=_dt_string(-1),
                deadline=_dt_string(2),
                codeName="main",
            )
        )
        session.commit()
        _create_user(session, "copy-a", 20250011)
        _create_user(session, "copy-b", 20250012)
        _create_submission(session, 1, "copy-a", "print('same output')\n")
        _create_submission(session, 1, "copy-b", "print('same output')\n")

        service = PlagiarismService()
        run = service.run_for_homework(
            session, homework_num=1, created_by="copy-a"
        )
        stored_pairs = session.exec(select(PlagiarismPair)).all()
        stored_results = session.exec(select(SubmissionResult)).all()

    assert run.flagged_pair_count == 1
    assert len(stored_pairs) == 1
    assert stored_pairs[0].similarity_score == 1.0
    assert all(result.plagiarism_flag is True for result in stored_results)


def test_each_submission_is_decompressed_once(monkeypatch):
    with Session(engine) as session:
        session.add(
            Homework(
                num=2,
                title="Cached Plagiarism Homework",
                intro="Compare code",
                starttime=_dt_string(-1),
                deadline=_dt_string(2),
                codeName="main",
            )
        )
        session.commit()
        for index in range(5):
            user_id = f"cache-{index}"
            _create_user(session, user_id, 20250100 + index)
            _create_submission(session, 2, user_id, f"print({index})\n")

        original = plagiarism_module.decompress_text
        calls = 0

        def count_decompression(value):
            nonlocal calls
            calls += 1
            return original(value)

        monkeypatch.setattr(
            plagiarism_module, "decompress_text", count_decompression
        )
        PlagiarismService().run_for_homework(
            session, homework_num=2, created_by="cache-0"
        )

    assert calls == 5
