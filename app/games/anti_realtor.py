from __future__ import annotations

import random
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.games.types import GameQuestion

_ROOM_CONFIGS = [
    {
        "objects": {
            "Диван": "у левой стены",
            "Картина": "над диваном",
            "Торшер": "справа от дивана",
            "Журнальный столик": "перед диваном",
            "Полка": "у правой стены",
        },
        "changes": [
            ("Картина", "над журнальным столиком", "Картину сняли со стены над диваном и повесили над столиком."),
            ("Торшер", "слева от дивана", "Торшер переставили на противоположную сторону дивана."),
            ("Полка", "у левой стены рядом с диваном", "Полку перенесли на стену рядом с диваном."),
        ],
    },
    {
        "objects": {
            "Кровать": "у дальней стены",
            "Тумбочка": "справа от кровати",
            "Зеркало": "у входной двери",
            "Шкаф": "у левой стены",
            "Ковёр": "перед кроватью",
        },
        "changes": [
            ("Тумбочка", "слева от кровати", "Тумбочку переставили на другую сторону кровати."),
            ("Зеркало", "над кроватью", "Зеркало сняли от двери и повесили над изголовьем."),
            ("Ковёр", "у входной двери", "Ковёр переложили от кровати к двери."),
        ],
    },
    {
        "objects": {
            "Холодильник": "в левом углу",
            "Стол": "у окна",
            "Стул": "перед столом",
            "Микроволновка": "на холодильнике",
            "Мусорное ведро": "у правой стены",
        },
        "changes": [
            ("Стул", "у правой стены", "Стул убрали от стола и придвинули к правой стене."),
            ("Микроволновка", "на столе", "Микроволновку перенесли с холодильника на стол у окна."),
            ("Мусорное ведро", "под столом", "Ведро переставили к столу и задвинули под него."),
        ],
    },
    {
        "objects": {
            "Письменный стол": "у окна",
            "Стул": "перед столом",
            "Книжный шкаф": "у правой стены",
            "Настольная лампа": "на столе слева",
            "Растение": "в углу у окна",
        },
        "changes": [
            ("Настольная лампа", "на столе справа", "Лампу переставили с левой стороны стола на правую."),
            ("Растение", "у книжного шкафа", "Растение перенесли от окна к книжному шкафу."),
            ("Стул", "у левой стены", "Стул отодвинули от стола и поставили к левой стене."),
        ],
    },
    {
        "objects": {
            "Обеденный стол": "в центре кухни",
            "Четыре стула": "вокруг стола",
            "Плита": "у дальней стены",
            "Раковина": "под окном",
            "Кухонный шкаф": "у правой стены",
        },
        "changes": [
            ("Обеденный стол", "ближе к окну", "Стол подвинули от центра комнаты ближе к окну."),
            ("Один из стульев", "в углу", "Один стул убрали от стола и поставили в угол."),
        ],
    },
]


def generate_anti_realtor(difficulty: int = 1) -> GameQuestion:
    config = random.choice(_ROOM_CONFIGS)
    changed_obj, new_pos, change_desc = random.choice(config["changes"])
    room_lines = "\n".join(f"  • *{obj}* — {pos}" for obj, pos in config["objects"].items())
    memorize_time = max(10, 30 - difficulty * 2)

    text = (
        f"🏠 *АНТИ-РИЭЛТОР* — уровень {difficulty}\n"
        f"{'─' * 30}\n\n"
        f"Запомни расстановку мебели:\n\n"
        f"{room_lines}\n\n"
        f"⏱ У тебя *{memorize_time} секунд*. Потом я что-то изменю...\n\n"
        f"_Нажми «Готов» когда запомнишь_"
    )

    buttons = [
        [InlineKeyboardButton("✅ Готов! Показывай изменение", callback_data="game:anti_realtor:show_change:0")],
        [InlineKeyboardButton("🏠 Меню", callback_data="menu:main")],
    ]

    return GameQuestion(
        text=text,
        keyboard=InlineKeyboardMarkup(buttons),
        session_data={
            "game_id": "anti_realtor",
            "phase": "memorize",
            "room_config": config["objects"],
            "changed_obj": changed_obj,
            "new_position": new_pos,
            "change_desc": change_desc,
            "all_objects": list(config["objects"].keys()),
            "started_at": time.time(),
            "difficulty": difficulty,
        },
    )


def generate_anti_realtor_question(session: dict) -> GameQuestion:
    changed_obj = session["changed_obj"]
    new_pos = session["new_position"]
    all_objs = session["all_objects"]

    new_room = dict(session["room_config"])
    new_room[changed_obj] = new_pos
    room_lines = "\n".join(f"  • *{obj}* — {pos}" for obj, pos in new_room.items())

    wrong_objs = [o for o in all_objs if o != changed_obj]
    random.shuffle(wrong_objs)
    options = [changed_obj] + wrong_objs[:3]
    random.shuffle(options)

    buttons = [
        [
            InlineKeyboardButton(
                opt,
                callback_data=f"game:anti_realtor:{'correct' if opt == changed_obj else 'wrong'}:{opt}",
            )
        ]
        for opt in options
    ] + [[InlineKeyboardButton("🏠 Меню", callback_data="menu:main")]]

    text = (
        f"🏠 *АНТИ-РИЭЛТОР* — что изменилось?\n"
        f"{'─' * 30}\n\n"
        f"Новая расстановка:\n\n"
        f"{room_lines}\n\n"
        f"❓ *Какой предмет переставили?*"
    )

    return GameQuestion(text=text, keyboard=InlineKeyboardMarkup(buttons), session_data=session)
