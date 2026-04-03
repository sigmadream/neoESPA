import json
import logging
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from pydantic import ValidationError
from sqlmodel import Session, select

from ...api.dependencies import get_optional_current_user, require_roles, require_staff
from ...api.runtime import observability_service
from ...core.config import settings
from ...core.db import get_session
from ...models.schemas import (
    Homework,
    HomeworkAdminRead,
    HomeworkAdminWrite,
    HomeworkRead,
    Submission,
    User,
)
from ...services.user_management import ADMIN_ROLES
from ..homework.helpers import (
    sync_homework_rules,
    to_homework_admin_read,
    to_homework_admin_read_batch,
    to_homework_read,
    upsert_homework_artifact_metadata,
)
from ..homework.zip_parser import (
    HomeworkZipValidationError,
    parse_homework_testcase_archives,
)
from ..shared.schedules import compute_schedule_window, parse_datetime


_FILENAME_SANITIZE_PATTERN = re.compile(r"[^\w.\-]+")
_ALLOWED_PROBLEM_FILE_EXTENSIONS = {".pdf", ".md", ".txt"}

logger = logging.getLogger(__name__)


def _get_homework_artifact_root() -> Path:
    return settings.BASE_DIR / "supportFiles" / "homeworks"


def _safe_upload_name(original_name: str | None, *, fallback: str) -> str:
    safe_name = Path(original_name or "").name.strip()
    return safe_name or fallback


def _sanitize_uploaded_filename(original_name: str | None, *, fallback: str) -> str:
    safe_name = _safe_upload_name(original_name, fallback=fallback)
    suffix = Path(safe_name).suffix
    stem = Path(safe_name).stem or Path(fallback).stem or fallback
    sanitized_stem = _FILENAME_SANITIZE_PATTERN.sub("_", stem).strip("._")
    if not sanitized_stem:
        sanitized_stem = Path(fallback).stem or fallback
    sanitized_suffix = _FILENAME_SANITIZE_PATTERN.sub("", suffix)
    return f"{sanitized_stem}{sanitized_suffix}"


def _validate_problem_file_extension(problem_filename: str) -> None:
    if Path(problem_filename).suffix.lower() not in _ALLOWED_PROBLEM_FILE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Problem file extension must be one of: .pdf, .md, .txt",
        )


def _validate_schedule_order(starttime: str | None, deadline: str | None) -> None:
    start_at = parse_datetime(starttime)
    deadline_at = parse_datetime(deadline)
    if start_at is not None and deadline_at is not None and deadline_at <= start_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="deadline must be later than starttime",
        )


def _parse_allowed_languages_form(raw_allowed_languages: str) -> list[str]:
    if not raw_allowed_languages.strip():
        return []

    try:
        loaded = json.loads(raw_allowed_languages)
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="allowed_languages must be a JSON array string",
        ) from error

    if not isinstance(loaded, list) or any(
        not isinstance(language, str) for language in loaded
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="allowed_languages must be a JSON array string",
        )

    return loaded


def _to_stored_relpath(stored_path: Path) -> str:
    workspace_root = _get_homework_artifact_root().parents[1]
    return stored_path.relative_to(workspace_root).as_posix()


def _build_artifact_metadata(
    *,
    original_name: str,
    stored_path: Path,
    size_bytes: int,
    content_type: str | None,
) -> dict[str, str | int | None]:
    return {
        "original_name": original_name,
        "stored_relpath": _to_stored_relpath(stored_path),
        "size_bytes": size_bytes,
        "content_type": content_type,
    }


def _build_import_audit_payload(
    *,
    title: str,
    code_name: str,
    problem_file_name: str,
    input_zip_name: str,
    output_zip_name: str,
    testcase_count: int,
) -> dict[str, str | int]:
    return {
        "title": title,
        "codeName": code_name,
        "problem_file_name": problem_file_name,
        "input_zip_name": input_zip_name,
        "output_zip_name": output_zip_name,
        "testcase_count": testcase_count,
    }


router = APIRouter()


