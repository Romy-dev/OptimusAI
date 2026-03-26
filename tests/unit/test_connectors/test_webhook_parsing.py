"""Tests for webhook payload parsing across connectors."""

import pytest

from app.connectors.facebook import FacebookConnector
from app.connectors.whatsapp import WhatsAppConnector


class TestFacebookWebhookParsing:
    @pytest.fixture
    def connector(self):
        return FacebookConnector(page_id="123", access_token="fake")

    def test_parses_comment_event(self, connector):
        payload = {
            "entry": [{
                "id": "page_123",
                "changes": [{
                    "field": "feed",
                    "value": {
                        "item": "comment",
                        "comment_id": "comment_456",
                        "from": {"id": "user_789", "name": "Amadou"},
                        "message": "Combien ça coûte ?",
                        "post_id": "post_012",
                        "created_time": 1700000000,
                    },
                }],
            }],
        }
        events = connector.parse_webhook(payload)
        assert len(events) == 1
        assert events[0].event_type == "comment"
        assert events[0].platform == "facebook"
        assert events[0].content == "Combien ça coûte ?"
        assert events[0].author_name == "Amadou"
        assert events[0].parent_id == "post_012"

    def test_parses_messenger_event(self, connector):
        payload = {
            "entry": [{
                "id": "page_123",
                "messaging": [{
                    "sender": {"id": "user_789"},
                    "timestamp": 1700000000000,
                    "message": {
                        "mid": "msg_456",
                        "text": "Bonjour, je voudrais commander",
                    },
                }],
            }],
        }
        events = connector.parse_webhook(payload)
        assert len(events) == 1
        assert events[0].event_type == "message"
        assert events[0].platform == "messenger"
        assert events[0].content == "Bonjour, je voudrais commander"

    def test_returns_empty_for_unknown_event(self, connector):
        payload = {"entry": [{"id": "page_123", "changes": [{"field": "unknown"}]}]}
        events = connector.parse_webhook(payload)
        assert len(events) == 0


class TestWhatsAppWebhookParsing:
    @pytest.fixture
    def connector(self):
        return WhatsAppConnector(phone_number_id="123", access_token="fake")

    def test_parses_text_message(self, connector):
        payload = {
            "entry": [{
                "changes": [{
                    "field": "messages",
                    "value": {
                        "metadata": {"phone_number_id": "phone_123"},
                        "contacts": [{"profile": {"name": "Fatou"}}],
                        "messages": [{
                            "id": "wamid_456",
                            "from": "22670123456",
                            "type": "text",
                            "text": {"body": "Combien coûte le wax n°5?"},
                            "timestamp": "1700000000",
                        }],
                    },
                }],
            }],
        }
        events = connector.parse_webhook(payload)
        assert len(events) == 1
        assert events[0].event_type == "message"
        assert events[0].platform == "whatsapp"
        assert events[0].content == "Combien coûte le wax n°5?"
        assert events[0].author_name == "Fatou"
        assert events[0].author_id == "22670123456"

    def test_parses_image_message(self, connector):
        payload = {
            "entry": [{
                "changes": [{
                    "field": "messages",
                    "value": {
                        "metadata": {"phone_number_id": "phone_123"},
                        "contacts": [{"profile": {"name": "Ali"}}],
                        "messages": [{
                            "id": "wamid_789",
                            "from": "22670999999",
                            "type": "image",
                            "image": {"id": "media_123", "caption": "Voici le modèle"},
                            "timestamp": "1700000000",
                        }],
                    },
                }],
            }],
        }
        events = connector.parse_webhook(payload)
        assert len(events) == 1
        assert events[0].content_type == "image"
        assert events[0].content == "Voici le modèle"
        assert events[0].media_url == "media_123"

    def test_parses_status_update(self, connector):
        payload = {
            "entry": [{
                "changes": [{
                    "field": "messages",
                    "value": {
                        "metadata": {"phone_number_id": "phone_123"},
                        "statuses": [{
                            "id": "wamid_456",
                            "status": "delivered",
                            "timestamp": "1700000000",
                            "recipient_id": "22670123456",
                        }],
                    },
                }],
            }],
        }
        events = connector.parse_webhook(payload)
        assert len(events) == 1
        assert events[0].event_type == "status_update"
        assert events[0].content == "delivered"

    def test_returns_empty_for_non_messages_field(self, connector):
        payload = {
            "entry": [{
                "changes": [{"field": "account_update", "value": {}}],
            }],
        }
        events = connector.parse_webhook(payload)
        assert len(events) == 0
