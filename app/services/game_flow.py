from __future__ import annotations

import time
from dataclasses import dataclass

from app.services.scoring import compute_score


@dataclass(frozen=True)
class RoundResult:
    score: int
    elapsed_ms: int
    difficulty: int


def calculate_round_result(*, is_correct: bool, started_at: float | int | None, difficulty: int | None) -> RoundResult:
    now = time.time()
    safe_started_at = float(started_at) if started_at is not None else now
    elapsed_ms = int((now - safe_started_at) * 1000)
    safe_difficulty = int(difficulty) if difficulty is not None else 1
    score = compute_score(is_correct, elapsed_ms, safe_difficulty)
    return RoundResult(score=score, elapsed_ms=elapsed_ms, difficulty=safe_difficulty)


async def finalize_round(
    *,
    user_id: int,
    game_id: str,
    username: str,
    is_correct: bool,
    started_at: float | int | None,
    difficulty: int | None,
) -> RoundResult:
    from app.repositories.game_repository import clear_session, persist_round_result

    result = calculate_round_result(
        is_correct=is_correct,
        started_at=started_at,
        difficulty=difficulty,
    )
    await persist_round_result(
        user_id=user_id,
        game_id=game_id,
        score=result.score,
        time_ms=result.elapsed_ms,
        correct=is_correct,
        difficulty=result.difficulty,
        username=username,
    )
    await clear_session(user_id)
    return result
