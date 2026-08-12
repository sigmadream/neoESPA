from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ...api.dependencies import require_capability
from ...api.runtime import observability_service
from ...core.db import get_session
from ...models.schemas import (
    JudgeJob,
    JudgeJobEvent,
    JudgeJobEventRead,
    JudgeJobRead,
    JudgeWorker,
    JudgeWorkerRead,
    GradingMetricsRead,
    GradingRun,
    RejudgeCreate,
    RejudgePreviewRead,
    RejudgeScope,
    Submission,
    ContestResultEvent,
    Contest,
    ContestOperationApproval,
    User,
)
from ...services.judge_job_service import JobConflictError, JudgeJobService

router = APIRouter(prefix="/admin")
job_service = JudgeJobService()


@router.post(
    "/artifact-jobs/reconcile", response_model=JudgeJobRead, status_code=202
)
def create_artifact_reconciliation_job(
    current_user: User = Depends(require_capability("judge:operate")),
    session: Session = Depends(get_session),
):
    now_key = datetime.now(UTC).strftime("%Y%m%d%H")
    job = job_service.enqueue(
        session,
        job_type="artifact_reconciliation",
        payload={"full": True},
        idempotency_key=f"artifact-reconciliation:{now_key}",
        priority=300,
    )
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="create_artifact_reconciliation",
        target_type="judge_job",
        target_id=str(job.id),
        job_id=job.id,
    )
    session.commit()
    session.refresh(job)
    return job_service.to_read(job)


@router.get("/artifact-jobs", response_model=list[JudgeJobRead])
def list_artifact_jobs(
    _current_user: User = Depends(require_capability("judge:operate")),
    session: Session = Depends(get_session),
):
    jobs = session.exec(
        select(JudgeJob)
        .where(JudgeJob.job_type == "artifact_reconciliation")
        .order_by(JudgeJob.id.desc())
        .limit(100)
    ).all()
    return [job_service.to_read(job) for job in jobs]


@router.get("/judge-workers", response_model=list[JudgeWorkerRead])
def list_judge_workers(
    _current_user: User = Depends(require_capability("judge:operate")),
    session: Session = Depends(get_session),
):
    workers = session.exec(
        select(JudgeWorker).order_by(JudgeWorker.worker_id)
    ).all()
    now = datetime.now(UTC)
    result: list[JudgeWorkerRead] = []
    for worker in workers:
        effective_status = worker.status
        heartbeat_at = worker.heartbeat_at
        if heartbeat_at.tzinfo is None:
            heartbeat_at = heartbeat_at.replace(tzinfo=UTC)
        if (
            now - heartbeat_at
        ).total_seconds() > 60 and worker.status == "online":
            effective_status = "offline"
        item = JudgeWorkerRead.model_validate(worker)
        item.status = effective_status
        result.append(item)
    return result


@router.post("/judge-workers/{worker_id}/drain", response_model=JudgeWorkerRead)
def drain_judge_worker(
    worker_id: str,
    current_user: User = Depends(require_capability("judge:operate")),
    session: Session = Depends(get_session),
):
    worker = session.get(JudgeWorker, worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Judge worker not found")
    worker.status = "draining"
    session.add(worker)
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="drain_judge_worker",
        target_type="judge_worker",
        target_id=worker_id,
    )
    session.commit()
    session.refresh(worker)
    return JudgeWorkerRead.model_validate(worker)


@router.post(
    "/judge-workers/{worker_id}/enable", response_model=JudgeWorkerRead
)
def enable_judge_worker(
    worker_id: str,
    current_user: User = Depends(require_capability("judge:operate")),
    session: Session = Depends(get_session),
):
    worker = session.get(JudgeWorker, worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Judge worker not found")
    worker.status = "online"
    session.add(worker)
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="enable_judge_worker",
        target_type="judge_worker",
        target_id=worker_id,
    )
    session.commit()
    session.refresh(worker)
    return JudgeWorkerRead.model_validate(worker)


@router.post(
    "/judge-workers/{worker_id}/disable", response_model=JudgeWorkerRead
)
def disable_judge_worker(
    worker_id: str,
    current_user: User = Depends(require_capability("judge:operate")),
    session: Session = Depends(get_session),
):
    worker = session.get(JudgeWorker, worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Judge worker not found")
    if worker.current_job_id is not None:
        raise HTTPException(
            status_code=409, detail="Drain worker before disabling it"
        )
    worker.status = "disabled"
    session.add(worker)
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="disable_judge_worker",
        target_type="judge_worker",
        target_id=worker_id,
    )
    session.commit()
    session.refresh(worker)
    return JudgeWorkerRead.model_validate(worker)


