from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ...api.dependencies import get_current_active_user, require_capability
from ...api.runtime import (
    SUBMISSION_ATTEMPT_RETRY_LIMIT,
    feedback_service,
    judge_job_service,
)
from ...core.compression import compress_text, decompress_text
from ...core.config import settings
from ...core.db import get_session
from ...models.schemas import (
    AssignmentProblem,
    CodeSnapshot,
    CodeSnapshotCreate,
    CodeSnapshotRead,
    Homework,
    Submission,
    SubmissionCreate,
    SubmissionFeedbackRead,
    SubmissionRead,
    SubmissionResult,
    User,
)
from ...services.code_runner import SUPPORTED_LANGUAGES
from ...services.authorization_service import AuthorizationService
from ..homework.helpers import load_allowed_languages
from ..shared.schedules import compute_schedule_window
from ..submissions.helpers import to_submission_read
from ..settings.helpers import get_system_setting_value

router = APIRouter()
authorization_service = AuthorizationService()


def to_code_snapshot_read(snapshot):
    return CodeSnapshotRead(
        id=snapshot.id or 0,
        homework_num=snapshot.homework_num,
        user_id=snapshot.user_id,
        language=snapshot.language,
        code_text=decompress_text(snapshot.code_text),
        snapshot_type=snapshot.snapshot_type,
        created_at=snapshot.created_at,
    )


def enforce_snapshot_rate_limit(session: Session, user_id: str):
    limit = max(settings.SNAPSHOT_RATE_LIMIT_COUNT, 0)
    window_seconds = max(settings.SNAPSHOT_RATE_LIMIT_WINDOW_SECONDS, 0)
    if limit == 0 or window_seconds == 0:
        return

    window_start = datetime.now(UTC) - timedelta(seconds=window_seconds)
    recent_snapshot_ids = session.exec(
        select(CodeSnapshot.id).where(
            CodeSnapshot.user_id == user_id,
            CodeSnapshot.created_at >= window_start,
        )
    ).all()
    if len(recent_snapshot_ids) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Snapshot save limit exceeded. Up to {limit} saves are allowed per "
                f"{window_seconds} seconds."
            ),
        )


@router.post(
    "/submissions",
    response_model=SubmissionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_submission(
    payload: SubmissionCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    homework = session.get(Homework, payload.homework_num)
    if homework is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Homework not found"
        )

    language = payload.language.strip().lower()
    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported submission language",
        )

    allowed_languages = load_allowed_languages(session, payload.homework_num)
    globally_enabled = set(
        get_system_setting_value(session, "judge_enabled_languages").split(",")
    )
    if language not in globally_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submission language is disabled by system policy",
        )
    if language not in allowed_languages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submission language is not allowed for this homework",
        )

    if payload.code_text is None or not payload.code_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submission must include code text",
        )
    max_source_bytes = int(
        float(get_system_setting_value(session, "submission_max_source_bytes"))
    )
    if len(payload.code_text.encode("utf-8")) > max_source_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Submission source exceeds {max_source_bytes} byte limit",
        )
    rate_limit = int(
        float(
            get_system_setting_value(
                session, "submission_rate_limit_per_minute"
            )
        )
    )
    recent_cutoff = datetime.now(UTC) - timedelta(minutes=1)
    recent_ids = session.exec(
        select(Submission.id).where(
            Submission.user_id == current_user.id,
            Submission.submitted_at >= recent_cutoff,
        )
    ).all()
    if len(recent_ids) >= rate_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Submission rate limit exceeded",
        )

    schedule_status, can_submit = compute_schedule_window(
        homework.starttime, homework.deadline
    )
    if not can_submit:
        detail = (
            "Submission window has not opened"
            if schedule_status == "upcoming"
            else "Submission deadline has passed"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=detail
        )

    for _ in range(SUBMISSION_ATTEMPT_RETRY_LIMIT):
        last_attempt = session.exec(
            select(Submission.attempt_no)
            .where(
                Submission.homework_num == payload.homework_num,
                Submission.user_id == current_user.id,
                Submission.submission_mode == "official",
            )
            .order_by(Submission.attempt_no.desc())
        ).first()
        attempt_no = 1 if last_attempt is None else last_attempt + 1

        assigned_revision_id = session.exec(
            select(AssignmentProblem.revision_id)
            .where(AssignmentProblem.homework_num == payload.homework_num)
            .order_by(AssignmentProblem.position)
        ).first()
        submission = Submission(
            homework_num=payload.homework_num,
            problem_revision_id=assigned_revision_id,
            user_id=current_user.id,
            submission_mode="official",
            attempt_no=attempt_no,
            language=language,
            status="pending",
            code_text=compress_text(payload.code_text),
            original_filename=payload.original_filename,
            deadline_snapshot=homework.deadline,
        )
        session.add(submission)

        try:
            session.flush()
            session.add(
                SubmissionResult(
                    submission_id=submission.id or 0,
                    status="pending",
                    compile_status="not_started",
                    run_status="not_started",
                    grader_summary="Submission accepted. Waiting for grading.",
                )
            )
            if settings.AUTOMATIC_GRADING_AVAILABLE:
                judge_job_service.enqueue(
                    session,
                    job_type="grade_submission",
                    payload={
                        "submission_id": submission.id,
                        "target_revision_id": submission.problem_revision_id,
                    },
                    idempotency_key=f"submission:{submission.id}:initial",
                    revision_id=submission.problem_revision_id,
                    submission_id=submission.id,
                )
            session.commit()
        except IntegrityError:
            session.rollback()
            continue

        session.refresh(submission)

        if not settings.AUTOMATIC_GRADING_AVAILABLE:
            result_obj = session.exec(
                select(SubmissionResult).where(
                    SubmissionResult.submission_id == submission.id
                )
            ).first()
            submission.status = "pending_manual"
            if result_obj is not None:
                result_obj.status = "pending_manual"
                result_obj.grader_summary = "Automatic grading is disabled until an isolated judge runner is ready."
                session.add(result_obj)
            session.add(submission)
            session.commit()
            session.refresh(submission)
            return to_submission_read(session, submission)

        return to_submission_read(session, submission)

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Submission attempt conflicted with another request. Please retry.",
    )


