from __future__ import annotations

from app.domain.games import GameId
from app.games.anti_realtor import generate_anti_realtor
from app.games.blind_typing import generate_blind_typing
from app.games.double_strike import generate_double_strike
from app.games.sensation_maze import generate_sensation_maze
from app.games.stop_signal import generate_stop_signal
from app.games.types import GameQuestion


def get_game_generators():
    return {
        "double_strike": generate_double_strike,
        "sensation_maze": generate_sensation_maze,
        "anti_realtor": generate_anti_realtor,
        "stop_signal": generate_stop_signal,
        "blind_typing": generate_blind_typing,
    }


def generate_game(game_id: GameId, difficulty: int = 1) -> GameQuestion:
    generators = get_game_generators()
    if game_id not in generators:
        raise ValueError(f"Unknown game: {game_id}")
    return generators[game_id](difficulty)
