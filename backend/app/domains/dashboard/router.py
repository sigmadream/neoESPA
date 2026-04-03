from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ...api.dependencies import get_current_active_user
from ...core.db import get_session
from ...models.schemas import Homework, StudentDashboardOverview, StudentDashboardRead, Submission, User
from ..dashboard.helpers import to_student_dashboard_homework_item
from ..homework.helpers import to_homework_read
from ..shared.schedules import compute_schedule_window
from ..submissions.helpers import build_submission_result_map, to_submission_read
from ..users.serializers import is_staff


router = APIRouter()


@router.get("/dashboard/me", response_model=StudentDashboardRead)
def get_student_dashboard(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    homeworks = session.exec(select(Homework).order_by(Homework.num)).all()
    visible_homeworks: list[Homework] = []

    for homework in homeworks:
        schedule_status, _ = compute_schedule_window(homework.starttime, homework.deadline)
        if schedule_status == "upcoming" and not is_staff(current_user):
            continue
        visible_homeworks.append(homework)

    submissions = session.exec(
        select(Submission)
        .where(Submission.user_id == current_user.id)
        .order_by(Submission.submitted_at.desc(), Submission.id.desc())
    ).all()
    submissions_by_homework: dict[int, list[Submission]] = {}
    for submission in submissions:
        submissions_by_homework.setdefault(submission.homework_num, []).append(submission)

    result_by_submission_id = build_submission_result_map(session, submissions)
    homework_items = [
        to_student_dashboard_homework_item(
            homework,
            submissions_by_homework.get(homework.num or 0, []),
            result_by_submission_id,
        )
        for homework in visible_homeworks
    ]

    latest_scores = [
        item.latest_score for item in homework_items if item.latest_score is not None
    ]
    overview = StudentDashboardOverview(
        total_homeworks=len(homework_items),
        submitted_homeworks=sum(1 for item in homework_items if item.submission_count > 0),
        graded_homeworks=sum(
            1
            for item in homework_items
            if item.latest_submission_status in {"graded", "success", "passed"}
        ),
        pending_homeworks=sum(
            1
            for item in homework_items
            if item.latest_submission_status in {"pending", "queued", "grading"}
        ),
        missing_homeworks=sum(
            1
            for item in homework_items
            if item.schedule_status == "closed" and item.submission_count == 0
        ),
        closing_soon_homeworks=sum(
            1 for item in homework_items if item.schedule_status == "closing_soon"
        ),
        average_latest_score=(
            round(sum(latest_scores) / len(latest_scores), 2)
            if latest_scores
            else None
        ),
    )

    return StudentDashboardRead(
        generated_at=datetime.now(UTC),
        overview=overview,
        homework_items=homework_items,
        recent_submissions=[
            to_submission_read(session, submission) for submission in submissions[:5]
        ],
    )