@router.get("/grading/metrics", response_model=GradingMetricsRead)
def grading_metrics(
    _current_user: User = Depends(require_capability("judge:operate")),
    session: Session = Depends(get_session),
):
    jobs = session.exec(select(JudgeJob.status)).all()
    workers = list_judge_workers(_current_user, session)
    job_rows = session.exec(select(JudgeJob)).all()
    wait_values = []
    for job in job_rows:
        if job.started_at is not None:
            created = job.created_at
            started = job.started_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=UTC)
            if started.tzinfo is None:
                started = started.replace(tzinfo=UTC)
            wait_values.append(
                max(0, (started - created).total_seconds() * 1000)
            )
    verdict_counts: dict[str, int] = {}
    for verdict in session.exec(select(GradingRun.verdict)).all():
        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
    problem_error_counts: dict[str, int] = {}
    for job in job_rows:
        if job.problem_id is not None and job.status in {
            "failed",
            "dead_letter",
        }:
            key = str(job.problem_id)
            problem_error_counts[key] = problem_error_counts.get(key, 0) + 1
    terminal = [
        job
        for job in job_rows
        if job.status in {"succeeded", "failed", "dead_letter"}
    ]
    failed_terminal = sum(
        job.status in {"failed", "dead_letter"} for job in terminal
    )
    return GradingMetricsRead(
        queued_jobs=jobs.count("queued"),
        running_jobs=sum(status in {"leased", "running"} for status in jobs),
        failed_jobs=jobs.count("failed"),
        dead_letter_jobs=jobs.count("dead_letter"),
        workers_online=sum(
            worker.status in {"online", "draining"} for worker in workers
        ),
        workers_offline=sum(worker.status == "offline" for worker in workers),
        average_queue_wait_ms=(
            round(sum(wait_values) / len(wait_values), 2)
            if wait_values
            else 0.0
        ),
        verdict_counts=verdict_counts,
        problem_error_counts=problem_error_counts,
        worker_failure_rate=(
            round(failed_terminal / len(terminal) * 100, 2) if terminal else 0.0
        ),
    )


def _rejudge_statement(scope: RejudgeScope):
    statement = select(Submission)
    if scope.problem_id is not None:
        from ...models.schemas import ProblemRevision

        revision_ids = select(ProblemRevision.id).where(
            ProblemRevision.problem_id == scope.problem_id
        )
        statement = statement.where(
            Submission.problem_revision_id.in_(revision_ids)
        )
    if scope.revision_id is not None:
        statement = statement.where(
            Submission.problem_revision_id == scope.revision_id
        )
    if scope.homework_num is not None:
        statement = statement.where(
            Submission.homework_num == scope.homework_num
        )
    if scope.contest_id is not None:
        contest_submission_ids = select(ContestResultEvent.submission_id).where(
            ContestResultEvent.contest_id == scope.contest_id
        )
        statement = statement.where(Submission.id.in_(contest_submission_ids))
    if scope.user_id is not None:
        statement = statement.where(Submission.user_id == scope.user_id)
    if scope.submission_ids:
        statement = statement.where(Submission.id.in_(scope.submission_ids))
    if scope.statuses:
        statement = statement.where(Submission.status.in_(scope.statuses))
    if scope.verdicts:
        run_submission_ids = select(GradingRun.submission_id).where(
            GradingRun.verdict.in_(scope.verdicts)
        )
        statement = statement.where(Submission.id.in_(run_submission_ids))
    if scope.submitted_after is not None:
        statement = statement.where(
            Submission.submitted_at >= scope.submitted_after
        )
    if scope.submitted_before is not None:
        statement = statement.where(
            Submission.submitted_at <= scope.submitted_before
        )
    return statement


@router.get("/judge-jobs", response_model=list[JudgeJobRead])
def list_judge_jobs(
    status: str | None = None,
    problem_id: int | None = None,
    worker_id: str | None = None,
    job_type: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    _current_user: User = Depends(require_capability("judge:operate")),
    session: Session = Depends(get_session),
):
    statement = select(JudgeJob)
    if status:
        statement = statement.where(JudgeJob.status == status)
    if problem_id is not None:
        statement = statement.where(JudgeJob.problem_id == problem_id)
    if worker_id:
        statement = statement.where(JudgeJob.lease_owner == worker_id)
    if job_type:
        statement = statement.where(JudgeJob.job_type == job_type)
    jobs = session.exec(
        statement.order_by(JudgeJob.id.desc()).limit(limit)
    ).all()
    return [job_service.to_read(job) for job in jobs]


@router.get("/grading/incidents", response_model=list[JudgeJobRead])
def list_grading_incidents(
    problem_id: int | None = None,
    worker_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    _current_user: User = Depends(require_capability("judge:operate")),
    session: Session = Depends(get_session),
):
    statement = select(JudgeJob).where(
        JudgeJob.status.in_(["failed", "dead_letter"])
    )
    if problem_id is not None:
        statement = statement.where(JudgeJob.problem_id == problem_id)
    if worker_id:
        statement = statement.where(JudgeJob.lease_owner == worker_id)
    jobs = session.exec(
        statement.order_by(
            JudgeJob.finished_at.desc(), JudgeJob.id.desc()
        ).limit(limit)
    ).all()
    return [job_service.to_read(job) for job in jobs]


