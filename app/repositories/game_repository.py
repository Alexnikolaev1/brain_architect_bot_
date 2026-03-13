from __future__ import annotations

from app.models.db import (
    delete_session,
    save_game_stat,
    set_session,
    update_leaderboard,
)


async def store_session(user_id: int, session_data: dict) -> None:
    await set_session(user_id, session_data)


async def clear_session(user_id: int) -> None:
    await delete_session(user_id)


async def persist_round_result(
    *,
    user_id: int,
    game_id: str,
    score: int,
    time_ms: int,
    correct: bool,
    difficulty: int,
    username: str,
) -> None:
    await save_game_stat(
        user_id=user_id,
        game_id=game_id,
        score=score,
        time_ms=time_ms,
        correct=correct,
        difficulty=difficulty,
    )
    await update_leaderboard(user_id, username or str(user_id), score)
