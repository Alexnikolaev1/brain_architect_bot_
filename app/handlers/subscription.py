"""
🧠 Subscription Handler — Telegram Stars + управление тарифами
"""

from __future__ import annotations

import logging

from telegram import LabeledPrice, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.domain.subscription import PLAN_CONFIGS, is_valid_plan
from app.keyboards.builder import subscription_keyboard
from app.models.db import get_user
from app.services.access import effective_plan, is_pro_active
from app.services.callbacks import parse_subscription_callback

logger = logging.getLogger(__name__)

async def subscription_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    callback = parse_subscription_callback(query.data)
    if not callback:
        return
    action = callback.action

    if action == "plans":
        await query.edit_message_text(
            "💎 *Архитектор Мозга PRO*\n\n"
            "Что входит:\n"
            "• 🌪️ Режим ТУРБО (адаптивная сложность)\n"
            "• 📊 Детальная аналитика\n"
            "• 🏆 Еженедельные турниры\n"
            "• 🧬 RPG-прокачка архетипов\n"
            "• 🔔 Умные напоминания\n\n"
            "Выбери тариф:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=subscription_keyboard(),
        )

    elif action == "buy":
        plan_type = callback.plan_type
        stars = callback.stars
        if not is_valid_plan(plan_type):
            await query.answer("Неверный тариф", show_alert=True)
            return

        plan_config = PLAN_CONFIGS[plan_type]
        if stars != plan_config.stars:
            await query.answer("Цена тарифа устарела. Обнови меню подписок.", show_alert=True)
            return

        await query.message.reply_invoice(
            title=f"Подписка PRO — {plan_config.label}",
            description=(
                f"Полный доступ к Архитектор Мозга PRO на {plan_config.days} дней.\n"
                "Режим Турбо, турниры, аналитика."
            ),
            payload=f"sub:{plan_type}:{query.from_user.id}",
            currency="XTR",  # Telegram Stars
            prices=[LabeledPrice(label=f"PRO {plan_config.label}", amount=stars)],
            protect_content=True,
        )

    elif action == "status":
        user = await get_user(query.from_user.id)
        if not user:
            await query.answer("Используй /start")
            return

        if is_pro_active(user):
            exp = user.get("sub_expires")
            from datetime import timezone
            from datetime import datetime as dt
            if isinstance(exp, str):
                exp = dt.fromisoformat(exp)
            days = max(0, (exp.replace(tzinfo=timezone.utc) - dt.now(timezone.utc)).days)
            status_text = f"✅ PRO активна. Осталось {days} дней."
        elif effective_plan(user) == "trial":
            status_text = "🧪 Активен пробный период."
        else:
            status_text = "❌ PRO подписка не активна."

        await query.answer(status_text, show_alert=True)
