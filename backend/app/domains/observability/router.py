from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from ...api.dependencies import require_roles
from ...api.runtime import observability_service
from ...core.db import get_session
from ...models.schemas import AdminDashboardRead, AuditLogRead, SystemEventLogRead, User
from ...services.user_management import ADMIN_ROLES
from ..observability.helpers import build_admin_dashboard


router = APIRouter()


@router.get("/admin/dashboard", response_model=AdminDashboardRead)
def get_admin_dashboard(
    _: User = Depends(require_roles(*ADMIN_ROLES)),
    session: Session = Depends(get_session),
):
    return build_admin_dashboard(session)


@router.get("/admin/observability/events", response_model=list[SystemEventLogRead])
def list_system_events(
    category: str | None = Query(default=None),
    _: User = Depends(require_roles(*ADMIN_ROLES)),
    session: Session = Depends(get_session),
):
    return observability_service.list_events(session, category=category)


@router.get("/admin/audit-logs", response_model=list[AuditLogRead])
def list_audit_logs(
    _: User = Depends(require_roles("admin")),
    session: Session = Depends(get_session),
):
    return observability_service.list_audit_logs(session)