@router.post("/rejudge-jobs/preview", response_model=RejudgePreviewRead)
def preview_rejudge(
    scope: RejudgeScope,
    _current_user: User = Depends(require_capability("submission:rejudge")),
    session: Session = Depends(get_session),
):
    ids = session.exec(
        _rejudge_statement(scope)
        .with_only_columns(Submission.id)
        .order_by(Submission.id)
    ).all()
    return RejudgePreviewRead(
        target_count=len(ids),
        submission_ids=ids[:1000],
        truncated=len(ids) > 1000,
    )


@router.post("/rejudge-jobs", response_model=JudgeJobRead, status_code=202)
def create_rejudge(
    payload: RejudgeCreate,
    current_user: User = Depends(require_capability("submission:rejudge")),
    session: Session = Depends(get_session),
):
    ids = session.exec(
        _rejudge_statement(payload)
        .with_only_columns(Submission.id)
        .order_by(Submission.id)
    ).all()
    contest_approval = None
    if payload.contest_id is not None:
        contest = session.get(Contest, payload.contest_id)
        if contest is None:
            raise HTTPException(status_code=404, detail="Contest not found")
        contest_approval = session.get(
            ContestOperationApproval, payload.contest_approval_id
        )
        if (
            contest_approval is None
            or contest_approval.contest_id != payload.contest_id
            or contest_approval.operation != "rejudge"
            or contest_approval.used_at is not None
        ):
            raise HTTPException(
                status_code=409,
                detail="Unused contest rejudge approval is required",
            )
    try:
        parent = job_service.enqueue(
            session,
            job_type="rejudge_batch",
            payload={
                "scope": payload.model_dump(
                    mode="json", exclude={"reason", "idempotency_key"}
                ),
                "reason": payload.reason,
                "target_count": len(ids),
            },
            idempotency_key=payload.idempotency_key,
            revision_id=payload.target_revision_id,
            priority=200,
        )
        existing_children = session.exec(
            select(JudgeJob.id).where(JudgeJob.parent_job_id == parent.id)
        ).first()
        if existing_children is None:
            for submission_id in ids:
                job_service.enqueue(
                    session,
                    job_type="grade_submission",
                    payload={
                        "submission_id": submission_id,
                        "target_revision_id": payload.target_revision_id,
                        "reason": payload.reason,
                    },
                    idempotency_key=f"{payload.idempotency_key}:submission:{submission_id}",
                    submission_id=submission_id,
                    revision_id=payload.target_revision_id,
                    parent_job_id=parent.id,
                    priority=200,
                )
        observability_service.record_audit(
            session,
            actor_user_id=current_user.id,
            action_type="create_rejudge_batch",
            target_type="judge_job",
            target_id=str(parent.id),
            payload={"target_count": len(ids), "reason": payload.reason},
        )
        if contest_approval is not None:
            contest_approval.used_by_job_id = parent.id
            contest_approval.used_at = datetime.now(UTC)
            session.add(contest_approval)
        session.commit()
        session.refresh(parent)
        return job_service.to_read(parent)
    except JobConflictError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/rejudge-jobs", response_model=list[JudgeJobRead])
def list_rejudge_jobs(
    limit: int = Query(default=100, ge=1, le=500),
    _current_user: User = Depends(require_capability("submission:rejudge")),
    session: Session = Depends(get_session),
):
    jobs = session.exec(
        select(JudgeJob)
        .where(JudgeJob.job_type == "rejudge_batch")
        .order_by(JudgeJob.id.desc())
        .limit(limit)
    ).all()
    return [job_service.to_read(job) for job in jobs]


@router.get("/rejudge-jobs/{job_id}", response_model=JudgeJobRead)
def get_rejudge_job(
    job_id: int,
    _current_user: User = Depends(require_capability("submission:rejudge")),
    session: Session = Depends(get_session),
):
    job = session.get(JudgeJob, job_id)
    if job is None or job.job_type != "rejudge_batch":
        raise HTTPException(status_code=404, detail="Rejudge job not found")
    children = session.exec(
        select(JudgeJob).where(JudgeJob.parent_job_id == job.id)
    ).all()
    if children:
        completed = sum(
            child.status in {"succeeded", "failed", "cancelled", "dead_letter"}
            for child in children
        )
        job.progress = round(completed * 100 / len(children), 2)
    return job_service.to_read(job)


