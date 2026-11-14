from datetime import datetime, timezone

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

def expired(value: datetime | None, now: datetime | None = None) -> bool:
    if value is None:
        return False
    return as_utc(value) <= as_utc(now or utcnow())
