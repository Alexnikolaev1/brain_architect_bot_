"""
🧠 Payment Handlers — PreCheckout и успешная оплата Telegram Stars
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.domain.subscription import PLAN_CONFIGS, parse_subscription_payload
from app.keyboards.builder import main_menu_keyboard
from app.models.db import get_user, upsert_user
from app.services.access import effective_plan

logger = logging.getLogger(__name__)

async def precheckout_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Telegram требует ответить в течение 10 секунд."""
    query = update.pre_checkout_query
    payload = query.invoice_payload  # "sub:month:123456"

    try:
        parse_subscription_payload(payload)
        await query.answer(ok=True)
    except Exception as exc:
        logger.exception("PreCheckout error: %s", exc)
        await query.answer(ok=False, error_message="Ошибка обработки платежа.")


async def successful_payment(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка успешной оплаты."""
    payment = update.message.successful_payment
    payload = payment.invoice_payload  # "sub:month:123456"
    user_id = update.effective_user.id

    try:
        plan_type, payload_user_id = parse_subscription_payload(payload)
        if payload_user_id != user_id:
            logger.error("Payload user mismatch: payload=%s user=%s", payload_user_id, user_id)
            return
        plan_config = PLAN_CONFIGS[plan_type]
    except ValueError:
        logger.error("Bad payload: %s", payload)
        return

    user = await get_user(user_id)
    now = datetime.now(timezone.utc)

    # Продлеваем подписку, если уже есть активная
    current_exp = user.get("sub_expires") if user else None
    if current_exp:
        if isinstance(current_exp, str):
            current_exp = datetime.fromisoformat(current_exp)
        base = max(now, current_exp.replace(tzinfo=timezone.utc))
    else:
        base = now

    new_expires = base + timedelta(days=plan_config.days)

    await upsert_user(
        user_id,
        plan="pro",
        sub_expires=new_expires,
    )

    label = plan_config.label

    user_data = await get_user(user_id)
    plan = effective_plan(user_data)

    await update.message.reply_text(
        f"🎉 *Подписка активирована!*\n\n"
        f"💎 Тариф: PRO — {label}\n"
        f"📅 Действует до: {new_expires.strftime('%d.%m.%Y')}\n\n"
        f"Теперь тебе доступны:\n"
        f"• 🌪️ Режим ТУРБО\n"
        f"• 🏆 Еженедельные турниры\n"
        f"• 📊 Детальная аналитика\n\n"
        f"_Продолжай тренировать мозг каждый день!_ 🧠",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard(plan),
    )
