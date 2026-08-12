import json
from typing import Any

from fastapi import HTTPException, status
from sqlmodel import Session, select

from ...models.schemas import (
    GradingRule,
    Homework,
    HomeworkAdminRead,
    HomeworkAdminWrite,
    HomeworkRead,
    HomeworkTestCaseWrite,
)
from ...services.code_runner import SUPPORTED_LANGUAGES
from ..shared.schedules import compute_schedule_window

ARTIFACT_METADATA_RULE_DESCRIPTIONS: dict[str, str] = {
    "problem_file_meta": "Problem statement file metadata.",
    "input_zip_meta": "Input testcase archive metadata.",
    "output_zip_meta": "Output testcase archive metadata.",
}


def normalize_allowed_languages(raw_languages: list[str] | None) -> list[str]:
    if not raw_languages:
        return sorted(SUPPORTED_LANGUAGES)

    normalized_languages = sorted(
        {
            language.strip().lower()
            for language in raw_languages
            if isinstance(language, str) and language.strip()
        }
    )
    invalid_languages = [
        language
        for language in normalized_languages
        if language not in SUPPORTED_LANGUAGES
    ]
    if invalid_languages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported homework language policy: {', '.join(invalid_languages)}",
        )
    return normalized_languages or sorted(SUPPORTED_LANGUAGES)


def get_grading_rule(
    session: Session,
    homework_num: int,
    rule_name: str,
) -> GradingRule | None:
    return session.exec(
        select(GradingRule).where(
            GradingRule.scope == "homework",
            GradingRule.homework_num == homework_num,
            GradingRule.rule_name == rule_name,
        )
    ).first()


def load_allowed_languages(session: Session, homework_num: int) -> list[str]:
    rule = get_grading_rule(session, homework_num, "allowed_languages")
    if rule is None or not rule.is_active:
        return sorted(SUPPORTED_LANGUAGES)

    try:
        loaded = json.loads(rule.rule_value)
    except json.JSONDecodeError:
        return sorted(SUPPORTED_LANGUAGES)

    if not isinstance(loaded, list):
        return sorted(SUPPORTED_LANGUAGES)
    return normalize_allowed_languages(loaded)


def load_homework_testcases(
    session: Session,
    homework_num: int,
) -> list[HomeworkTestCaseWrite]:
    rule = get_grading_rule(session, homework_num, "testcases")
    if rule is None or not rule.is_active:
        return []

    try:
        loaded = json.loads(rule.rule_value)
    except json.JSONDecodeError:
        return []

    raw_cases = loaded.get("cases", []) if isinstance(loaded, dict) else []
    if not isinstance(raw_cases, list):
        return []

    testcases: list[HomeworkTestCaseWrite] = []
    for raw_case in raw_cases:
        if not isinstance(raw_case, dict):
            continue
        testcases.append(
            HomeworkTestCaseWrite(
                name=str(raw_case.get("name", f"case-{len(testcases) + 1}")),
                input=str(raw_case.get("input", "")),
                expected_output=str(raw_case.get("expected_output", "")),
                score=float(raw_case.get("score", 0.0)),
                is_hidden=bool(raw_case.get("is_hidden", False)),
            )
        )
    return testcases


def load_homework_lint_week(session: Session, homework_num: int) -> str | None:
    rule = get_grading_rule(session, homework_num, "lint_week")
    if rule is None or not rule.is_active:
        return None
    return rule.rule_value.strip() or None


def _validate_artifact_metadata_rule_name(rule_name: str) -> None:
    if rule_name not in ARTIFACT_METADATA_RULE_DESCRIPTIONS:
        raise ValueError(
            f"Unsupported artifact metadata rule name: {rule_name}"
        )


def _normalize_artifact_metadata_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Artifact metadata payload must be an object")

    required_keys = {
        "original_name",
        "stored_relpath",
        "size_bytes",
        "content_type",
    }
    if set(payload.keys()) != required_keys:
        raise ValueError(
            "Artifact metadata payload must include exactly original_name, "
            "stored_relpath, size_bytes, content_type"
        )

    original_name = payload["original_name"]
    stored_relpath = payload["stored_relpath"]
    size_bytes = payload["size_bytes"]
    content_type = payload["content_type"]

    if not isinstance(original_name, str) or not original_name.strip():
        raise ValueError(
            "Artifact metadata original_name must be a non-empty string"
        )
    if not isinstance(stored_relpath, str) or not stored_relpath.strip():
        raise ValueError(
            "Artifact metadata stored_relpath must be a non-empty string"
        )
    if (
        isinstance(size_bytes, bool)
        or not isinstance(size_bytes, int)
        or size_bytes < 0
    ):
        raise ValueError(
            "Artifact metadata size_bytes must be a non-negative integer"
        )
    if content_type is not None and not isinstance(content_type, str):
        raise ValueError(
            "Artifact metadata content_type must be a string or null"
        )

    return {
        "original_name": original_name.strip(),
        "stored_relpath": stored_relpath.strip(),
        "size_bytes": size_bytes,
        "content_type": (
            content_type.strip() if isinstance(content_type, str) else None
        ),
    }


