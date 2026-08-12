from datetime import UTC, datetime

from ...models.schemas import (
    Homework,
    StudentDashboardHomeworkItem,
    Submission,
    SubmissionResult,
)
from ..shared.schedules import compute_schedule_window, parse_datetime
from ..submissions.helpers import dashboard_score_for_submission


def to_student_dashboard_homework_item(
    homework: Homework,
    submissions: list[Submission],
    result_by_submission_id: dict[int, SubmissionResult],
) -> StudentDashboardHomeworkItem:
    schedule_status, can_submit = compute_schedule_window(
        homework.starttime, homework.deadline
    )
    latest_submission = submissions[0] if submissions else None
    latest_result = (
        result_by_submission_id.get(latest_submission.id or 0)
        if latest_submission is not None
        else None
    )
    deadline_at = parse_datetime(homework.deadline)
    remaining_seconds = None
    if deadline_at is not None:
        remaining_seconds = max(
            0,
            int((deadline_at - datetime.now(UTC)).total_seconds()),
        )

    return StudentDashboardHomeworkItem(
        homework_num=homework.num or 0,
        title=homework.title,
        deadline=homework.deadline,
        starttime=homework.starttime,
        schedule_status=schedule_status,
        can_submit=can_submit,
        submission_count=len(submissions),
        latest_submission_id=(
            latest_submission.id if latest_submission is not None else None
        ),
        latest_submission_status=(
            latest_submission.status if latest_submission is not None else None
        ),
        latest_submission_at=(
            latest_submission.submitted_at
            if latest_submission is not None
            else None
        ),
        latest_score=dashboard_score_for_submission(
            latest_submission, latest_result
        ),
        latest_language=(
            latest_submission.language
            if latest_submission is not None
            else None
        ),
        remaining_seconds=remaining_seconds,
        grader_summary=(
            latest_result.grader_summary if latest_result is not None else None
        ),
    )
