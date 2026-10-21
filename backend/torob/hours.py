from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

TEHRAN = ZoneInfo("Asia/Tehran")
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _shifts(day):
    result = []
    if not isinstance(day, dict) or day.get("status") != "declared":
        return result
    for shift in day.get("shifts") or []:
        try:
            start, end = time.fromisoformat(shift["start_time"]), time.fromisoformat(shift["end_time"])
            if start != end:
                result.append((start, end))
        except (ValueError, KeyError, TypeError):
            continue
    return result


def hours_state(weekly_hours: dict | None, now: datetime) -> str:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Visit time must include its timezone")
    if not isinstance(weekly_hours, dict):
        return "unknown"
    local = now.astimezone(TEHRAN)
    clock = local.time()
    previous = weekly_hours.get(DAYS[(local - timedelta(days=1)).weekday()])
    if any(end < start and clock < end for start, end in _shifts(previous)):
        return "open"
    day = weekly_hours.get(DAYS[local.weekday()])
    if not isinstance(day, dict):
        return "unknown"
    if day.get("status") == "closed":
        return "closed"
    shifts = _shifts(day)
    if not shifts:
        return "unknown"
    for start, end in shifts:
        if (start < end and start <= clock < end) or (end < start and clock >= start):
            return "open"
    return "closed"