def upsert_homework_artifact_metadata(
    session: Session,
    homework_num: int,
    rule_name: str,
    metadata: dict[str, Any] | None,
) -> None:
    _validate_artifact_metadata_rule_name(rule_name)

    if metadata is None:
        delete_homework_rule(session, homework_num, rule_name)
        return

    normalized_payload = _normalize_artifact_metadata_payload(metadata)
    upsert_homework_rule(
        session,
        homework_num,
        rule_name,
        json.dumps(normalized_payload),
        description=ARTIFACT_METADATA_RULE_DESCRIPTIONS[rule_name],
    )


def load_homework_artifact_metadata(
    session: Session,
    homework_num: int,
    rule_name: str,
) -> dict[str, Any] | None:
    _validate_artifact_metadata_rule_name(rule_name)

    rule = get_grading_rule(session, homework_num, rule_name)
    if rule is None or not rule.is_active:
        return None

    try:
        loaded = json.loads(rule.rule_value)
        return _normalize_artifact_metadata_payload(loaded)
    except json.JSONDecodeError, ValueError:
        return None


def upsert_homework_rule(
    session: Session,
    homework_num: int,
    rule_name: str,
    rule_value: str,
    *,
    description: str,
) -> None:
    from datetime import UTC, datetime

    rule = get_grading_rule(session, homework_num, rule_name)
    now = datetime.now(UTC)

    if rule is None:
        session.add(
            GradingRule(
                scope="homework",
                homework_num=homework_num,
                rule_name=rule_name,
                rule_value=rule_value,
                is_active=True,
                description=description,
                created_at=now,
                updated_at=now,
            )
        )
        return

    rule.rule_value = rule_value
    rule.is_active = True
    rule.description = description
    rule.updated_at = now
    session.add(rule)


def delete_homework_rule(
    session: Session, homework_num: int, rule_name: str
) -> None:
    rule = get_grading_rule(session, homework_num, rule_name)
    if rule is not None:
        session.delete(rule)


def sync_homework_rules(
    session: Session,
    homework_num: int,
    payload: HomeworkAdminWrite,
) -> None:
    allowed_languages = normalize_allowed_languages(payload.allowed_languages)
    upsert_homework_rule(
        session,
        homework_num,
        "allowed_languages",
        json.dumps(allowed_languages),
        description="Allowed submission languages for the homework.",
    )

    if payload.testcases:
        serialized_cases = [
            {
                "name": testcase.name,
                "input": testcase.input,
                "expected_output": testcase.expected_output,
                "score": testcase.score,
                "is_hidden": testcase.is_hidden,
            }
            for testcase in payload.testcases
        ]
        upsert_homework_rule(
            session,
            homework_num,
            "testcases",
            json.dumps({"cases": serialized_cases}),
            description="Homework testcase policy.",
        )
    else:
        delete_homework_rule(session, homework_num, "testcases")

    if payload.lint_week is not None and payload.lint_week.strip():
        upsert_homework_rule(
            session,
            homework_num,
            "lint_week",
            payload.lint_week.strip(),
            description="Lint rule week mapping for the homework.",
        )
    else:
        delete_homework_rule(session, homework_num, "lint_week")


def to_homework_read(session: Session, homework: Homework) -> HomeworkRead:
    schedule_status, can_submit = compute_schedule_window(
        homework.starttime, homework.deadline
    )
    return HomeworkRead(
        num=homework.num or 0,
        title=homework.title,
        intro=homework.intro,
        deadline=homework.deadline,
        codeName=homework.codeName,
        filename=homework.filename,
        ratedatanum=homework.ratedatanum,
        sec=homework.sec,
        sbnum=homework.sbnum,
        starttime=homework.starttime,
        isDetected=homework.isDetected,
        vitalSpace=homework.vitalSpace,
        disorderedOutput=homework.disorderedOutput,
        isLint=homework.isLint,
        schedule_status=schedule_status,
        can_submit=can_submit,
        allowed_languages=load_allowed_languages(session, homework.num or 0),
    )


def to_homework_admin_read(
    session: Session, homework: Homework
) -> HomeworkAdminRead:
    homework_read = to_homework_read(session, homework)
    homework_num = homework.num or 0
    testcases = load_homework_testcases(session, homework_num)
    problem_file_meta = load_homework_artifact_metadata(
        session,
        homework_num,
        "problem_file_meta",
    )
    input_zip_meta = load_homework_artifact_metadata(
        session,
        homework_num,
        "input_zip_meta",
    )
    output_zip_meta = load_homework_artifact_metadata(
        session,
        homework_num,
        "output_zip_meta",
    )

    return HomeworkAdminRead(
        **homework_read.model_dump(),
        testcases=testcases,
        lint_week=load_homework_lint_week(session, homework_num),
        problem_file_name=(
            problem_file_meta["original_name"]
            if problem_file_meta is not None
            else None
        ),
        input_zip_name=(
            input_zip_meta["original_name"]
            if input_zip_meta is not None
            else None
        ),
        output_zip_name=(
            output_zip_meta["original_name"]
            if output_zip_meta is not None
            else None
        ),
        parsed_testcase_count=len(testcases),
    )


