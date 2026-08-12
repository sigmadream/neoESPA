from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from ...api.dependencies import require_capability
from ...api.runtime import observability_service, plagiarism_service
from ...core.db import get_session
from ...models.schemas import Homework, PlagiarismPairRead, PlagiarismRunRead, User


router = APIRouter()


@router.post("/admin/homeworks/{homework_num}/plagiarism/run", response_model=PlagiarismRunRead)
def run_plagiarism_scan(
    homework_num: int,
    current_user: User = Depends(require_capability("plagiarism:operate")),
    session: Session = Depends(get_session),
):
    homework = session.get(Homework, homework_num)
    if homework is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Homework not found")
    run = plagiarism_service.run_for_homework(
        session,
        homework_num=homework_num,
        created_by=current_user.id,
    )
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="run_plagiarism_scan",
        target_type="homework",
        target_id=str(homework_num),
        payload={"run_id": run.id},
    )
    session.commit()
    return plagiarism_service.to_run_read(run)


@router.get("/admin/plagiarism/runs", response_model=list[PlagiarismRunRead])
def list_plagiarism_runs(
    _: User = Depends(require_capability("plagiarism:operate")),
    session: Session = Depends(get_session),
):
    return plagiarism_service.list_runs(session)


@router.get("/admin/plagiarism/pairs", response_model=list[PlagiarismPairRead])
def list_plagiarism_pairs(
    homework_num: int | None = Query(default=None),
    _: User = Depends(require_capability("plagiarism:operate")),
    session: Session = Depends(get_session),
):
    return plagiarism_service.list_pairs(session, homework_num=homework_num)


@router.get("/admin/plagiarism/pairs/{pair_id}", response_model=PlagiarismPairRead)
def get_plagiarism_pair(
    pair_id: int,
    _: User = Depends(require_capability("plagiarism:operate")),
    session: Session = Depends(get_session),
):
    pair = plagiarism_service.get_pair(session, pair_id)
    if pair is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plagiarism pair not found")
    return pair
