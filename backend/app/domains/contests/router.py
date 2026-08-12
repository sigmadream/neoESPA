import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from ...api.dependencies import get_current_active_user, require_capability
from ...api.runtime import observability_service
from ...core.db import get_session
from ...models.schemas import (
    Contest,
    ContestCreate,
    ContestProblem,
    ContestProblemCreate,
    ContestProblemRead,
    ContestRead,
    ContestParticipation,
    ContestParticipationCreate,
    ContestParticipationRead,
    Clarification,
    ClarificationCreate,
    ClarificationAnswer,
    ClarificationRead,
    ContestAnnouncement,
    ContestAnnouncementCreate,
    ContestAnnouncementRead,
    ContestResultEvent,
    ContestResultEventCreate,
    ContestScoreboardRow,
    Submission,
    GradingRun,
    ContestOperationApproval,
    ContestOperationApprovalCreate,
    ContestOperationApprovalRead,
    ProblemRevision,
    User,
)


router = APIRouter(prefix="/admin/contests")
public_router = APIRouter(prefix="/contests")


def _contest_read(contest: Contest) -> ContestRead:
    data = contest.model_dump()
    data["allowed_organizations"] = json.loads(contest.allowed_organizations_json)
    return ContestRead.model_validate(data)


def _contest_or_404(session: Session, contest_id: int) -> Contest:
    contest = session.get(Contest, contest_id)
    if contest is None:
        raise HTTPException(status_code=404, detail="Contest not found")
    return contest


def _participation_or_403(session: Session, contest_id: int, user_id: str) -> ContestParticipation:
    participation = session.exec(
        select(ContestParticipation).where(
            ContestParticipation.contest_id == contest_id,
            ContestParticipation.user_id == user_id,
        )
    ).first()
    if participation is None:
        raise HTTPException(status_code=403, detail="Contest participation is required")
    return participation


@router.get("", response_model=list[ContestRead])
def list_contests(
    _current_user: User = Depends(require_capability("problem:data.read")),
    session: Session = Depends(get_session),
):
    return [_contest_read(item) for item in session.exec(select(Contest).order_by(Contest.id.desc())).all()]


@router.post("", response_model=ContestRead, status_code=201)
def create_contest(
    payload: ContestCreate,
    current_user: User = Depends(require_capability("problem:publish")),
    session: Session = Depends(get_session),
):
    if payload.ends_at <= payload.starts_at:
        raise HTTPException(status_code=400, detail="Contest end must follow start")
    if payload.freeze_at and not (payload.starts_at <= payload.freeze_at <= payload.ends_at):
        raise HTTPException(status_code=400, detail="Scoreboard freeze must be inside contest window")
    if payload.scoring_format not in {"icpc", "ioi"}:
        raise HTTPException(status_code=400, detail="Unsupported contest scoring format")
    contest = Contest(
        code=payload.code.strip().lower(),
        title=payload.title.strip(),
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        freeze_at=payload.freeze_at,
        visibility=payload.visibility,
        access_code_hash=(
            hashlib.sha256(payload.access_code.encode()).hexdigest()
            if payload.access_code
            else None
        ),
        allowed_organizations_json=json.dumps(
            sorted({item.strip() for item in payload.allowed_organizations if item.strip()})
        ),
        scoring_format=payload.scoring_format,
        allow_virtual=payload.allow_virtual,
        created_by=current_user.id,
    )
    session.add(contest)
    try:
        session.flush()
        observability_service.record_audit(
            session,
            actor_user_id=current_user.id,
            action_type="create_contest",
            target_type="contest",
            target_id=str(contest.id),
            payload={"code": contest.code, "scoring_format": contest.scoring_format},
        )
        session.commit()
        session.refresh(contest)
        return _contest_read(contest)
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="Contest code already exists") from error


@router.post("/{contest_id}/problems", response_model=ContestProblemRead, status_code=201)
def attach_contest_problem(
    contest_id: int,
    payload: ContestProblemCreate,
    current_user: User = Depends(require_capability("problem:publish")),
    session: Session = Depends(get_session),
):
    contest = session.get(Contest, contest_id)
    if contest is None:
        raise HTTPException(status_code=404, detail="Contest not found")
    if contest.status != "draft":
        raise HTTPException(status_code=409, detail="Contest problems are pinned after publication")
    revision = session.get(ProblemRevision, payload.revision_id)
    if revision is None or revision.status != "published":
        raise HTTPException(status_code=409, detail="Contest requires a published problem revision")
    item = ContestProblem(contest_id=contest_id, **payload.model_dump())
    session.add(item)
    try:
        session.commit()
        session.refresh(item)
        return item
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="Contest problem position already exists") from error


