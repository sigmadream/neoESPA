import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ...api.dependencies import get_current_active_user, require_staff
from ...api.runtime import (
    SUBMISSION_ATTEMPT_RETRY_LIMIT,
    feedback_service,
    grading_service,
)
from ...core.compression import compress_text, decompress_text
from ...core.db import get_session
from ...models.schemas import (
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
from ..homework.helpers import load_allowed_languages
from ..shared.schedules import compute_schedule_window
from ..submissions.helpers import to_submission_read
from ...services.user_management import ADMIN_ROLES


router = APIRouter()


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Homework not found")

    language = payload.language.strip().lower()
    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported submission language",
        )

    allowed_languages = load_allowed_languages(session, payload.homework_num)
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

    schedule_status, can_submit = compute_schedule_window(homework.starttime, homework.deadline)
    if not can_submit:
        detail = (
            "Submission window has not opened"
            if schedule_status == "upcoming"
            else "Submission deadline has passed"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

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

        submission = Submission(
            homework_num=payload.homework_num,
            user_id=current_user.id,
            submission_mode="official",
            attempt_no=attempt_no,
            language=language,
            status="pending",
            code_text=payload.code_text,
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
            session.commit()
        except IntegrityError:
            session.rollback()
            continue

        session.refresh(submission)

        try:
            homework = session.get(Homework, submission.homework_num)
            if homework is not None:
                submission.status = "grading"
                result_obj = session.exec(
                    select(SubmissionResult).where(
                        SubmissionResult.submission_id == submission.id
                    )
                ).first()
                if result_obj is not None:
                    result_obj.status = "grading"
                    result_obj.grader_summary = "Grading in progress."
                    session.add(result_obj)
                session.add(submission)
                session.commit()

                grading_service.grade_submission(session, submission, homework)
                session.refresh(submission)
        except Exception as grading_error:
            session.rollback()
            submission = session.get(Submission, submission.id)
            if submission is not None:
                result_obj = session.exec(
                    select(SubmissionResult).where(
                        SubmissionResult.submission_id == submission.id
                    )
                ).first()
                submission.status = "retryable"
                if result_obj is not None:
                    result_obj.status = "retryable"
                    result_obj.grader_summary = f"Auto-grading failed: {grading_error}"
                    session.add(result_obj)
                session.add(submission)
                session.commit()
                session.refresh(submission)
            logging.getLogger(__name__).warning(
                "Auto-grading failed for submission %s: %s",
                submission.id if submission else "?",
                grading_error,
            )

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
    return [to_submission_read(session, submission) for submission in submissions]


@router.get("/submissions/{submission_id}", response_model=SubmissionRead)
def get_submission_detail(
    submission_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    submission = session.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    is_staff_user = current_user.user_group in ADMIN_ROLES
    if submission.user_id != current_user.id and not is_staff_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot access this submission",
        )

    return to_submission_read(session, submission)


@router.get("/submissions/{submission_id}/feedback", response_model=SubmissionFeedbackRead)
def get_submission_feedback(
    submission_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    submission = session.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    is_staff_user = current_user.user_group in ADMIN_ROLES
    if submission.user_id != current_user.id and not is_staff_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot access this submission",
        )

    homework = session.get(Homework, submission.homework_num)
    if homework is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Homework not found")
    result = session.exec(
        select(SubmissionResult).where(SubmissionResult.submission_id == submission_id)
    ).first()
    return feedback_service.build_submission_feedback(session, submission, homework, result)


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Homework not found")

    last_snapshot = session.exec(
        select(CodeSnapshot)
        .where(
            CodeSnapshot.homework_num == payload.homework_num,
            CodeSnapshot.user_id == current_user.id,
        )
        .order_by(CodeSnapshot.created_at.desc())
    ).first()

    if last_snapshot and decompress_text(last_snapshot.code_text) == payload.code_text:
        last_snapshot.code_text = payload.code_text
        return last_snapshot

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
    snapshot.code_text = decompress_text(snapshot.code_text)
    return snapshot


@router.get("/homeworks/{homework_num}/snapshots/latest", response_model=CodeSnapshotRead | None)
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
        snapshot.code_text = decompress_text(snapshot.code_text)
    return snapshot


@router.get("/admin/homeworks/{homework_num}/snapshots/{user_id}", response_model=list[CodeSnapshotRead])
def get_student_snapshots(
    homework_num: int,
    user_id: str,
    _: User = Depends(require_staff),
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
    for s in snapshots:
        s.code_text = decompress_text(s.code_text)
    return snapshots
