from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sqlmodel import Session, select

from ..models.schemas import (
    AssignmentProblem,
    GradingRule,
    ProblemAsset,
    Submission,
    SubmissionFile,
)
from .artifact_store import LocalArtifactStore
from .course_bundle import CourseBundleService


@dataclass(frozen=True)
class LegacyBackfillReport:
    migrated: int
    already_migrated: int
    missing: list[str]
    invalid: list[str]

    @property
    def valid(self) -> bool:
        return not self.missing and not self.invalid


class LegacyArtifactBackfillService:
    METADATA_KINDS = {
        "problem_file_meta": "statement",
        "input_zip_meta": "legacy_input_archive",
        "output_zip_meta": "legacy_output_archive",
    }

    def __init__(
        self,
        store: LocalArtifactStore | None = None,
        legacy_root: Path | None = None,
    ):
        self.store = store or LocalArtifactStore()
        self.legacy_root = (legacy_root or self.store.root.parent).resolve()

    def run(self, session: Session) -> LegacyBackfillReport:
        migrated = 0
        already = 0
        missing: list[str] = []
        invalid: list[str] = []
        for row in session.exec(select(Submission)).all():
            result = self._migrate_storage_row(row)
            migrated += result == "migrated"
            already += result == "already"
            if result and result.startswith("missing:"):
                missing.append(result.removeprefix("missing:"))
            if result and result.startswith("invalid:"):
                invalid.append(result.removeprefix("invalid:"))
        for row in session.exec(select(SubmissionFile)).all():
            result = self._migrate_storage_row(row)
            migrated += result == "migrated"
            already += result == "already"
            if result and result.startswith("missing:"):
                missing.append(result.removeprefix("missing:"))
            if result and result.startswith("invalid:"):
                invalid.append(result.removeprefix("invalid:"))
        for rule in session.exec(
            select(GradingRule).where(
                GradingRule.rule_name.in_(list(self.METADATA_KINDS))
            )
        ).all():
            result = self._migrate_metadata_rule(session, rule)
            migrated += result == "migrated"
            already += result == "already"
            if result and result.startswith("missing:"):
                missing.append(result.removeprefix("missing:"))
            if result and result.startswith("invalid:"):
                invalid.append(result.removeprefix("invalid:"))
        # Persist the reversible reference switch first. Legacy sources remain
        # untouched and are not declared held until a complete bundle-wide
        # reconciliation proves every referenced object exists and matches.
        session.commit()
        reconciliation = CourseBundleService(self.store).reconcile(session)
        if not missing and not invalid and reconciliation.valid:
            for row in session.exec(select(Submission)).all():
                if row.legacy_storage_status == "pending_reconciliation":
                    row.legacy_storage_status = "held"
                    session.add(row)
            for row in session.exec(select(SubmissionFile)).all():
                if row.legacy_storage_status == "pending_reconciliation":
                    row.legacy_storage_status = "held"
                    session.add(row)
            session.commit()
        else:
            missing.extend(reconciliation.missing)
            invalid.extend(reconciliation.checksum_mismatch)
        return LegacyBackfillReport(
            migrated, already, sorted(missing), sorted(invalid)
        )

    def _legacy_path(self, value: str) -> Path:
        raw = Path(value)
        candidate = (
            raw.resolve()
            if raw.is_absolute()
            else (self.legacy_root / raw).resolve()
        )
        if not raw.is_absolute() and self.legacy_root not in candidate.parents:
            raise ValueError(value)
        return candidate

    def _migrate_storage_row(self, row) -> str | None:
        if not row.storage_path:
            return None
        if row.storage_sha256:
            self.store.resolve(row.storage_path, row.storage_sha256)
            return "already"
        try:
            source = self._legacy_path(row.storage_path)
        except ValueError:
            return f"invalid:{row.storage_path}"
        if not source.is_file():
            return f"missing:{row.storage_path}"
        with source.open("rb") as stream:
            stored = self.store.put_stream(stream)
        row.legacy_storage_path = row.storage_path
        row.legacy_storage_status = "pending_reconciliation"
        row.storage_path = stored.relative_path
        row.storage_sha256 = stored.sha256
        return "migrated"

    def _migrate_metadata_rule(
        self, session: Session, rule: GradingRule
    ) -> str:
        try:
            metadata = json.loads(rule.rule_value)
            relative = metadata["stored_relpath"]
            source = self._legacy_path(relative)
        except ValueError, KeyError, TypeError, json.JSONDecodeError:
            return f"invalid:grading_rule:{rule.id}"
        assignment = session.exec(
            select(AssignmentProblem)
            .where(AssignmentProblem.homework_num == rule.homework_num)
            .order_by(AssignmentProblem.position)
        ).first()
        if assignment is None:
            return f"invalid:grading_rule:{rule.id}:no_revision"
        existing = session.exec(
            select(ProblemAsset).where(
                ProblemAsset.revision_id == assignment.revision_id,
                ProblemAsset.asset_kind == self.METADATA_KINDS[rule.rule_name],
                ProblemAsset.display_name
                == metadata.get("original_name", source.name),
            )
        ).first()
        if existing is not None:
            return "already"
        if not source.is_file():
            return f"missing:{relative}"
        with source.open("rb") as stream:
            stored = self.store.put_stream(stream)
        session.add(
            ProblemAsset(
                revision_id=assignment.revision_id,
                asset_kind=self.METADATA_KINDS[rule.rule_name],
                display_name=metadata.get("original_name", source.name),
                storage_path=stored.relative_path,
                sha256=stored.sha256,
                size_bytes=stored.size_bytes,
                content_type=metadata.get("content_type"),
                is_hidden=True,
            )
        )
        return "migrated"
