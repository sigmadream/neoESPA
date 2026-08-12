from datetime import UTC, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlmodel import Session, SQLModel, create_engine, select
from app.core.db import configure_sqlite_foreign_keys

from app.models.schemas import (
    JudgeJob,
    JudgeJobEvent,
    Problem,
    ProblemAsset,
    ProblemRevision,
    ProblemTestCase,
    User,
    Homework,
    Submission,
    SubmissionResult,
    GradingRun,
)
from app.services.judge_job_service import JobConflictError, JudgeJobService
from app.services.checkers import CheckerError
from app.services.grading_service import GradingService


class SuccessfulGradingService:
    def grade_submission(self, session, submission, homework):
        result = session.exec(
            select(SubmissionResult).where(
                SubmissionResult.submission_id == submission.id
            )
        ).first()
        if result is None:
            result = SubmissionResult(submission_id=submission.id)
        submission.status = "graded"
        result.status = "graded"
        result.compile_status = "passed"
        result.run_status = "passed"
        result.total_case_count = 1
        result.passed_case_count = 1
        result.total_score = 100
        session.add(submission)
        session.add(result)
        session.commit()
        session.refresh(result)
        return result


class BrokenCheckerGradingService:
    def grade_submission(self, *_args, **_kwargs):
        raise CheckerError("checker crashed")


class HeartbeatingGradingService(GradingService):
    def grade_submission(
        self, session, submission, homework=None, progress_callback=None
    ):
        assert progress_callback is not None
        progress_callback(1, 2, 45)
        return SuccessfulGradingService().grade_submission(
            session, submission, homework
        )


def test_enqueue_is_idempotent_and_rejects_changed_payload(session):
    service = JudgeJobService()
    first = service.enqueue(
        session,
        job_type="problem_validation",
        payload={"revision_id": 1},
        idempotency_key="validate-1",
    )
    session.commit()
    same = service.enqueue(
        session,
        job_type="problem_validation",
        payload={"revision_id": 1},
        idempotency_key="validate-1",
    )

    assert same.id == first.id
    with pytest.raises(JobConflictError):
        service.enqueue(
            session,
            job_type="problem_validation",
            payload={"revision_id": 2},
            idempotency_key="validate-1",
        )


def test_claim_fencing_rejects_stale_worker_result(session):
    service = JudgeJobService()
    service.enqueue(session, job_type="problem_validation", payload={})
    session.commit()
    first_claim = service.claim_next(session, "worker-a", lease_seconds=1)
    assert first_claim is not None
    first_generation = first_claim.lease_generation

    first_claim.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.add(first_claim)
    session.commit()
    second_claim = service.claim_next(session, "worker-b", lease_seconds=30)

    assert second_claim is not None
    assert second_claim.id == first_claim.id
    assert second_claim.lease_generation == first_generation + 1
    with pytest.raises(JobConflictError, match="Stale or foreign"):
        service.complete(
            session,
            first_claim.id or 0,
            "worker-a",
            first_generation,
            {"wrong": True},
        )


def test_validation_worker_marks_revision_ready(session):
    service = JudgeJobService()
    user = User(
        id="owner",
        sid=20259201,
        name="Owner",
        phone="010",
        email="owner@example.com",
        user_group="admin",
        ps="hash",
    )
    session.add(user)
    session.flush()
    problem = Problem(code="job-problem", title="Job", owner_id="owner")
    session.add(problem)
    session.flush()
    revision = ProblemRevision(
        problem_id=problem.id or 0,
        revision_no=1,
        statement="Statement",
        status="draft",
        created_by="owner",
    )
    session.add(revision)
    session.flush()
    input_asset = ProblemAsset(
        revision_id=revision.id or 0,
        asset_kind="test_input",
        display_name="1.in",
        storage_path="objects/sha256/aa/input",
        size_bytes=1,
    )
    output_asset = ProblemAsset(
        revision_id=revision.id or 0,
        asset_kind="test_output",
        display_name="1.out",
        storage_path="objects/sha256/bb/output",
        size_bytes=1,
    )
    session.add(input_asset)
    session.add(output_asset)
    session.flush()
    session.add(
        ProblemTestCase(
            revision_id=revision.id or 0,
            case_name="one",
            position=1,
            input_asset_id=input_asset.id or 0,
            output_asset_id=output_asset.id or 0,
            score=100,
        )
    )
    job = service.enqueue(
        session,
        job_type="problem_validation",
        payload={"revision_id": revision.id},
        revision_id=revision.id,
        problem_id=problem.id,
    )
    session.commit()

    claimed = service.claim_next(session, "validation-worker")
    assert claimed is not None
    completed = service.process_validation_job(
        session, claimed, "validation-worker"
    )

    session.refresh(revision)
    assert completed.status == "succeeded"
    assert revision.status == "ready"
    events = session.exec(
        select(JudgeJobEvent).where(JudgeJobEvent.job_id == job.id)
    ).all()
    assert [event.event_type for event in events] == [
        "queued",
        "leased",
        "running",
        "succeeded",
    ]


def test_grading_job_records_immutable_run_and_selects_it(session):
    user = User(
        id="graded-user",
        sid=20259203,
        name="Graded",
        phone="010",
        email="graded@example.com",
        user_group="student",
        ps="hash",
    )
    session.add(user)
    session.flush()
    homework = Homework(num=901, title="Grade", intro="Grade", codeName="main")
    session.add(homework)
    session.flush()
    submission = Submission(
        homework_num=901,
        user_id="graded-user",
        language="python",
        code_text="print(1)",
    )
    session.add(submission)
    session.flush()
    service = JudgeJobService(grading_service=SuccessfulGradingService())
    job = service.enqueue(
        session,
        job_type="grade_submission",
        payload={"submission_id": submission.id},
        submission_id=submission.id,
    )
    session.commit()

    claimed = service.claim_next(
        session, "judge-worker", job_types=["grade_submission"]
    )
    assert claimed is not None
    completed = service.process_grading_job(session, claimed, "judge-worker")

    session.refresh(submission)
    run = session.exec(
        select(GradingRun).where(GradingRun.job_id == job.id)
    ).one()
    assert completed.status == "succeeded"
    assert run.verdict == "AC"
    assert submission.selected_grading_run_id == run.id


