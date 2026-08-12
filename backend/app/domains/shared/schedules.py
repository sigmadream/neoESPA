from datetime import UTC, datetime, timedelta


def parse_datetime(raw_value: str | None) -> datetime | None:
    if not raw_value:
        return None

    normalized = raw_value.replace(" ", "T")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def compute_schedule_window(
    starttime: str | None,
    deadline: str | None,
) -> tuple[str, bool]:
    now = datetime.now(UTC)
    start_at = parse_datetime(starttime)
    deadline_at = parse_datetime(deadline)

    if start_at and now < start_at:
        return "upcoming", False
    if deadline_at and now > deadline_at:
        return "closed", False
    if deadline_at and deadline_at - now <= timedelta(hours=24):
        return "closing_soon", True
    return "open", True
