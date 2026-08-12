from datetime import UTC, datetime
import hashlib
import json
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
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from ...api.dependencies import require_capability
from ...api.runtime import observability_service
from ...core.db import get_session
from ...core.config import settings
from ...models.schemas import (
    AssignmentProblem,
    AssignmentProblemCreate,
    AssignmentProblemRead,
    Homework,
    JudgeJobRead,
    Problem,
    ProblemAsset,
    ProblemAssetRead,
    ProblemCreate,
    ProblemRead,
    ProblemRevision,
    ProblemRevisionCreate,
    ProblemRevisionRead,
    ProblemRevisionApproval,
    ProblemRevisionApprovalCreate,
    ProblemRevisionApprovalRead,
    ProblemTestCase,
    ProblemTestCaseRead,
    ProblemTestCaseUpdate,
    ProblemUpdate,
    ProblemCollaborator,
    ProblemCollaboratorCreate,
    ProblemCollaboratorRead,
    TestCaseGroup,
    TestCaseGroupCreate,
    TestCaseGroupRead,
    User,
)
from ...services.problem_service import (
    ProblemConflictError,
    ProblemService,
    ProblemValidationError,
)
from ...services.problem_package import (
    ProblemPackageError,
    parse_problem_package,
    read_limited_package,
)
from ...services.artifact_store import (
    ArtifactValidationError,
    LocalArtifactStore,
)
from ...services.judge_job_service import JobConflictError, JudgeJobService
from ...services.authorization_service import AuthorizationService
from ..settings.helpers import get_system_setting_value

router = APIRouter(prefix="/admin")
problem_service = ProblemService()
job_service = JudgeJobService()
authorization_service = AuthorizationService()


def _enqueue_upload_validation(
    session: Session, *, problem_id: int, revision_id: int, hashes: list[str]
) -> None:
    digest = hashlib.sha256(":".join(sorted(hashes)).encode()).hexdigest()[:24]
    job_service.enqueue(
        session,
        job_type="problem_validation",
        payload={
            "problem_id": problem_id,
            "revision_id": revision_id,
            "source": "upload",
        },
        idempotency_key=f"problem-validation:{revision_id}:{digest}",
        problem_id=problem_id,
        revision_id=revision_id,
    )


def _problem_or_404(session: Session, problem_id: int) -> Problem:
    problem = session.get(Problem, problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")
    return problem


def _revision_or_404(
    session: Session, problem_id: int, revision_id: int
) -> ProblemRevision:
    revision = session.get(ProblemRevision, revision_id)
    if revision is None or revision.problem_id != problem_id:
        raise HTTPException(
            status_code=404, detail="Problem revision not found"
        )
    return revision


def _raise_problem_error(error: ValueError) -> None:
    code = (
        status.HTTP_409_CONFLICT
        if isinstance(error, ProblemConflictError)
        else 400
    )
    raise HTTPException(status_code=code, detail=str(error)) from error


def _editable_revision_or_409(
    session: Session, problem_id: int, revision_id: int
) -> ProblemRevision:
    revision = _revision_or_404(session, problem_id, revision_id)
    if revision.status != "draft":
        raise HTTPException(
            status_code=409, detail="Only draft revisions can change test data"
        )
    return revision


def _authorize_problem_scope(
    session: Session, user: User, problem: Problem, capability: str
) -> None:
    if not authorization_service.can_access_problem(
        session, user, problem, capability
    ):
        raise HTTPException(
            status_code=403, detail="Problem is outside the user's scope"
        )


def _asset_read(asset: ProblemAsset) -> ProblemAssetRead:
    return ProblemAssetRead.model_validate(asset)


def _testcase_read(testcase: ProblemTestCase) -> ProblemTestCaseRead:
    return ProblemTestCaseRead.model_validate(testcase)


@router.get("/problems", response_model=list[ProblemRead])
def list_problems(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_capability("problem:data.read")),
    session: Session = Depends(get_session),
):
    problems = session.exec(
        select(Problem).order_by(Problem.id.desc()).offset(offset).limit(limit)
    ).all()
    return [
        problem_service.to_problem_read(session, problem)
        for problem in problems
        if authorization_service.can_access_problem(
            session, current_user, problem, "problem:data.read"
        )
    ]


@router.post("/problems", response_model=ProblemRead, status_code=201)
def create_problem(
    payload: ProblemCreate,
    current_user: User = Depends(require_capability("problem:create")),
    session: Session = Depends(get_session),
):
    try:
        problem, revision = problem_service.create_problem(
            session, payload, current_user.id
        )
        observability_service.record_audit(
            session,
            actor_user_id=current_user.id,
            action_type="create_problem",
            target_type="problem",
            target_id=str(problem.id),
            payload={"code": problem.code, "revision_id": revision.id},
        )
        session.commit()
        session.refresh(problem)
        return problem_service.to_problem_read(session, problem)
    except (ProblemConflictError, ProblemValidationError) as error:
        session.rollback()
        _raise_problem_error(error)
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=409, detail="Problem code already exists"
        ) from error


