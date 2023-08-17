import asyncio
from clickhouse_driver import Client
from app.common.config import settings


class ClickHousePool:
    def __init__(self, max_connections=5):
        self._semaphore = asyncio.Semaphore(max_connections)
        self._clients = []
        self._host = settings.CLICKHOUSE_HOST
        self._port = settings.CLICKHOUSE_PORT
        self._username = settings.CLICKHOUSE_USERNAME
        self._password = settings.CLICKHOUSE_PASSWORD
        self._database = settings.CLICKHOUSE_DATABASE

        for _ in range(max_connections):
            client = self._create_client()
            self._clients.append(client)

    def _create_client(self):
        connection_settings = {
            "host": self._host,
            "port": self._port,
            "user": self._username,
            "password": self._password,
            "database": self._database,
        }
        if self._port == 9440:
            connection_settings["secure"] = True
            connection_settings["verify"] = False

        return Client(**connection_settings)

    async def execute(self, query, params=None):
        async with self._semaphore:
            client = self._clients.pop()
            try:
                return await asyncio.to_thread(self._execute_sync, client, query, params)
            finally:
                self._clients.append(client)

    def _execute_sync(self, client, query, params):
        return client.execute(query, params)
