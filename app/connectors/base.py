"""Base social connector interface."""

from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel


class NormalizedEvent(BaseModel):
    """Normalized event from any social platform."""

    event_type: str  # "message", "comment", "reaction", "status_update"
    platform: str
    account_id: str
    external_id: str
    author_id: str | None = None
    author_name: str | None = None
    content: str | None = None
    content_type: str = "text"
    media_url: str | None = None
    parent_id: str | None = None
    timestamp: datetime
    raw_data: dict


class PublishResult(BaseModel):
    """Result of publishing to a social platform."""

    success: bool
    external_id: str | None = None
    external_url: str | None = None
    error: str | None = None
    platform: str


class BaseSocialConnector(ABC):
    """Abstract base for all social platform connectors."""

    platform: str

    @abstractmethod
    async def publish_post(
        self,
        content: str,
        media_urls: list[str] | None = None,
        **kwargs,
    ) -> PublishResult:
        ...

    @abstractmethod
    async def reply_to_comment(
        self,
        comment_id: str,
        content: str,
    ) -> PublishResult:
        ...

    @abstractmethod
    async def send_message(
        self,
        recipient_id: str,
        content: str,
        content_type: str = "text",
        media_url: str | None = None,
    ) -> PublishResult:
        ...

    @abstractmethod
    async def get_post_insights(self, external_post_id: str) -> dict:
        ...

    @abstractmethod
    async def verify_token(self) -> bool:
        ...

    @abstractmethod
    async def refresh_access_token(self) -> str | None:
        ...

    @abstractmethod
    def parse_webhook(self, payload: dict) -> list[NormalizedEvent]:
        ...