@router.get("/problems/{problem_id}", response_model=ProblemRead)
def get_problem(
    problem_id: int,
    current_user: User = Depends(require_capability("problem:data.read")),
    session: Session = Depends(get_session),
):
    problem = _problem_or_404(session, problem_id)
    _authorize_problem_scope(
        session, current_user, problem, "problem:data.read"
    )
    return problem_service.to_problem_read(session, problem)


@router.get(
    "/problems/{problem_id}/collaborators",
    response_model=list[ProblemCollaboratorRead],
)
def list_problem_collaborators(
    problem_id: int,
    current_user: User = Depends(require_capability("problem:edit")),
    session: Session = Depends(get_session),
):
    problem = _problem_or_404(session, problem_id)
    _authorize_problem_scope(session, current_user, problem, "problem:edit")
    return session.exec(
        select(ProblemCollaborator)
        .where(ProblemCollaborator.problem_id == problem_id)
        .order_by(ProblemCollaborator.user_id)
    ).all()


@router.post(
    "/problems/{problem_id}/collaborators",
    response_model=ProblemCollaboratorRead,
    status_code=201,
)
def add_problem_collaborator(
    problem_id: int,
    payload: ProblemCollaboratorCreate,
    current_user: User = Depends(require_capability("problem:edit")),
    session: Session = Depends(get_session),
):
    problem = _problem_or_404(session, problem_id)
    _authorize_problem_scope(session, current_user, problem, "problem:edit")
    collaborator_user = session.get(User, payload.user_id)
    if collaborator_user is None:
        raise HTTPException(
            status_code=404, detail="Collaborator user not found"
        )
    if not authorization_service.has_capability(
        session, collaborator_user, "problem:data.read"
    ):
        raise HTTPException(
            status_code=400,
            detail="Collaborator role cannot access problem data",
        )
    collaborator = ProblemCollaborator(
        problem_id=problem_id, **payload.model_dump()
    )
    session.add(collaborator)
    try:
        observability_service.record_audit(
            session,
            actor_user_id=current_user.id,
            action_type="add_problem_collaborator",
            target_type="problem",
            target_id=str(problem_id),
            after=payload.model_dump(),
        )
        session.commit()
        session.refresh(collaborator)
        return collaborator
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=409, detail="Problem collaborator already exists"
        ) from error


@router.delete(
    "/problems/{problem_id}/collaborators/{user_id}", status_code=204
)
def remove_problem_collaborator(
    problem_id: int,
    user_id: str,
    current_user: User = Depends(require_capability("problem:edit")),
    session: Session = Depends(get_session),
):
    problem = _problem_or_404(session, problem_id)
    _authorize_problem_scope(session, current_user, problem, "problem:edit")
    collaborator = session.exec(
        select(ProblemCollaborator).where(
            ProblemCollaborator.problem_id == problem_id,
            ProblemCollaborator.user_id == user_id,
        )
    ).first()
    if collaborator is None:
        raise HTTPException(
            status_code=404, detail="Problem collaborator not found"
        )
    session.delete(collaborator)
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="remove_problem_collaborator",
        target_type="problem",
        target_id=str(problem_id),
        before={"user_id": user_id},
    )
    session.commit()
    return None


@router.patch("/problems/{problem_id}", response_model=ProblemRead)
def update_problem(
    problem_id: int,
    payload: ProblemUpdate,
    current_user: User = Depends(require_capability("problem:edit")),
    session: Session = Depends(get_session),
):
    problem = _problem_or_404(session, problem_id)
    _authorize_problem_scope(session, current_user, problem, "problem:edit")
    before = {"title": problem.title, "is_active": problem.is_active}
    if payload.title is not None:
        problem.title = payload.title.strip()
    if payload.is_active is not None:
        problem.is_active = payload.is_active
    problem.updated_at = datetime.now(UTC)
    session.add(problem)
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="update_problem",
        target_type="problem",
        target_id=str(problem.id),
        payload={
            "before": before,
            "after": payload.model_dump(exclude_none=True),
        },
    )
    session.commit()
    session.refresh(problem)
    return problem_service.to_problem_read(session, problem)


@router.post(
    "/problems/{problem_id}/revisions",
    response_model=ProblemRevisionRead,
    status_code=201,
)
def create_revision(
    problem_id: int,
    payload: ProblemRevisionCreate,
    current_user: User = Depends(require_capability("problem:edit")),
    session: Session = Depends(get_session),
):
    problem = _problem_or_404(session, problem_id)
    _authorize_problem_scope(session, current_user, problem, "problem:edit")
    try:
        revision = problem_service.create_revision(
            session, problem, payload, current_user.id
        )
        session.commit()
        session.refresh(revision)
        return problem_service.to_revision_read(revision)
    except (ProblemConflictError, ProblemValidationError) as error:
        session.rollback()
        _raise_problem_error(error)


