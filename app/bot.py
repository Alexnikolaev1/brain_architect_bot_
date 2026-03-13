"""
🧠 Bot Application Factory
Регистрирует все хендлеры, команды и ConversationHandler-ы.
"""

import os
import logging

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from app.handlers.commands import (
    cmd_help,
    cmd_profile,
    cmd_start,
    cmd_stats,
    cmd_subscribe,
)
from app.handlers.games import (
    game_callback,
    game_menu,
    handle_text_answer,
)
from app.handlers.payment import (
    precheckout_callback,
    successful_payment,
)
from app.handlers.subscription import subscription_menu

logger = logging.getLogger(__name__)


async def _log_errors(update, context) -> None:
    logger.exception("Unhandled bot error. update=%s", update, exc_info=context.error)


async def _debug_incoming_update(update, context) -> None:
    """Non-intrusive debug logger for incoming updates in local runs."""
    message = update.effective_message
    callback = update.callback_query
    if message:
        logger.info(
            "Incoming message: chat_id=%s user_id=%s text=%r",
            message.chat_id,
            update.effective_user.id if update.effective_user else None,
            message.text,
        )
    elif callback:
        logger.info(
            "Incoming callback: chat_id=%s user_id=%s data=%r",
            callback.message.chat_id if callback.message else None,
            update.effective_user.id if update.effective_user else None,
            callback.data,
        )
    else:
        logger.info("Incoming update type without message/callback: %s", update.update_id)


async def _text_command_fallback(update, context) -> None:
    """Fallback for clients that send '/start' as plain text."""
    text = (update.effective_message.text or "").strip().split()[0].lower()
    command = text.split("@")[0]

    if command == "/start":
        await cmd_start(update, context)
    elif command == "/help":
        await cmd_help(update, context)
    elif command == "/profile":
        await cmd_profile(update, context)
    elif command == "/stats":
        await cmd_stats(update, context)
    elif command == "/subscribe":
        await cmd_subscribe(update, context)


async def create_application() -> Application:
    token = os.environ["TELEGRAM_BOT_TOKEN"]

    app = (
        Application.builder()
        .token(token)
        .read_timeout(7)
        .write_timeout(7)
        .connect_timeout(7)
        .pool_timeout(7)
        .build()
    )

    # ── Core commands ──────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("subscribe", cmd_subscribe))

    # ── Game flow ──────────────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(game_menu, pattern="^menu"))
    app.add_handler(CallbackQueryHandler(game_callback, pattern="^game:"))
    app.add_handler(CallbackQueryHandler(subscription_menu, pattern="^sub:"))

    # ── Command fallback from plain text ───────────────────────────────────
    app.add_handler(
        MessageHandler(
            filters.Regex(r"^/(start|help|profile|stats|subscribe)(@\w+)?(\s+.*)?$"),
            _text_command_fallback,
        )
    )

    # ── Text answers (Blind Typing game) ──────────────────────────────────
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_answer)
    )

    # ── Payments ──────────────────────────────────────────────────────────
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment)
    )

    app.add_error_handler(_log_errors)
    # Keep lightweight update diagnostics always on in local runs.
    app.add_handler(MessageHandler(filters.ALL, _debug_incoming_update), group=99)

    return app
