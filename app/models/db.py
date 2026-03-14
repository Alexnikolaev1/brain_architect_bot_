"""
Storage access layer.

Production:
- Postgres for users/game_stats
- Redis for sessions/leaderboard

Local fallback (when env vars are missing):
- In-memory storage for both SQL and Redis concerns
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

try:
    import redis.asyncio as aioredis
except ModuleNotFoundError:  # optional in local mode
    aioredis = None

try:
    import asyncpg
except ModuleNotFoundError:  # optional in local mode
    asyncpg = None

logger = logging.getLogger(__name__)

_pg_pool: Any = None
_redis_client: Any = None

_memory_users: dict[int, dict[str, Any]] = {}
_memory_game_stats: list[dict[str, Any]] = []

_warned_memory_sql = False
_warned_memory_redis = False
_pg_schema_ready = False
_pg_init_lock = asyncio.Lock()


def _is_placeholder(value: str | None) -> bool:
    if not value:
        return True
    lowered = value.lower().strip()
    return (
        "your_" in lowered
        or "example" in lowered
        or "your-endpoint.upstash.io" in lowered
        or "your-postgres-host" in lowered
    )


def _get_postgres_dsn() -> str | None:
    return (
        os.environ.get("DATABASE_URL")
        or os.environ.get("POSTGRES_URL")
        or os.environ.get("POSTGRES_PRISMA_URL")
    )


def _get_redis_url() -> str | None:
    return os.environ.get("UPSTASH_REDIS_URL") or os.environ.get("REDIS_URL")


def _get_redis_password() -> str | None:
    return os.environ.get("UPSTASH_REDIS_PASSWORD") or os.environ.get("REDIS_PASSWORD")


def _warn_using_memory_sql() -> None:
    global _warned_memory_sql
    if not _warned_memory_sql:
        logger.warning("DATABASE_URL/POSTGRES_URL не задан. Используется in-memory storage для users/game_stats.")
        _warned_memory_sql = True


class InMemoryRedis:
    def __init__(self) -> None:
        self._kv: dict[str, str] = {}
        self._zsets: dict[str, dict[str, float]] = {}

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self._kv[key] = value

    async def get(self, key: str) -> str | None:
        return self._kv.get(key)

    async def delete(self, key: str) -> None:
        self._kv.pop(key, None)

    async def expire(self, key: str, ttl: int) -> bool:
        return True

    async def zincrby(self, key: str, increment: int | float, member: str) -> float:
        zset = self._zsets.setdefault(key, {})
        zset[member] = float(zset.get(member, 0.0)) + float(increment)
        return zset[member]

    async def zrevrangebyscore(
        self,
        key: str,
        max_score: str,
        min_score: str,
        withscores: bool = True,
        start: int = 0,
        num: int = 10,
    ) -> list[Any]:
        items = sorted(self._zsets.get(key, {}).items(), key=lambda kv: kv[1], reverse=True)
        items = items[start : start + num]
        if withscores:
            return [(member, score) for member, score in items]
        return [member for member, _ in items]


def _use_memory_sql() -> bool:
    postgres_dsn = _get_postgres_dsn()
    return _is_placeholder(postgres_dsn)


def _use_memory_redis() -> bool:
    redis_url = _get_redis_url()
    return _is_placeholder(redis_url)


async def _get_pg_pool() -> Any:
    global _pg_pool
    if _use_memory_sql():
        return None

    if asyncpg is None:
        raise RuntimeError("DATABASE_URL задан, но пакет 'asyncpg' не установлен.")

    if _pg_pool is None:
        dsn = _get_postgres_dsn()
        if not dsn:
            return None
        _pg_pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=1,
            max_size=3,
            command_timeout=5,
            statement_cache_size=0,
        )
    return _pg_pool


async def _ensure_pg_schema() -> None:
    global _pg_schema_ready
    if _pg_schema_ready:
        return

    async with _pg_init_lock:
        if _pg_schema_ready:
            return

        pool = await _get_pg_pool()
        if pool is None:
            return

        async with pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT NOT NULL DEFAULT '',
                    full_name TEXT NOT NULL DEFAULT '',
                    plan TEXT NOT NULL DEFAULT 'trial',
                    trial_start TIMESTAMPTZ,
                    sub_expires TIMESTAMPTZ,
                    xp INTEGER NOT NULL DEFAULT 0,
                    level INTEGER NOT NULL DEFAULT 1,
                    archetype TEXT NOT NULL DEFAULT 'oracle',
                    streak INTEGER NOT NULL DEFAULT 0,
                    last_session TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS game_stats (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    game_id TEXT NOT NULL,
                    played_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    score INTEGER NOT NULL,
                    time_ms INTEGER NOT NULL,
                    correct BOOLEAN NOT NULL,
                    difficulty INTEGER NOT NULL
                );
                """
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_game_stats_user_played ON game_stats(user_id, played_at DESC);"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_game_stats_game_user ON game_stats(game_id, user_id);"
            )

        _pg_schema_ready = True


