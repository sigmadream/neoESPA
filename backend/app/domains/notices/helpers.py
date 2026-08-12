from datetime import UTC, datetime

from fastapi import HTTPException, status

from ...models.schemas import Notice, NoticeRead
from ..shared.schedules import parse_datetime


def to_notice_read(notice: Notice) -> NoticeRead:
    return NoticeRead(
        num=notice.num or 0,
        title=notice.title,
        author=notice.author,
        content=notice.content,
        date=notice.date,
        is_pinned=notice.is_pinned,
        is_published=notice.is_published,
    )


def normalize_notice_date(raw_value: str | None) -> str:
    if raw_value is None or not raw_value.strip():
        return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")

    parsed = parse_datetime(raw_value.strip())
    if parsed is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Notice publish date must be a valid datetime",
        )
    return parsed.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")


def notice_sort_key(notice: Notice) -> tuple[bool, datetime]:
    publish_at = parse_datetime(notice.date) or datetime.min.replace(tzinfo=UTC)
    return notice.is_pinned, publish_at


def notice_is_publicly_visible(notice: Notice) -> bool:
    if not notice.is_published:
        return False

    publish_at = parse_datetime(notice.date)
    if publish_at is None:
        return True
    return publish_at <= datetime.now(UTC)
