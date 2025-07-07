from datetime import UTC, datetime, timezone


def convert_time(
    time_to_convert: datetime,
    to_timezone: timezone = UTC,
    is_offset_naive: bool = True,
) -> datetime:
    """Convert provided time to desired timezone."""
    if not time_to_convert.tzinfo:
        time_to_convert = time_to_convert.replace(tzinfo=UTC)
    time = time_to_convert.astimezone(to_timezone)
    return time.replace(tzinfo=None) if is_offset_naive else time


def utcnow(is_timezone: bool = False):
    """Get current datetime object."""
    now = datetime.now().astimezone(UTC)
    return now if is_timezone else now.replace(tzinfo=None)


def custom_urljoin(base_url: str, path: str) -> str:
    """Join two url parts."""
    return '{}/{}'.format(base_url.rstrip('/'), path.lstrip('/'))
