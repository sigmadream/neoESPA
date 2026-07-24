import shutil
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from ...api.dependencies import get_optional_current_user, require_roles
from ...api.runtime import observability_service
from ...core.config import settings
from ...core.db import get_session
from ...models.schemas import (
    LectureMaterial,
    LectureMaterialRead,
    LectureMaterialWrite,
    MaterialComment,
    MaterialCommentCreate,
    User,
)
from ...services.user_management import ADMIN_ROLES
from ..materials.serializers import to_lecture_material_read
from ..users.serializers import is_staff


router = APIRouter()


def _get_material_attachment_root() -> Path:
    return settings.BASE_DIR / "supportFiles" / "materials"


def _get_visible_material(
    session: Session,
    material_id: int,
    current_user: User | None,
) -> LectureMaterial:
    material = session.get(LectureMaterial, material_id)
    if material is None or (not material.is_published and not is_staff(current_user)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    return material


@router.get("/materials", response_model=list[LectureMaterialRead])
def list_materials(
    current_user: User | None = Depends(get_optional_current_user),
    session: Session = Depends(get_session),
):
    materials = session.exec(select(LectureMaterial).order_by(LectureMaterial.id.desc())).all()
    if is_staff(current_user):
        return [to_lecture_material_read(material, session) for material in materials]
    return [
        to_lecture_material_read(material, session)
        for material in materials
        if material.is_published
    ]


@router.get("/materials/{material_id}", response_model=LectureMaterialRead)
def get_material(
    material_id: int,
    current_user: User | None = Depends(get_optional_current_user),
    session: Session = Depends(get_session),
):
    material = _get_visible_material(session, material_id, current_user)
    return to_lecture_material_read(material, session)


@router.get("/materials/{material_id}/attachment")
def download_material_attachment(
    material_id: int,
    current_user: User | None = Depends(get_optional_current_user),
    session: Session = Depends(get_session),
):
    material = _get_visible_material(session, material_id, current_user)
    if not material.attachment_relpath:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    attachment_root = _get_material_attachment_root().resolve()
    attachment_path = (attachment_root / material.attachment_relpath).resolve()
    if not attachment_path.is_relative_to(attachment_root) or not attachment_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    return FileResponse(
        attachment_path,
        filename=material.attachment_name or attachment_path.name,
        media_type="application/octet-stream",
    )


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
        content=payload.content,
        attachment_name=payload.attachment_name,
        attachment_relpath=payload.attachment_relpath,
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
    return to_lecture_material_read(material, session)


@router.post("/admin/materials/{material_id}/attachment", response_model=LectureMaterialRead)
def upload_material_attachment(
    material_id: int,
    upload: UploadFile,
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
    session: Session = Depends(get_session),
):
    material = session.get(LectureMaterial, material_id)
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")

    safe_name = Path(upload.filename or "").name.strip()
    if not safe_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attachment filename is required",
        )

    material_dir = _get_material_attachment_root() / str(material_id)
    material_dir.mkdir(parents=True, exist_ok=True)
    destination = material_dir / safe_name
    with destination.open("wb") as target:
        shutil.copyfileobj(upload.file, target)

    material.attachment_name = safe_name
    material.attachment_relpath = f"{material_id}/{safe_name}"
    material.updated_at = datetime.now(UTC)
    session.add(material)
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="upload_material_attachment",
        target_type="lecture_material",
        payload={"material_id": material_id, "attachment_name": safe_name},
    )
    session.commit()
    session.refresh(material)
    return to_lecture_material_read(material, session)


@router.patch("/admin/materials/{material_id}", response_model=LectureMaterialRead)
def update_material(
    material_id: int,
    payload: LectureMaterialWrite,
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
    session: Session = Depends(get_session),
):
    material = session.get(LectureMaterial, material_id)
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")

    material.title = payload.title
    material.description = payload.description
    material.url = payload.url
    material.content = payload.content
    material.attachment_name = payload.attachment_name
    material.attachment_relpath = payload.attachment_relpath
    material.is_published = payload.is_published
    material.updated_at = datetime.now(UTC)

    session.add(material)
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="update_material",
        target_type="lecture_material",
        payload=payload.model_dump(),
    )
    session.commit()
    session.refresh(material)
    return to_lecture_material_read(material, session)


@router.delete("/admin/materials/{material_id}")
def delete_material(
    material_id: int,
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
    session: Session = Depends(get_session),
):
    material = session.get(LectureMaterial, material_id)
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")

    session.delete(material)
    observability_service.record_audit(
        session,
        actor_user_id=current_user.id,
        action_type="delete_material",
        target_type="lecture_material",
        payload={"material_id": material_id},
    )
    session.commit()

    material_dir = _get_material_attachment_root() / str(material_id)
    if material_dir.is_dir():
        shutil.rmtree(material_dir, ignore_errors=True)

    return {"message": "Material deleted successfully"}


@router.post("/materials/{material_id}/comments", response_model=LectureMaterialRead)
def add_material_comment(
    material_id: int,
    payload: MaterialCommentCreate,
    current_user: User = Depends(require_roles("student", "ta", "instructor", "admin")),
    session: Session = Depends(get_session),
):
    material = _get_visible_material(session, material_id, current_user)

    content = payload.content.strip()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comment content cannot be empty",
        )

    comment = MaterialComment(
        material_id=material_id,
        user_id=current_user.id,
        content=content,
        created_at=datetime.now(UTC),
    )
    session.add(comment)
    session.commit()
    return to_lecture_material_read(material, session)
