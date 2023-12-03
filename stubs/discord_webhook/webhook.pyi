from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from _typeshed import Incomplete

from .webhook_exceptions import ColorNotInRangeException as ColorNotInRangeException

logger: Incomplete

class DiscordEmbed:
    author: Optional[Dict[str, Optional[str]]]
    color: Optional[int]
    description: Optional[str]
    fields: List[Dict[str, Optional[Any]]]
    footer: Optional[Dict[str, Optional[str]]]
    image: Optional[Dict[str, Optional[Union[str, int]]]]
    provider: Optional[Dict[str, Any]]
    thumbnail: Optional[Dict[str, Optional[Union[str, int]]]]
    timestamp: Optional[str]
    title: Optional[str]
    url: Optional[str]
    video: Optional[Dict[str, Optional[Union[str, int]]]]

    def __init__(
        self,
        title: Optional[str] = ...,
        description: Optional[str] = ...,
        **kwargs: Any
    ) -> None: ...
    def set_title(self, title: str) -> None: ...
    def set_description(self, description: str) -> None: ...
    def set_url(self, url: str) -> None: ...
    def set_timestamp(
        self, timestamp: Optional[Union[float, int, datetime]] = ...
    ) -> None: ...
    def set_color(self, color: Union[str, int]) -> None: ...
    def set_footer(self, text: str, **kwargs) -> None: ...  # type: ignore
    def set_image(self, url: str, **kwargs: Union[str, int]) -> None: ...
    def set_thumbnail(self, url: str, **kwargs: Union[str, int]) -> None: ...
    def set_video(self, **kwargs: Union[str, int]) -> None: ...
    def set_provider(self, **kwargs: str) -> None: ...
    def set_author(self, name: str, **kwargs: str) -> None: ...
    def add_embed_field(
        self, name: str, value: str, inline: bool = ...
    ) -> None: ...
    def delete_embed_field(self, index: int) -> None: ...
    def get_embed_fields(self) -> List[Dict[str, Optional[Any]]]: ...

class DiscordWebhook:
    allowed_mentions: List[str]
    attachments: Optional[List[Dict[str, Any]]]
    avatar_url: Optional[str]
    components: Optional[list]
    content: Optional[Union[str, bytes]]
    embeds: List[Dict[str, Any]]
    files: Dict[str, Tuple[Optional[str], Union[bytes, str]]]
    id: Optional[str]
    proxies: Optional[Dict[str, str]]
    rate_limit_retry: bool
    thread_id: Optional[str]
    thread_name: Optional[str]
    timeout: Optional[float]
    tts: Optional[bool]
    url: str
    username: Optional[str]
    wait: Optional[bool]
    def __init__(self, url: str, **kwargs) -> None: ...  # type: ignore
    def add_embed(
        self, embed: Union[DiscordEmbed, Dict[str, Any]]
    ) -> None: ...
    def get_embeds(self) -> List[Dict[str, Any]]: ...
    def remove_embed(self, index: int) -> None: ...
    def remove_embeds(self) -> None: ...
    def add_file(self, file: bytes, filename: str) -> None: ...
    def remove_file(self, filename: str) -> None: ...
    def remove_files(self, clear_attachments: bool = ...) -> None: ...
    def clear_attachments(self) -> None: ...
    def set_proxies(self, proxies: Dict[str, str]) -> None: ...
    def set_content(self, content: str) -> None: ...
    @property
    def json(self) -> Dict[str, Any]: ...
    def api_post_request(self) -> requests.Response: ...
    def handle_rate_limit(self, response, request): ...  # type: ignore
    def execute(self, remove_embeds: bool = ...) -> requests.Response: ...
    def edit(self) -> requests.Response: ...
    def delete(self) -> requests.Response: ...
    @classmethod
    def create_batch(  # type: ignore
        cls, urls: List[str], **kwargs
    ) -> Tuple["DiscordWebhook", ...]: ...
