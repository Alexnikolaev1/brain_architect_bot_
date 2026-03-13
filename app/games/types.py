from __future__ import annotations

from dataclasses import dataclass

from telegram import InlineKeyboardMarkup


@dataclass
class GameQuestion:
    text: str
    keyboard: InlineKeyboardMarkup
    session_data: dict
    hint: str = ""
