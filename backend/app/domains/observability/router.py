from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from datetime import UTC, datetime

from ...api.dependencies import require_capability
from ...api.runtime import observability_service
from ...core.db import get_session
from ...core.config import settings
from ...models.schemas import (
    AdminDashboardRead,
    AuditLogRead,
    SystemEventLogRead,
    User,
    JudgeWorker,
)
from ..observability.helpers import build_admin_dashboard

router = APIRouter()


@router.get("/admin/health/judge")
def get_detailed_judge_health(
    _: User = Depends(require_capability("observability:read")),
    session: Session = Depends(get_session),
):
    now = datetime.now(UTC)
    online_workers = []
    for worker in session.exec(select(JudgeWorker)).all():
        heartbeat = worker.heartbeat_at
        if heartbeat.tzinfo is None:
            heartbeat = heartbeat.replace(tzinfo=UTC)
        if (
            worker.status in {"online", "draining"}
            and (now - heartbeat).total_seconds() <= 60
        ):
            online_workers.append(worker.worker_id)
    available = settings.AUTOMATIC_GRADING_AVAILABLE and bool(online_workers)
    return {
        "status": "ready" if available else "not_ready",
        "automatic_grading_enabled": settings.AUTO_GRADING_ENABLED,
        "sandbox_ready": settings.SANDBOX_READY,
        "online_workers": online_workers,
    }


@router.get("/admin/dashboard", response_model=AdminDashboardRead)
def get_admin_dashboard(
    _: User = Depends(require_capability("observability:read")),
    session: Session = Depends(get_session),
):
    return build_admin_dashboard(session)


@router.get(
    "/admin/observability/events", response_model=list[SystemEventLogRead]
)
def list_system_events(
    category: str | None = Query(default=None),
    _: User = Depends(require_capability("observability:read")),
    session: Session = Depends(get_session),
):
    return observability_service.list_events(session, category=category)


@router.get("/admin/audit-logs", response_model=list[AuditLogRead])
def list_audit_logs(
    actor_user_id: str | None = Query(default=None),
    action_type: str | None = Query(default=None),
    target_type: str | None = Query(default=None),
    target_id: str | None = Query(default=None),
    result: str | None = Query(default=None),
    request_id: str | None = Query(default=None),
    job_id: int | None = Query(default=None),
    cursor_id: int | None = Query(default=None, ge=1),
    created_after: datetime | None = Query(default=None),
    created_before: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    _: User = Depends(require_capability("audit:read")),
    session: Session = Depends(get_session),
):
    return observability_service.list_audit_logs(
        session,
        actor_user_id=actor_user_id,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        result=result,
        request_id=request_id,
        job_id=job_id,
        cursor_id=cursor_id,
        created_after=created_after,
        created_before=created_before,
        limit=limit,
    )