@router.get("/homework", response_model=list[HomeworkRead])
def get_homeworks(
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_optional_current_user),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    homeworks = (
        session.exec(select(Homework).order_by(Homework.num).limit(limit).offset(offset))
        .all()
    )
    admin_reads = to_homework_admin_read_batch(session, homeworks)

    is_staff_user = current_user and current_user.user_group in ADMIN_ROLES

    visible_homeworks: list[HomeworkRead] = []
    for h_admin in admin_reads:
        if h_admin.schedule_status == "upcoming" and not is_staff_user:
            continue

        visible_homeworks.append(
            HomeworkRead(
                **h_admin.model_dump(
                    exclude={
                        "testcases",
                        "lint_week",
                        "problem_file_name",
                        "input_zip_name",
                        "output_zip_name",
                        "parsed_testcase_count",
                    }
                )
            )
        )

    return visible_homeworks


@router.get("/homework/{homework_num}", response_model=HomeworkRead)
def get_homework_detail(
    homework_num: int,
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_optional_current_user),
):
    homework = session.get(Homework, homework_num)
    if homework is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Homework not found"
        )

    schedule_status, _ = compute_schedule_window(homework.starttime, homework.deadline)
    is_staff_user = current_user and current_user.user_group in ADMIN_ROLES

    if schedule_status == "upcoming" and not is_staff_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Homework not found"
        )

    return to_homework_read(session, homework)


@router.get("/admin/homeworks", response_model=list[HomeworkAdminRead])
async def list_admin_homeworks(
    _: User = Depends(require_staff),
    session: Session = Depends(get_session),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    homeworks = (
        session.exec(select(Homework).order_by(Homework.num).limit(limit).offset(offset))
        .all()
    )
    return to_homework_admin_read_batch(session, homeworks)



@router.get("/admin/homeworks/{homework_num}", response_model=HomeworkAdminRead)
async def get_admin_homework(
    homework_num: int,
    _: User = Depends(require_staff),
    session: Session = Depends(get_session),
):
    homework = session.get(Homework, homework_num)
    if homework is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Homework not found"
        )
    return to_homework_admin_read(session, homework)


@router.post("/admin/homeworks", response_model=HomeworkAdminRead)
async def create_homework(
    payload: HomeworkAdminWrite,
    current_user: User = Depends(require_staff),
    session: Session = Depends(get_session),
):
    now = datetime.now(UTC)

    homework = Homework(
        title=payload.title,
        intro=payload.intro,
        deadline=payload.deadline,
        codeName=payload.codeName,
        filename=payload.filename,
        ratedatanum=payload.ratedatanum,
        sec=payload.sec,
        sbnum=payload.sbnum,
        starttime=payload.starttime,
        isDetected=payload.isDetected,
        vitalSpace=payload.vitalSpace,
        disorderedOutput=payload.disorderedOutput,
        isLint=payload.isLint,
        created_at=now,
        updated_at=now,
    )
    session.add(homework)
    session.flush()
    sync_homework_rules(session, homework.num or 0, payload)
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="create_homework",
        target_type="homework",
        target_id=str(homework.num or 0),
        payload=payload.model_dump(),
    )
    session.commit()
    session.refresh(homework)
    return to_homework_admin_read(session, homework)


