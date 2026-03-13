from __future__ import annotations

import random
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.games.types import GameQuestion

_MOTOR_RULES = [
    ("👈 Нажимай ТОЛЬКО левым большим пальцем!", "left_thumb"),
    ("👉 Нажимай ТОЛЬКО правым мизинцем!", "right_pinky"),
    ("👏 Сначала хлопни в ладоши — потом жми!", "clap_first"),
    ("🦶 Топни ногой перед нажатием!", "stomp_first"),
    ("🤜 Сожми кулак и разожми — потом жми!", "fist_first"),
    ("👀 Закрой глаза на секунду, открой — и сразу жми!", "eyes_blink"),
    ("🙃 Поверни телефон боком — и только потом жми!", "rotate_phone"),
]

_COLORS = ["🔴", "🟢", "🔵", "🟡", "🟠", "🟣"]


def _make_math_question(difficulty: int) -> tuple[str, int]:
    if difficulty <= 3:
        a, b = random.randint(1, 9), random.randint(1, 9)
        op = random.choice(["+", "-"])
    elif difficulty <= 6:
        a, b = random.randint(10, 50), random.randint(1, 20)
        op = random.choice(["+", "-", "*"])
    else:
        a, b = random.randint(10, 30), random.randint(2, 9)
        op = random.choice(["*", "-", "+"])

    if op == "+":
        return f"{a} + {b}", a + b
    if op == "-":
        if a < b:
            a, b = b, a
        return f"{a} − {b}", a - b
    return f"{a} × {b}", a * b


def generate_double_strike(difficulty: int = 1) -> GameQuestion:
    expr, correct = _make_math_question(difficulty)

    wrong_pool = set()
    while len(wrong_pool) < 3:
        delta = random.choice([-3, -2, -1, 1, 2, 3])
        candidate = correct + delta
        if candidate != correct and candidate > 0:
            wrong_pool.add(candidate)

    answers = [correct] + list(wrong_pool)
    random.shuffle(answers)

    rule_text, rule_id = random.choice(_MOTOR_RULES)
    colors = random.sample(_COLORS, 4)

    buttons = [
        [
            InlineKeyboardButton(
                f"{colors[i]} {answers[i]}",
                callback_data=f"game:double_strike:{'correct' if answers[i] == correct else 'wrong'}:{answers[i]}",
            )
            for i in range(2)
        ],
        [
            InlineKeyboardButton(
                f"{colors[i + 2]} {answers[i + 2]}",
                callback_data=f"game:double_strike:{'correct' if answers[i + 2] == correct else 'wrong'}:{answers[i + 2]}",
            )
            for i in range(2)
        ],
        [InlineKeyboardButton("🏠 Меню", callback_data="menu:main")],
    ]

    text = (
        f"⚡ *ДВОЙНОЙ УДАР* — уровень {difficulty}\n"
        f"{'─' * 30}\n\n"
        f"Реши пример:\n\n"
        f"```\n   {expr} = ?\n```\n\n"
        f"🎯 *Правило раунда:*\n{rule_text}\n\n"
        f"_Цвета кнопок — это только обёртка. Думай быстро!_"
    )

    return GameQuestion(
        text=text,
        keyboard=InlineKeyboardMarkup(buttons),
        session_data={
            "game_id": "double_strike",
            "correct_answer": correct,
            "motor_rule": rule_id,
            "expr": expr,
            "started_at": time.time(),
            "difficulty": difficulty,
        },
        hint=f"Правильный ответ: {correct}",
    )
