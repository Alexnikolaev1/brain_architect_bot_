"""
🧠 Profile Service — вычисление уровня, статистики, архетипов
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from telegram import User
from app.domain.games import GAME_NAMES
from app.services.access import TRIAL_DAYS, effective_plan

ARCHETYPE_ICONS = {
    "mage": "🧙 Маг",
    "knight": "⚔️ Рыцарь",
    "scout": "🏹 Разведчик",
    "oracle": "🔮 Оракул",
}

ARCHETYPE_SKILLS = {
    "mage": "Пространственное мышление",
    "knight": "Скорость реакции",
    "scout": "Сенсорная интеграция",
    "oracle": "Критическое мышление",
}

LEVEL_THRESHOLDS = [0, 100, 300, 600, 1000, 1500, 2500, 4000, 6500, 10000]


def compute_level(xp: int) -> tuple[int, int, int]:
    """Возвращает (level, xp_in_level, xp_to_next)."""
    for i, threshold in enumerate(LEVEL_THRESHOLDS):
        if xp < threshold:
            prev = LEVEL_THRESHOLDS[i - 1]
            return i, xp - prev, threshold - xp
    level = len(LEVEL_THRESHOLDS)
    extra = xp - LEVEL_THRESHOLDS[-1]
    return level, extra, 1000  # After max level


def compute_difficulty(user: dict | None) -> int:
    """Адаптивная сложность на основе XP."""
    if not user:
        return 1
    xp = user.get("xp", 0)
    level, _, _ = compute_level(xp)
    return max(1, min(10, level))


def _xp_bar(xp: int, width: int = 10) -> str:
    level, in_level, to_next = compute_level(xp)
    total = in_level + to_next
    filled = int(width * in_level / total) if total > 0 else 0
    return "█" * filled + "░" * (width - filled)


async def build_profile_text(user: dict, tg_user: User) -> str:
    xp = user.get("xp", 0)
    level, in_level, to_next = compute_level(xp)
    archetype = user.get("archetype", "oracle")
    arch_icon = ARCHETYPE_ICONS.get(archetype, "🧠")
    arch_skill = ARCHETYPE_SKILLS.get(archetype, "")
    bar = _xp_bar(xp)
    streak = user.get("streak", 0)
    plan = effective_plan(user)

    plan_label = {
        "free": "Фримиум",
        "trial": "Пробный 7 дней",
        "pro": "PRO",
        "vip": "VIP",
    }.get(plan, plan)

    sub_exp = user.get("sub_expires")
    sub_line = ""
    if plan == "pro" and sub_exp:
        if isinstance(sub_exp, str):
            sub_exp = datetime.fromisoformat(sub_exp)
        days_left = (sub_exp.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).days
        sub_line = f"\n⏳ Подписка до: {sub_exp.strftime('%d.%m.%Y')} ({days_left} дн.)"
    elif plan == "trial":
        trial_start = user.get("trial_start")
        if isinstance(trial_start, str):
            trial_start = datetime.fromisoformat(trial_start)
        if trial_start:
            if trial_start.tzinfo is None:
                trial_start = trial_start.replace(tzinfo=timezone.utc)
            days_left = max(0, (trial_start + timedelta(days=TRIAL_DAYS) - datetime.now(timezone.utc)).days)
            sub_line = f"\n⏳ Пробный период: {days_left} дн."

    return (
        f"👤 *Профиль Архитектора*\n"
        f"{'─'*30}\n\n"
        f"🆔 {tg_user.full_name}\n"
        f"💎 Тариф: {plan_label}{sub_line}\n\n"
        f"🎭 Архетип: {arch_icon}\n"
        f"   Сила: *{arch_skill}*\n\n"
        f"📊 *Прогресс:*\n"
        f"   Уровень: **{level}** [{bar}]\n"
        f"   XP: {xp} (+{to_next} до след. уровня)\n"
        f"   🔥 Серия: {streak} дней подряд\n\n"
        f"🧠 *Индекс нейропластичности:* {_neuro_index(xp)}/100"
    )


def _neuro_index(xp: int) -> int:
    """Псевдо-индекс нейропластичности от 0 до 100."""
    return min(100, int(xp / 100))


def build_stats_text(user: dict, stats: list[dict]) -> str:
    if not stats:
        return (
            "📊 *Статистика*\n\n"
            "Пока нет данных. Сыграй хотя бы одну игру!"
        )

    by_game: dict[str, list] = defaultdict(list)
    for s in stats:
        by_game[s["game_id"]].append(s)

    lines = ["📊 *Твоя статистика*\n" + "─" * 30]

    for gid, records in by_game.items():
        correct = sum(1 for r in records if r.get("correct"))
        total = len(records)
        avg_time = sum(r.get("time_ms", 0) for r in records) / total / 1000
        best_score = max(r.get("score", 0) for r in records)

        game_name = GAME_NAMES.get(gid, gid)
        accuracy = int(100 * correct / total) if total else 0

        lines.append(
            f"\n*{game_name}*\n"
            f"  ✅ Точность: {accuracy}% ({correct}/{total})\n"
            f"  ⏱ Среднее время: {avg_time:.1f}с\n"
            f"  🏆 Лучший счёт: {best_score} XP"
        )

    total_games = len(stats)
    total_xp = user.get("xp", 0)
    lines.append(f"\n{'─'*30}\n🎮 Всего игр: {total_games} | 💎 Всего XP: {total_xp}")

    return "\n".join(lines)
