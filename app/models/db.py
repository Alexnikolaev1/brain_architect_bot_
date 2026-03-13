"""
Storage access layer.

Production:
- MongoDB for users/game_stats
- Redis for sessions/leaderboard

Local fallback (when env vars are missing):
- In-memory storage for both Mongo and Redis concerns
"""

from __future__ import annotations

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
    from motor.motor_asyncio import AsyncIOMotorClient
except ModuleNotFoundError:  # optional in local mode
    AsyncIOMotorClient = None

logger = logging.getLogger(__name__)

_mongo_client: Any = None
_redis_client: Any = None

_memory_users: dict[int, dict[str, Any]] = {}
_memory_game_stats: list[dict[str, Any]] = []

_warned_memory_mongo = False
_warned_memory_redis = False


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


def _use_memory_mongo() -> bool:
    mongo_uri = os.environ.get("MONGODB_URI")
    return _is_placeholder(mongo_uri)


def _use_memory_redis() -> bool:
    redis_url = os.environ.get("UPSTASH_REDIS_URL")
    return _is_placeholder(redis_url)


def get_mongo() -> Any:
    global _mongo_client
    if _use_memory_mongo():
        return None

    if AsyncIOMotorClient is None:
        raise RuntimeError("MONGODB_URI задан, но пакет 'motor' не установлен.")

    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(
            os.environ["MONGODB_URI"],
            serverSelectionTimeoutMS=3000,
        )
    return _mongo_client


def get_db():
    global _warned_memory_mongo
    if _use_memory_mongo():
        if not _warned_memory_mongo:
            logger.warning("MONGODB_URI не задан. Используется in-memory storage для users/game_stats.")
            _warned_memory_mongo = True
        return None
    return get_mongo()[os.environ.get("MONGODB_DB", "brain_architect")]


async def get_redis() -> Any:
    global _redis_client, _warned_memory_redis
    if _use_memory_redis():
        if _redis_client is None:
            _redis_client = InMemoryRedis()
        if not _warned_memory_redis:
            logger.warning("UPSTASH_REDIS_URL не задан. Используется in-memory storage для sessions/leaderboard.")
            _warned_memory_redis = True
        return _redis_client

    if aioredis is None:
        raise RuntimeError("UPSTASH_REDIS_URL задан, но пакет 'redis' не установлен.")

    if _redis_client is None:
        _redis_client = aioredis.from_url(
            os.environ["UPSTASH_REDIS_URL"],
            password=os.environ.get("UPSTASH_REDIS_PASSWORD"),
            decode_responses=True,
        )
    return _redis_client


async def get_user(user_id: int) -> dict | None:
    db = get_db()
    if db is None:
        return _memory_users.get(user_id)
    return await db.users.find_one({"_id": user_id})


async def upsert_user(user_id: int, **fields) -> None:
    db = get_db()
    if db is None:
        user = _memory_users.get(user_id)
        if user is None:
            user = {"_id": user_id, "created_at": datetime.now(timezone.utc)}
            _memory_users[user_id] = user
        user.update(fields)
        return

    await db.users.update_one(
        {"_id": user_id},
        {"$set": fields, "$setOnInsert": {"created_at": datetime.now(timezone.utc)}},
        upsert=True,
    )


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
        db = get_db()
        if db is None:
            _memory_users[user_id] = user
        else:
            await db.users.insert_one(user)
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

    db = get_db()
    if db is None:
        _memory_game_stats.append(record)
        user = _memory_users.get(user_id)
        if user is not None:
            user["xp"] = int(user.get("xp", 0)) + xp_gain
        return

    await db.game_stats.insert_one(record)
    await db.users.update_one({"_id": user_id}, {"$inc": {"xp": xp_gain}})


async def get_user_stats(user_id: int) -> list[dict]:
    db = get_db()
    if db is None:
        rows = [r for r in _memory_game_stats if r.get("user_id") == user_id]
        rows.sort(key=lambda x: x.get("played_at", datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
        return rows[:100]

    cursor = db.game_stats.find({"user_id": user_id}).sort("played_at", -1).limit(100)
    return await cursor.to_list(length=100)


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
