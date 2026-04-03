from datetime import UTC, datetime

from sqlmodel import Session, select

from ...models.schemas import Homework, Submission, SubmissionRead, SubmissionResult


def get_or_create_submission_result(
    session: Session,
    submission_id: int,
) -> SubmissionResult:
    result = session.exec(
        select(SubmissionResult).where(SubmissionResult.submission_id == submission_id)
    ).first()
    if result is not None:
        return result

    result = SubmissionResult(submission_id=submission_id)
    session.add(result)
    session.flush()
    return result


def effective_total_score(result: SubmissionResult | None) -> float:
    if result is None:
        return 0.0
    if result.manual_total_score is not None:
        return result.manual_total_score
    return result.total_score


def to_submission_read(session: Session, submission: Submission) -> SubmissionRead:
    result = session.exec(
        select(SubmissionResult).where(SubmissionResult.submission_id == submission.id)
    ).first()
    homework = session.get(Homework, submission.homework_num)

    return SubmissionRead(
        id=submission.id or 0,
        homework_num=submission.homework_num,
        homework_title=homework.title if homework is not None else None,
        user_id=submission.user_id,
        submission_mode=submission.submission_mode,
        attempt_no=submission.attempt_no,
        language=submission.language,
        status=submission.status,
        original_filename=submission.original_filename,
        deadline_snapshot=submission.deadline_snapshot,
        submitted_at=submission.submitted_at,
        total_score=effective_total_score(result),
        submission_score=result.submission_score if result is not None else 0.0,
        quality_score=result.quality_score if result is not None else 0.0,
        compile_status=result.compile_status if result is not None else "not_started",
        run_status=result.run_status if result is not None else "not_started",
        grader_summary=result.grader_summary if result is not None else None,
        manual_total_score=result.manual_total_score if result is not None else None,
        score_adjustment_note=result.adjustment_note if result is not None else None,
        score_adjusted_at=result.adjusted_at if result is not None else None,
        score_adjusted_by=result.adjusted_by if result is not None else None,
    )


def build_submission_result_map(
    session: Session,
    submissions: list[Submission],
) -> dict[int, SubmissionResult]:
    submission_ids = [submission.id for submission in submissions if submission.id is not None]
    if not submission_ids:
        return {}

    results = session.exec(
        select(SubmissionResult).where(SubmissionResult.submission_id.in_(submission_ids))
    ).all()
    return {result.submission_id: result for result in results}


def dashboard_score_for_submission(
    submission: Submission | None,
    result: SubmissionResult | None,
) -> float | None:
    if submission is None or result is None:
        return None
    if submission.status in {"pending", "queued", "grading"}:
        return None
    return effective_total_score(result)
