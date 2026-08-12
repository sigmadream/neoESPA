import argparse
import socket
import time
import json
from pathlib import Path

from sqlmodel import Session

from .core.db import engine
from .core.migrations import apply_migrations
from .services.user_management import UserManagementError, create_admin_user
from .services.judge_job_service import JudgeJobService
from .services.bootstrap_service import BootstrapError, issue_bootstrap_token
from .services.course_bundle import CourseBundleService
from .services.openapi_contract import breaking_changes, canonical_openapi, load_schema
from .services.analytics_export import AnalyticsExportError, AnalyticsExportService
from .core.config import settings
from .services.code_runner import NsJailCodeRunner
from .services.code_runner import SUPPORTED_LANGUAGES
from .services.grading_service import GradingService
from .services.legacy_artifact_backfill import LegacyArtifactBackfillService
from .services.capacity_baseline import record_capacity_baseline
from .services.sandbox.selftest import run_hostile_selftest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="neoESPA backend administration CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_admin_parser = subparsers.add_parser(
        "create-admin",
        help="Create a local admin account",
    )
    create_admin_parser.add_argument("--id", dest="user_id", required=True, help="Login ID")
    create_admin_parser.add_argument("--sid", type=int, required=True, help="Student or staff ID")
    create_admin_parser.add_argument("--name", required=True, help="Display name")
    create_admin_parser.add_argument("--phone", required=True, help="Phone number")
    create_admin_parser.add_argument("--email", required=True, help="Email address")
    create_admin_parser.add_argument("--password", required=True, help="Initial password")
    create_admin_parser.add_argument(
        "--inactive",
        action="store_true",
        help="Create the account in a disabled state",
    )

    worker_parser = subparsers.add_parser(
        "run-judge-worker",
        aliases=["run-validation-worker"],
        help="Process persistent validation and submission grading jobs",
    )
    worker_parser.add_argument(
        "--worker-id", default=f"validation-{socket.gethostname()}", help="Stable worker identity"
    )
    worker_parser.add_argument("--once", action="store_true", help="Process at most one job")
    worker_parser.add_argument("--poll-seconds", type=float, default=1.0)

    bootstrap_parser = subparsers.add_parser(
        "issue-bootstrap-token",
        help="Issue a one-time token for the first super administrator",
    )
    bootstrap_parser.add_argument("--ttl-minutes", type=int, default=15)

    subparsers.add_parser(
        "verify-course-bundle",
        help="Verify course bundle manifests and checksums",
    )
    restore_bundle = subparsers.add_parser(
        "restore-course-bundle", help="Restore a verified SQLite snapshot"
    )
    restore_bundle.add_argument("--target", required=True)
    restore_bundle.add_argument(
        "--replace", action="store_true", help="Replace an existing target database"
    )

    export_openapi = subparsers.add_parser(
        "export-openapi", help="Write the canonical FastAPI OpenAPI contract"
    )
    export_openapi.add_argument("--output", default="openapi.json")
    check_openapi = subparsers.add_parser(
        "check-openapi", help="Fail when the current API breaks a saved OpenAPI contract"
    )
    check_openapi.add_argument("--baseline", default="openapi.json")
    analytics_export = subparsers.add_parser(
        "export-analytics-jsonl", help="Export consent-filtered pseudonymous analytics data"
    )
    analytics_export.add_argument("--purpose", required=True)
    analytics_export.add_argument("--policy-version", required=True)
    subparsers.add_parser(
        "reconcile-artifacts",
        help="Report missing, mismatched and orphan problem artifacts",
    )
    backfill_artifacts = subparsers.add_parser(
        "backfill-legacy-artifacts", help="Copy legacy files into the content-addressed store"
    )
    backfill_artifacts.add_argument("--legacy-root", required=True)
    capacity = subparsers.add_parser(
        "record-capacity-baseline", help="Record host capacity and course workload assumptions"
    )
    capacity.add_argument("--expected-students", type=int, required=True)
    capacity.add_argument("--max-concurrent-submissions", type=int, required=True)
    capacity.add_argument("--expected-term-submissions", type=int, required=True)
    snapshot = subparsers.add_parser(
        "create-course-snapshot", help="Checkpoint and snapshot an idle or frozen course database"
    )
    snapshot.add_argument("--course-id", required=True)
    snapshot.add_argument("--term", required=True)
    snapshot.add_argument("--schema-version", required=True)
    snapshot.add_argument("--write-frozen", action="store_true")
    sandbox_test = subparsers.add_parser(
        "run-sandbox-self-test", help="Run hostile fixtures and write a policy-bound attestation"
    )
    sandbox_test.add_argument("--policy", required=True)
    sandbox_test.add_argument("--attestation", required=True)

    return parser


