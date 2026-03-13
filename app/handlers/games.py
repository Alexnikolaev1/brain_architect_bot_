"""
🧠 Game Handlers

Роутинг callback_data и текстовых ответов для всех 5 игр.

Паттерны callback_data:
  game:{game_id}:start:0          — начать игру
  game:double_strike:correct/wrong:{val}
  game:sensation_maze:correct/wrong:{idx}
  game:anti_realtor:show_change:0 / correct/wrong:{obj}
  game:stop_signal:correct/wrong:{idx}
  game:blind_typing:start:0       — фаза ввода
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.domain.games import ARCHETYPE_MAP, GAME_NAMES
from app.games.anti_realtor import generate_anti_realtor_question
from app.games.blind_typing import check_blind_typing_answer
from app.games.factory import generate_game
from app.keyboards.builder import (
    back_to_menu_keyboard,
    game_result_keyboard,
    main_menu_keyboard,
)
from app.models.db import (
    ensure_user,
    get_top_leaderboard,
    get_session,
    get_user,
)
from app.repositories.game_repository import store_session
from app.services.access import effective_plan, is_pro_active
from app.services.callbacks import parse_game_callback, parse_menu_callback
from app.services.game_flow import finalize_round
from app.services.profile import ARCHETYPE_ICONS, compute_difficulty

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════
#  MAIN MENU callback
# ══════════════════════════════════════════════════════════════════════════


async def game_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    menu_callback = parse_menu_callback(query.data)
    if not menu_callback:
        return
    action = menu_callback.action
    user = await get_user(query.from_user.id)
    plan = effective_plan(user)

    if action == "main":
        await query.edit_message_text(
            "🧠 *Архитектор Мозга* — выбери тренировку:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard(plan),
        )
    elif action == "stats":
        await query.edit_message_text(
            "📊 Открой /stats для подробной статистики.",
            reply_markup=back_to_menu_keyboard(),
        )
    elif action == "profile":
        await query.edit_message_text(
            "👤 Открой /profile для профиля.",
            reply_markup=back_to_menu_keyboard(),
        )
    elif action == "tournament":
        await _show_tournament(query)
    elif action == "turbo":
        if not is_pro_active(user):
            await query.edit_message_text(
                "🌪️ Режим ТУРБО доступен в PRO-подписке.\n\nОткрой /subscribe для подключения.",
                reply_markup=back_to_menu_keyboard(),
            )
            return
        await _start_turbo_session(query, user)


async def _show_tournament(query) -> None:
    top = await get_top_leaderboard(10)
    if not top:
        text = "🏆 *Турнир этой недели*\n\nПока никто не набрал очки. Будь первым!"
    else:
        from app.models.db import get_redis
        r = await get_redis()
        lines = []
        medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
        for i, (uid, score) in enumerate(top):
            name = await r.get(f"lb_name:{uid}") or f"user_{uid}"
            lines.append(f"{medals[i]} {name} — {int(score)} XP")
        text = "🏆 *Топ-10 этой недели*\n\n" + "\n".join(lines)

    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_to_menu_keyboard(),
    )


async def _start_turbo_session(query, user: dict | None) -> None:
    difficulty = compute_difficulty(user)
    plan = effective_plan(user)
    await query.edit_message_text(
        f"🌪️ *Режим ТУРБО* — уровень сложности {difficulty}/10\n\n"
        f"Адаптивная программа на основе твоих последних результатов.\n\n"
        f"Выбери игру:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard(plan),
    )


# ══════════════════════════════════════════════════════════════════════════
#  GAME callback dispatcher
# ══════════════════════════════════════════════════════════════════════════


async def game_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    callback = parse_game_callback(query.data)
    if not callback:
        return

    game_id = callback.game_id
    action = callback.action
    user_id = query.from_user.id

    await ensure_user(
        user_id,
        query.from_user.username or "",
        query.from_user.full_name or "",
    )

    # ── START a game ───────────────────────────────────────────────────────
    if action == "start":
        user = await get_user(user_id)
        difficulty = compute_difficulty(user) if user else 1
        q = generate_game(game_id, difficulty)
        await store_session(user_id, q.session_data)
        await query.edit_message_text(
            q.text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=q.keyboard,
        )

    # ── ANTI-REALTOR: phase 2 ─────────────────────────────────────────────
    elif game_id == "anti_realtor" and action == "show_change":
        session = await get_session(user_id)
        if not session:
            await query.edit_message_text("Сессия истекла. Начни заново.", reply_markup=back_to_menu_keyboard())
            return
        q2 = generate_anti_realtor_question(session)
        await store_session(user_id, q2.session_data)
        await query.edit_message_text(
            q2.text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=q2.keyboard,
        )

    # ── BLIND TYPING: start input phase ───────────────────────────────────
    elif game_id == "blind_typing" and action == "start":
        session = await get_session(user_id)
        if not session:
            await query.edit_message_text("Сессия истекла.", reply_markup=back_to_menu_keyboard())
            return
        session["phase"] = "input"
        await store_session(user_id, session)
        await query.edit_message_text(
            "⌨️ *Слова скрыты!*\n\n"
            "Теперь напечатай слова *в обратном порядке* через пробел.\n\n"
            "_Попробуй не смотреть на клавиатуру телефона!_",
            parse_mode=ParseMode.MARKDOWN,
        )

    # ── ANSWER: correct / wrong ───────────────────────────────────────────
    elif action in ("correct", "wrong"):
        await _handle_answer(query, user_id, game_id, action == "correct")


async def _handle_answer(query, user_id: int, game_id: str, is_correct: bool) -> None:
    session = await get_session(user_id)
    result = await finalize_round(
        user_id=user_id,
        game_id=game_id,
        username=query.from_user.username or str(user_id),
        is_correct=is_correct,
        started_at=(session or {}).get("started_at"),
        difficulty=(session or {}).get("difficulty"),
    )

    explanation = (session or {}).get("explanation", "")

    if is_correct:
        result_emoji = "✅"
        result_line = f"*Верно!* +{result.score} XP"
    else:
        result_emoji = "❌"
        result_line = "Неверно. Но мозг всё равно тренируется!"

    text = (
        f"{result_emoji} *{GAME_NAMES.get(game_id, game_id)}*\n"
        f"{'─'*30}\n\n"
        f"{result_line}\n"
        f"⏱ Время: {result.elapsed_ms / 1000:.1f}с\n\n"
    )
    if explanation:
        text += f"🧪 *Объяснение:*\n{explanation}\n\n"

    # Обновляем архетип
    archetype = ARCHETYPE_MAP.get(game_id, "oracle")
    icon = ARCHETYPE_ICONS.get(archetype, "🧠")
    text += f"{icon} Прокачан архетип: *{archetype.capitalize()}*"

    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=game_result_keyboard(game_id),
    )

# ══════════════════════════════════════════════════════════════════════════
#  TEXT ANSWER HANDLER (Blind Typing)
# ══════════════════════════════════════════════════════════════════════════


async def handle_text_answer(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    session = await get_session(user_id)

    if not session or session.get("game_id") != "blind_typing" or session.get("phase") != "input":
        return  # Не наш ответ

    user_input = update.message.text.strip()
    is_correct, feedback = check_blind_typing_answer(user_input, session)
    result = await finalize_round(
        user_id=user_id,
        game_id="blind_typing",
        username=update.effective_user.username or str(user_id),
        is_correct=is_correct,
        started_at=session.get("started_at"),
        difficulty=session.get("difficulty"),
    )

    words_original = session["words"]
    correct_answer = " ".join(reversed(words_original))

    text = (
        f"⌨️ *СЛЕПОЙ ДЕСЯТИПАЛЬЦЕВЫЙ*\n"
        f"{'─'*30}\n\n"
        f"{feedback}\n"
        f"Правильно: `{correct_answer}`\n"
        f"Твой ответ: `{user_input}`\n\n"
        f"⏱ Время: {result.elapsed_ms / 1000:.1f}с | +{result.score} XP"
    )

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=game_result_keyboard("blind_typing"),
    )