def _user_row_to_doc(row: Any) -> dict[str, Any]:
    return {
        "_id": int(row["user_id"]),
        "username": row["username"],
        "full_name": row["full_name"],
        "plan": row["plan"],
        "trial_start": row["trial_start"],
        "sub_expires": row["sub_expires"],
        "xp": int(row["xp"]),
        "level": int(row["level"]),
        "archetype": row["archetype"],
        "streak": int(row["streak"]),
        "last_session": row["last_session"],
        "created_at": row["created_at"],
    }


def _game_row_to_doc(row: Any) -> dict[str, Any]:
    return {
        "user_id": int(row["user_id"]),
        "game_id": row["game_id"],
        "played_at": row["played_at"],
        "score": int(row["score"]),
        "time_ms": int(row["time_ms"]),
        "correct": bool(row["correct"]),
        "difficulty": int(row["difficulty"]),
    }


async def get_redis() -> Any:
    global _redis_client, _warned_memory_redis
    if _use_memory_redis():
        if _redis_client is None:
            _redis_client = InMemoryRedis()
        if not _warned_memory_redis:
            logger.warning("UPSTASH_REDIS_URL/REDIS_URL не задан. Используется in-memory storage для sessions/leaderboard.")
            _warned_memory_redis = True
        return _redis_client

    if aioredis is None:
        raise RuntimeError("UPSTASH_REDIS_URL/REDIS_URL задан, но пакет 'redis' не установлен.")

    if _redis_client is None:
        redis_url = _get_redis_url()
        if not redis_url:
            raise RuntimeError("Не найден URL Redis (UPSTASH_REDIS_URL или REDIS_URL).")
        _redis_client = aioredis.from_url(
            redis_url,
            password=_get_redis_password(),
            decode_responses=True,
        )
    return _redis_client


async def get_user(user_id: int) -> dict | None:
    if _use_memory_sql():
        _warn_using_memory_sql()
        return _memory_users.get(user_id)
    await _ensure_pg_schema()
    pool = await _get_pg_pool()
    if pool is None:
        return None
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT user_id, username, full_name, plan, trial_start, sub_expires,
                   xp, level, archetype, streak, last_session, created_at
            FROM users
            WHERE user_id = $1
            """,
            int(user_id),
        )
    return _user_row_to_doc(row) if row else None


async def upsert_user(user_id: int, **fields) -> None:
    if _use_memory_sql():
        _warn_using_memory_sql()
        user = _memory_users.get(user_id)
        if user is None:
            user = {"_id": user_id, "created_at": datetime.now(timezone.utc)}
            _memory_users[user_id] = user
        user.update(fields)
        return

    await _ensure_pg_schema()
    pool = await _get_pg_pool()
    if pool is None:
        return

    allowed = {
        "username",
        "full_name",
        "plan",
        "trial_start",
        "sub_expires",
        "xp",
        "level",
        "archetype",
        "streak",
        "last_session",
    }
    cleaned = {k: v for k, v in fields.items() if k in allowed}

    if not cleaned:
        return

    columns = ["user_id", "created_at"] + list(cleaned.keys())
    values = [int(user_id), datetime.now(timezone.utc)] + [cleaned[k] for k in cleaned]
    placeholders = ", ".join(f"${i}" for i in range(1, len(values) + 1))
    col_sql = ", ".join(columns)
    updates = ", ".join(f"{col} = EXCLUDED.{col}" for col in cleaned)

    query = f"""
        INSERT INTO users ({col_sql})
        VALUES ({placeholders})
        ON CONFLICT (user_id) DO UPDATE SET
            {updates}
    """
    async with pool.acquire() as conn:
        await conn.execute(query, *values)


async def ensure_user(user_id: int, username: str, full_name: str) -> dict:
    user = await get_user(user_id)
    if user is None:
        now = datetime.now(timezone.utc)
        user = {
            "_id": user_id,
            "username": username,
            "full_name": full_name,
            "plan": "trial",
            "trial_start": now,
            "sub_expires": None,
            "xp": 0,
            "level": 1,
            "archetype": "oracle",
            "streak": 0,
            "last_session": None,
            "created_at": now,
        }
        if _use_memory_sql():
            _warn_using_memory_sql()
            _memory_users[user_id] = user
        else:
            await _ensure_pg_schema()
            pool = await _get_pg_pool()
            if pool is not None:
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO users (
                            user_id, username, full_name, plan, trial_start, sub_expires,
                            xp, level, archetype, streak, last_session, created_at
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                        ON CONFLICT (user_id) DO NOTHING
                        """,
                        int(user_id),
                        user["username"],
                        user["full_name"],
                        user["plan"],
                        user["trial_start"],
                        user["sub_expires"],
                        int(user["xp"]),
                        int(user["level"]),
                        user["archetype"],
                        int(user["streak"]),
                        user["last_session"],
                        user["created_at"],
                    )
    else:
        if user.get("username") != username or user.get("full_name") != full_name:
            await upsert_user(user_id, username=username, full_name=full_name)
            user["username"] = username
            user["full_name"] = full_name
    return user


