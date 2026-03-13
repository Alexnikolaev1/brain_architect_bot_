from __future__ import annotations

from datetime import datetime, timedelta, timezone

TRIAL_DAYS = 7


def _to_utc_datetime(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def is_trial_active(user: dict | None) -> bool:
    if not user:
        return False
    if user.get("plan") != "trial":
        return False

    trial_start = _to_utc_datetime(user.get("trial_start"))
    if trial_start is None:
        return False

    return datetime.now(timezone.utc) < trial_start + timedelta(days=TRIAL_DAYS)


def is_pro_active(user: dict | None) -> bool:
    if not user:
        return False
    if user.get("plan") not in {"pro", "vip"}:
        return False
    if user.get("plan") == "vip":
        return True

    expires_at = _to_utc_datetime(user.get("sub_expires"))
    return bool(expires_at and expires_at > datetime.now(timezone.utc))


def effective_plan(user: dict | None) -> str:
    if not user:
        return "free"
    if user.get("plan") == "vip":
        return "vip"
    if is_pro_active(user):
        return "pro"
    if is_trial_active(user):
        return "trial"
    return "free"