@router.get(
    "/problems/{problem_id}/revisions", response_model=list[ProblemRevisionRead]
)
def list_revisions(
    problem_id: int,
    current_user: User = Depends(require_capability("problem:data.read")),
    session: Session = Depends(get_session),
):
    problem = _problem_or_404(session, problem_id)
    _authorize_problem_scope(
        session, current_user, problem, "problem:data.read"
    )
    revisions = session.exec(
        select(ProblemRevision)
        .where(ProblemRevision.problem_id == problem_id)
        .order_by(ProblemRevision.revision_no.desc())
    ).all()
    return [
        problem_service.to_revision_read(revision) for revision in revisions
    ]


@router.get(
    "/problems/{problem_id}/revisions/{revision_id}",
    response_model=ProblemRevisionRead,
)
def get_revision(
    problem_id: int,
    revision_id: int,
    current_user: User = Depends(require_capability("problem:data.read")),
    session: Session = Depends(get_session),
):
    problem = _problem_or_404(session, problem_id)
    _authorize_problem_scope(
        session, current_user, problem, "problem:data.read"
    )
    return problem_service.to_revision_read(
        _revision_or_404(session, problem_id, revision_id)
    )


@router.patch(
    "/problems/{problem_id}/revisions/{revision_id}",
    response_model=ProblemRevisionRead,
)
def update_draft_revision(
    problem_id: int,
    revision_id: int,
    payload: ProblemRevisionCreate,
    current_user: User = Depends(require_capability("problem:edit")),
    session: Session = Depends(get_session),
):
    problem = _problem_or_404(session, problem_id)
    _authorize_problem_scope(session, current_user, problem, "problem:edit")
    revision = _editable_revision_or_409(session, problem_id, revision_id)
    before = problem_service.to_revision_read(revision).model_dump(mode="json")
    values = payload.model_dump(exclude_none=True)
    scalar_fields = {
        "statement",
        "input_description",
        "output_description",
        "time_limit_ms",
        "memory_limit_mb",
        "output_limit_kb",
        "process_limit",
        "source_limit_kb",
        "checker_type",
        "problem_mode",
    }
    for field in scalar_fields & values.keys():
        setattr(revision, field, values[field])
    if "allowed_languages" in values:
        revision.allowed_languages_json = json.dumps(
            problem_service.validate_languages(values["allowed_languages"])
        )
    if "checker_config" in values:
        revision.checker_config_json = json.dumps(
            values["checker_config"], sort_keys=True
        )
    if "language_multipliers" in values:
        revision.language_multipliers_json = json.dumps(
            values["language_multipliers"], sort_keys=True
        )
    revision.validation_report = None
    session.add(revision)
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="update_problem_revision",
        target_type="problem_revision",
        target_id=str(revision_id),
        before=before,
        after=values,
    )
    session.commit()
    session.refresh(revision)
    return problem_service.to_revision_read(revision)


@router.post("/problems/{problem_id}/archive", response_model=ProblemRead)
def archive_problem(
    problem_id: int,
    current_user: User = Depends(require_capability("problem:publish")),
    session: Session = Depends(get_session),
):
    problem = _problem_or_404(session, problem_id)
    _authorize_problem_scope(session, current_user, problem, "problem:publish")
    revisions = session.exec(
        select(ProblemRevision).where(ProblemRevision.problem_id == problem_id)
    ).all()
    for revision in revisions:
        if revision.status in {"ready", "published"}:
            revision.status = "archived"
            session.add(revision)
    problem.is_active = False
    problem.updated_at = datetime.now(UTC)
    session.add(problem)
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="archive_problem",
        target_type="problem",
        target_id=str(problem_id),
        before={"is_active": True},
        after={"is_active": False},
    )
    session.commit()
    session.refresh(problem)
    return problem_service.to_problem_read(session, problem)


@router.post(
    "/problems/{problem_id}/revisions/{revision_id}/validate",
    response_model=ProblemRevisionRead,
)
def validate_revision(
    problem_id: int,
    revision_id: int,
    current_user: User = Depends(require_capability("problem:review")),
    session: Session = Depends(get_session),
):
    problem = _problem_or_404(session, problem_id)
    _authorize_problem_scope(session, current_user, problem, "problem:review")
    revision = _revision_or_404(session, problem_id, revision_id)
    try:
        problem_service.validate_revision(revision)
        session.add(revision)
        observability_service.record_audit(
            session,
            actor_user_id=current_user.id,
            action_type="validate_problem_revision",
            target_type="problem_revision",
            target_id=str(revision.id),
            payload={"status": revision.status},
        )
        session.commit()
        session.refresh(revision)
        return problem_service.to_revision_read(revision)
    except (ProblemConflictError, ProblemValidationError) as error:
        # Persist the validation report even when the API reports failure.
        session.add(revision)
        session.commit()
        _raise_problem_error(error)


