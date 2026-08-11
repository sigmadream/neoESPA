from datetime import UTC, datetime

from sqlmodel import Session, select

from ...api.runtime import observability_service
from ...models.schemas import (
    AdminDashboardFailureMetric,
    AdminDashboardHomeworkMetric,
    AdminDashboardQueueStatus,
    AdminDashboardRead,
    Homework,
    JudgeJob,
    Submission,
    User,
)
from ..submissions.helpers import build_submission_result_map, effective_total_score


def build_admin_dashboard(session: Session) -> AdminDashboardRead:
    students = session.exec(
        select(User).where(User.user_group == "student", User.is_active.is_(True))
    ).all()
    homeworks = session.exec(select(Homework).order_by(Homework.num)).all()
    submissions = session.exec(
        select(Submission).order_by(Submission.submitted_at.desc(), Submission.id.desc())
    ).all()
    result_by_submission_id = build_submission_result_map(session, submissions)
    latest_by_homework_user: dict[tuple[int, str], Submission] = {}

    for submission in submissions:
        latest_by_homework_user.setdefault((submission.homework_num, submission.user_id), submission)

    homework_metrics: list[AdminDashboardHomeworkMetric] = []
    for homework in homeworks:
        latest_submissions = [
            submission
            for (homework_num, _), submission in latest_by_homework_user.items()
            if homework_num == (homework.num or 0)
        ]
        latest_results = [
            result_by_submission_id.get(submission.id or 0)
            for submission in latest_submissions
        ]
        latest_scores = [
            effective_total_score(result)
            for submission, result in zip(latest_submissions, latest_results, strict=False)
            if result is not None and submission.status not in {"pending", "queued", "grading"}
        ]
        submitted_students = len({submission.user_id for submission in latest_submissions})
        homework_metrics.append(
            AdminDashboardHomeworkMetric(
                homework_num=homework.num or 0,
                title=homework.title,
                submission_rate=(
                    round(submitted_students / len(students) * 100, 2)
                    if students
                    else 0.0
                ),
                total_students=len(students),
                submitted_students=submitted_students,
                average_latest_score=(
                    round(sum(latest_scores) / len(latest_scores), 2)
                    if latest_scores
                    else None
                ),
                failed_submission_count=sum(
                    1
                    for submission in latest_submissions
                    if submission.status in {"failed", "retryable"}
                ),
                pending_submission_count=sum(
                    1
                    for submission in latest_submissions
                    if submission.status in {"pending", "queued", "grading"}
                ),
            )
        )

    failure_counts: dict[str, int] = {}
    for submission in submissions:
        result = result_by_submission_id.get(submission.id or 0)
        failure_type = None
        if submission.status == "retryable":
            failure_type = "queue_retryable"
        elif result is not None and result.compile_status == "failed":
            failure_type = "compile_failed"
        elif result is not None and result.run_status == "timeout":
            failure_type = "timeout"
        elif result is not None and result.run_status == "failed":
            failure_type = "runtime_failed"
        if failure_type:
            failure_counts[failure_type] = failure_counts.get(failure_type, 0) + 1

    queued_jobs = session.exec(
        select(JudgeJob).where(
            JudgeJob.job_type == "grade_submission",
            JudgeJob.status.in_(["queued", "leased", "running"]),
        ).order_by(JudgeJob.priority, JudgeJob.created_at)
    ).all()
    queued_submission_ids = [
        job.submission_id for job in queued_jobs if job.submission_id is not None
    ]
    return AdminDashboardRead(
        generated_at=datetime.now(UTC),
        total_homeworks=len(homeworks),
        active_students=len(students),
        total_submissions=len(submissions),
        queue=AdminDashboardQueueStatus(
            queue_size=len(queued_jobs),
            queued_submission_ids=queued_submission_ids,
        ),
        homework_metrics=homework_metrics,
        failure_metrics=[
            AdminDashboardFailureMetric(failure_type=key, count=value)
            for key, value in sorted(failure_counts.items())
        ],
        recent_events=observability_service.list_events(session, limit=8),
    )
