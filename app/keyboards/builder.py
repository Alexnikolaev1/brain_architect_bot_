"""
🧠 Клавиатуры бота

Главное меню, профиль, подписка, турнир и т.д.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.domain.games import GAME_NAMES
from app.domain.subscription import PLAN_CONFIGS


def main_menu_keyboard(plan: str = "free") -> InlineKeyboardMarkup:
    """Главное меню с 5 играми."""
    game_buttons = [
        [InlineKeyboardButton(name, callback_data=f"game:{gid}:start:0")]
        for gid, name in GAME_NAMES.items()
    ]

    bottom = [
        [
            InlineKeyboardButton("📊 Статистика", callback_data="menu:stats"),
            InlineKeyboardButton("🏆 Турнир", callback_data="menu:tournament"),
        ],
        [
            InlineKeyboardButton("👤 Мой профиль", callback_data="menu:profile"),
            InlineKeyboardButton("💎 Подписка", callback_data="sub:plans"),
        ],
    ]

    if plan in ("pro", "vip"):
        bottom.insert(
            0,
            [InlineKeyboardButton("🌪️ Режим ТУРБО", callback_data="menu:turbo")],
        )

    return InlineKeyboardMarkup(game_buttons + bottom)


def subscription_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("⭐ 1 месяц — 299 Stars", callback_data=f"sub:buy:month:{PLAN_CONFIGS['month'].stars}")],
            [InlineKeyboardButton("🔥 6 месяцев — 1199 Stars (−33%)", callback_data=f"sub:buy:half:{PLAN_CONFIGS['half'].stars}")],
            [InlineKeyboardButton("💎 Год — 1999 Stars (−44%)", callback_data=f"sub:buy:year:{PLAN_CONFIGS['year'].stars}")],
            [InlineKeyboardButton("◀️ Назад", callback_data="menu:main")],
        ]
    )


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main")]]
    )


def game_result_keyboard(game_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔁 Ещё раз", callback_data=f"game:{game_id}:start:0")],
            [InlineKeyboardButton("🎲 Другая игра", callback_data="menu:main")],
            [InlineKeyboardButton("📊 Моя статистика", callback_data="menu:stats")],
        ]
    )


def profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📈 Детальная статистика", callback_data="menu:stats")],
            [InlineKeyboardButton("🏆 Таблица лидеров", callback_data="menu:tournament")],
            [InlineKeyboardButton("🏠 Меню", callback_data="menu:main")],
        ]
    )
