from __future__ import annotations

import json
import re
from datetime import UTC, datetime

from sqlmodel import Session, select

from ..models.schemas import (
    PROBLEM_REVISION_STATUSES,
    Problem,
    ProblemCreate,
    ProblemRead,
    ProblemRevision,
    ProblemRevisionCreate,
    ProblemRevisionRead,
)
from .code_runner import SUPPORTED_LANGUAGES
from .checkers import get_checker, CheckerError
from ..core.config import settings

PROBLEM_CODE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")


class ProblemConflictError(ValueError):
    pass


class ProblemValidationError(ValueError):
    pass


class ProblemService:
    def normalize_code(self, code: str) -> str:
        normalized = code.strip().lower()
        if not PROBLEM_CODE_PATTERN.fullmatch(normalized):
            raise ProblemValidationError(
                "Problem code must use lowercase letters, numbers, '_' or '-'"
            )
        return normalized

    def validate_languages(self, languages: list[str]) -> list[str]:
        normalized = list(
            dict.fromkeys(language.strip().lower() for language in languages)
        )
        if not normalized:
            raise ProblemValidationError("At least one language is required")
        unsupported = sorted(set(normalized) - set(SUPPORTED_LANGUAGES))
        if unsupported:
            raise ProblemValidationError(
                f"Unsupported languages: {', '.join(unsupported)}"
            )
        return normalized

    def create_problem(
        self, session: Session, payload: ProblemCreate, actor_id: str
    ) -> tuple[Problem, ProblemRevision]:
        code = self.normalize_code(payload.code)
        if (
            session.exec(select(Problem.id).where(Problem.code == code)).first()
            is not None
        ):
            raise ProblemConflictError("Problem code already exists")

        languages = self.validate_languages(payload.allowed_languages)
        problem = Problem(
            code=code, title=payload.title.strip(), owner_id=actor_id
        )
        session.add(problem)
        session.flush()
        revision = ProblemRevision(
            problem_id=problem.id or 0,
            revision_no=1,
            statement=payload.statement,
            input_description=payload.input_description,
            output_description=payload.output_description,
            time_limit_ms=payload.time_limit_ms,
            memory_limit_mb=payload.memory_limit_mb,
            output_limit_kb=payload.output_limit_kb,
            process_limit=payload.process_limit,
            source_limit_kb=payload.source_limit_kb,
            checker_type=payload.checker_type,
            problem_mode=payload.problem_mode,
            checker_config_json=json.dumps(
                payload.checker_config, sort_keys=True
            ),
            language_multipliers_json=json.dumps(
                payload.language_multipliers, sort_keys=True
            ),
            allowed_languages_json=json.dumps(languages),
            status="draft",
            created_by=actor_id,
        )
        session.add(revision)
        session.flush()
        return problem, revision

    def create_revision(
        self,
        session: Session,
        problem: Problem,
        payload: ProblemRevisionCreate,
        actor_id: str,
    ) -> ProblemRevision:
        latest = session.exec(
            select(ProblemRevision)
            .where(ProblemRevision.problem_id == problem.id)
            .order_by(ProblemRevision.revision_no.desc())
        ).first()
        source = latest
        if payload.clone_from_revision_id is not None:
            source = session.get(
                ProblemRevision, payload.clone_from_revision_id
            )
            if source is None or source.problem_id != problem.id:
                raise ProblemValidationError(
                    "Clone source revision does not belong to problem"
                )
        next_no = 1 if latest is None else latest.revision_no + 1
        languages = self.validate_languages(
            payload.allowed_languages
            if payload.allowed_languages is not None
            else json.loads(source.allowed_languages_json if source else "[]")
        )
        revision = ProblemRevision(
            problem_id=problem.id or 0,
            revision_no=next_no,
            statement=(
                payload.statement
                if payload.statement is not None
                else (source.statement if source else "")
            ),
            input_description=(
                payload.input_description
                if payload.input_description is not None
                else (source.input_description if source else "")
            ),
            output_description=(
                payload.output_description
                if payload.output_description is not None
                else (source.output_description if source else "")
            ),
            time_limit_ms=payload.time_limit_ms
            or (source.time_limit_ms if source else 1000),
            memory_limit_mb=payload.memory_limit_mb
            or (source.memory_limit_mb if source else 256),
            output_limit_kb=payload.output_limit_kb
            or (source.output_limit_kb if source else 1024),
            process_limit=payload.process_limit
            or (source.process_limit if source else 1),
            source_limit_kb=payload.source_limit_kb
            or (source.source_limit_kb if source else 1024),
            checker_type=payload.checker_type
            or (source.checker_type if source else "token"),
            problem_mode=payload.problem_mode
            or (source.problem_mode if source else "standard"),
            checker_config_json=json.dumps(
                (
                    payload.checker_config
                    if payload.checker_config is not None
                    else json.loads(
                        source.checker_config_json if source else "{}"
                    )
                ),
                sort_keys=True,
            ),
            language_multipliers_json=json.dumps(
                (
                    payload.language_multipliers
                    if payload.language_multipliers is not None
                    else json.loads(
                        source.language_multipliers_json if source else "{}"
                    )
                ),
                sort_keys=True,
            ),
            allowed_languages_json=json.dumps(languages),
            status="draft",
            created_by=actor_id,
        )
        session.add(revision)
        session.flush()
        return revision

    def validate_revision(self, revision: ProblemRevision) -> None:
        if revision.status != "draft":
            raise ProblemConflictError("Only draft revisions can be validated")
        errors: list[str] = []
        if not revision.statement.strip():
            errors.append("statement is required")
        if revision.time_limit_ms < 1 or revision.time_limit_ms > 60_000:
            errors.append("time_limit_ms is out of range")
        if revision.memory_limit_mb < 1 or revision.memory_limit_mb > 4096:
            errors.append("memory_limit_mb is out of range")
        try:
            self.validate_languages(json.loads(revision.allowed_languages_json))
        except (
            json.JSONDecodeError,
            TypeError,
            ProblemValidationError,
        ) as error:
            errors.append(str(error))
        if revision.checker_type == "special":
            if not settings.SANDBOX_READY:
                errors.append(
                    "special judge requires the sandbox hostile-fixture gate"
                )
        else:
            try:
                get_checker(
                    revision.checker_type,
                    json.loads(revision.checker_config_json),
                )
            except (CheckerError, json.JSONDecodeError, TypeError) as error:
                errors.append(str(error))
        if revision.problem_mode not in {"standard", "interactive"}:
            errors.append("problem mode is invalid")
        elif (
            revision.problem_mode == "interactive"
            and not settings.INTERACTIVE_JUDGING_ENABLED
        ):
            errors.append("interactive judging feature is disabled")
        try:
            multipliers = json.loads(revision.language_multipliers_json)
            if not isinstance(multipliers, dict) or any(
                language not in SUPPORTED_LANGUAGES
                or float(value) <= 0
                or float(value) > 10
                for language, value in multipliers.items()
            ):
                errors.append("language multipliers are invalid")
        except json.JSONDecodeError, TypeError, ValueError:
            errors.append("language multipliers are invalid")

        revision.validation_report = json.dumps(
            {"errors": errors}, ensure_ascii=False
        )
        revision.status = "draft" if errors else "ready"
        if errors:
            raise ProblemValidationError("; ".join(errors))

    def publish_revision(
        self, session: Session, problem: Problem, revision: ProblemRevision
    ) -> None:
        if revision.problem_id != problem.id:
            raise ProblemValidationError("Revision does not belong to problem")
        if revision.status != "ready":
            raise ProblemConflictError("Only ready revisions can be published")
        published = session.exec(
            select(ProblemRevision).where(
                ProblemRevision.problem_id == problem.id,
                ProblemRevision.status == "published",
            )
        ).all()
        for current in published:
            current.status = "archived"
            session.add(current)
        revision.status = "published"
        revision.published_at = datetime.now(UTC)
        session.add(revision)

    def to_problem_read(
        self, session: Session, problem: Problem
    ) -> ProblemRead:
        revisions = session.exec(
            select(ProblemRevision)
            .where(ProblemRevision.problem_id == problem.id)
            .order_by(ProblemRevision.revision_no.desc())
        ).all()
        published = next(
            (
                revision
                for revision in revisions
                if revision.status == "published"
            ),
            None,
        )
        return ProblemRead(
            id=problem.id or 0,
            code=problem.code,
            title=problem.title,
            owner_id=problem.owner_id,
            is_active=problem.is_active,
            latest_revision_no=revisions[0].revision_no if revisions else None,
            published_revision_id=published.id if published else None,
            created_at=problem.created_at,
            updated_at=problem.updated_at,
        )

    def to_revision_read(
        self, revision: ProblemRevision
    ) -> ProblemRevisionRead:
        if revision.status not in PROBLEM_REVISION_STATUSES:
            raise ProblemValidationError("Unknown revision status")
        return ProblemRevisionRead(
            id=revision.id or 0,
            problem_id=revision.problem_id,
            revision_no=revision.revision_no,
            statement=revision.statement,
            input_description=revision.input_description,
            output_description=revision.output_description,
            time_limit_ms=revision.time_limit_ms,
            memory_limit_mb=revision.memory_limit_mb,
            output_limit_kb=revision.output_limit_kb,
            process_limit=revision.process_limit,
            source_limit_kb=revision.source_limit_kb,
            checker_type=revision.checker_type,
            problem_mode=revision.problem_mode,
            checker_config=json.loads(revision.checker_config_json),
            language_multipliers=json.loads(revision.language_multipliers_json),
            allowed_languages=json.loads(revision.allowed_languages_json),
            status=revision.status,
            validation_report=revision.validation_report,
            created_by=revision.created_by,
            created_at=revision.created_at,
            published_at=revision.published_at,
        )
