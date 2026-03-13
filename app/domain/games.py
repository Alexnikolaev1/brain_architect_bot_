from __future__ import annotations

from typing import Literal

GameId = Literal[
    "double_strike",
    "sensation_maze",
    "anti_realtor",
    "stop_signal",
    "blind_typing",
]

GAME_NAMES: dict[GameId, str] = {
    "double_strike": "⚡ Двойной удар",
    "sensation_maze": "🖐️ Лабиринт ощущений",
    "anti_realtor": "🏠 Анти-риэлтор",
    "stop_signal": "🛑 Стоп-кран",
    "blind_typing": "⌨️ Слепой десятипальцевый",
}

ARCHETYPE_MAP: dict[GameId, str] = {
    "double_strike": "knight",
    "sensation_maze": "scout",
    "anti_realtor": "mage",
    "stop_signal": "oracle",
    "blind_typing": "knight",
}
