from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

from sqlmodel import Session, select

from ..models.schemas import (
    AnalyticsConsent,
    GradingRun,
    Submission,
    SubmissionCaseResult,
    SystemEventLog,
    User,
)
from .artifact_store import LocalArtifactStore


class AnalyticsExportError(ValueError):
    pass


class AnalyticsExportService:
    def __init__(self, secret: str, root: Path | None = None):
        if len(secret.encode()) < 32:
            raise AnalyticsExportError(
                "Analytics HMAC secret must be at least 32 bytes"
            )
        self.secret = secret.encode()
        self.root = (root or LocalArtifactStore().root).resolve()

    def pseudonym(self, institutional_id: int) -> str:
        return hmac.new(
            self.secret, str(institutional_id).encode(), hashlib.sha256
        ).hexdigest()

    def export_jsonl(
        self, session: Session, *, purpose: str, policy_version: str
    ) -> dict[str, int]:
        export_root = self.root / "exports"
        export_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        users = session.exec(select(User)).all()
        eligible: dict[str, User] = {}
        eligible_scopes: dict[str, set[str]] = {}
        for user in users:
            latest = session.exec(
                select(AnalyticsConsent)
                .where(
                    AnalyticsConsent.user_id == user.id,
                    AnalyticsConsent.purpose == purpose,
                    AnalyticsConsent.policy_version == policy_version,
                )
                .order_by(
                    AnalyticsConsent.created_at.desc(),
                    AnalyticsConsent.id.desc(),
                )
            ).first()
            if latest is not None and latest.granted:
                scopes = set(json.loads(latest.scope_json))
                eligible_scopes[user.id] = scopes
                if "submissions" in scopes:
                    eligible[user.id] = user
        submissions = (
            session.exec(
                select(Submission).where(Submission.user_id.in_(list(eligible)))
            ).all()
            if eligible
            else []
        )
        submission_rows = [
            {
                "submission_id": submission.id,
                "learner_id": self.pseudonym(eligible[submission.user_id].sid),
                "homework_num": submission.homework_num,
                "problem_revision_id": submission.problem_revision_id,
                "attempt_no": submission.attempt_no,
                "language": submission.language,
                "status": submission.status,
                "submitted_at": submission.submitted_at.isoformat(),
            }
            for submission in submissions
        ]
        submission_ids = [row["submission_id"] for row in submission_rows]
        runs = (
            session.exec(
                select(GradingRun).where(
                    GradingRun.submission_id.in_(submission_ids)
                )
            ).all()
            if submission_ids
            else []
        )
        run_rows = [
            {
                "grading_run_id": run.id,
                "submission_id": run.submission_id,
                "problem_revision_id": run.problem_revision_id,
                "verdict": run.verdict,
                "score": run.score,
                "runtime_version": run.runtime_version,
                "checker_version": run.checker_version,
                "created_at": run.created_at.isoformat(),
            }
            for run in runs
        ]
        case_results = (
            session.exec(
                select(SubmissionCaseResult).where(
                    SubmissionCaseResult.submission_id.in_(submission_ids)
                )
            ).all()
            if submission_ids
            else []
        )
        case_rows = [
            {
                "submission_id": result.submission_id,
                "case_index": result.case_index,
                "passed": result.passed,
                "score_awarded": result.score_awarded,
                "runtime_ms": result.runtime_ms,
            }
            for result in case_results
        ]
        event_users = {
            user.id: user
            for user in users
            if "learning_events" in eligible_scopes.get(user.id, set())
        }
        events = (
            session.exec(
                select(SystemEventLog).where(
                    SystemEventLog.user_id.in_(list(event_users))
                )
            ).all()
            if event_users
            else []
        )
        event_rows = [
            {
                "event_id": event.id,
                "learner_id": self.pseudonym(event_users[event.user_id].sid),
                "category": event.category,
                "event_type": event.event_type,
                "submission_id": event.submission_id,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
            if event.user_id in event_users
        ]
        self._write_jsonl(export_root / "submissions.jsonl", submission_rows)
        self._write_jsonl(export_root / "grading_runs.jsonl", run_rows)
        self._write_jsonl(export_root / "testcase_results.jsonl", case_rows)
        self._write_jsonl(export_root / "learning_events.jsonl", event_rows)
        return {
            "submissions": len(submission_rows),
            "grading_runs": len(run_rows),
            "testcase_results": len(case_rows),
            "learning_events": len(event_rows),
        }

    @staticmethod
    def _write_jsonl(path: Path, rows: list[dict]) -> None:
        path.write_text(
            "".join(
                json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                for row in rows
            ),
            encoding="utf-8",
        )
        path.chmod(0o600)
