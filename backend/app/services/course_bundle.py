from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlmodel import Session, select

from ..models.schemas import JudgeJob, ProblemAsset, Submission, SubmissionFile
from .artifact_store import LocalArtifactStore

BUNDLE_FORMAT_VERSION = "1"


@dataclass(frozen=True)
class ReconciliationReport:
    referenced: int
    present: int
    missing: list[str]
    checksum_mismatch: list[str]
    orphan: list[str]

    @property
    def valid(self) -> bool:
        return not self.missing and not self.checksum_mismatch


class CourseBundleService:
    def __init__(self, store: LocalArtifactStore | None = None):
        self.store = store or LocalArtifactStore()

    def initialize(self) -> None:
        self.store.initialize()
        for name in ("database", "manifests", "exports", "snapshots"):
            (self.store.root / name).mkdir(
                parents=True, exist_ok=True, mode=0o700
            )
        version = self.store.root / "VERSION"
        if not version.exists():
            version.write_text(BUNDLE_FORMAT_VERSION + "\n", encoding="utf-8")
            version.chmod(0o600)

    def reconcile(self, session: Session) -> ReconciliationReport:
        self.initialize()
        assets = session.exec(select(ProblemAsset)).all()
        expected = {asset.storage_path: asset.sha256 for asset in assets}
        for submission in session.exec(select(Submission)).all():
            if submission.storage_path and submission.storage_sha256:
                expected[submission.storage_path] = submission.storage_sha256
        for submission_file in session.exec(select(SubmissionFile)).all():
            if submission_file.storage_path and submission_file.storage_sha256:
                expected[submission_file.storage_path] = (
                    submission_file.storage_sha256
                )
        missing: list[str] = []
        mismatch: list[str] = []
        present = 0
        for relative_path, expected_hash in expected.items():
            path = self.store.root / relative_path
            if not path.is_file():
                missing.append(relative_path)
                continue
            present += 1
            if expected_hash:
                actual = hashlib.sha256(path.read_bytes()).hexdigest()
                if actual != expected_hash:
                    mismatch.append(relative_path)
        stored = {
            path.relative_to(self.store.root).as_posix()
            for path in self.store.objects_root.glob("*/*")
            if path.is_file()
        }
        return ReconciliationReport(
            referenced=len(expected),
            present=present,
            missing=sorted(missing),
            checksum_mismatch=sorted(mismatch),
            orphan=sorted(stored - set(expected)),
        )

    def create_snapshot(
        self,
        database_path: Path,
        *,
        course_id: str,
        term: str,
        schema_version: str,
    ) -> Path:
        self.initialize()
        if not database_path.is_file():
            raise FileNotFoundError(database_path)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        snapshot = self.store.root / "snapshots" / f"course-{timestamp}.sqlite3"
        source = sqlite3.connect(database_path)
        destination = sqlite3.connect(snapshot)
        try:
            source.backup(destination)
        finally:
            destination.close()
            source.close()
        snapshot.chmod(0o600)
        objects = []
        checksum_lines = []
        for path in sorted(self.store.objects_root.glob("*/*")):
            if not path.is_file():
                continue
            relative = path.relative_to(self.store.root).as_posix()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            objects.append(
                {
                    "path": relative,
                    "sha256": digest,
                    "size_bytes": path.stat().st_size,
                }
            )
            checksum_lines.append(f"{digest}  {relative}")
        snapshot_digest = hashlib.sha256(snapshot.read_bytes()).hexdigest()
        snapshot_relative = snapshot.relative_to(self.store.root).as_posix()
        checksum_lines.append(f"{snapshot_digest}  {snapshot_relative}")
        manifests = self.store.root / "manifests"
        (manifests / "course.json").write_text(
            json.dumps(
                {
                    "course_id": course_id,
                    "term": term,
                    "exported_at": datetime.now(UTC).isoformat(),
                    "schema_version": schema_version,
                    "artifact_format_version": BUNDLE_FORMAT_VERSION,
                    "database_snapshot": snapshot_relative,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        (manifests / "objects.jsonl").write_text(
            "".join(
                json.dumps(item, sort_keys=True) + "\n" for item in objects
            ),
            encoding="utf-8",
        )
        (manifests / "checksums.sha256").write_text(
            "\n".join(checksum_lines) + "\n", encoding="utf-8"
        )
        for path in manifests.iterdir():
            if path.is_file():
                path.chmod(0o600)
        return snapshot

    def create_operational_snapshot(
        self,
        session: Session,
        database_path: Path,
        *,
        course_id: str,
        term: str,
        schema_version: str,
        write_frozen: bool = False,
    ) -> Path:
        active_jobs = session.exec(
            select(JudgeJob.id)
            .where(JudgeJob.status.in_(["queued", "leased", "running"]))
            .limit(1)
        ).first()
        if active_jobs is not None and not write_frozen:
            raise ValueError(
                "Queue must be idle or course writes must be frozen before snapshot"
            )
        # Checkpoint only while the coordinator is idle/frozen. SQLite Backup
        # remains the actual snapshot mechanism, so no WAL file is copied alone.
        session.connection().exec_driver_sql("PRAGMA wal_checkpoint(PASSIVE)")
        session.commit()
        return self.create_snapshot(
            database_path,
            course_id=course_id,
            term=term,
            schema_version=schema_version,
        )

    def verify(self) -> list[str]:
        self.initialize()
        errors: list[str] = []
        checksums = self.store.root / "manifests" / "checksums.sha256"
        course = self.store.root / "manifests" / "course.json"
        if not checksums.is_file() or not course.is_file():
            return ["Bundle manifests are incomplete"]
        try:
            metadata = json.loads(course.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as error:
            return [f"course.json is invalid: {error}"]
        if metadata.get("artifact_format_version") != BUNDLE_FORMAT_VERSION:
            errors.append("Unsupported artifact format version")
        for line in checksums.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                expected, relative = line.split("  ", 1)
            except ValueError:
                errors.append("Malformed checksum line")
                continue
            path = (self.store.root / relative).resolve()
            if self.store.root not in path.parents or not path.is_file():
                errors.append(f"Missing bundle file: {relative}")
                continue
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                errors.append(f"Checksum mismatch: {relative}")
        return errors

    def restore_snapshot(
        self, target: Path, *, replace: bool = False
    ) -> dict[str, int]:
        errors = self.verify()
        if errors:
            raise ValueError("Bundle verification failed: " + "; ".join(errors))
        target = target.resolve()
        if target.exists() and not replace:
            raise FileExistsError(f"Restore target already exists: {target}")
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        metadata = json.loads(
            (self.store.root / "manifests" / "course.json").read_text(
                encoding="utf-8"
            )
        )
        snapshot = (self.store.root / metadata["database_snapshot"]).resolve()
        if self.store.root not in snapshot.parents:
            raise ValueError("Database snapshot path escapes bundle")
        source = sqlite3.connect(f"file:{snapshot}?mode=ro", uri=True)
        destination = sqlite3.connect(target)
        try:
            source.backup(destination)
            integrity = destination.execute("PRAGMA integrity_check").fetchone()
            if integrity is None or integrity[0] != "ok":
                raise ValueError(
                    "Restored SQLite database failed integrity_check"
                )
            tables = destination.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            counts = {}
            for (name,) in tables:
                quoted_name = name.replace('"', '""')
                counts[name] = destination.execute(
                    f'SELECT COUNT(*) FROM "{quoted_name}"'
                ).fetchone()[0]
        finally:
            destination.close()
            source.close()
        target.chmod(0o600)
        return counts

    @staticmethod
    def report_json(report: ReconciliationReport) -> str:
        return json.dumps(
            asdict(report), ensure_ascii=False, indent=2, sort_keys=True
        )
