from contextlib import asynccontextmanager
from typing import AsyncIterator

import asyncpg


class Database:
    def __init__(self, url: str, min_size: int = 2, max_size: int = 20) -> None:
        self._url = url
        self._min_size = min_size
        self._max_size = max_size
        self._pool: asyncpg.Pool | None = None

    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Database has not been started")
        return self._pool

    async def start(self) -> None:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                dsn=self._url,
                min_size=self._min_size,
                max_size=self._max_size,
                command_timeout=60,
            )

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def health_check(self) -> bool:
        try:
            return bool(await self.pool.fetchval("SELECT 1"))
        except (asyncpg.PostgresError, OSError, RuntimeError):
            return False

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[asyncpg.Connection]:
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                yield connection

