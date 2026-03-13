from __future__ import annotations

from dataclasses import dataclass

from app.domain.games import GameId


@dataclass(frozen=True)
class GameCallback:
    game_id: GameId
    action: str
    value: str


@dataclass(frozen=True)
class MenuCallback:
    action: str


@dataclass(frozen=True)
class SubscriptionCallback:
    action: str
    plan_type: str = ""
    stars: int = 0


def parse_game_callback(data: str) -> GameCallback | None:
    parts = data.split(":")
    if len(parts) != 4 or parts[0] != "game":
        return None

    game_id, action, value = parts[1], parts[2], parts[3]
    if game_id not in {"double_strike", "sensation_maze", "anti_realtor", "stop_signal", "blind_typing"}:
        return None

    return GameCallback(game_id=game_id, action=action, value=value)  # type: ignore[arg-type]


def parse_menu_callback(data: str) -> MenuCallback | None:
    parts = data.split(":")
    if len(parts) != 2 or parts[0] != "menu":
        return None
    return MenuCallback(action=parts[1])


def parse_subscription_callback(data: str) -> SubscriptionCallback | None:
    parts = data.split(":")
    if len(parts) < 2 or parts[0] != "sub":
        return None

    action = parts[1]
    if action == "buy" and len(parts) == 4:
        try:
            return SubscriptionCallback(
                action=action,
                plan_type=parts[2],
                stars=int(parts[3]),
            )
        except ValueError:
            return None

    return SubscriptionCallback(action=action)
