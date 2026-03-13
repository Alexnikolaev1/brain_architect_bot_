"""
Backward-compatible facade for game modules.

Новый код должен импортировать из:
- app.games.factory
- app.games.anti_realtor
- app.games.blind_typing
- app.games.types
"""

from app.domain.games import ARCHETYPE_MAP, GAME_NAMES, GameId
from app.games.anti_realtor import generate_anti_realtor_question
from app.games.blind_typing import check_blind_typing_answer
from app.games.factory import generate_game, get_game_generators
from app.games.types import GameQuestion

__all__ = [
    "ARCHETYPE_MAP",
    "GAME_NAMES",
    "GameId",
    "GameQuestion",
    "generate_game",
    "get_game_generators",
    "check_blind_typing_answer",
    "generate_anti_realtor_question",
]