@router.post(
    "/problems/{problem_id}/revisions/{revision_id}/validation-jobs",
    response_model=JudgeJobRead,
    status_code=202,
)
def create_validation_job(
    problem_id: int,
    revision_id: int,
    idempotency_key: str | None = Query(default=None, max_length=120),
    current_user: User = Depends(require_capability("problem:review")),
    session: Session = Depends(get_session),
):
    problem = _problem_or_404(session, problem_id)
    _authorize_problem_scope(session, current_user, problem, "problem:review")
    _editable_revision_or_409(session, problem_id, revision_id)
    try:
        job = job_service.enqueue(
            session,
            job_type="problem_validation",
            payload={"problem_id": problem_id, "revision_id": revision_id},
            idempotency_key=idempotency_key,
            problem_id=problem_id,
            revision_id=revision_id,
        )
        observability_service.record_audit(
            session,
            actor_user_id=current_user.id,
            action_type="queue_problem_validation",
            target_type="problem_revision",
            target_id=str(revision_id),
            payload={"job_id": job.id},
        )
        session.commit()
        session.refresh(job)
        return job_service.to_read(job)
    except JobConflictError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post(
    "/problems/{problem_id}/revisions/{revision_id}/dry-runs",
    response_model=JudgeJobRead,
    status_code=202,
)
def create_problem_dry_run(
    problem_id: int,
    revision_id: int,
    language: str = Form(...),
    source_file: UploadFile = File(...),
    current_user: User = Depends(require_capability("problem:review")),
    session: Session = Depends(get_session),
):
    if not settings.SANDBOX_READY:
        raise HTTPException(
            status_code=503,
            detail="Sandbox hostile-fixture gate is not enabled",
        )
    problem = _problem_or_404(session, problem_id)
    _authorize_problem_scope(session, current_user, problem, "problem:review")
    revision = _revision_or_404(session, problem_id, revision_id)
    if revision.status not in {"draft", "ready"}:
        raise HTTPException(
            status_code=409, detail="Dry-runs require a draft or ready revision"
        )
    allowed = set(json.loads(revision.allowed_languages_json))
    normalized_language = language.strip().lower()
    if normalized_language not in allowed:
        raise HTTPException(
            status_code=400, detail="Language is not allowed by revision"
        )
    try:
        stored = LocalArtifactStore().put_stream(
            source_file.file, max_bytes=revision.source_limit_kb * 1024
        )
    except ArtifactValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    asset = session.exec(
        select(ProblemAsset).where(
            ProblemAsset.revision_id == revision_id,
            ProblemAsset.asset_kind == "reference_solution",
            ProblemAsset.sha256 == stored.sha256,
        )
    ).first()
    if asset is None:
        asset = ProblemAsset(
            revision_id=revision_id,
            asset_kind="reference_solution",
            display_name=(
                f"reference-{stored.sha256[:12]}-{Path(source_file.filename or 'main.txt').name}"
            ),
            storage_path=stored.relative_path,
            sha256=stored.sha256,
            size_bytes=stored.size_bytes,
            content_type=source_file.content_type,
            is_hidden=True,
        )
        session.add(asset)
        session.flush()
    job = job_service.enqueue(
        session,
        job_type="problem_dry_run",
        payload={"asset_id": asset.id, "language": normalized_language},
        idempotency_key=f"dry-run:{revision_id}:{normalized_language}:{stored.sha256}",
        problem_id=problem_id,
        revision_id=revision_id,
    )
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="create_problem_dry_run",
        target_type="judge_job",
        target_id=str(job.id),
        job_id=job.id,
        payload={"revision_id": revision_id, "language": normalized_language},
    )
    session.commit()
    session.refresh(job)
    return job_service.to_read(job)


@router.post(
    "/problems/{problem_id}/revisions/{revision_id}/publish",
    response_model=ProblemRevisionRead,
)
def publish_revision(
    problem_id: int,
    revision_id: int,
    current_user: User = Depends(require_capability("problem:publish")),
    session: Session = Depends(get_session),
):
    problem = _problem_or_404(session, problem_id)
    _authorize_problem_scope(session, current_user, problem, "problem:publish")
    revision = _revision_or_404(session, problem_id, revision_id)
    if (
        get_system_setting_value(session, "problem_two_person_publish")
        == "true"
    ):
        approval = session.exec(
            select(ProblemRevisionApproval).where(
                ProblemRevisionApproval.revision_id == revision_id,
                ProblemRevisionApproval.decision == "approved",
                ProblemRevisionApproval.reviewer_id != revision.created_by,
            )
        ).first()
        if approval is None:
            raise HTTPException(
                status_code=409,
                detail="Independent reviewer approval is required",
            )
    try:
        problem_service.publish_revision(session, problem, revision)
        observability_service.record_audit(
            session,
            actor_user_id=current_user.id,
            action_type="publish_problem_revision",
            target_type="problem_revision",
            target_id=str(revision.id),
            payload={
                "problem_id": problem_id,
                "revision_no": revision.revision_no,
            },
        )
        session.commit()
        session.refresh(revision)
        return problem_service.to_revision_read(revision)
    except (ProblemConflictError, ProblemValidationError) as error:
        session.rollback()
        _raise_problem_error(error)