@router.post("/{contest_id}/publish", response_model=ContestRead)
def publish_contest(
    contest_id: int,
    current_user: User = Depends(require_capability("problem:publish")),
    session: Session = Depends(get_session),
):
    contest = session.get(Contest, contest_id)
    if contest is None:
        raise HTTPException(status_code=404, detail="Contest not found")
    if contest.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft contests can be published")
    if session.exec(select(ContestProblem.id).where(ContestProblem.contest_id == contest_id)).first() is None:
        raise HTTPException(status_code=409, detail="Contest must contain a problem")
    contest.status = "published"
    session.add(contest)
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="publish_contest",
        target_type="contest",
        target_id=str(contest.id),
    )
    session.commit()
    session.refresh(contest)
    return _contest_read(contest)


@router.post(
    "/{contest_id}/operation-approvals",
    response_model=ContestOperationApprovalRead,
    status_code=201,
)
def approve_contest_operation(
    contest_id: int,
    payload: ContestOperationApprovalCreate,
    current_user: User = Depends(require_capability("problem:publish")),
    session: Session = Depends(get_session),
):
    contest = _contest_or_404(session, contest_id)
    if contest.status != "published":
        raise HTTPException(status_code=409, detail="Only published contests need operation approval")
    if payload.operation not in {"rejudge", "system_testing"}:
        raise HTTPException(status_code=400, detail="Unsupported contest operation")
    approval = ContestOperationApproval(
        contest_id=contest_id, operation=payload.operation,
        reason=payload.reason.strip(), approved_by=current_user.id,
    )
    session.add(approval)
    observability_service.record_audit(
        session, actor_user_id=current_user.id, action_type="approve_contest_operation",
        target_type="contest", target_id=str(contest_id), after=payload.model_dump(),
    )
    session.commit()
    session.refresh(approval)
    return approval


@router.post("/{contest_id}/system-testing", response_model=ContestRead)
def enable_contest_system_testing(
    contest_id: int,
    approval_id: int,
    current_user: User = Depends(require_capability("judge:operate")),
    session: Session = Depends(get_session),
):
    contest = _contest_or_404(session, contest_id)
    approval = session.get(ContestOperationApproval, approval_id)
    if (
        approval is None or approval.contest_id != contest_id
        or approval.operation != "system_testing" or approval.used_at is not None
    ):
        raise HTTPException(status_code=409, detail="Unused system testing approval is required")
    contest.system_testing = True
    approval.used_at = datetime.now(UTC)
    session.add(contest)
    session.add(approval)
    observability_service.record_audit(
        session, actor_user_id=current_user.id, action_type="enable_contest_system_testing",
        target_type="contest", target_id=str(contest_id),
        payload={"approval_id": approval_id, "reason": approval.reason},
    )
    session.commit()
    session.refresh(contest)
    return _contest_read(contest)


@public_router.post("/{contest_id}/participations", response_model=ContestParticipationRead, status_code=201)
def join_contest(
    contest_id: int,
    payload: ContestParticipationCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    contest = _contest_or_404(session, contest_id)
    if contest.status != "published":
        raise HTTPException(status_code=409, detail="Contest is not open for participation")
    if payload.participation_type not in {"official", "virtual"}:
        raise HTTPException(status_code=400, detail="Unsupported participation type")
    if payload.participation_type == "virtual" and not contest.allow_virtual:
        raise HTTPException(status_code=409, detail="Virtual participation is disabled")
    if contest.access_code_hash:
        supplied = hashlib.sha256((payload.access_code or "").encode()).hexdigest()
        if not hmac.compare_digest(supplied, contest.access_code_hash):
            raise HTTPException(status_code=403, detail="Contest access code is invalid")
    allowed_organizations = json.loads(contest.allowed_organizations_json)
    if allowed_organizations and current_user.organization_id not in allowed_organizations:
        raise HTTPException(status_code=403, detail="Contest is restricted to selected organizations")
    now = datetime.now(UTC)
    ends_at = contest.ends_at
    if payload.participation_type == "virtual":
        duration = contest.ends_at - contest.starts_at
        ends_at = now + duration
    participation = ContestParticipation(
        contest_id=contest_id, user_id=current_user.id,
        participation_type=payload.participation_type, started_at=now, ends_at=ends_at,
    )
    session.add(participation)
    try:
        session.commit()
        session.refresh(participation)
        return participation
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="Contest participation already exists") from error


