from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlmodel import Session, select

from ...api.dependencies import require_capability
from ...api.runtime import (
    export_service,
    grading_service,
    judge_job_service,
    notification_service,
    observability_service,
)
from ...core.config import settings
from ...core.db import get_session
from ...models.schemas import (
    Homework,
    JudgeJob,
    Submission,
    SubmissionRead,
    SubmissionResult,
    SubmissionScoreAdjustRequest,
    User,
)
from ..submissions.helpers import (
    get_or_create_submission_result,
    to_submission_read,
)

router = APIRouter()


@router.post(
    "/admin/submissions/{submission_id}/grade", response_model=SubmissionRead
)
def grade_submission(
    submission_id: int,
    current_user: User = Depends(require_capability("grading:manual")),
    session: Session = Depends(get_session),
):
    submission = session.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )

    homework = session.get(Homework, submission.homework_num)
    if homework is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Homework not found",
        )

    try:
        grading_service.grade_submission(session, submission, homework)
    except ValueError as error:
        session.rollback()
        submission = session.get(Submission, submission_id)
        if submission is not None:
            submission.status = "retryable"
            result = get_or_create_submission_result(session, submission_id)
            result.status = "retryable"
            result.grader_summary = f"Auto-grading failed: {error}"
            session.add(submission)
            session.add(result)
        observability_service.log_event(
            session,
            category="grading",
            level="error",
            event_type="grading_failed",
            message=str(error),
            submission_id=submission_id,
            user_id=current_user.id,
            request_path=f"/api/admin/submissions/{submission_id}/grade",
            context={"homework_num": submission.homework_num},
        )
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except Exception as error:
        session.rollback()
        observability_service.log_event(
            session,
            category="grading",
            level="error",
            event_type="grading_failed",
            message=str(error),
            submission_id=submission_id,
            user_id=current_user.id,
            request_path=f"/api/admin/submissions/{submission_id}/grade",
            context={"homework_num": submission.homework_num},
        )
        session.commit()
        raise

    session.refresh(submission)
    result = session.exec(
        select(SubmissionResult).where(
            SubmissionResult.submission_id == submission_id
        )
    ).first()
    if result is not None:
        queued_jobs = session.exec(
            select(JudgeJob).where(
                JudgeJob.submission_id == submission_id,
                JudgeJob.job_type == "grade_submission",
                JudgeJob.status == "queued",
            )
        ).all()
        for queued_job in queued_jobs:
            queued_job.status = "cancelled"
            queued_job.finished_at = datetime.now(UTC)
            session.add(queued_job)
        notification_service.notify_submission_graded(
            session, submission, result
        )
        observability_service.record_audit(
            session,
            actor_user_id=current_user.id,
            action_type="grade_submission",
            target_type="submission",
            target_id=str(submission_id),
            payload={"status": submission.status},
        )
        session.commit()
    return to_submission_read(session, submission)


@router.post(
    "/admin/submissions/{submission_id}/queue", response_model=SubmissionRead
)
def queue_submission_for_grading(
    submission_id: int,
    _: User = Depends(require_capability("grading:manual")),
    session: Session = Depends(get_session),
):
    submission = session.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    _enqueue_persistent_grading_job(session, submission)
    return to_submission_read(session, submission)


@router.post(
    "/admin/submissions/{submission_id}/requeue", response_model=SubmissionRead
)
def requeue_submission_for_grading(
    submission_id: int,
    _: User = Depends(require_capability("grading:manual")),
    session: Session = Depends(get_session),
):
    submission = session.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )

    _enqueue_persistent_grading_job(session, submission)
    return to_submission_read(session, submission)


def _enqueue_persistent_grading_job(
    session: Session, submission: Submission
) -> None:
    result = get_or_create_submission_result(session, submission.id or 0)
    submission.status = "pending"
    result.status = "pending"
    result.compile_status = "not_started"
    result.run_status = "not_started"
    result.total_score = 0
    result.passed_case_count = 0
    result.total_case_count = 0
    result.grader_summary = "Submission queued for grading."
    session.add(submission)
    session.add(result)
    active_job = session.exec(
        select(JudgeJob).where(
            JudgeJob.submission_id == submission.id,
            JudgeJob.job_type == "grade_submission",
            JudgeJob.status.in_(["queued", "leased", "running"]),
        )
    ).first()
    if active_job is None:
        judge_job_service.enqueue(
            session,
            job_type="grade_submission",
            payload={
                "submission_id": submission.id,
                "target_revision_id": submission.problem_revision_id,
            },
            submission_id=submission.id,
            revision_id=submission.problem_revision_id,
        )
    session.commit()
    session.refresh(submission)