@router.post(
    "/problems/{problem_id}/revisions/{revision_id}/approvals",
    response_model=ProblemRevisionApprovalRead,
    status_code=201,
)
def review_problem_revision(
    problem_id: int,
    revision_id: int,
    payload: ProblemRevisionApprovalCreate,
    current_user: User = Depends(require_capability("problem:review")),
    session: Session = Depends(get_session),
):
    problem = _problem_or_404(session, problem_id)
    _authorize_problem_scope(session, current_user, problem, "problem:review")
    revision = _revision_or_404(session, problem_id, revision_id)
    if revision.status != "ready":
        raise HTTPException(
            status_code=409, detail="Only ready revisions can be reviewed"
        )
    if current_user.id == revision.created_by:
        raise HTTPException(
            status_code=409,
            detail="Revision author cannot independently approve it",
        )
    if payload.decision not in {"approved", "rejected"}:
        raise HTTPException(
            status_code=400, detail="Unsupported review decision"
        )
    approval = ProblemRevisionApproval(
        revision_id=revision_id,
        reviewer_id=current_user.id,
        decision=payload.decision,
        note=payload.note,
    )
    session.add(approval)
    try:
        observability_service.record_audit(
            session,
            actor_user_id=current_user.id,
            action_type="review_problem_revision",
            target_type="problem_revision",
            target_id=str(revision_id),
            after=payload.model_dump(),
        )
        session.commit()
        session.refresh(approval)
        return approval
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=409, detail="Reviewer already decided this revision"
        ) from error


@router.post(
    "/homeworks/{homework_num}/problems",
    response_model=AssignmentProblemRead,
    status_code=201,
)
def attach_problem_to_homework(
    homework_num: int,
    payload: AssignmentProblemCreate,
    current_user: User = Depends(require_capability("problem:publish")),
    session: Session = Depends(get_session),
):
    if session.get(Homework, homework_num) is None:
        raise HTTPException(status_code=404, detail="Homework not found")
    revision = session.get(ProblemRevision, payload.revision_id)
    if revision is None:
        raise HTTPException(
            status_code=404, detail="Problem revision not found"
        )
    problem = _problem_or_404(session, revision.problem_id)
    _authorize_problem_scope(session, current_user, problem, "problem:publish")
    if revision.status != "published":
        raise HTTPException(
            status_code=409, detail="Only published revisions can be assigned"
        )
    assignment = AssignmentProblem(
        homework_num=homework_num,
        revision_id=revision.id or 0,
        position=payload.position,
    )
    session.add(assignment)
    try:
        session.flush()
        observability_service.record_audit(
            session,
            actor_user_id=current_user.id,
            action_type="attach_problem_to_homework",
            target_type="homework",
            target_id=str(homework_num),
            payload={"revision_id": revision.id, "position": payload.position},
        )
        session.commit()
        session.refresh(assignment)
        return AssignmentProblemRead.model_validate(assignment)
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=409, detail="Homework problem position already exists"
        ) from error


@router.get(
    "/problems/{problem_id}/revisions/{revision_id}/assets",
    response_model=list[ProblemAssetRead],
)
def list_assets(
    problem_id: int,
    revision_id: int,
    current_user: User = Depends(require_capability("problem:data.read")),
    session: Session = Depends(get_session),
):
    problem = _problem_or_404(session, problem_id)
    _authorize_problem_scope(
        session, current_user, problem, "problem:data.read"
    )
    _revision_or_404(session, problem_id, revision_id)
    assets = session.exec(
        select(ProblemAsset)
        .where(ProblemAsset.revision_id == revision_id)
        .order_by(ProblemAsset.id)
    ).all()
    return [_asset_read(asset) for asset in assets]


