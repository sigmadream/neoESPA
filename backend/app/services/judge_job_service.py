from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import update
from sqlmodel import Session, select

from ..models.schemas import (
    JUDGE_JOB_STATUSES,
    GradingRun,
    Homework,
    JudgeJob,
    JudgeJobEvent,
    JudgeJobRead,
    JudgeWorker,
    ProblemRevision,
    ProblemAsset,
    ProblemTestCase,
    TestCaseGroup,
    Submission,
    SubmissionResult,
)
from .grading_service import GradingService
from .artifact_store import LocalArtifactStore
from .checkers import get_checker
from .checkers import CheckerError, SpecialJudgeChecker
from ..core.config import settings
from .code_runner import NsJailCodeRunner
from .sandbox import NsJailLimits
from .course_bundle import CourseBundleService


class JobConflictError(ValueError):
    pass


class JudgeJobService:
    def __init__(self, grading_service: GradingService | None = None):
        self.grading_service = grading_service or GradingService()

    def enqueue(
        self,
        session: Session,
        *,
        job_type: str,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
        problem_id: int | None = None,
        revision_id: int | None = None,
        submission_id: int | None = None,
        parent_job_id: int | None = None,
        priority: int = 100,
    ) -> JudgeJob:
        canonical = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        payload_hash = hashlib.sha256(canonical.encode()).hexdigest()
        if idempotency_key:
            existing = session.exec(
                select(JudgeJob).where(
                    JudgeJob.idempotency_key == idempotency_key
                )
            ).first()
            if existing is not None:
                if (
                    existing.payload_hash != payload_hash
                    or existing.job_type != job_type
                ):
                    raise JobConflictError(
                        "Idempotency key was used with another payload"
                    )
                return existing
        job = JudgeJob(
            job_type=job_type,
            payload_json=canonical,
            payload_hash=payload_hash,
            idempotency_key=idempotency_key,
            problem_id=problem_id,
            revision_id=revision_id,
            submission_id=submission_id,
            parent_job_id=parent_job_id,
            priority=priority,
        )
        session.add(job)
        session.flush()
        self._event(session, job, "queued", "Job queued")
        return job

    def reclaim_expired(
        self, session: Session, now: datetime | None = None
    ) -> int:
        timestamp = now or datetime.now(UTC)
        expired = session.exec(
            select(JudgeJob).where(
                JudgeJob.status.in_(["leased", "running"]),
                JudgeJob.lease_expires_at < timestamp,
            )
        ).all()
        for job in expired:
            if job.attempt_count >= job.max_attempts:
                job.status = "dead_letter"
                job.finished_at = timestamp
                self._event(
                    session,
                    job,
                    "dead_letter",
                    "Lease expired after maximum attempts",
                )
            else:
                job.status = "queued"
                job.lease_owner = None
                job.lease_expires_at = None
                self._event(session, job, "requeued", "Expired lease reclaimed")
            session.add(job)
        return len(expired)

    def claim_next(
        self,
        session: Session,
        worker_id: str,
        *,
        lease_seconds: int = 30,
        job_types: list[str] | None = None,
        worker_capabilities: dict[str, Any] | None = None,
    ) -> JudgeJob | None:
        bind = session.get_bind()
        if bind.dialect.name == "sqlite" and not session.in_transaction():
            # Serialize the candidate read and conditional update across API
            # and worker processes. The transaction stays intentionally short.
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        now = datetime.now(UTC)
        worker = session.get(JudgeWorker, worker_id)
        if worker is None:
            worker = JudgeWorker(
                worker_id=worker_id,
                status="online",
                capabilities_json=json.dumps(
                    worker_capabilities or {"job_types": job_types or []},
                    sort_keys=True,
                ),
                heartbeat_at=now,
            )
        if worker.status in {"draining", "disabled"}:
            worker.heartbeat_at = now
            session.add(worker)
            session.commit()
            return None
        worker.status = "online"
        worker.heartbeat_at = now
        if worker_capabilities is not None:
            worker.capabilities_json = json.dumps(
                worker_capabilities, sort_keys=True
            )
        session.add(worker)
        self.reclaim_expired(session, now)
        statement = select(JudgeJob.id).where(JudgeJob.status == "queued")
        if job_types:
            statement = statement.where(JudgeJob.job_type.in_(job_types))
        candidate_id = session.exec(
            statement.order_by(
                JudgeJob.priority, JudgeJob.created_at, JudgeJob.id
            ).limit(1)
        ).first()
        if candidate_id is None:
            session.commit()
            return None
        result = session.exec(
            update(JudgeJob)
            .where(JudgeJob.id == candidate_id, JudgeJob.status == "queued")
            .values(
                status="leased",
                lease_owner=worker_id,
                lease_expires_at=now + timedelta(seconds=max(lease_seconds, 1)),
                heartbeat_at=now,
                lease_generation=JudgeJob.lease_generation + 1,
                attempt_count=JudgeJob.attempt_count + 1,
                started_at=now,
            )
        )
        if result.rowcount != 1:
            session.rollback()
            return None
        job = session.get(JudgeJob, candidate_id)
        if job is None:
            session.rollback()
            return None
        self._event(session, job, "leased", f"Claimed by {worker_id}")
        worker.current_job_id = job.id
        session.add(worker)
        session.commit()
        session.refresh(job)
        return job

    def start(
        self, session: Session, job: JudgeJob, worker_id: str, generation: int
    ) -> None:
        self._assert_lease(job, worker_id, generation)
        if job.status != "leased":
            raise JobConflictError("Only leased jobs can start")
        job.status = "running"
        self._event(session, job, "running", "Job started")
        session.add(job)
        session.commit()

    def heartbeat(
        self,
        session: Session,
        job_id: int,
        worker_id: str,
        generation: int,
        *,
        lease_seconds: int = 30,
        progress: float | None = None,
    ) -> JudgeJob:
        job = session.get(JudgeJob, job_id)
        if job is None:
            raise JobConflictError("Job not found")
        self._assert_lease(job, worker_id, generation)
        if job.status not in {"leased", "running"}:
            raise JobConflictError("Job is not active")
        now = datetime.now(UTC)
        job.heartbeat_at = now
        job.lease_expires_at = now + timedelta(seconds=max(lease_seconds, 1))
        if progress is not None:
            job.progress = min(99.0, max(job.progress, progress))
        worker = session.get(JudgeWorker, worker_id)
        if worker is not None:
            worker.heartbeat_at = now
            session.add(worker)
        session.add(job)
        session.commit()
        session.refresh(job)
        return job

    def complete(
        self,
        session: Session,
        job_id: int,
        worker_id: str,
        generation: int,
        result_payload: dict[str, Any],
    ) -> JudgeJob:
        job = session.get(JudgeJob, job_id)
        if job is None:
            raise JobConflictError("Job not found")
        self._assert_lease(job, worker_id, generation)
        if job.status not in {"leased", "running"}:
            raise JobConflictError("Job is not running")
        job.status = "succeeded"
        job.progress = 100
        job.result_json = json.dumps(
            result_payload, ensure_ascii=False, sort_keys=True
        )
        job.finished_at = datetime.now(UTC)
        self._event(session, job, "succeeded", "Job completed")
        session.add(job)
        worker = session.get(JudgeWorker, worker_id)
        if worker is not None and worker.current_job_id == job.id:
            worker.current_job_id = None
            worker.heartbeat_at = datetime.now(UTC)
            session.add(worker)
        session.commit()
        session.refresh(job)
        return job

    def fail(
        self,
        session: Session,
        job_id: int,
        worker_id: str,
        generation: int,
        message: str,
    ) -> JudgeJob:
        job = session.get(JudgeJob, job_id)
        if job is None:
            raise JobConflictError("Job not found")
        self._assert_lease(job, worker_id, generation)
        job.status = (
            "dead_letter" if job.attempt_count >= job.max_attempts else "failed"
        )
        job.error_message = message[:4000]
        job.finished_at = datetime.now(UTC)
        self._event(session, job, job.status, message[:500])
        session.add(job)
        worker = session.get(JudgeWorker, worker_id)
        if worker is not None and worker.current_job_id == job.id:
            worker.current_job_id = None
            worker.last_error = message[:4000]
            worker.heartbeat_at = datetime.now(UTC)
            session.add(worker)
        session.commit()
        session.refresh(job)
        return job

    def cancel(self, session: Session, job: JudgeJob) -> JudgeJob:
        if job.status not in {"queued", "leased"}:
            raise JobConflictError(
                "Only queued or leased jobs can be cancelled"
            )
        job.status = "cancelled"
        job.finished_at = datetime.now(UTC)
        self._event(session, job, "cancelled", "Job cancelled")
        session.add(job)
        session.commit()
        session.refresh(job)
        return job

    def retry(
        self, session: Session, job: JudgeJob, *, commit: bool = True
    ) -> JudgeJob:
        if job.status not in {"failed", "dead_letter"}:
            raise JobConflictError(
                "Only failed or dead-letter jobs can be retried"
            )
        previous_status = job.status
        job.status = "queued"
        job.progress = 0
        job.lease_owner = None
        job.lease_expires_at = None
        job.heartbeat_at = None
        job.started_at = None
        job.finished_at = None
        job.error_message = None
        job.result_json = None
        if previous_status == "dead_letter":
            job.attempt_count = 0
        self._event(
            session, job, "retried", f"Admin retried {previous_status} job"
        )
        session.add(job)
        if commit:
            session.commit()
            session.refresh(job)
        return job

    def process_validation_job(
        self, session: Session, job: JudgeJob, worker_id: str
    ) -> JudgeJob:
        generation = job.lease_generation
        self.start(session, job, worker_id, generation)
        revision = session.get(ProblemRevision, job.revision_id)
        if revision is None:
            return self.fail(
                session,
                job.id or 0,
                worker_id,
                generation,
                "Revision not found",
            )
        testcases = session.exec(
            select(ProblemTestCase).where(
                ProblemTestCase.revision_id == revision.id
            )
        ).all()
        errors: list[str] = []
        if not revision.statement.strip():
            errors.append("statement is required")
        if not testcases:
            errors.append("at least one testcase is required")
        if (
            testcases
            and abs(sum(case.score for case in testcases) - 100.0) > 0.01
        ):
            errors.append("testcase scores must sum to 100")
        pair_hashes: set[tuple[str | None, str | None]] = set()
        total_size = 0
        store = LocalArtifactStore()
        for testcase in testcases:
            input_asset = session.get(ProblemAsset, testcase.input_asset_id)
            output_asset = session.get(ProblemAsset, testcase.output_asset_id)
            if input_asset is None or output_asset is None:
                errors.append(
                    f"testcase {testcase.case_name} has an unmatched pair"
                )
                continue
            total_size += input_asset.size_bytes + output_asset.size_bytes
            if input_asset.size_bytes == 0 or output_asset.size_bytes == 0:
                errors.append(
                    f"testcase {testcase.case_name} contains an empty file"
                )
            pair = (input_asset.sha256, output_asset.sha256)
            if all(pair) and pair in pair_hashes:
                errors.append(
                    f"testcase {testcase.case_name} duplicates another pair"
                )
            pair_hashes.add(pair)
            if (
                input_asset.is_hidden == testcase.is_sample
                or output_asset.is_hidden == testcase.is_sample
            ):
                errors.append(
                    f"testcase {testcase.case_name} sample visibility is inconsistent"
                )
            for asset in (input_asset, output_asset):
                if asset.sha256:
                    try:
                        store.resolve(asset.storage_path, asset.sha256)
                    except (FileNotFoundError, ValueError) as error:
                        errors.append(
                            f"artifact {asset.display_name} failed checksum validation: {error}"
                        )
        if total_size > 200 * 1024 * 1024:
            errors.append("testcase data exceeds total size limit")
        if revision.checker_type == "special":
            checker_asset = session.exec(
                select(ProblemAsset).where(
                    ProblemAsset.revision_id == revision.id,
                    ProblemAsset.asset_kind == "checker",
                )
            ).first()
            if checker_asset is None or not checker_asset.sha256:
                errors.append("special judge checker asset is required")
            else:
                try:
                    LocalArtifactStore().resolve(
                        checker_asset.storage_path, checker_asset.sha256
                    )
                except (FileNotFoundError, ValueError) as error:
                    errors.append(
                        f"special judge checker failed checksum validation: {error}"
                    )
        groups = session.exec(
            select(TestCaseGroup).where(
                TestCaseGroup.revision_id == revision.id
            )
        ).all()
        group_by_id = {group.id: group for group in groups}
        for group in groups:
            if group.scoring_policy not in {"sum", "all_or_nothing"}:
                errors.append(
                    f"unsupported scoring policy for group {group.group_key}"
                )
            seen: set[int] = set()
            current = group
            while current.dependency_group_id is not None:
                if current.id in seen:
                    errors.append("testcase group dependencies contain a cycle")
                    break
                seen.add(current.id or 0)
                dependency = group_by_id.get(current.dependency_group_id)
                if dependency is None:
                    errors.append(
                        f"group {current.group_key} has an invalid dependency"
                    )
                    break
                current = dependency
        report = {"errors": errors, "testcase_count": len(testcases)}
        revision.validation_report = json.dumps(
            report, ensure_ascii=False, sort_keys=True
        )
        revision.status = "draft" if errors else "ready"
        session.add(revision)
        if errors:
            session.commit()
            return self.fail(
                session, job.id or 0, worker_id, generation, "; ".join(errors)
            )
        session.commit()
        return self.complete(
            session, job.id or 0, worker_id, generation, report
        )

    def process_grading_job(
        self, session: Session, job: JudgeJob, worker_id: str
    ) -> JudgeJob:
        generation = job.lease_generation
        self.start(session, job, worker_id, generation)
        submission = session.get(Submission, job.submission_id)
        if submission is None:
            return self.fail(
                session,
                job.id or 0,
                worker_id,
                generation,
                "Submission not found",
            )
        payload = json.loads(job.payload_json)
        target_revision_id = (
            payload.get("target_revision_id") or submission.problem_revision_id
        )
        if target_revision_id is not None:
            submission.problem_revision_id = int(target_revision_id)
        homework = session.get(Homework, submission.homework_num)
        if homework is None:
            self._mark_submission_retryable(
                session, submission, "Auto-grading failed: Homework not found"
            )
            session.commit()
            return self.fail(
                session,
                job.id or 0,
                worker_id,
                generation,
                "Homework not found",
            )
        try:
            if isinstance(self.grading_service, GradingService):

                def heartbeat_progress(
                    completed: int, total: int, case_timeout: int
                ) -> None:
                    self.heartbeat(
                        session,
                        job.id or 0,
                        worker_id,
                        generation,
                        lease_seconds=max(30, case_timeout + 15),
                        progress=(completed / total * 95) if total else 0,
                    )

                result = self.grading_service.grade_submission(
                    session,
                    submission,
                    homework,
                    progress_callback=heartbeat_progress,
                )
            else:
                # Lightweight test/custom graders keep the historical
                # three-argument protocol.
                result = self.grading_service.grade_submission(
                    session, submission, homework
                )
        except CheckerError as error:
            session.rollback()
            submission = session.get(Submission, job.submission_id)
            if submission is not None:
                run = self._record_internal_error_run(
                    session,
                    submission,
                    job,
                    generation,
                    f"Checker error: {error}",
                )
                session.commit()
                submission.selected_grading_run_id = run.id
                session.add(submission)
                session.commit()
            return self.fail(
                session, job.id or 0, worker_id, generation, str(error)
            )
        except Exception as error:
            session.rollback()
            submission = session.get(Submission, job.submission_id)
            if submission is not None:
                self._mark_submission_retryable(
                    session, submission, f"Auto-grading failed: {error}"
                )
                session.commit()
            return self.fail(
                session, job.id or 0, worker_id, generation, str(error)
            )
        verdict = self._verdict_for(result)
        run = GradingRun(
            submission_id=submission.id or 0,
            job_id=job.id,
            problem_revision_id=submission.problem_revision_id,
            lease_generation=generation,
            verdict=verdict,
            score=result.total_score,
            runtime_version=settings.JUDGE_RUNTIME_VERSION,
            checker_version=self._checker_version(
                session, submission.problem_revision_id
            ),
            result_json=json.dumps(
                {
                    "compile_status": result.compile_status,
                    "run_status": result.run_status,
                    "passed_case_count": result.passed_case_count,
                    "total_case_count": result.total_case_count,
                },
                sort_keys=True,
            ),
        )
        session.add(run)
        session.flush()
        submission.selected_grading_run_id = run.id
        session.add(submission)
        session.commit()
        session.refresh(run)
        return self.complete(
            session,
            job.id or 0,
            worker_id,
            generation,
            {
                "grading_run_id": run.id,
                "verdict": verdict,
                "score": result.total_score,
            },
        )

    def process_dry_run_job(
        self, session: Session, job: JudgeJob, worker_id: str
    ) -> JudgeJob:
        generation = job.lease_generation
        self.start(session, job, worker_id, generation)
        revision = session.get(ProblemRevision, job.revision_id)
        if revision is None:
            return self.fail(
                session,
                job.id or 0,
                worker_id,
                generation,
                "Revision not found",
            )
        payload = json.loads(job.payload_json)
        asset = session.get(ProblemAsset, payload.get("asset_id"))
        if asset is None or asset.revision_id != revision.id:
            return self.fail(
                session,
                job.id or 0,
                worker_id,
                generation,
                "Reference asset not found",
            )
        store = LocalArtifactStore()
        try:
            source = store.resolve(asset.storage_path, asset.sha256).read_text(
                encoding="utf-8"
            )
            if revision.checker_type == "special":
                if not isinstance(
                    self.grading_service.runner, NsJailCodeRunner
                ):
                    raise CheckerError("Special judge requires NsJail")
                checker_asset = session.exec(
                    select(ProblemAsset)
                    .where(
                        ProblemAsset.revision_id == revision.id,
                        ProblemAsset.asset_kind == "checker",
                    )
                    .order_by(ProblemAsset.id.desc())
                ).first()
                if checker_asset is None:
                    raise CheckerError("Special judge checker asset is missing")
                checker_source = store.resolve(
                    checker_asset.storage_path, checker_asset.sha256
                ).read_text(encoding="utf-8")
                checker = SpecialJudgeChecker(
                    self.grading_service.runner.sandbox, checker_source
                )
            else:
                checker = get_checker(
                    revision.checker_type,
                    json.loads(revision.checker_config_json),
                )
            cases = session.exec(
                select(ProblemTestCase)
                .where(ProblemTestCase.revision_id == revision.id)
                .order_by(ProblemTestCase.position)
            ).all()
            if not cases:
                raise ValueError("Revision has no testcases")
            case_results = []
            all_passed = True
            for case in cases:
                self.heartbeat(
                    session,
                    job.id or 0,
                    worker_id,
                    generation,
                    lease_seconds=max(30, revision.time_limit_ms // 1000 + 10),
                    progress=len(case_results) * 95 / len(cases),
                )
                input_asset = session.get(ProblemAsset, case.input_asset_id)
                output_asset = session.get(ProblemAsset, case.output_asset_id)
                if input_asset is None or output_asset is None:
                    raise ValueError("Testcase artifact is missing")
                input_data = store.resolve(
                    input_asset.storage_path, input_asset.sha256
                ).read_text("utf-8")
                expected = store.resolve(
                    output_asset.storage_path, output_asset.sha256
                ).read_text("utf-8")
                timeout = max(1, revision.time_limit_ms // 1000)
                if isinstance(self.grading_service.runner, NsJailCodeRunner):
                    execution = (
                        self.grading_service.runner.run_code_with_limits(
                            payload["language"],
                            source,
                            input_data=input_data,
                            source_name=None,
                            limits=NsJailLimits(
                                wall_seconds=timeout + 2,
                                cpu_seconds=timeout,
                                memory_mb=revision.memory_limit_mb,
                                file_size_mb=max(
                                    1, revision.output_limit_kb // 1024
                                ),
                                process_count=revision.process_limit,
                                output_bytes=revision.output_limit_kb * 1024,
                            ),
                        )
                    )
                else:
                    execution = self.grading_service.runner.run_code(
                        payload["language"],
                        source,
                        input_data=input_data,
                        source_name=None,
                        timeout_seconds=timeout,
                    )
                actual = (
                    execution.run_result.stdout if execution.run_result else ""
                )
                checked = (
                    checker.check(input_data, expected, actual)
                    if execution.status == "passed"
                    and revision.checker_type == "special"
                    else (
                        checker.check(expected, actual)
                        if execution.status == "passed"
                        else None
                    )
                )
                passed = bool(checked and checked.accepted)
                all_passed = all_passed and passed
                case_results.append(
                    {
                        "case_id": case.id,
                        "case_name": case.case_name,
                        "status": execution.status,
                        "verdict": (
                            "AC"
                            if passed
                            else (
                                "WA"
                                if execution.status == "passed"
                                else execution.status
                            )
                        ),
                        "runtime_ms": (
                            execution.run_result.duration_ms
                            if execution.run_result
                            else None
                        ),
                    }
                )
        except Exception as error:
            session.rollback()
            return self.fail(
                session, job.id or 0, worker_id, generation, str(error)
            )
        return self.complete(
            session,
            job.id or 0,
            worker_id,
            generation,
            {
                "accepted": all_passed,
                "testcase_count": len(case_results),
                "cases": case_results,
            },
        )

    def process_artifact_reconciliation_job(
        self, session: Session, job: JudgeJob, worker_id: str
    ) -> JudgeJob:
        generation = job.lease_generation
        self.start(session, job, worker_id, generation)
        try:
            report = CourseBundleService().reconcile(session)
            payload = {
                "referenced": report.referenced,
                "present": report.present,
                "missing": report.missing,
                "checksum_mismatch": report.checksum_mismatch,
                "orphan": report.orphan,
            }
        except Exception as error:
            session.rollback()
            return self.fail(
                session, job.id or 0, worker_id, generation, str(error)
            )
        if not report.valid:
            return self.fail(
                session,
                job.id or 0,
                worker_id,
                generation,
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
            )
        return self.complete(
            session, job.id or 0, worker_id, generation, payload
        )

    @staticmethod
    def _verdict_for(result: SubmissionResult) -> str:
        if result.compile_status == "failed":
            return "CE"
        if result.compile_status == "timeout" or result.run_status == "timeout":
            return "TLE"
        if result.run_status == "output_limit":
            return "OLE"
        if result.run_status == "memory_limit":
            return "MLE"
        if result.run_status == "failed":
            return "RE"
        if (
            result.total_case_count > 0
            and result.passed_case_count == result.total_case_count
        ):
            return "AC"
        return "WA"

    @staticmethod
    def _mark_submission_retryable(
        session: Session, submission: Submission, summary: str
    ) -> None:
        submission.status = "retryable"
        result = session.exec(
            select(SubmissionResult).where(
                SubmissionResult.submission_id == submission.id
            )
        ).first()
        if result is None:
            result = SubmissionResult(submission_id=submission.id or 0)
        result.status = "retryable"
        result.grader_summary = summary
        session.add(submission)
        session.add(result)

    @staticmethod
    def _checker_version(session: Session, revision_id: int | None) -> str:
        if revision_id is None:
            return "legacy-standard-v1"
        revision = session.get(ProblemRevision, revision_id)
        if revision is None:
            return "unknown"
        try:
            return get_checker(
                revision.checker_type, json.loads(revision.checker_config_json)
            ).version
        except Exception:
            return "checker-error"

    def _record_internal_error_run(
        self,
        session: Session,
        submission: Submission,
        job: JudgeJob,
        generation: int,
        message: str,
    ) -> GradingRun:
        submission.status = "judge_error"
        result = session.exec(
            select(SubmissionResult).where(
                SubmissionResult.submission_id == submission.id
            )
        ).first()
        if result is None:
            result = SubmissionResult(submission_id=submission.id or 0)
        result.status = "judge_error"
        result.run_status = "judge_error"
        result.grader_summary = message
        run = GradingRun(
            submission_id=submission.id or 0,
            job_id=job.id,
            problem_revision_id=submission.problem_revision_id,
            lease_generation=generation,
            verdict="IE",
            score=0,
            runtime_version=settings.JUDGE_RUNTIME_VERSION,
            checker_version="checker-error",
            result_json=json.dumps({"error": message}, sort_keys=True),
        )
        session.add(submission)
        session.add(result)
        session.add(run)
        session.flush()
        return run

    def to_read(self, job: JudgeJob) -> JudgeJobRead:
        if job.status not in JUDGE_JOB_STATUSES:
            raise JobConflictError("Unknown job status")
        return JudgeJobRead.model_validate(job)

    def _assert_lease(
        self, job: JudgeJob, worker_id: str, generation: int
    ) -> None:
        if job.lease_owner != worker_id or job.lease_generation != generation:
            raise JobConflictError("Stale or foreign job lease")

    def _event(
        self, session: Session, job: JudgeJob, event_type: str, message: str
    ) -> JudgeJobEvent:
        latest = session.exec(
            select(JudgeJobEvent.sequence_no)
            .where(JudgeJobEvent.job_id == job.id)
            .order_by(JudgeJobEvent.sequence_no.desc())
        ).first()
        event = JudgeJobEvent(
            job_id=job.id or 0,
            sequence_no=(latest or 0) + 1,
            event_type=event_type,
            message=message,
        )
        session.add(event)
        return event
