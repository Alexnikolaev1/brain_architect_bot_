#!/usr/bin/env python3
"""
Local smoke checks for Brain Architect bot.

Usage:
  python scripts/smoke_local.py
  python scripts/smoke_local.py --network
  python scripts/smoke_local.py --write-checks
"""

from __future__ import annotations

import argparse
import asyncio
import os
import pathlib
import sys
import time

from dotenv import load_dotenv
from telegram.ext import CallbackQueryHandler, CommandHandler

# Allow running as `python scripts/smoke_local.py`.
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.bot import create_application
from app.games.anti_realtor import generate_anti_realtor_question
from app.games.blind_typing import check_blind_typing_answer
from app.games.factory import generate_game


def _ok(label: str) -> None:
    print(f"[OK] {label}")


def _fail(label: str, reason: str) -> None:
    print(f"[FAIL] {label}: {reason}")
    raise RuntimeError(reason)


def _pattern_as_text(handler: CallbackQueryHandler) -> str:
    pattern = getattr(handler, "pattern", None)
    if pattern is None:
        return ""
    return getattr(pattern, "pattern", str(pattern))


def _is_placeholder(value: str | None) -> bool:
    if not value:
        return True
    lowered = value.lower().strip()
    return (
        "your_" in lowered
        or "example" in lowered
        or "user:password@cluster.mongodb.net" in lowered
        or "your-endpoint.upstash.io" in lowered
    )


def _has_command(handlers: list, command: str) -> bool:
    for handler in handlers:
        if isinstance(handler, CommandHandler) and command in handler.commands:
            return True
    return False


def _has_callback_pattern(handlers: list, pattern_prefix: str) -> bool:
    for handler in handlers:
        if isinstance(handler, CallbackQueryHandler):
            if _pattern_as_text(handler).startswith(pattern_prefix):
                return True
    return False


async def _check_app_wiring(network: bool) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        _fail("Env", "TELEGRAM_BOT_TOKEN is missing in .env")
    if ":" not in token:
        _fail("Env", "TELEGRAM_BOT_TOKEN looks invalid (missing ':')")
    _ok("TELEGRAM_BOT_TOKEN present")

    app = await create_application()
    handlers = [h for group in app.handlers.values() for h in group]

    if not _has_command(handlers, "start"):
        _fail("Router", "/start CommandHandler not registered")
    if not _has_callback_pattern(handlers, "^menu"):
        _fail("Router", "menu callback handler not registered")
    if not _has_callback_pattern(handlers, "^game:"):
        _fail("Router", "game callback handler not registered")
    if not _has_callback_pattern(handlers, "^sub:"):
        _fail("Router", "subscription callback handler not registered")
    _ok("Handlers wiring (/start, menu, game, sub)")

    if network:
        me = await app.bot.get_me()
        _ok(f"Telegram API reachable as @{me.username}")


def _check_game_generation() -> None:
    for game_id in ("double_strike", "sensation_maze", "anti_realtor", "stop_signal", "blind_typing"):
        q = generate_game(game_id, difficulty=2)  # type: ignore[arg-type]
        if not q.text or not q.session_data:
            _fail("Game generation", f"{game_id} returned empty content")

    anti_session = generate_game("anti_realtor", difficulty=2).session_data
    anti_q2 = generate_anti_realtor_question(anti_session)
    if "Какой предмет переставили?" not in anti_q2.text:
        _fail("Anti-realtor phase 2", "second phase text is malformed")

    blind_session = generate_game("blind_typing", difficulty=2).session_data
    ok, _ = check_blind_typing_answer(blind_session["answer"], blind_session)
    if not ok:
        _fail("Blind typing answer check", "expected answer is not accepted")
    _ok("Game engine smoke")


async def _check_storage(write_checks: bool) -> None:
    from app.models.db import (
        delete_session,
        ensure_user,
        get_session,
        get_top_leaderboard,
        set_session,
        update_leaderboard,
    )

    has_external_storage = not (
        _is_placeholder(os.environ.get("MONGODB_URI"))
        and _is_placeholder(os.environ.get("UPSTASH_REDIS_URL"))
    )
    if has_external_storage and not write_checks:
        _ok("Storage checks skipped (external DB/Redis detected; use --write-checks to enable)")
        return

    user_id = int(time.time()) % 1_000_000 + 9_000_000_000
    await ensure_user(user_id, "smoke_user", "Smoke User")

    payload = {"game_id": "double_strike", "started_at": time.time(), "difficulty": 1}
    await set_session(user_id, payload)
    loaded = await get_session(user_id)
    if not loaded or loaded.get("game_id") != "double_strike":
        _fail("Session storage", "saved session cannot be read")

    await update_leaderboard(user_id, "smoke_user", 123)
    top = await get_top_leaderboard(50)
    if not any(str(uid) == str(user_id) for uid, _ in top):
        _fail("Leaderboard storage", "user score not found in leaderboard")

    await delete_session(user_id)
    _ok("Storage write/read smoke")


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run local smoke checks.")
    parser.add_argument("--network", action="store_true", help="Also call Telegram getMe.")
    parser.add_argument(
        "--write-checks",
        action="store_true",
        help="Enable storage write checks even when external DB/Redis is configured.",
    )
    args = parser.parse_args()

    load_dotenv(override=True)
    print("== Brain Architect local smoke ==")

    try:
        await _check_app_wiring(network=args.network)
        _check_game_generation()
        await _check_storage(write_checks=args.write_checks)
    except Exception as exc:  # noqa: BLE001
        print(f"\nSmoke failed: {exc}")
        return 1

    print("\nSmoke passed. You can run: python run_local.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