@router.post(
    "/problems/{problem_id}/revisions/{revision_id}/assets",
    response_model=ProblemAssetRead,
    status_code=201,
)
def upload_problem_asset(
    problem_id: int,
    revision_id: int,
    asset_kind: str = Form(...),
    asset_file: UploadFile = File(...),
    current_user: User = Depends(require_capability("problem:edit")),
    session: Session = Depends(get_session),
):
    problem = _problem_or_404(session, problem_id)
    _authorize_problem_scope(session, current_user, problem, "problem:edit")
    revision = _editable_revision_or_409(session, problem_id, revision_id)
    allowed_kinds = {
        "attachment",
        "image",
        "checker",
        "generator",
        "reference_solution",
    }
    if asset_kind not in allowed_kinds:
        raise HTTPException(
            status_code=400, detail="Unsupported problem asset kind"
        )
    suffix = Path(asset_file.filename or "").suffix.lower()
    # SpecialJudgeChecker currently has one explicit, sandboxed contract: a
    # Python program invoked with input/expected/actual paths.  Do not accept
    # checker languages that the worker cannot execute according to that
    # contract.  Generators and reference solutions are only stored/validated
    # here and may use any supported source language.
    allowed_executable_suffixes = {".py", ".c", ".cc", ".cpp", ".java"}
    if asset_kind == "checker" and suffix != ".py":
        raise HTTPException(
            status_code=400,
            detail="Special checker must be a Python source file",
        )
    if (
        asset_kind in {"generator", "reference_solution"}
        and suffix not in allowed_executable_suffixes
    ):
        raise HTTPException(
            status_code=400, detail="Executable asset extension is not allowed"
        )
    store = LocalArtifactStore()
    try:
        stored = store.put_stream(
            asset_file.file, max_bytes=revision.source_limit_kb * 1024
        )
    except ArtifactValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    asset = ProblemAsset(
        revision_id=revision_id,
        asset_kind=asset_kind,
        display_name=Path(
            asset_file.filename or f"{asset_kind}-{stored.sha256[:12]}"
        ).name,
        storage_path=stored.relative_path,
        sha256=stored.sha256,
        size_bytes=stored.size_bytes,
        content_type=asset_file.content_type,
        is_hidden=True,
    )
    session.add(asset)
    try:
        session.flush()
        _enqueue_upload_validation(
            session,
            problem_id=problem_id,
            revision_id=revision_id,
            hashes=[stored.sha256],
        )
        observability_service.record_audit(
            session,
            actor_user_id=current_user.id,
            action_type="upload_problem_asset",
            target_type="problem_asset",
            target_id=str(asset.id),
            payload={"kind": asset_kind, "sha256": stored.sha256},
        )
        session.commit()
        session.refresh(asset)
        return _asset_read(asset)
    except IntegrityError as error:
        session.rollback()
        store.discard_new(stored)
        raise HTTPException(
            status_code=409, detail="Problem asset name already exists"
        ) from error


@router.get(
    "/problems/{problem_id}/revisions/{revision_id}/assets/{asset_id}/download"
)
def download_asset(
    problem_id: int,
    revision_id: int,
    asset_id: int,
    current_user: User = Depends(require_capability("problem:data.read")),
    session: Session = Depends(get_session),
):
    problem = _problem_or_404(session, problem_id)
    _authorize_problem_scope(
        session, current_user, problem, "problem:data.read"
    )
    _revision_or_404(session, problem_id, revision_id)
    asset = session.get(ProblemAsset, asset_id)
    if asset is None or asset.revision_id != revision_id:
        raise HTTPException(status_code=404, detail="Problem asset not found")
    try:
        path = LocalArtifactStore().resolve(asset.storage_path, asset.sha256)
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=410, detail="Problem asset is missing"
        ) from error
    except ArtifactValidationError as error:
        raise HTTPException(
            status_code=500, detail="Problem asset failed integrity check"
        ) from error
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="download_problem_asset",
        target_type="problem_asset",
        target_id=str(asset.id),
        payload={"revision_id": revision_id, "asset_kind": asset.asset_kind},
    )
    session.commit()
    return FileResponse(
        path, media_type=asset.content_type, filename=asset.display_name
    )


@router.get(
    "/problems/{problem_id}/revisions/{revision_id}/testcase-groups",
    response_model=list[TestCaseGroupRead],
)
def list_testcase_groups(
    problem_id: int,
    revision_id: int,
    current_user: User = Depends(require_capability("problem:data.read")),
    session: Session = Depends(get_session),
):
    problem = _problem_or_404(session, problem_id)
    _authorize_problem_scope(
        session, current_user, problem, "problem:data.read"
    )
    _revision_or_404(session, problem_id, revision_id)
    return session.exec(
        select(TestCaseGroup)
        .where(TestCaseGroup.revision_id == revision_id)
        .order_by(TestCaseGroup.position, TestCaseGroup.id)
    ).all()


@router.post(
    "/problems/{problem_id}/revisions/{revision_id}/testcase-groups",
    response_model=TestCaseGroupRead,
    status_code=201,
)
def create_testcase_group(
    problem_id: int,
    revision_id: int,
    payload: TestCaseGroupCreate,
    current_user: User = Depends(require_capability("problem:edit")),
    session: Session = Depends(get_session),
):
    problem = _problem_or_404(session, problem_id)
    _authorize_problem_scope(session, current_user, problem, "problem:edit")
    _editable_revision_or_409(session, problem_id, revision_id)
    if payload.scoring_policy not in {"sum", "all_or_nothing"}:
        raise HTTPException(
            status_code=400, detail="Unsupported testcase group policy"
        )
    if payload.dependency_group_id is not None:
        dependency = session.get(TestCaseGroup, payload.dependency_group_id)
        if dependency is None or dependency.revision_id != revision_id:
            raise HTTPException(
                status_code=400,
                detail="Dependency group does not belong to revision",
            )
    group = TestCaseGroup(revision_id=revision_id, **payload.model_dump())
    session.add(group)
    try:
        session.commit()
        session.refresh(group)
        return group
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=409, detail="Testcase group key already exists"
        ) from error