def test_real_grading_protocol_heartbeats_during_long_running_job(session):
    session.add(
        User(
            id="heartbeat-user",
            sid=20259205,
            name="Heartbeat",
            phone="010",
            email="heartbeat@example.com",
            user_group="student",
            ps="hash",
        )
    )
    session.add(
        Homework(num=903, title="Heartbeat", intro="Heartbeat", codeName="main")
    )
    session.flush()
    submission = Submission(
        homework_num=903,
        user_id="heartbeat-user",
        language="python",
        code_text="print(1)",
    )
    session.add(submission)
    session.flush()
    service = JudgeJobService(grading_service=HeartbeatingGradingService())
    job = service.enqueue(
        session,
        job_type="grade_submission",
        payload={"submission_id": submission.id},
        submission_id=submission.id,
    )
    session.commit()
    claimed = service.claim_next(
        session, "heartbeat-judge", job_types=["grade_submission"]
    )
    assert claimed is not None

    service.process_grading_job(session, claimed, "heartbeat-judge")

    session.refresh(job)
    assert job.status == "succeeded"
    assert job.progress == 100
    assert job.heartbeat_at is not None


def test_checker_failure_records_ie_instead_of_wa(session):
    session.add(
        User(
            id="ie-user",
            sid=20259204,
            name="IE",
            phone="010",
            email="ie@example.com",
            user_group="student",
            ps="hash",
        )
    )
    session.add(Homework(num=902, title="IE", intro="IE", codeName="main"))
    session.flush()
    submission = Submission(
        homework_num=902,
        user_id="ie-user",
        language="python",
        code_text="print(1)",
    )
    session.add(submission)
    session.flush()
    service = JudgeJobService(grading_service=BrokenCheckerGradingService())
    job = service.enqueue(
        session,
        job_type="grade_submission",
        payload={"submission_id": submission.id},
        submission_id=submission.id,
    )
    session.commit()
    claimed = service.claim_next(
        session, "ie-worker", job_types=["grade_submission"]
    )
    assert claimed is not None
    failed = service.process_grading_job(session, claimed, "ie-worker")
    session.refresh(submission)
    run = session.exec(
        select(GradingRun).where(GradingRun.job_id == job.id)
    ).one()
    assert failed.status == "failed"
    assert run.verdict == "IE"
    assert submission.status == "judge_error"
    assert submission.selected_grading_run_id == run.id


def test_failed_job_can_be_explicitly_retried(session):
    service = JudgeJobService()
    job = service.enqueue(
        session, job_type="problem_validation", payload={"revision_id": 1}
    )
    session.commit()
    claimed = service.claim_next(session, "retry-worker")
    assert claimed is not None
    failed = service.fail(
        session,
        claimed.id or 0,
        "retry-worker",
        claimed.lease_generation,
        "temporary error",
    )
    retried = service.retry(session, failed)
    assert retried.status == "queued"
    assert retried.error_message is None
    claimed_again = service.claim_next(session, "retry-worker")
    assert claimed_again is not None
    assert claimed_again.id == job.id
    assert claimed_again.attempt_count == 2


def test_successful_job_cannot_be_retried(session):
    service = JudgeJobService()
    service.enqueue(session, job_type="noop", payload={})
    session.commit()
    claimed = service.claim_next(session, "retry-worker")
    assert claimed is not None
    completed = service.complete(
        session, claimed.id or 0, "retry-worker", claimed.lease_generation, {}
    )
    with pytest.raises(JobConflictError, match="failed or dead-letter"):
        service.retry(session, completed)


def test_heartbeat_extends_only_current_lease_generation(session):
    service = JudgeJobService()
    service.enqueue(session, job_type="noop", payload={})
    session.commit()
    claimed = service.claim_next(session, "heartbeat-worker", lease_seconds=1)
    assert claimed is not None
    original_expiry = claimed.lease_expires_at
    renewed = service.heartbeat(
        session,
        claimed.id or 0,
        "heartbeat-worker",
        claimed.lease_generation,
        lease_seconds=60,
        progress=25,
    )
    assert renewed.lease_expires_at > original_expiry
    assert renewed.progress == 25
    with pytest.raises(JobConflictError, match="Stale or foreign"):
        service.heartbeat(
            session,
            renewed.id or 0,
            "heartbeat-worker",
            renewed.lease_generation - 1,
        )


def test_two_coordinators_cannot_claim_the_same_job(tmp_path):
    engine = configure_sqlite_foreign_keys(
        create_engine(
            f"sqlite:///{tmp_path / 'race.sqlite3'}",
            connect_args={"check_same_thread": False},
        )
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        JudgeJobService().enqueue(session, job_type="noop", payload={})
        session.commit()

    def claim(worker_id: str):
        with Session(engine) as session:
            job = JudgeJobService().claim_next(session, worker_id)
            return job.id if job else None

    with ThreadPoolExecutor(max_workers=2) as executor:
        claimed = list(executor.map(claim, ["race-a", "race-b"]))
    assert sum(item is not None for item in claimed) == 1
    with Session(engine) as session:
        job = session.exec(select(JudgeJob)).one()
        assert job.attempt_count == 1
    SQLModel.metadata.drop_all(engine)
