import json

from ...models.schemas import Exam, ExamRead, ExamSubmission, ExamSubmissionRead
from ...services.code_runner import SUPPORTED_LANGUAGES
from ..homework.helpers import normalize_allowed_languages
from ..shared.schedules import compute_schedule_window


def normalize_exam_languages(raw_languages: list[str] | None) -> list[str]:
    return normalize_allowed_languages(raw_languages)


def load_exam_languages(exam: Exam) -> list[str]:
    try:
        loaded = json.loads(exam.allowed_languages_json)
    except json.JSONDecodeError:
        return sorted(SUPPORTED_LANGUAGES)

    if not isinstance(loaded, list):
        return sorted(SUPPORTED_LANGUAGES)
    return normalize_exam_languages(loaded)


def to_exam_read(exam: Exam) -> ExamRead:
    schedule_status, can_submit = compute_schedule_window(exam.starttime, exam.deadline)
    return ExamRead(
        id=exam.id or 0,
        title=exam.title,
        intro=exam.intro,
        codeName=exam.codeName,
        starttime=exam.starttime,
        deadline=exam.deadline,
        allowed_languages=load_exam_languages(exam),
        schedule_status=schedule_status,
        can_submit=can_submit,
        created_by=exam.created_by,
        created_at=exam.created_at,
        updated_at=exam.updated_at,
    )


def to_exam_submission_read(submission: ExamSubmission) -> ExamSubmissionRead:
    return ExamSubmissionRead(
        id=submission.id or 0,
        exam_id=submission.exam_id,
        user_id=submission.user_id,
        language=submission.language,
        status=submission.status,
        original_filename=submission.original_filename,
        submitted_at=submission.submitted_at,
    )
