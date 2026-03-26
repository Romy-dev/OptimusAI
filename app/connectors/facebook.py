"""Facebook Pages connector — publish, comments, insights."""

from datetime import datetime, timezone

import httpx
import structlog

from app.connectors.base import BaseSocialConnector, NormalizedEvent, PublishResult

logger = structlog.get_logger()

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


class FacebookConnector(BaseSocialConnector):
    platform = "facebook"

    def __init__(self, page_id: str, access_token: str):
        self.page_id = page_id
        self.access_token = access_token

    async def publish_post(
        self, content: str, media_urls: list[str] | None = None, **kwargs
    ) -> PublishResult:
        async with httpx.AsyncClient(timeout=60) as client:
            if media_urls:
                # Upload photos first
                photo_ids = []
                for url in media_urls:
                    resp = await client.post(
                        f"{GRAPH_API_BASE}/{self.page_id}/photos",
                        params={"access_token": self.access_token},
                        json={"url": url, "published": False},
                    )
                    if resp.status_code == 200:
                        photo_ids.append(resp.json()["id"])

                payload = {
                    "message": content,
                    "attached_media": [{"media_fbid": pid} for pid in photo_ids],
                }
            else:
                payload = {"message": content}

            # Handle scheduling
            if scheduled_at := kwargs.get("scheduled_at"):
                payload["scheduled_publish_time"] = int(scheduled_at.timestamp())
                payload["published"] = False

            resp = await client.post(
                f"{GRAPH_API_BASE}/{self.page_id}/feed",
                params={"access_token": self.access_token},
                json=payload,
            )
            data = resp.json()

            if "id" in data:
                return PublishResult(
                    success=True,
                    external_id=data["id"],
                    external_url=f"https://facebook.com/{data['id']}",
                    platform="facebook",
                )
            else:
                error_msg = data.get("error", {}).get("message", "Unknown error")
                logger.error("facebook_publish_failed", error=error_msg)
                return PublishResult(
                    success=False,
                    error=error_msg,
                    platform="facebook",
                )

    async def reply_to_comment(self, comment_id: str, content: str) -> PublishResult:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{GRAPH_API_BASE}/{comment_id}/comments",
                params={"access_token": self.access_token},
                json={"message": content},
            )
            data = resp.json()
            if "id" in data:
                return PublishResult(
                    success=True,
                    external_id=data["id"],
                    platform="facebook",
                )
            return PublishResult(
                success=False,
                error=data.get("error", {}).get("message", "Unknown error"),
                platform="facebook",
            )

    async def send_message(
        self, recipient_id: str, content: str,
        content_type: str = "text", media_url: str | None = None,
    ) -> PublishResult:
        """Send via Messenger Send API."""
        message = {"text": content} if content_type == "text" else {"attachment": {"type": content_type, "payload": {"url": media_url}}}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{GRAPH_API_BASE}/{self.page_id}/messages",
                params={"access_token": self.access_token},
                json={
                    "recipient": {"id": recipient_id},
                    "message": message,
                    "messaging_type": "RESPONSE",
                },
            )
            data = resp.json()
            if "message_id" in data:
                return PublishResult(
                    success=True,
                    external_id=data["message_id"],
                    platform="facebook",
                )
            return PublishResult(
                success=False,
                error=data.get("error", {}).get("message", "Unknown error"),
                platform="facebook",
            )

    async def get_post_insights(self, external_post_id: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{GRAPH_API_BASE}/{external_post_id}",
                params={
                    "access_token": self.access_token,
                    "fields": "likes.summary(true),comments.summary(true),shares,insights",
                },
            )
            return resp.json()

    async def verify_token(self) -> bool:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{GRAPH_API_BASE}/{self.page_id}",
                params={"access_token": self.access_token, "fields": "id,name"},
            )
            return resp.status_code == 200 and "id" in resp.json()

    async def refresh_access_token(self) -> str | None:
        """Exchange short-lived token for long-lived one."""
        from app.config import settings
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{GRAPH_API_BASE}/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": settings.facebook_app_id,
                    "client_secret": settings.facebook_app_secret,
                    "fb_exchange_token": self.access_token,
                },
            )
            data = resp.json()
            return data.get("access_token")

    def parse_webhook(self, payload: dict) -> list[NormalizedEvent]:
        events = []
        for entry in payload.get("entry", []):
            # Feed events (comments, posts)
            for change in entry.get("changes", []):
                if change.get("field") == "feed":
                    value = change["value"]
                    if value.get("item") == "comment":
                        events.append(NormalizedEvent(
                            event_type="comment",
                            platform="facebook",
                            account_id=entry["id"],
                            external_id=value.get("comment_id", ""),
                            author_id=value.get("from", {}).get("id"),
                            author_name=value.get("from", {}).get("name"),
                            content=value.get("message"),
                            content_type="text",
                            parent_id=value.get("post_id"),
                            timestamp=datetime.fromtimestamp(
                                value.get("created_time", 0), tz=timezone.utc
                            ),
                            raw_data=value,
                        ))

            # Messaging events (Messenger)
            for messaging in entry.get("messaging", []):
                if "message" in messaging:
                    msg = messaging["message"]
                    events.append(NormalizedEvent(
                        event_type="message",
                        platform="messenger",
                        account_id=entry["id"],
                        external_id=msg.get("mid", ""),
                        author_id=messaging["sender"]["id"],
                        author_name=None,
                        content=msg.get("text"),
                        content_type="text",
                        media_url=None,
                        parent_id=None,
                        timestamp=datetime.fromtimestamp(
                            messaging.get("timestamp", 0) / 1000, tz=timezone.utc
                        ),
                        raw_data=messaging,
                    ))

        return events
