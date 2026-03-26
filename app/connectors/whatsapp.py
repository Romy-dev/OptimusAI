"""WhatsApp Business Cloud API connector."""

from datetime import datetime, timezone

import httpx
import structlog

from app.connectors.base import BaseSocialConnector, NormalizedEvent, PublishResult

logger = structlog.get_logger()

WHATSAPP_API_BASE = "https://graph.facebook.com/v21.0"


class WhatsAppConnector(BaseSocialConnector):
    platform = "whatsapp"

    def __init__(self, phone_number_id: str, access_token: str):
        self.phone_number_id = phone_number_id
        self.access_token = access_token

    async def publish_post(self, content: str, media_urls=None, **kwargs) -> PublishResult:
        """WhatsApp doesn't support 'posts'. Use send_message instead."""
        return PublishResult(
            success=False,
            error="WhatsApp does not support posts",
            platform="whatsapp",
        )

    async def reply_to_comment(self, comment_id: str, content: str) -> PublishResult:
        """WhatsApp doesn't have comments."""
        return PublishResult(
            success=False,
            error="WhatsApp does not support comments",
            platform="whatsapp",
        )

    async def send_message(
        self, recipient_id: str, content: str,
        content_type: str = "text", media_url: str | None = None,
    ) -> PublishResult:
        """Send a message via WhatsApp Cloud API.

        recipient_id = phone number in international format (e.g., "22670123456")
        """
        if content_type == "text":
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_id,
                "type": "text",
                "text": {"body": content},
            }
        elif content_type == "image" and media_url:
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_id,
                "type": "image",
                "image": {"link": media_url, "caption": content},
            }
        elif content_type == "document" and media_url:
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_id,
                "type": "document",
                "document": {"link": media_url, "caption": content},
            }
        elif content_type == "template":
            # Template messages require pre-approved templates
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_id,
                "type": "template",
                "template": {
                    "name": content,  # template name
                    "language": {"code": "fr"},
                },
            }
        else:
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_id,
                "type": "text",
                "text": {"body": content},
            }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{WHATSAPP_API_BASE}/{self.phone_number_id}/messages",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            data = resp.json()

            if "messages" in data and data["messages"]:
                msg_id = data["messages"][0]["id"]
                return PublishResult(
                    success=True,
                    external_id=msg_id,
                    platform="whatsapp",
                )
            else:
                error = data.get("error", {}).get("message", "Unknown error")
                logger.error("whatsapp_send_failed", error=error, to=recipient_id)
                return PublishResult(
                    success=False,
                    error=error,
                    platform="whatsapp",
                )

    async def send_template_message(
        self,
        recipient_id: str,
        template_name: str,
        language_code: str = "fr",
        components: list[dict] | None = None,
    ) -> PublishResult:
        """Send a pre-approved template message (for business-initiated conversations)."""
        template = {
            "name": template_name,
            "language": {"code": language_code},
        }
        if components:
            template["components"] = components

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": "template",
            "template": template,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{WHATSAPP_API_BASE}/{self.phone_number_id}/messages",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            data = resp.json()

            if "messages" in data:
                return PublishResult(
                    success=True,
                    external_id=data["messages"][0]["id"],
                    platform="whatsapp",
                )
            return PublishResult(
                success=False,
                error=data.get("error", {}).get("message", "Unknown"),
                platform="whatsapp",
            )

    async def get_post_insights(self, external_post_id: str) -> dict:
        return {}  # WhatsApp doesn't have post insights

    async def verify_token(self) -> bool:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{WHATSAPP_API_BASE}/{self.phone_number_id}",
                headers={"Authorization": f"Bearer {self.access_token}"},
                params={"fields": "id,display_phone_number,verified_name"},
            )
            return resp.status_code == 200

    async def refresh_access_token(self) -> str | None:
        return None  # WhatsApp Cloud API tokens don't auto-refresh the same way

    def parse_webhook(self, payload: dict) -> list[NormalizedEvent]:
        events = []
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") != "messages":
                    continue

                value = change["value"]
                metadata = value.get("metadata", {})
                phone_id = metadata.get("phone_number_id", "")

                # Incoming messages
                for msg in value.get("messages", []):
                    content = None
                    content_type = msg.get("type", "text")
                    media_url = None

                    if content_type == "text":
                        content = msg.get("text", {}).get("body")
                    elif content_type in ("image", "video", "audio", "document"):
                        media_data = msg.get(content_type, {})
                        media_url = media_data.get("id")  # Media ID, needs download
                        content = media_data.get("caption")
                    elif content_type == "location":
                        loc = msg.get("location", {})
                        content = f"Location: {loc.get('latitude')}, {loc.get('longitude')}"
                    elif content_type == "interactive":
                        interactive = msg.get("interactive", {})
                        if "button_reply" in interactive:
                            content = interactive["button_reply"].get("title")
                        elif "list_reply" in interactive:
                            content = interactive["list_reply"].get("title")

                    contacts = value.get("contacts", [{}])
                    contact_name = contacts[0].get("profile", {}).get("name") if contacts else None

                    events.append(NormalizedEvent(
                        event_type="message",
                        platform="whatsapp",
                        account_id=phone_id,
                        external_id=msg.get("id", ""),
                        author_id=msg.get("from", ""),
                        author_name=contact_name,
                        content=content,
                        content_type=content_type,
                        media_url=media_url,
                        parent_id=msg.get("context", {}).get("id"),
                        timestamp=datetime.fromtimestamp(
                            int(msg.get("timestamp", 0)), tz=timezone.utc
                        ),
                        raw_data=msg,
                    ))

                # Status updates (sent, delivered, read)
                for status in value.get("statuses", []):
                    events.append(NormalizedEvent(
                        event_type="status_update",
                        platform="whatsapp",
                        account_id=phone_id,
                        external_id=status.get("id", ""),
                        author_id=status.get("recipient_id", ""),
                        content=status.get("status"),  # sent, delivered, read, failed
                        content_type="status",
                        timestamp=datetime.fromtimestamp(
                            int(status.get("timestamp", 0)), tz=timezone.utc
                        ),
                        raw_data=status,
                    ))

        return events
