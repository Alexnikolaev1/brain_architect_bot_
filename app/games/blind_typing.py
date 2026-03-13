from __future__ import annotations

import random
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.games.types import GameQuestion

_WORD_POOLS = {
    "easy": [
        "кот",
        "дом",
        "лес",
        "сон",
        "мир",
        "свет",
        "вода",
        "огонь",
        "земля",
        "небо",
        "книга",
        "стол",
        "окно",
        "дверь",
        "рука",
        "слово",
        "путь",
        "жизнь",
        "время",
        "день",
        "мозг",
        "игра",
        "мысль",
        "точка",
        "шаг",
    ],
    "medium": [
        "библиотека",
        "программа",
        "алгоритм",
        "нейропластичность",
        "концентрация",
        "воображение",
        "архитектура",
        "философия",
        "математика",
        "физиология",
        "синхронизация",
        "ассоциация",
        "интуиция",
        "парадокс",
        "метафора",
        "внимательность",
        "саморегуляция",
        "переключение",
    ],
    "hard": [
        "экзистенциализм",
        "феноменология",
        "нейробиология",
        "трансформация",
        "психофизиология",
        "эпистемология",
        "интроспекция",
        "ретроспектива",
        "метакогниция",
        "нейровизуализация",
        "нейромодуляция",
        "консолидация",
    ],
}


def _pick_words(difficulty: int) -> list[str]:
    count = min(3 + difficulty // 3, 7)
    if difficulty <= 3:
        pool = _WORD_POOLS["easy"]
    elif difficulty <= 6:
        pool = _WORD_POOLS["easy"] + _WORD_POOLS["medium"]
    else:
        pool = _WORD_POOLS["medium"] + _WORD_POOLS["hard"]
    return random.sample(pool, min(count, len(pool)))


def generate_blind_typing(difficulty: int = 1) -> GameQuestion:
    words = _pick_words(difficulty)
    memorize_time = max(5, 20 - difficulty)

    text = (
        f"⌨️ *СЛЕПОЙ ДЕСЯТИПАЛЬЦЕВЫЙ* — уровень {difficulty}\n"
        f"{'─' * 30}\n\n"
        f"Запомни эти слова:\n\n"
        + "\n".join(f"  {i + 1}. **{w}**" for i, w in enumerate(words))
        + f"\n\n⏱ У тебя *{memorize_time} секунд*.\n\n"
        f"Потом напечатай их *в обратном порядке* через пробел.\n"
        f"_Попробуй не смотреть на экран!_"
    )

    buttons = [
        [InlineKeyboardButton("✅ Запомнил! Начинаем", callback_data="game:blind_typing:start:0")],
        [InlineKeyboardButton("🏠 Меню", callback_data="menu:main")],
    ]

    return GameQuestion(
        text=text,
        keyboard=InlineKeyboardMarkup(buttons),
        session_data={
            "game_id": "blind_typing",
            "phase": "memorize",
            "words": words,
            "answer": " ".join(reversed(words)),
            "started_at": time.time(),
            "difficulty": difficulty,
        },
    )


def check_blind_typing_answer(user_input: str, session: dict) -> tuple[bool, str]:
    expected = session["answer"].lower().strip()
    given = user_input.lower().strip()

    if given == expected:
        return True, "💯 Идеально!"

    exp_words = expected.split()
    given_words = given.split()
    if len(exp_words) != len(given_words):
        return False, f"Нужно было {len(exp_words)} слов, написано {len(given_words)}."

    errors = sum(1 for e, g in zip(exp_words, given_words) if e != g)
    max_errors = max(0, session["difficulty"] // 3)
    if errors <= max_errors:
        return True, f"✅ Почти идеально! Опечаток: {errors}"

    return False, f"❌ Ошибок: {errors}. Правильно: {' '.join(reversed(session['words']))}"
