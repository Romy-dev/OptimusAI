"""Webhook handlers for social platform events.

These endpoints MUST return 200 quickly (< 5s).
Actual processing is queued for async workers.
"""

import hashlib
import hmac

import structlog
from fastapi import APIRouter, HTTPException, Query, Request

from app.config import settings
from app.core.queue import enqueue

logger = structlog.get_logger()
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("/facebook")
async def facebook_webhook_verify(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    """Facebook webhook verification (GET challenge)."""
    if hub_mode == "subscribe" and hub_verify_token == settings.facebook_webhook_verify_token:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/facebook")
async def facebook_webhook_receive(request: Request):
    """Receive Facebook/Instagram/Messenger webhook events."""
    # Verify signature
    signature = request.headers.get("x-hub-signature-256", "")
    body = await request.body()

    if settings.facebook_app_secret:
        expected = "sha256=" + hmac.new(
            settings.facebook_app_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected):
            raise HTTPException(status_code=403, detail="Invalid signature")

    payload = await request.json()
    await enqueue("process_facebook_webhook", payload)

    return {"status": "ok"}


@router.get("/whatsapp")
async def whatsapp_webhook_verify(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    """WhatsApp webhook verification."""
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_webhook_verify_token:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp")
async def whatsapp_webhook_receive(request: Request):
    """Receive WhatsApp webhook events."""
    payload = await request.json()
    await enqueue("process_whatsapp_webhook", payload)

    return {"status": "ok"}