@router.patch(
    "/admin/submissions/{submission_id}/score", response_model=SubmissionRead
)
def adjust_submission_score(
    submission_id: int,
    payload: SubmissionScoreAdjustRequest,
    current_user: User = Depends(require_capability("grading:manual")),
    session: Session = Depends(get_session),
):
    submission = session.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )

    if submission.status in {"pending", "grading"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot adjust score while grading is in progress",
        )

    if payload.manual_total_score < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Adjusted score must be non-negative",
        )

    result = get_or_create_submission_result(session, submission_id)
    result.manual_total_score = round(payload.manual_total_score, 2)
    result.adjustment_note = (
        payload.adjustment_note.strip() if payload.adjustment_note else None
    )
    result.adjusted_at = datetime.now(UTC)
    result.adjusted_by = current_user.id
    session.add(result)
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="adjust_submission_score",
        target_type="submission",
        target_id=str(submission_id),
        payload=payload.model_dump(),
    )
    session.commit()
    session.refresh(submission)
    return to_submission_read(session, submission)


@router.post("/admin/grading/process-next", response_model=SubmissionRead)
def process_next_grading_job(
    current_user: User = Depends(require_capability("grading:manual")),
    session: Session = Depends(get_session),
):
    if not settings.HOST_CODE_EXECUTION_ALLOWED:
        raise HTTPException(
            status_code=503, detail="Isolated automatic grading is disabled"
        )
    job = judge_job_service.claim_next(
        session,
        f"admin-compat-{current_user.id}",
        job_types=["grade_submission"],
    )
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No queued submissions found",
        )
    completed_job = judge_job_service.process_grading_job(
        session, job, f"admin-compat-{current_user.id}"
    )
    submission = session.get(Submission, job.submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    result = session.exec(
        select(SubmissionResult).where(
            SubmissionResult.submission_id == (submission.id or 0)
        )
    ).first()
    if result is not None and result.status in {
        "graded",
        "failed",
        "retryable",
    }:
        notification_service.notify_submission_graded(
            session, submission, result
        )
        if result.status == "retryable":
            observability_service.log_event(
                session,
                category="grading",
                level="error",
                event_type="queue_processing_failed",
                message=(
                    f"Queue processing failed: {completed_job.error_message}"
                    if completed_job.error_message
                    else result.grader_summary or "Queue processing failed."
                ),
                submission_id=submission.id or 0,
                user_id=current_user.id,
                request_path="/api/admin/grading/process-next",
            )
        observability_service.record_audit(
            session,
            actor_user_id=current_user.id,
            action_type="process_grading_queue",
            target_type="submission",
            target_id=str(submission.id or 0),
            payload={"status": submission.status},
        )
        session.commit()
    return to_submission_read(session, submission)


@router.get("/admin/homeworks/{homework_num}/grades/export")
def export_homework_grades(
    homework_num: int,
    _: User = Depends(require_capability("grading:manual")),
    session: Session = Depends(get_session),
):
    homework = session.get(Homework, homework_num)
    if homework is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Homework not found",
        )

    csv_bytes = export_service.build_grade_csv(session, homework)
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="homework_{homework_num}_grades.csv"'
            )
        },
    )


@router.get("/admin/homeworks/{homework_num}/submissions/archive")
def export_latest_submissions_archive(
    homework_num: int,
    _: User = Depends(require_capability("grading:manual")),
    session: Session = Depends(get_session),
):
    homework = session.get(Homework, homework_num)
    if homework is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Homework not found",
        )

    archive_bytes = export_service.build_latest_submission_archive(
        session, homework
    )
    return Response(
        content=archive_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="homework_{homework_num}_latest_submissions.zip"'
            )
        },
    )
