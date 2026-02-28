"""
SQLite-based async cache for analysis results.
TTL is configurable via CACHE_TTL_HOURS env var (default 24h).
Cache key: ticker_YYYY-MM-DD to ensure daily refresh.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime

import aiosqlite

from src.backend.config import CACHE_DB_PATH, CACHE_TTL_HOURS

logger = logging.getLogger(__name__)

_TTL_SECONDS = CACHE_TTL_HOURS * 3600


def _cache_key(ticker: str) -> str:
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    return f"{ticker.upper()}_{date_str}"


async def init_db() -> None:
    """Create the cache table if it doesn't exist."""
    async with aiosqlite.connect(CACHE_DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                expires_at INTEGER NOT NULL
            )
            """
        )
        await db.commit()
    logger.info(f"Cache DB initialised at {CACHE_DB_PATH}")


async def get(ticker: str) -> dict | None:
    """Return cached analysis dict or None on miss/expiry."""
    key = _cache_key(ticker)
    now = int(time.time())
    async with aiosqlite.connect(CACHE_DB_PATH) as db:
        async with db.execute(
            "SELECT data, expires_at FROM cache WHERE key = ?", (key,)
        ) as cursor:
            row = await cursor.fetchone()
    if row is None:
        logger.debug(f"Cache miss: {key}")
        return None
    data_str, expires_at = row
    if now > expires_at:
        logger.debug(f"Cache expired: {key}")
        return None
    logger.info(f"Cache hit: {key}")
    return json.loads(data_str)


async def set(ticker: str, data: dict) -> None:
    """Store analysis dict with TTL."""
    key = _cache_key(ticker)
    expires_at = int(time.time()) + _TTL_SECONDS
    data_str = json.dumps(data)
    async with aiosqlite.connect(CACHE_DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO cache (key, data, expires_at) VALUES (?, ?, ?)",
            (key, data_str, expires_at),
        )
        await db.commit()
    logger.debug(f"Cached: {key} (expires in {CACHE_TTL_HOURS}h)")


async def clear(ticker: str) -> None:
    """Remove all cache entries for a ticker."""
    pattern = f"{ticker.upper()}_%"
    async with aiosqlite.connect(CACHE_DB_PATH) as db:
        await db.execute("DELETE FROM cache WHERE key LIKE ?", (pattern,))
        await db.commit()
    logger.info(f"Cache cleared for {ticker}")