@router.post("/admin/homeworks/import", response_model=HomeworkAdminRead)
async def import_homework(
    title: str = Form(...),
    intro: str = Form(...),
    codeName: str = Form(...),
    starttime: str | None = Form(None),
    deadline: str | None = Form(None),
    allowed_languages: str = Form("[]"),
    isLint: bool = Form(...),
    lint_week: str | None = Form(None),
    problem_file: UploadFile = File(...),
    input_zip: UploadFile = File(...),
    output_zip: UploadFile = File(...),
    current_user: User = Depends(require_staff),
    session: Session = Depends(get_session),
):
    normalized_lint_week = (
        (lint_week.strip() or None) if lint_week is not None else None
    )

    try:
        parsed_allowed_languages = _parse_allowed_languages_form(allowed_languages)

        # Parse testcases from streams to avoid loading whole Zips into memory
        parsed_testcases = parse_homework_testcase_archives(
            input_zip.file,
            output_zip.file,
        )

        # Reset streams after parsing if we need to read them again for disk storage
        input_zip.file.seek(0)
        output_zip.file.seek(0)

        problem_original_name = _safe_upload_name(
            problem_file.filename,
            fallback="problem-file",
        )
        _validate_problem_file_extension(problem_original_name)
        _validate_schedule_order(starttime, deadline)
        input_zip_original_name = _safe_upload_name(
            input_zip.filename,
            fallback="inputs.zip",
        )
        output_zip_original_name = _safe_upload_name(
            output_zip.filename,
            fallback="outputs.zip",
        )
        sanitized_problem_name = _sanitize_uploaded_filename(
            problem_file.filename,
            fallback="problem-file",
        )
        payload = HomeworkAdminWrite(
            title=title,
            intro=intro,
            deadline=deadline,
            codeName=codeName,
            filename=sanitized_problem_name,
            ratedatanum=len(parsed_testcases),
            starttime=starttime,
            isLint=isLint,
            allowed_languages=parsed_allowed_languages,
            testcases=parsed_testcases,
            lint_week=normalized_lint_week,
        )
    except HomeworkZipValidationError as error:
        logger.warning(f"Homework import zip validation failed: {error}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except ValidationError as error:
        logger.warning(f"Homework import model validation failed: {error}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error.errors(include_url=False),
        ) from error

    now = datetime.now(UTC)
    homework = Homework(
        title=payload.title,
        intro=payload.intro,
        deadline=payload.deadline,
        codeName=payload.codeName,
        filename=payload.filename,
        ratedatanum=payload.ratedatanum,
        sec=payload.sec,
        sbnum=payload.sbnum,
        starttime=payload.starttime,
        isDetected=payload.isDetected,
        vitalSpace=payload.vitalSpace,
        disorderedOutput=payload.disorderedOutput,
        isLint=payload.isLint,
        created_at=now,
        updated_at=now,
    )
    homework_root: Path | None = None

    try:
        session.add(homework)
        session.flush()

        homework_num = homework.num or 0
        homework_root = _get_homework_artifact_root() / str(homework_num)
        problem_dir = homework_root / "problem"
        archives_dir = homework_root / "archives"
        problem_path = problem_dir / sanitized_problem_name
        input_zip_path = archives_dir / "inputs.zip"
        output_zip_path = archives_dir / "outputs.zip"

        homework_root.mkdir(parents=True, exist_ok=False)
        problem_dir.mkdir()
        archives_dir.mkdir()

        # Write files using streams
        problem_file.file.seek(0)
        with open(problem_path, "wb") as pf:
            shutil.copyfileobj(problem_file.file, pf)
        with open(input_zip_path, "wb") as izf:
            shutil.copyfileobj(input_zip.file, izf)
        with open(output_zip_path, "wb") as ozf:
            shutil.copyfileobj(output_zip.file, ozf)

        sync_homework_rules(session, homework_num, payload)
        upsert_homework_artifact_metadata(
            session,
            homework_num,
            "problem_file_meta",
            _build_artifact_metadata(
                original_name=problem_original_name,
                stored_path=problem_path,
                size_bytes=problem_path.stat().st_size,
                content_type=problem_file.content_type,
            ),
        )
        upsert_homework_artifact_metadata(
            session,
            homework_num,
            "input_zip_meta",
            _build_artifact_metadata(
                original_name=input_zip_original_name,
                stored_path=input_zip_path,
                size_bytes=input_zip_path.stat().st_size,
                content_type=input_zip.content_type,
            ),
        )
        upsert_homework_artifact_metadata(
            session,
            homework_num,
            "output_zip_meta",
            _build_artifact_metadata(
                original_name=output_zip_original_name,
                stored_path=output_zip_path,
                size_bytes=output_zip_path.stat().st_size,
                content_type=output_zip.content_type,
            ),
        )
        observability_service.record_audit(
            session,
            actor_user_id=current_user.id,
            action_type="create_homework",
            target_type="homework",
            target_id=str(homework_num),
            payload=_build_import_audit_payload(
                title=payload.title,
                code_name=payload.codeName,
                problem_file_name=problem_original_name,
                input_zip_name=input_zip_original_name,
                output_zip_name=output_zip_original_name,
                testcase_count=len(parsed_testcases),
            ),
        )
        session.commit()
        session.refresh(homework)
        return to_homework_admin_read(session, homework)
    except HTTPException as error:
        logger.error(f"HTTP error during homework import: {error.detail}")
        session.rollback()
        if homework_root is not None:
            try:
                shutil.rmtree(homework_root, ignore_errors=True)
            except Exception as rmtree_error:
                logger.warning(f"Failed to cleanup homework artifacts at {homework_root}: {rmtree_error}")
        raise
    except Exception as error:
        logger.exception(f"Unexpected error during homework import: {error}")
        session.rollback()
        if homework_root is not None:
            try:
                shutil.rmtree(homework_root, ignore_errors=True)
            except Exception as rmtree_error:
                logger.warning(f"Failed to cleanup homework artifacts at {homework_root}: {rmtree_error}")
        raise


@router.patch("/admin/homeworks/{homework_num}", response_model=HomeworkAdminRead)
async def update_homework(
    homework_num: int,
    payload: HomeworkAdminWrite,
    current_user: User = Depends(require_staff),
    session: Session = Depends(get_session),
):
    homework = session.get(Homework, homework_num)
    if homework is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Homework not found"
        )

    homework.title = payload.title
    homework.intro = payload.intro
    homework.deadline = payload.deadline
    homework.codeName = payload.codeName
    homework.filename = payload.filename
    homework.ratedatanum = payload.ratedatanum
    homework.sec = payload.sec
    homework.sbnum = payload.sbnum
    homework.starttime = payload.starttime
    homework.isDetected = payload.isDetected
    homework.vitalSpace = payload.vitalSpace
    homework.disorderedOutput = payload.disorderedOutput
    homework.isLint = payload.isLint
    homework.updated_at = datetime.now(UTC)
    session.add(homework)
    sync_homework_rules(session, homework_num, payload)
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="update_homework",
        target_type="homework",
        target_id=str(homework_num),
        payload=payload.model_dump(),
    )
    session.commit()
    session.refresh(homework)
    return to_homework_admin_read(session, homework)