@public_router.get("/{contest_id}/announcements", response_model=list[ContestAnnouncementRead])
def list_contest_announcements(
    contest_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    _participation_or_403(session, contest_id, current_user.id)
    return session.exec(
        select(ContestAnnouncement).where(ContestAnnouncement.contest_id == contest_id)
        .order_by(ContestAnnouncement.created_at, ContestAnnouncement.id)
    ).all()


@public_router.post("/{contest_id}/clarifications", response_model=ClarificationRead, status_code=201)
def ask_clarification(
    contest_id: int,
    payload: ClarificationCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    _participation_or_403(session, contest_id, current_user.id)
    item = Clarification(
        contest_id=contest_id, user_id=current_user.id,
        problem_id=payload.problem_id, question=payload.question.strip(),
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@public_router.get("/{contest_id}/clarifications", response_model=list[ClarificationRead])
def list_my_clarifications(
    contest_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    _participation_or_403(session, contest_id, current_user.id)
    return session.exec(
        select(Clarification).where(
            Clarification.contest_id == contest_id, Clarification.user_id == current_user.id
        ).order_by(Clarification.created_at, Clarification.id)
    ).all()


@router.post("/{contest_id}/announcements", response_model=ContestAnnouncementRead, status_code=201)
def create_contest_announcement(
    contest_id: int,
    payload: ContestAnnouncementCreate,
    current_user: User = Depends(require_capability("problem:publish")),
    session: Session = Depends(get_session),
):
    _contest_or_404(session, contest_id)
    item = ContestAnnouncement(
        contest_id=contest_id, title=payload.title.strip(),
        message=payload.message.strip(), created_by=current_user.id,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.patch("/{contest_id}/clarifications/{clarification_id}", response_model=ClarificationRead)
def answer_clarification(
    contest_id: int,
    clarification_id: int,
    payload: ClarificationAnswer,
    _current_user: User = Depends(require_capability("problem:publish")),
    session: Session = Depends(get_session),
):
    item = session.get(Clarification, clarification_id)
    if item is None or item.contest_id != contest_id:
        raise HTTPException(status_code=404, detail="Clarification not found")
    item.answer = payload.answer.strip()
    item.status = "answered"
    item.answered_at = datetime.now(UTC)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.post("/{contest_id}/result-events", status_code=201)
def append_contest_result_event(
    contest_id: int,
    payload: ContestResultEventCreate,
    _current_user: User = Depends(require_capability("judge:operate")),
    session: Session = Depends(get_session),
):
    _contest_or_404(session, contest_id)
    participation = session.get(ContestParticipation, payload.participation_id)
    contest_problem = session.get(ContestProblem, payload.contest_problem_id)
    submission = session.get(Submission, payload.submission_id)
    if participation is None or participation.contest_id != contest_id:
        raise HTTPException(status_code=400, detail="Participation does not belong to contest")
    if contest_problem is None or contest_problem.contest_id != contest_id:
        raise HTTPException(status_code=400, detail="Problem does not belong to contest")
    if submission is None or submission.user_id != participation.user_id:
        raise HTTPException(status_code=400, detail="Submission does not belong to participant")
    if payload.grading_run_id is not None:
        run = session.get(GradingRun, payload.grading_run_id)
        if run is None or run.submission_id != submission.id:
            raise HTTPException(status_code=400, detail="Grading run does not belong to submission")
    latest = session.exec(
        select(ContestResultEvent.sequence_no)
        .where(ContestResultEvent.contest_id == contest_id)
        .order_by(ContestResultEvent.sequence_no.desc())
    ).first()
    event = ContestResultEvent(
        contest_id=contest_id, sequence_no=(latest or 0) + 1,
        result_phase="system" if contest.system_testing else "live",
        **payload.model_dump(),
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


@public_router.get("/{contest_id}/scoreboard", response_model=list[ContestScoreboardRow])
def contest_scoreboard(
    contest_id: int,
    phase: Literal["current", "live", "system"] = "current",
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    contest = _contest_or_404(session, contest_id)
    _participation_or_403(session, contest_id, current_user.id)
    events = session.exec(
        select(ContestResultEvent).where(ContestResultEvent.contest_id == contest_id)
        .order_by(ContestResultEvent.sequence_no)
    ).all()
    # `live` replays the immutable pre-system-testing history. `system`
    # includes the subsequent system-test events, while `current` is an alias
    # for the latest complete history.
    if phase == "live":
        events = [event for event in events if event.result_phase == "live"]
    if contest.freeze_at and datetime.now(UTC) >= contest.freeze_at:
        events = [event for event in events if event.occurred_at <= contest.freeze_at]
    participations = {
        item.id: item for item in session.exec(
            select(ContestParticipation).where(ContestParticipation.contest_id == contest_id)
        ).all()
    }
    per_user: dict[str, dict] = {}
    for event in events:
        participation = participations.get(event.participation_id)
        if participation is None:
            continue
        state = per_user.setdefault(participation.user_id, {"scores": {}, "solved": set(), "penalty": 0})
        state["scores"][event.contest_problem_id] = max(
            event.score, state["scores"].get(event.contest_problem_id, 0)
        )
        if event.verdict == "AC":
            state["solved"].add(event.contest_problem_id)
            state["penalty"] += max(
                0, int((event.occurred_at - participation.started_at).total_seconds() // 60)
            )
    ordered = sorted(
        per_user.items(),
        key=lambda item: (-len(item[1]["solved"]), -sum(item[1]["scores"].values()), item[1]["penalty"], item[0]),
    )
    return [
        ContestScoreboardRow(
            rank=index, user_id=user_id, solved=len(state["solved"]),
            score=sum(state["scores"].values()), penalty_minutes=state["penalty"],
        )
        for index, (user_id, state) in enumerate(ordered, start=1)
    ]