@router.post("/rejudge-jobs/{job_id}/cancel", response_model=JudgeJobRead)
def cancel_rejudge_job(
    job_id: int,
    current_user: User = Depends(require_capability("submission:rejudge")),
    session: Session = Depends(get_session),
):
    parent = session.get(JudgeJob, job_id)
    if parent is None or parent.job_type != "rejudge_batch":
        raise HTTPException(status_code=404, detail="Rejudge job not found")
    children = session.exec(
        select(JudgeJob).where(
            JudgeJob.parent_job_id == parent.id,
            JudgeJob.status.in_(["queued", "leased"]),
        )
    ).all()
    for child in children:
        child.status = "cancelled"
        session.add(child)
    if parent.status in {"queued", "leased"}:
        parent.status = "cancelled"
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="cancel_rejudge_batch",
        target_type="judge_job",
        target_id=str(parent.id),
        payload={"cancelled_children": len(children)},
    )
    session.commit()
    session.refresh(parent)
    return job_service.to_read(parent)


@router.post("/rejudge-jobs/{job_id}/retry-failed", response_model=JudgeJobRead)
def retry_failed_rejudge_jobs(
    job_id: int,
    current_user: User = Depends(require_capability("submission:rejudge")),
    session: Session = Depends(get_session),
):
    parent = session.get(JudgeJob, job_id)
    if parent is None or parent.job_type != "rejudge_batch":
        raise HTTPException(status_code=404, detail="Rejudge job not found")
    children = session.exec(
        select(JudgeJob).where(
            JudgeJob.parent_job_id == parent.id,
            JudgeJob.status.in_(["failed", "dead_letter"]),
        )
    ).all()
    for child in children:
        job_service.retry(session, child, commit=False)
    if children and parent.status in {"failed", "dead_letter", "succeeded"}:
        parent.status = "running"
        parent.finished_at = None
        parent.progress = 0
        session.add(parent)
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="retry_failed_rejudge_jobs",
        target_type="judge_job",
        target_id=str(parent.id),
        payload={"retried_children": len(children)},
    )
    session.commit()
    session.refresh(parent)
    return job_service.to_read(parent)


@router.get("/problem-jobs", response_model=list[JudgeJobRead])
def list_problem_jobs(
    status: str | None = None,
    revision_id: int | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    _current_user: User = Depends(require_capability("judge:operate")),
    session: Session = Depends(get_session),
):
    statement = select(JudgeJob).where(
        JudgeJob.job_type == "problem_validation"
    )
    if status:
        statement = statement.where(JudgeJob.status == status)
    if revision_id:
        statement = statement.where(JudgeJob.revision_id == revision_id)
    jobs = session.exec(
        statement.order_by(JudgeJob.id.desc()).limit(limit)
    ).all()
    return [job_service.to_read(job) for job in jobs]


@router.get("/problem-jobs/{job_id}", response_model=JudgeJobRead)
def get_problem_job(
    job_id: int,
    _current_user: User = Depends(require_capability("judge:operate")),
    session: Session = Depends(get_session),
):
    job = session.get(JudgeJob, job_id)
    if job is None or job.job_type != "problem_validation":
        raise HTTPException(status_code=404, detail="Problem job not found")
    return job_service.to_read(job)


@router.get(
    "/problem-jobs/{job_id}/events", response_model=list[JudgeJobEventRead]
)
def get_problem_job_events(
    job_id: int,
    _current_user: User = Depends(require_capability("judge:operate")),
    session: Session = Depends(get_session),
):
    if session.get(JudgeJob, job_id) is None:
        raise HTTPException(status_code=404, detail="Problem job not found")
    events = session.exec(
        select(JudgeJobEvent)
        .where(JudgeJobEvent.job_id == job_id)
        .order_by(JudgeJobEvent.sequence_no)
    ).all()
    return [JudgeJobEventRead.model_validate(event) for event in events]


@router.post("/problem-jobs/{job_id}/cancel", response_model=JudgeJobRead)
def cancel_problem_job(
    job_id: int,
    _current_user: User = Depends(require_capability("judge:operate")),
    session: Session = Depends(get_session),
):
    job = session.get(JudgeJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Problem job not found")
    try:
        return job_service.to_read(job_service.cancel(session, job))
    except JobConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/problem-jobs/{job_id}/retry", response_model=JudgeJobRead)
def retry_problem_job(
    job_id: int,
    current_user: User = Depends(require_capability("judge:operate")),
    session: Session = Depends(get_session),
):
    job = session.get(JudgeJob, job_id)
    if job is None or job.job_type != "problem_validation":
        raise HTTPException(status_code=404, detail="Problem job not found")
    try:
        retried = job_service.retry(session, job)
        observability_service.record_audit(
            session,
            actor_user_id=current_user.id,
            action_type="retry_problem_job",
            target_type="judge_job",
            target_id=str(job.id),
        )
        session.commit()
        return job_service.to_read(retried)
    except JobConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
