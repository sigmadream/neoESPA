from sqlmodel import Session, select
from ...models.schemas import (
    LectureMaterial,
    LectureMaterialRead,
    MaterialComment,
    MaterialCommentRead,
    User,
)


def to_lecture_material_read(
    material: LectureMaterial, session: Session | None = None
) -> LectureMaterialRead:
    comments_read: list[MaterialCommentRead] = []
    if session and material.id:
        raw_comments = session.exec(
            select(MaterialComment)
            .where(MaterialComment.material_id == material.id)
            .order_by(MaterialComment.created_at.asc())
        ).all()
        for comment in raw_comments:
            user = session.get(User, comment.user_id)
            comments_read.append(
                MaterialCommentRead(
                    id=comment.id or 0,
                    material_id=comment.material_id,
                    user_id=comment.user_id,
                    user_name=user.name if user else comment.user_id,
                    content=comment.content,
                    created_at=comment.created_at,
                )
            )

    return LectureMaterialRead(
        id=material.id or 0,
        title=material.title,
        description=material.description,
        url=material.url,
        content=material.content,
        attachment_name=material.attachment_name,
        attachment_relpath=material.attachment_relpath,
        is_published=material.is_published,
        created_by=material.created_by,
        comments=comments_read,
        created_at=material.created_at,
        updated_at=material.updated_at,
    )
