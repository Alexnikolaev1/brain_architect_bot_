from __future__ import annotations


def compute_score(is_correct: bool, elapsed_ms: int, difficulty: int) -> int:
    if not is_correct:
        return 0

    base = 100 * difficulty
    # Бонус за скорость: максимум удваивает награду.
    speed_bonus = max(0.0, 1.0 - elapsed_ms / 30_000)
    return int(base * (1 + speed_bonus))