@router.get("/submissions", response_model=list[SubmissionRead])
def list_submissions(
    homework_num: int | None = Query(default=None),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    statement = select(Submission).where(Submission.user_id == current_user.id)
    if homework_num is not None:
        statement = statement.where(Submission.homework_num == homework_num)

    submissions = session.exec(
        statement.order_by(Submission.submitted_at.desc(), Submission.id.desc())
    ).all()
    return [
        to_submission_read(session, submission) for submission in submissions
    ]


@router.get("/submissions/{submission_id}", response_model=SubmissionRead)
def get_submission_detail(
    submission_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    submission = session.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )

    can_read_any = authorization_service.has_capability(
        session, current_user, "grading:manual"
    )
    if submission.user_id != current_user.id and not can_read_any:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot access this submission",
        )

    return to_submission_read(session, submission)


@router.get(
    "/submissions/{submission_id}/feedback",
    response_model=SubmissionFeedbackRead,
)
def get_submission_feedback(
    submission_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    submission = session.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )
    can_read_any = authorization_service.has_capability(
        session, current_user, "grading:manual"
    )
    if submission.user_id != current_user.id and not can_read_any:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot access this submission",
        )

    homework = session.get(Homework, submission.homework_num)
    if homework is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Homework not found"
        )
    result = session.exec(
        select(SubmissionResult).where(
            SubmissionResult.submission_id == submission_id
        )
    ).first()
    return feedback_service.build_submission_feedback(
        session, submission, homework, result
    )


@router.post(
    "/submissions/snapshots",
    response_model=CodeSnapshotRead,
    status_code=status.HTTP_201_CREATED,
)
def save_code_snapshot(
    payload: CodeSnapshotCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    homework = session.get(Homework, payload.homework_num)
    if homework is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Homework not found"
        )
    max_source_bytes = int(
        float(get_system_setting_value(session, "submission_max_source_bytes"))
    )
    if len(payload.code_text.encode("utf-8")) > max_source_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Snapshot source exceeds {max_source_bytes} byte limit",
        )

    last_snapshot = session.exec(
        select(CodeSnapshot)
        .where(
            CodeSnapshot.homework_num == payload.homework_num,
            CodeSnapshot.user_id == current_user.id,
        )
        .order_by(CodeSnapshot.created_at.desc())
    ).first()

    if (
        last_snapshot
        and decompress_text(last_snapshot.code_text) == payload.code_text
    ):
        return to_code_snapshot_read(last_snapshot)
    enforce_snapshot_rate_limit(session, current_user.id)

    snapshot = CodeSnapshot(
        homework_num=payload.homework_num,
        user_id=current_user.id,
        language=payload.language,
        code_text=compress_text(payload.code_text),
        snapshot_type=payload.snapshot_type,
    )
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return to_code_snapshot_read(snapshot)


@router.get(
    "/homeworks/{homework_num}/snapshots/latest",
    response_model=CodeSnapshotRead | None,
)
def get_latest_snapshot(
    homework_num: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    snapshot = session.exec(
        select(CodeSnapshot)
        .where(
            CodeSnapshot.homework_num == homework_num,
            CodeSnapshot.user_id == current_user.id,
        )
        .order_by(CodeSnapshot.created_at.desc())
    ).first()
    if snapshot:
        return to_code_snapshot_read(snapshot)
    return snapshot


@router.get(
    "/admin/homeworks/{homework_num}/snapshots/{user_id}",
    response_model=list[CodeSnapshotRead],
)
def get_student_snapshots(
    homework_num: int,
    user_id: str,
    _: User = Depends(require_capability("grading:manual")),
    session: Session = Depends(get_session),
):
    snapshots = session.exec(
        select(CodeSnapshot)
        .where(
            CodeSnapshot.homework_num == homework_num,
            CodeSnapshot.user_id == user_id,
        )
        .order_by(CodeSnapshot.created_at.desc())
    ).all()
    return [to_code_snapshot_read(snapshot) for snapshot in snapshots]