@router.get(
    "/problems/{problem_id}/revisions/{revision_id}/testcases",
    response_model=list[ProblemTestCaseRead],
)
def list_testcases(
    problem_id: int,
    revision_id: int,
    current_user: User = Depends(require_capability("problem:data.read")),
    session: Session = Depends(get_session),
):
    problem = _problem_or_404(session, problem_id)
    _authorize_problem_scope(
        session, current_user, problem, "problem:data.read"
    )
    _revision_or_404(session, problem_id, revision_id)
    testcases = session.exec(
        select(ProblemTestCase)
        .where(ProblemTestCase.revision_id == revision_id)
        .order_by(ProblemTestCase.position)
    ).all()
    return [_testcase_read(testcase) for testcase in testcases]


@router.post(
    "/problems/{problem_id}/revisions/{revision_id}/testcases",
    response_model=ProblemTestCaseRead,
    status_code=201,
)
def create_testcase(
    problem_id: int,
    revision_id: int,
    case_name: str = Form(...),
    position: int = Form(..., ge=1),
    score: float = Form(default=0.0, ge=0),
    group_id: int | None = Form(default=None),
    is_sample: bool = Form(default=False),
    input_file: UploadFile = File(...),
    output_file: UploadFile = File(...),
    current_user: User = Depends(require_capability("problem:edit")),
    session: Session = Depends(get_session),
):
    problem = _problem_or_404(session, problem_id)
    _authorize_problem_scope(session, current_user, problem, "problem:edit")
    _editable_revision_or_409(session, problem_id, revision_id)
    if group_id is not None:
        group = session.get(TestCaseGroup, group_id)
        if group is None or group.revision_id != revision_id:
            raise HTTPException(
                status_code=400,
                detail="Testcase group does not belong to revision",
            )
    store = LocalArtifactStore()
    stored_objects = []
    try:
        input_stored = store.put_stream(input_file.file)
        stored_objects.append(input_stored)
        output_stored = store.put_stream(output_file.file)
        stored_objects.append(output_stored)
    except ArtifactValidationError as error:
        for stored in stored_objects:
            store.discard_new(stored)
        raise HTTPException(status_code=400, detail=str(error)) from error

    input_asset = ProblemAsset(
        revision_id=revision_id,
        asset_kind="test_input",
        display_name=input_file.filename or f"{case_name}.in",
        storage_path=input_stored.relative_path,
        sha256=input_stored.sha256,
        size_bytes=input_stored.size_bytes,
        content_type=input_file.content_type,
        is_hidden=not is_sample,
    )
    output_asset = ProblemAsset(
        revision_id=revision_id,
        asset_kind="test_output",
        display_name=output_file.filename or f"{case_name}.out",
        storage_path=output_stored.relative_path,
        sha256=output_stored.sha256,
        size_bytes=output_stored.size_bytes,
        content_type=output_file.content_type,
        is_hidden=not is_sample,
    )
    session.add(input_asset)
    session.add(output_asset)
    try:
        session.flush()
        testcase = ProblemTestCase(
            revision_id=revision_id,
            group_id=group_id,
            case_name=case_name.strip(),
            position=position,
            input_asset_id=input_asset.id or 0,
            output_asset_id=output_asset.id or 0,
            score=score,
            is_sample=is_sample,
        )
        session.add(testcase)
        session.flush()
        observability_service.record_audit(
            session,
            actor_user_id=current_user.id,
            action_type="create_problem_testcase",
            target_type="problem_revision",
            target_id=str(revision_id),
            payload={
                "case_name": case_name,
                "position": position,
                "is_sample": is_sample,
            },
        )
        _enqueue_upload_validation(
            session,
            problem_id=problem_id,
            revision_id=revision_id,
            hashes=[input_stored.sha256, output_stored.sha256],
        )
        session.commit()
        session.refresh(testcase)
        return _testcase_read(testcase)
    except IntegrityError as error:
        session.rollback()
        for stored in stored_objects:
            store.discard_new(stored)
        raise HTTPException(
            status_code=409, detail="Testcase name or position already exists"
        ) from error


