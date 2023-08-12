import asyncio

from clickhouse_driver import Client

from app.common.config import settings


class ClickHousePool:
    def __init__(self, max_connections=5):
        self._semaphore = asyncio.Semaphore(max_connections)
        self._host = settings.CLICKHOUSE_HOST
        self._port = settings.CLICKHOUSE_PORT
        self._username = settings.CLICKHOUSE_USERNAME
        self._password = settings.CLICKHOUSE_PASSWORD

    async def execute(self, query, params=None):
        async with self._semaphore:
            return await asyncio.to_thread(self._execute_sync, query, params)

    def _execute_sync(self, query, params):
        with Client(
            host=self._host,
            port=self._port,
            username=self._username,
            password=self._password,
        ) as client:
            return client.execute(query, params)
