from __future__ import annotations

import json
import logging
from typing import Any

from sqlmodel import Session, select

from ..models.schemas import AuditLog, AuditLogRead, SystemEventLog, SystemEventLogRead

logger = logging.getLogger(__name__)


class ObservabilityService:
    def log_event(
        self,
        session: Session,
        *,
        category: str,
        level: str,
        event_type: str,
        message: str,
        submission_id: int | None = None,
        user_id: str | None = None,
        request_path: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> SystemEventLog:
        event = SystemEventLog(
            category=category,
            level=level,
            event_type=event_type,
            message=message,
            submission_id=submission_id,
            user_id=user_id,
            request_path=request_path,
            context_json=(
                json.dumps(context, ensure_ascii=False, sort_keys=True)
                if context
                else None
            ),
        )
        session.add(event)

        log_method = getattr(logger, level.lower(), logger.info)
        log_method(
            "%s[%s] %s submission_id=%s user_id=%s",
            category,
            event_type,
            message,
            submission_id,
            user_id,
        )
        return event

    def record_audit(
        self,
        session: Session,
        *,
        actor_user_id: str | None,
        action_type: str,
        target_type: str,
        target_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> AuditLog:
        audit_log = AuditLog(
            actor_user_id=actor_user_id,
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            payload_json=(
                json.dumps(payload, ensure_ascii=False, sort_keys=True)
                if payload
                else None
            ),
        )
        session.add(audit_log)
        return audit_log

    def list_events(
        self,
        session: Session,
        *,
        category: str | None = None,
        limit: int = 20,
    ) -> list[SystemEventLogRead]:
        statement = select(SystemEventLog)
        if category:
            statement = statement.where(SystemEventLog.category == category)
        events = session.exec(
            statement.order_by(SystemEventLog.created_at.desc(), SystemEventLog.id.desc()).limit(limit)
        ).all()
        return [self.to_event_read(event) for event in events]

    def list_audit_logs(self, session: Session, *, limit: int = 50) -> list[AuditLogRead]:
        audit_logs = session.exec(
            select(AuditLog)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(limit)
        ).all()
        return [self.to_audit_read(log) for log in audit_logs]

    def to_event_read(self, event: SystemEventLog) -> SystemEventLogRead:
        return SystemEventLogRead(
            id=event.id or 0,
            category=event.category,
            level=event.level,
            event_type=event.event_type,
            message=event.message,
            submission_id=event.submission_id,
            user_id=event.user_id,
            request_path=event.request_path,
            context_json=event.context_json,
            created_at=event.created_at,
        )

    def to_audit_read(self, audit_log: AuditLog) -> AuditLogRead:
        return AuditLogRead(
            id=audit_log.id or 0,
            actor_user_id=audit_log.actor_user_id,
            action_type=audit_log.action_type,
            target_type=audit_log.target_type,
            target_id=audit_log.target_id,
            payload_json=audit_log.payload_json,
            created_at=audit_log.created_at,
        )