@router.delete("/admin/homeworks/{homework_num}")
async def delete_homework(
    homework_num: int,
    current_user: User = Depends(require_staff),
    session: Session = Depends(get_session),
):
    from ...models.schemas import GradingRule

    homework = session.get(Homework, homework_num)
    if homework is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Homework not found"
        )

    existing_submission = session.exec(
        select(Submission.id).where(Submission.homework_num == homework_num)
    ).first()
    if existing_submission is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete homework with submissions",
        )

    homework_artifact_root = _get_homework_artifact_root() / str(homework_num)

    try:
        artifact_rule_names = ["problem_file_meta", "input_zip_meta", "output_zip_meta"]
        grading_rules = session.exec(
            select(GradingRule).where(GradingRule.homework_num == homework_num)
        ).all()
        for grading_rule in grading_rules:
            if grading_rule.rule_name in artifact_rule_names:
                session.delete(grading_rule)

        remaining_rules = session.exec(
            select(GradingRule).where(GradingRule.homework_num == homework_num)
        ).all()
        for grading_rule in remaining_rules:
            session.delete(grading_rule)

        observability_service.record_audit(
            session,
            actor_user_id=current_user.id,
            action_type="delete_homework",
            target_type="homework",
            target_id=str(homework_num),
            payload={"title": homework.title},
        )
        session.delete(homework)
        session.commit()
    except Exception:
        session.rollback()
        raise

    if homework_artifact_root.exists():
        shutil.rmtree(homework_artifact_root, ignore_errors=True)

    return {"message": "Homework deleted successfully"}
