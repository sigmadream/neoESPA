from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ...api.dependencies import get_optional_current_user, require_roles
from ...api.runtime import observability_service
from ...core.db import get_session
from ...models.schemas import LectureMaterial, LectureMaterialRead, LectureMaterialWrite, User
from ...services.user_management import ADMIN_ROLES
from ..materials.serializers import to_lecture_material_read
from ..users.serializers import is_staff


router = APIRouter()


@router.get("/materials", response_model=list[LectureMaterialRead])
def list_materials(
    current_user: User | None = Depends(get_optional_current_user),
    session: Session = Depends(get_session),
):
    materials = session.exec(select(LectureMaterial).order_by(LectureMaterial.id.desc())).all()
    if is_staff(current_user):
        return [to_lecture_material_read(material) for material in materials]
    return [
        to_lecture_material_read(material)
        for material in materials
        if material.is_published
    ]


@router.post("/admin/materials", response_model=LectureMaterialRead)
def create_material(
    payload: LectureMaterialWrite,
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
    session: Session = Depends(get_session),
):
    material = LectureMaterial(
        title=payload.title,
        description=payload.description,
        url=payload.url,
        is_published=payload.is_published,
        created_by=current_user.id,
        updated_at=datetime.now(UTC),
    )
    session.add(material)
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="create_material",
        target_type="lecture_material",
        payload=payload.model_dump(),
    )
    session.commit()
    session.refresh(material)
    return to_lecture_material_read(material)
