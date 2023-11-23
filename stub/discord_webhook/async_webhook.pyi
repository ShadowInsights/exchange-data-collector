from typing import Any

import httpx

from . import DiscordWebhook as DiscordWebhook

logger: Any

class AsyncDiscordWebhook(DiscordWebhook):
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
    @property
    async def http_client(self) -> httpx.AsyncClient: ...
    async def api_post_request(self) -> httpx.Response: ...  # type: ignore
    async def handle_rate_limit(
        self, response: Any, request: Any
    ) -> httpx.Response: ...

    id: Any

    async def execute(self, remove_embeds: bool = ...) -> httpx.Response: ...  # type: ignore
    async def edit(self) -> httpx.Response: ...  # type: ignore
    async def delete(self) -> httpx.Response: ...  # type: ignore