def to_homework_admin_read_batch(
    session: Session, homeworks: list[Homework]
) -> list[HomeworkAdminRead]:
    """Convert multiple Homework objects to HomeworkAdminRead using batch fetching to avoid N+1 queries."""
    from collections import defaultdict

    if not homeworks:
        return []

    homework_nums = [h.num for h in homeworks if h.num is not None]

    # Batch fetch all grading rules for these homeworks
    all_rules = session.exec(
        select(GradingRule).where(
            GradingRule.scope == "homework",
            GradingRule.homework_num.in_(homework_nums),
            GradingRule.is_active == True,
        )
    ).all()

    # Group rules by homework_num
    rules_by_homework = defaultdict(list)
    for rule in all_rules:
        rules_by_homework[rule.homework_num].append(rule)

    results: list[HomeworkAdminRead] = []
    for homework in homeworks:
        h_num = homework.num or 0
        h_rules = {r.rule_name: r for r in rules_by_homework[h_num]}

        # Parse allowed_languages
        allowed_languages = sorted(SUPPORTED_LANGUAGES)
        lang_rule = h_rules.get("allowed_languages")
        if lang_rule:
            try:
                loaded = json.loads(lang_rule.rule_value)
                if isinstance(loaded, list):
                    allowed_languages = normalize_allowed_languages(loaded)
            except json.JSONDecodeError, HTTPException:
                pass

        # Parse testcases
        testcases: list[HomeworkTestCaseWrite] = []
        tc_rule = h_rules.get("testcases")
        if tc_rule:
            try:
                loaded = json.loads(tc_rule.rule_value)
                raw_cases = (
                    loaded.get("cases", []) if isinstance(loaded, dict) else []
                )
                if isinstance(raw_cases, list):
                    for raw_case in raw_cases:
                        if isinstance(raw_case, dict):
                            testcases.append(
                                HomeworkTestCaseWrite(
                                    name=str(
                                        raw_case.get(
                                            "name", f"case-{len(testcases)+1}"
                                        )
                                    ),
                                    input=str(raw_case.get("input", "")),
                                    expected_output=str(
                                        raw_case.get("expected_output", "")
                                    ),
                                    score=float(raw_case.get("score", 0.0)),
                                    is_hidden=bool(
                                        raw_case.get("is_hidden", False)
                                    ),
                                )
                            )
            except json.JSONDecodeError, ValueError:
                pass

        # Parse metadata
        meta_keys = ["problem_file_meta", "input_zip_meta", "output_zip_meta"]
        metas = {}
        for key in meta_keys:
            meta_rule = h_rules.get(key)
            if meta_rule:
                try:
                    loaded = json.loads(meta_rule.rule_value)
                    metas[key] = _normalize_artifact_metadata_payload(loaded)
                except json.JSONDecodeError, ValueError:
                    metas[key] = None
            else:
                metas[key] = None

        lint_week = (
            (h_rules.get("lint_week").rule_value.strip() or None)
            if h_rules.get("lint_week")
            else None
        )

        schedule_status, can_submit = compute_schedule_window(
            homework.starttime, homework.deadline
        )

        homework_read_data = {
            "num": h_num,
            "title": homework.title,
            "intro": homework.intro,
            "deadline": homework.deadline,
            "codeName": homework.codeName,
            "filename": homework.filename,
            "ratedatanum": homework.ratedatanum,
            "sec": homework.sec,
            "sbnum": homework.sbnum,
            "starttime": homework.starttime,
            "isDetected": homework.isDetected,
            "vitalSpace": homework.vitalSpace,
            "disorderedOutput": homework.disorderedOutput,
            "isLint": homework.isLint,
            "schedule_status": schedule_status,
            "can_submit": can_submit,
            "allowed_languages": allowed_languages,
        }

        results.append(
            HomeworkAdminRead(
                **homework_read_data,
                testcases=testcases,
                lint_week=lint_week,
                problem_file_name=(
                    metas["problem_file_meta"]["original_name"]
                    if metas["problem_file_meta"]
                    else None
                ),
                input_zip_name=(
                    metas["input_zip_meta"]["original_name"]
                    if metas["input_zip_meta"]
                    else None
                ),
                output_zip_name=(
                    metas["output_zip_meta"]["original_name"]
                    if metas["output_zip_meta"]
                    else None
                ),
                parsed_testcase_count=len(testcases),
            )
        )
    return results
