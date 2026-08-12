from __future__ import annotations

import json
import logging
from typing import Any
from datetime import datetime

from sqlmodel import Session, select

from ..models.schemas import (
    AuditLog,
    AuditLogRead,
    SystemEventLog,
    SystemEventLogRead,
)
from ..core.request_context import request_id_context

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
        result: str = "success",
        request_id: str | None = None,
        job_id: int | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
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
            result=result,
            request_id=request_id or request_id_context.get(),
            job_id=job_id,
            before_json=(
                json.dumps(before, ensure_ascii=False, sort_keys=True)
                if before
                else None
            ),
            after_json=(
                json.dumps(after, ensure_ascii=False, sort_keys=True)
                if after
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
            statement.order_by(
                SystemEventLog.created_at.desc(), SystemEventLog.id.desc()
            ).limit(limit)
        ).all()
        return [self.to_event_read(event) for event in events]

    def list_audit_logs(
        self,
        session: Session,
        *,
        actor_user_id: str | None = None,
        action_type: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        result: str | None = None,
        request_id: str | None = None,
        job_id: int | None = None,
        cursor_id: int | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        limit: int = 50,
    ) -> list[AuditLogRead]:
        statement = select(AuditLog)
        if actor_user_id:
            statement = statement.where(AuditLog.actor_user_id == actor_user_id)
        if action_type:
            statement = statement.where(AuditLog.action_type == action_type)
        if target_type:
            statement = statement.where(AuditLog.target_type == target_type)
        if target_id:
            statement = statement.where(AuditLog.target_id == target_id)
        if result:
            statement = statement.where(AuditLog.result == result)
        if request_id:
            statement = statement.where(AuditLog.request_id == request_id)
        if job_id is not None:
            statement = statement.where(AuditLog.job_id == job_id)
        if cursor_id is not None:
            statement = statement.where(AuditLog.id < cursor_id)
        if created_after is not None:
            statement = statement.where(AuditLog.created_at >= created_after)
        if created_before is not None:
            statement = statement.where(AuditLog.created_at <= created_before)
        audit_logs = session.exec(
            statement.order_by(AuditLog.id.desc()).limit(limit)
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
            result=audit_log.result,
            request_id=audit_log.request_id,
            job_id=audit_log.job_id,
            before_json=audit_log.before_json,
            after_json=audit_log.after_json,
            created_at=audit_log.created_at,
        )
