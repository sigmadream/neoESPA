from ...models.schemas import LectureMaterial, LectureMaterialRead


def to_lecture_material_read(material: LectureMaterial) -> LectureMaterialRead:
    return LectureMaterialRead(
        id=material.id or 0,
        title=material.title,
        description=material.description,
        url=material.url,
        is_published=material.is_published,
        created_by=material.created_by,
        created_at=material.created_at,
        updated_at=material.updated_at,
    )
