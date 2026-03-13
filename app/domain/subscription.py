from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PlanType = Literal["month", "half", "year"]


@dataclass(frozen=True)
class PlanConfig:
    label: str
    days: int
    stars: int


PLAN_CONFIGS: dict[PlanType, PlanConfig] = {
    "month": PlanConfig(label="1 месяц", days=30, stars=299),
    "half": PlanConfig(label="6 месяцев", days=180, stars=1199),
    "year": PlanConfig(label="1 год", days=365, stars=1999),
}


def is_valid_plan(plan_type: str) -> bool:
    return plan_type in PLAN_CONFIGS


def parse_subscription_payload(payload: str) -> tuple[PlanType, int]:
    """Parse payload вида sub:{plan_type}:{user_id}."""
    parts = payload.split(":")
    if len(parts) != 3 or parts[0] != "sub":
        raise ValueError(f"Invalid payload format: {payload}")

    plan_type, user_id_str = parts[1], parts[2]
    if not is_valid_plan(plan_type):
        raise ValueError(f"Invalid plan type: {plan_type}")

    return plan_type, int(user_id_str)