async def save_game_stat(
    user_id: int,
    game_id: str,
    score: int,
    time_ms: int,
    correct: bool,
    difficulty: int,
) -> None:
    record = {
        "user_id": user_id,
        "game_id": game_id,
        "played_at": datetime.now(timezone.utc),
        "score": score,
        "time_ms": time_ms,
        "correct": correct,
        "difficulty": difficulty,
    }
    xp_gain = score * (2 if correct else 0)

    if _use_memory_sql():
        _warn_using_memory_sql()
        _memory_game_stats.append(record)
        user = _memory_users.get(user_id)
        if user is not None:
            user["xp"] = int(user.get("xp", 0)) + xp_gain
        return

    await _ensure_pg_schema()
    pool = await _get_pg_pool()
    if pool is None:
        return
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO game_stats (user_id, game_id, played_at, score, time_ms, correct, difficulty)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                int(user_id),
                game_id,
                record["played_at"],
                int(score),
                int(time_ms),
                bool(correct),
                int(difficulty),
            )
            await conn.execute(
                """
                UPDATE users
                SET xp = COALESCE(xp, 0) + $2
                WHERE user_id = $1
                """,
                int(user_id),
                int(xp_gain),
            )


async def get_user_stats(user_id: int) -> list[dict]:
    if _use_memory_sql():
        _warn_using_memory_sql()
        rows = [r for r in _memory_game_stats if r.get("user_id") == user_id]
        rows.sort(key=lambda x: x.get("played_at", datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
        return rows[:100]

    await _ensure_pg_schema()
    pool = await _get_pg_pool()
    if pool is None:
        return []
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT user_id, game_id, played_at, score, time_ms, correct, difficulty
            FROM game_stats
            WHERE user_id = $1
            ORDER BY played_at DESC
            LIMIT 100
            """,
            int(user_id),
        )
    return [_game_row_to_doc(row) for row in rows]


async def set_session(user_id: int, data: dict, ttl: int = 3600) -> None:
    r = await get_redis()
    await r.setex(f"session:{user_id}", ttl, json.dumps(data, default=str))


async def get_session(user_id: int) -> dict | None:
    r = await get_redis()
    raw = await r.get(f"session:{user_id}")
    return json.loads(raw) if raw else None


async def delete_session(user_id: int) -> None:
    r = await get_redis()
    await r.delete(f"session:{user_id}")


async def update_leaderboard(user_id: int, username: str, weekly_score: int) -> None:
    r = await get_redis()
    week = int(time.time()) // (7 * 86400)
    key = f"leaderboard:{week}"
    await r.zincrby(key, weekly_score, str(user_id))
    await r.setex(f"lb_name:{user_id}", 7 * 86400, username or str(user_id))
    await r.expire(key, 8 * 86400)


async def get_top_leaderboard(n: int = 10) -> list[tuple[str, float]]:
    r = await get_redis()
    week = int(time.time()) // (7 * 86400)
    key = f"leaderboard:{week}"
    rows = await r.zrevrangebyscore(key, "+inf", "-inf", withscores=True, start=0, num=n)
    return [(str(uid), float(score)) for uid, score in rows]