def _run_create_admin(args: argparse.Namespace) -> int:
    apply_migrations(engine)

    with Session(engine) as session:
        user = create_admin_user(
            session,
            user_id=args.user_id,
            sid=args.sid,
            password=args.password,
            name=args.name,
            phone=args.phone,
            email=args.email,
            is_active=not args.inactive,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    print(
        f"Created admin user '{user.id}' "
        f"(sid={user.sid}, active={str(user.is_active).lower()})"
    )
    return 0


def _run_validation_worker(args: argparse.Namespace) -> int:
    apply_migrations(engine)
    if settings.ENVIRONMENT == "production":
        runner = NsJailCodeRunner()
        readiness_errors = runner.sandbox.readiness_errors()
        if not settings.SANDBOX_READY or readiness_errors:
            raise RuntimeError(
                "Judge sandbox is not ready: "
                + "; ".join(readiness_errors or ["SANDBOX_READY is false"])
            )
        service = JudgeJobService(GradingService(runner=runner))
    else:
        service = JudgeJobService()
    while True:
        with Session(engine) as session:
            job = service.claim_next(
                session,
                args.worker_id,
                job_types=[
                    "problem_validation", "problem_dry_run", "grade_submission",
                    "artifact_reconciliation",
                ],
                worker_capabilities={
                    "job_types": [
                        "problem_validation", "problem_dry_run", "grade_submission",
                        "artifact_reconciliation",
                    ],
                    "languages": list(SUPPORTED_LANGUAGES),
                    "runtime_version": settings.JUDGE_RUNTIME_VERSION,
                    "sandbox": "nsjail" if settings.ENVIRONMENT == "production" else "host-development",
                },
            )
            if job is not None:
                if job.job_type == "problem_validation":
                    service.process_validation_job(session, job, args.worker_id)
                elif job.job_type == "grade_submission":
                    service.process_grading_job(session, job, args.worker_id)
                elif job.job_type == "problem_dry_run":
                    service.process_dry_run_job(session, job, args.worker_id)
                elif job.job_type == "artifact_reconciliation":
                    service.process_artifact_reconciliation_job(session, job, args.worker_id)
        if args.once:
            return 0
        if job is None:
            time.sleep(max(args.poll_seconds, 0.1))


def _run_issue_bootstrap_token(args: argparse.Namespace) -> int:
    apply_migrations(engine)
    with Session(engine) as session:
        token = issue_bootstrap_token(session, ttl_minutes=args.ttl_minutes)
    print(token)
    return 0


def _run_verify_course_bundle() -> int:
    errors = CourseBundleService().verify()
    if errors:
        print(json.dumps({"valid": False, "errors": errors}, ensure_ascii=False))
        return 1
    print(json.dumps({"valid": True, "errors": []}))
    return 0


def _run_reconcile_artifacts() -> int:
    apply_migrations(engine)
    service = CourseBundleService()
    with Session(engine) as session:
        report = service.reconcile(session)
    print(service.report_json(report))
    return 0 if report.valid else 1


def _run_backfill_legacy_artifacts(legacy_root: str) -> int:
    apply_migrations(engine)
    with Session(engine) as session:
        report = LegacyArtifactBackfillService(
            legacy_root=Path(legacy_root)
        ).run(session)
    print(json.dumps(report.__dict__, ensure_ascii=False, sort_keys=True))
    return 0 if report.valid else 1


def _run_restore_course_bundle(target: str, replace: bool) -> int:
    counts = CourseBundleService().restore_snapshot(Path(target), replace=replace)
    print(json.dumps({"restored": True, "row_counts": counts}, ensure_ascii=False))
    return 0


def _current_openapi() -> dict:
    from .main import app

    return app.openapi()


def _run_export_openapi(output: str) -> int:
    path = Path(output)
    path.write_text(canonical_openapi(_current_openapi()), encoding="utf-8")
    print(f"Wrote OpenAPI contract to {path}")
    return 0


def _run_check_openapi(baseline: str) -> int:
    errors = breaking_changes(load_schema(Path(baseline)), _current_openapi())
    print(json.dumps({"compatible": not errors, "breaking_changes": errors}, ensure_ascii=False))
    return 0 if not errors else 1


def _run_export_analytics(purpose: str, policy_version: str) -> int:
    secret = settings.ANALYTICS_HMAC_SECRET
    if not secret:
        raise AnalyticsExportError("ANALYTICS_HMAC_SECRET is required")
    apply_migrations(engine)
    with Session(engine) as session:
        counts = AnalyticsExportService(secret).export_jsonl(
            session, purpose=purpose, policy_version=policy_version
        )
    print(json.dumps({"exported": True, "row_counts": counts}, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "create-admin":
            return _run_create_admin(args)
        if args.command in {"run-judge-worker", "run-validation-worker"}:
            return _run_validation_worker(args)
        if args.command == "issue-bootstrap-token":
            return _run_issue_bootstrap_token(args)
        if args.command == "verify-course-bundle":
            return _run_verify_course_bundle()
        if args.command == "restore-course-bundle":
            return _run_restore_course_bundle(args.target, args.replace)
        if args.command == "reconcile-artifacts":
            return _run_reconcile_artifacts()
        if args.command == "backfill-legacy-artifacts":
            return _run_backfill_legacy_artifacts(args.legacy_root)
        if args.command == "record-capacity-baseline":
            baseline = record_capacity_baseline(
                expected_students=args.expected_students,
                max_concurrent_submissions=args.max_concurrent_submissions,
                expected_term_submissions=args.expected_term_submissions,
            )
            print(json.dumps(baseline, ensure_ascii=False, sort_keys=True))
            return 0
        if args.command == "create-course-snapshot":
            database_path = Path(engine.url.database or "")
            with Session(engine) as session:
                path = CourseBundleService().create_operational_snapshot(
                    session, database_path, course_id=args.course_id, term=args.term,
                    schema_version=args.schema_version, write_frozen=args.write_frozen,
                )
            print(path)
            return 0
        if args.command == "run-sandbox-self-test":
            result = run_hostile_selftest(
                policy_path=Path(args.policy), attestation_path=Path(args.attestation),
                runtime_version=settings.JUDGE_RUNTIME_VERSION,
            )
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            return 0
        if args.command == "export-openapi":
            return _run_export_openapi(args.output)
        if args.command == "check-openapi":
            return _run_check_openapi(args.baseline)
        if args.command == "export-analytics-jsonl":
            return _run_export_analytics(args.purpose, args.policy_version)
    except (UserManagementError, BootstrapError, AnalyticsExportError) as error:
        parser.exit(1, f"Error: {error}\n")

    parser.exit(1, f"Error: unsupported command '{args.command}'\n")


if __name__ == "__main__":
    raise SystemExit(main())
