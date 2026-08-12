import json

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ...api.dependencies import get_current_active_user
from ...core.db import get_session
from ...models.schemas import (
    AnalyticsConsent,
    AnalyticsConsentCreate,
    AnalyticsConsentRead,
    User,
)

router = APIRouter()


def _read(consent: AnalyticsConsent) -> AnalyticsConsentRead:
    return AnalyticsConsentRead(
        id=consent.id or 0,
        user_id=consent.user_id,
        granted=consent.granted,
        purpose=consent.purpose,
        policy_version=consent.policy_version,
        scopes=json.loads(consent.scope_json),
        created_at=consent.created_at,
    )


@router.get("/analytics-consents", response_model=list[AnalyticsConsentRead])
def list_my_consents(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    rows = session.exec(
        select(AnalyticsConsent)
        .where(AnalyticsConsent.user_id == current_user.id)
        .order_by(
            AnalyticsConsent.created_at.desc(), AnalyticsConsent.id.desc()
        )
    ).all()
    return [_read(row) for row in rows]


@router.post(
    "/analytics-consents", response_model=AnalyticsConsentRead, status_code=201
)
def record_my_consent(
    payload: AnalyticsConsentCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    scopes = sorted(
        {scope.strip() for scope in payload.scopes if scope.strip()}
    )
    row = AnalyticsConsent(
        user_id=current_user.id,
        granted=payload.granted,
        purpose=payload.purpose.strip(),
        policy_version=payload.policy_version.strip(),
        scope_json=json.dumps(scopes, ensure_ascii=False),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return _read(row)