@router.post(
    "/problems/{problem_id}/revisions/{revision_id}/testcases/package",
    response_model=list[ProblemTestCaseRead],
    status_code=201,
)
def import_testcase_package(
    problem_id: int,
    revision_id: int,
    package: UploadFile = File(...),
    current_user: User = Depends(require_capability("problem:edit")),
    session: Session = Depends(get_session),
):
    problem = _problem_or_404(session, problem_id)
    _authorize_problem_scope(session, current_user, problem, "problem:edit")
    _editable_revision_or_409(session, problem_id, revision_id)
    try:
        cases = parse_problem_package(read_limited_package(package.file))
    except ProblemPackageError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    store = LocalArtifactStore()
    created: list[ProblemTestCase] = []
    stored_objects = []
    try:
        for case in cases:
            input_stored = store.put_bytes(case.input_content)
            output_stored = store.put_bytes(case.output_content)
            stored_objects.extend([input_stored, output_stored])
            input_asset = ProblemAsset(
                revision_id=revision_id,
                asset_kind="test_input",
                display_name=case.input_name,
                storage_path=input_stored.relative_path,
                sha256=input_stored.sha256,
                size_bytes=input_stored.size_bytes,
                content_type="application/octet-stream",
                is_hidden=not case.is_sample,
            )
            output_asset = ProblemAsset(
                revision_id=revision_id,
                asset_kind="test_output",
                display_name=case.output_name,
                storage_path=output_stored.relative_path,
                sha256=output_stored.sha256,
                size_bytes=output_stored.size_bytes,
                content_type="application/octet-stream",
                is_hidden=not case.is_sample,
            )
            session.add(input_asset)
            session.add(output_asset)
            session.flush()
            testcase = ProblemTestCase(
                revision_id=revision_id,
                case_name=case.name,
                position=case.position,
                input_asset_id=input_asset.id or 0,
                output_asset_id=output_asset.id or 0,
                score=case.score,
                is_sample=case.is_sample,
            )
            session.add(testcase)
            session.flush()
            created.append(testcase)
        observability_service.record_audit(
            session,
            actor_user_id=current_user.id,
            action_type="import_problem_testcase_package",
            target_type="problem_revision",
            target_id=str(revision_id),
            payload={
                "filename": package.filename,
                "testcase_count": len(created),
            },
        )
        _enqueue_upload_validation(
            session,
            problem_id=problem_id,
            revision_id=revision_id,
            hashes=[stored.sha256 for stored in stored_objects],
        )
        session.commit()
        for testcase in created:
            session.refresh(testcase)
        return [_testcase_read(testcase) for testcase in created]
    except (IntegrityError, ArtifactValidationError) as error:
        session.rollback()
        for stored in stored_objects:
            store.discard_new(stored)
        raise HTTPException(
            status_code=409, detail="Package conflicts with existing test data"
        ) from error


@router.patch(
    "/problems/{problem_id}/revisions/{revision_id}/testcases/{testcase_id}",
    response_model=ProblemTestCaseRead,
)
def update_testcase(
    problem_id: int,
    revision_id: int,
    testcase_id: int,
    payload: ProblemTestCaseUpdate,
    current_user: User = Depends(require_capability("problem:edit")),
    session: Session = Depends(get_session),
):
    problem = _problem_or_404(session, problem_id)
    _authorize_problem_scope(session, current_user, problem, "problem:edit")
    _editable_revision_or_409(session, problem_id, revision_id)
    testcase = session.get(ProblemTestCase, testcase_id)
    if testcase is None or testcase.revision_id != revision_id:
        raise HTTPException(status_code=404, detail="Testcase not found")
    if payload.group_id is not None:
        group = session.get(TestCaseGroup, payload.group_id)
        if group is None or group.revision_id != revision_id:
            raise HTTPException(
                status_code=400,
                detail="Testcase group does not belong to revision",
            )
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(testcase, field, value)
    session.add(testcase)
    try:
        session.commit()
        session.refresh(testcase)
        return _testcase_read(testcase)
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=409, detail="Testcase name or position already exists"
        ) from error


@router.delete(
    "/problems/{problem_id}/revisions/{revision_id}/testcases/{testcase_id}",
    status_code=204,
)
def delete_testcase(
    problem_id: int,
    revision_id: int,
    testcase_id: int,
    current_user: User = Depends(require_capability("problem:edit")),
    session: Session = Depends(get_session),
):
    problem = _problem_or_404(session, problem_id)
    _authorize_problem_scope(session, current_user, problem, "problem:edit")
    _editable_revision_or_409(session, problem_id, revision_id)
    testcase = session.get(ProblemTestCase, testcase_id)
    if testcase is None or testcase.revision_id != revision_id:
        raise HTTPException(status_code=404, detail="Testcase not found")
    input_asset = session.get(ProblemAsset, testcase.input_asset_id)
    output_asset = session.get(ProblemAsset, testcase.output_asset_id)
    session.delete(testcase)
    session.flush()
    if input_asset is not None:
        session.delete(input_asset)
    if output_asset is not None:
        session.delete(output_asset)
    session.commit()
    return None
