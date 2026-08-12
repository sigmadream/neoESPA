from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ...api.dependencies import get_current_active_user, get_optional_current_user, require_capability
from ...api.runtime import observability_service
from ...core.db import get_session
from ...models.schemas import Exam, ExamRead, ExamResult, ExamSubmission, ExamSubmissionCreate, ExamSubmissionRead, ExamWrite, User
from ...services.user_management import ADMIN_ROLES
from ..exams.helpers import load_exam_languages, normalize_exam_languages, to_exam_read, to_exam_submission_read
from ..shared.schedules import compute_schedule_window
from ..users.serializers import is_staff


router = APIRouter()


@router.get("/exams", response_model=list[ExamRead])
def list_exams(
    current_user: User | None = Depends(get_optional_current_user),
    session: Session = Depends(get_session),
):
    exams = session.exec(select(Exam).order_by(Exam.id.desc())).all()
    visible_exams: list[ExamRead] = []
    for exam in exams:
        schedule_status, _ = compute_schedule_window(exam.starttime, exam.deadline)
        if schedule_status == "upcoming" and not is_staff(current_user):
            continue
        visible_exams.append(to_exam_read(exam))
    return visible_exams


@router.post("/admin/exams", response_model=ExamRead)
def create_exam(
    payload: ExamWrite,
    current_user: User = Depends(require_capability("exam:manage")),
    session: Session = Depends(get_session),
):
    import json

    exam = Exam(
        title=payload.title,
        intro=payload.intro,
        codeName=payload.codeName,
        starttime=payload.starttime,
        deadline=payload.deadline,
        allowed_languages_json=json.dumps(normalize_exam_languages(payload.allowed_languages)),
        created_by=current_user.id,
        updated_at=datetime.now(UTC),
    )
    session.add(exam)
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="create_exam",
        target_type="exam",
        payload=payload.model_dump(),
    )
    session.commit()
    session.refresh(exam)
    return to_exam_read(exam)


@router.get("/exams/{exam_id}", response_model=ExamRead)
def get_exam(
    exam_id: int,
    current_user: User | None = Depends(get_optional_current_user),
    session: Session = Depends(get_session),
):
    exam = session.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    schedule_status, _ = compute_schedule_window(exam.starttime, exam.deadline)
    if schedule_status == "upcoming" and not is_staff(current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    return to_exam_read(exam)


@router.get("/exams/{exam_id}/submissions", response_model=list[ExamSubmissionRead])
def list_exam_submissions(
    exam_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    exam = session.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    submissions = session.exec(
        select(ExamSubmission)
        .where(ExamSubmission.exam_id == exam_id, ExamSubmission.user_id == current_user.id)
        .order_by(ExamSubmission.id.desc())
    ).all()

    return [to_exam_submission_read(s) for s in submissions]


@router.post(
    "/exams/{exam_id}/submit",
    response_model=ExamSubmissionRead,
    status_code=status.HTTP_201_CREATED,
)
def submit_exam(
    exam_id: int,
    payload: ExamSubmissionCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    exam = session.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    schedule_status, can_submit = compute_schedule_window(exam.starttime, exam.deadline)
    if not can_submit:
        detail = (
            "Exam has not opened yet"
            if schedule_status == "upcoming"
            else "Exam submission deadline has passed"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    language = payload.language.strip().lower()
    if language not in load_exam_languages(exam):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exam submission language is not allowed",
        )

    submission = ExamSubmission(
        exam_id=exam_id,
        user_id=current_user.id,
        language=language,
        code_text=payload.code_text,
        original_filename=payload.original_filename,
        status="submitted",
    )
    session.add(submission)
    session.flush()
    session.add(ExamResult(exam_submission_id=submission.id or 0))
    session.commit()
    session.refresh(submission)
    return to_exam_submission_read(submission)
