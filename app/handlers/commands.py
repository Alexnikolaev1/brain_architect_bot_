"""
🧠 Command Handlers — /start, /help, /profile, /stats, /subscribe
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.keyboards.builder import (
    back_to_menu_keyboard,
    main_menu_keyboard,
    profile_keyboard,
    subscription_keyboard,
)
from app.models.db import (
    ensure_user,
    get_top_leaderboard,
    get_user,
    get_user_stats,
)
from app.services.access import effective_plan
from app.services.profile import build_profile_text, build_stats_text, compute_level
from app.utils.texts import ONBOARDING_TEXT, HELP_TEXT

logger = logging.getLogger(__name__)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    user = await ensure_user(
        tg_user.id,
        tg_user.username or "",
        tg_user.full_name or "",
    )

    is_new = (datetime.now(timezone.utc) - user["created_at"]).total_seconds() < 5

    if is_new:
        text = ONBOARDING_TEXT.format(name=tg_user.first_name)
    else:
        current_plan = effective_plan(user)
        text = (
            f"С возвращением, *{tg_user.first_name}*! 🧠\n\n"
            f"Уровень: {user['level']} | XP: {user['xp']} | Стрик: {user['streak']} 🔥\n\n"
            f"Тариф: {current_plan.upper()}\n\n"
            f"Выбери тренировку:"
        )

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard(effective_plan(user)),
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        HELP_TEXT,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_to_menu_keyboard(),
    )


async def cmd_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("Используй /start чтобы начать!")
        return

    text = await build_profile_text(user, update.effective_user)
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=profile_keyboard(),
    )


async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("Используй /start чтобы начать!")
        return

    stats = await get_user_stats(update.effective_user.id)
    text = build_stats_text(user, stats)
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_to_menu_keyboard(),
    )


async def cmd_subscribe(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "💎 *Подписка Архитектор Мозга PRO*\n\n"
        "Что включено:\n"
        "• 📊 Детальная аналитика прогресса\n"
        "• 🌪️ Режим ТУРБО (адаптивная сложность)\n"
        "• 🏆 Еженедельные турниры\n"
        "• 🧬 Персональный профиль мозга (RPG-прокачка)\n"
        "• 🔔 Напоминания по нейро-расписанию\n\n"
        "Выбери тариф:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=subscription_keyboard(),
    )
