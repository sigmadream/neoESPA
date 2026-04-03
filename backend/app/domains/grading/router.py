from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlmodel import Session, select

from ...api.dependencies import require_staff
from ...api.runtime import export_service, grading_queue, grading_service, notification_service, observability_service
from ...core.db import get_session
from ...models.schemas import Homework, Submission, SubmissionRead, SubmissionResult, SubmissionScoreAdjustRequest, User
from ...services.user_management import ADMIN_ROLES
from ..submissions.helpers import get_or_create_submission_result, to_submission_read


router = APIRouter()


@router.post("/admin/submissions/{submission_id}/grade", response_model=SubmissionRead)
def grade_submission(
    submission_id: int,
    current_user: User = Depends(require_staff),
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
        select(SubmissionResult).where(SubmissionResult.submission_id == submission_id)
    ).first()
    if result is not None:
        notification_service.notify_submission_graded(session, submission, result)
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


@router.post("/admin/submissions/{submission_id}/queue", response_model=SubmissionRead)
def queue_submission_for_grading(
    submission_id: int,
    _: User = Depends(require_staff),
    session: Session = Depends(get_session),
):
    try:
        submission = grading_queue.enqueue(session, submission_id)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    return to_submission_read(session, submission)


@router.post("/admin/submissions/{submission_id}/requeue", response_model=SubmissionRead)
def requeue_submission_for_grading(
    submission_id: int,
    _: User = Depends(require_staff),
    session: Session = Depends(get_session),
):
    submission = session.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )

    try:
        queued_submission = grading_queue.enqueue(session, submission_id)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    return to_submission_read(session, queued_submission)


@router.patch("/admin/submissions/{submission_id}/score", response_model=SubmissionRead)
def adjust_submission_score(
    submission_id: int,
    payload: SubmissionScoreAdjustRequest,
    current_user: User = Depends(require_staff),
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
    current_user: User = Depends(require_staff),
    session: Session = Depends(get_session),
):
    submission = grading_queue.process_next(session)
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No queued submissions found",
        )
    result = session.exec(
        select(SubmissionResult).where(SubmissionResult.submission_id == (submission.id or 0))
    ).first()
    if result is not None and result.status in {"graded", "failed", "retryable"}:
        notification_service.notify_submission_graded(session, submission, result)
        if result.status == "retryable":
            observability_service.log_event(
                session,
                category="grading",
                level="error",
                event_type="queue_processing_failed",
                message=result.grader_summary or "Queue processing failed.",
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
    _: User = Depends(require_staff),
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
    _: User = Depends(require_staff),
    session: Session = Depends(get_session),
):
    homework = session.get(Homework, homework_num)
    if homework is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Homework not found",
        )

    archive_bytes = export_service.build_latest_submission_archive(session, homework)
    return Response(
        content=archive_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="homework_{homework_num}_latest_submissions.zip"'
            )
        },
    )
