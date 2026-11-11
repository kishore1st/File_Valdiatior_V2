import asyncpg
from .config import settings

_pool: asyncpg.Pool | None = None

async def init_pool():
    global _pool
    _pool = await asyncpg.create_pool(settings.PG_DSN, min_size=2, max_size=20)

async def close_pool():
    if _pool:
        await _pool.close()

async def pool() -> asyncpg.Pool:
    assert _pool is not None, "pool not initialised"
    return _pool