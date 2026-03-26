"""Social account management — connect Facebook, Instagram, WhatsApp."""

import uuid
from datetime import datetime, timedelta, timezone

import httpx
import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import get_current_user
from app.core.database import get_session
from app.core.exceptions import InvalidInputError, NotFoundError
from app.core.permissions import RequirePermission
from app.core.security import encrypt_token
from app.models.social_account import SocialAccount, Channel, Platform
from app.models.user import User

logger = structlog.get_logger()

router = APIRouter(prefix="/social-accounts", tags=["social-accounts"])


# ── List connected accounts ──
@router.get("")
async def list_accounts(
    user: User = Depends(RequirePermission("brands.read")),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(SocialAccount)
        .where(SocialAccount.tenant_id == user.tenant_id)
        .order_by(SocialAccount.created_at.desc())
    )
    result = await session.execute(stmt)
    accounts = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "brand_id": str(a.brand_id),
            "platform": a.platform.value,
            "account_name": a.account_name,
            "platform_account_id": a.platform_account_id,
            "is_active": a.is_active,
            "token_expires_at": a.token_expires_at.isoformat() if a.token_expires_at else None,
            "scopes": a.scopes,
            "capabilities": a.capabilities,
            "created_at": a.created_at.isoformat(),
        }
        for a in accounts
    ]


# ── Facebook OAuth — Step 1: Get auth URL ──
@router.get("/facebook/auth-url")
async def facebook_auth_url(
    brand_id: str = Query(...),
    user: User = Depends(RequirePermission("brands.update")),
):
    if not settings.facebook_app_id:
        raise InvalidInputError("Facebook App ID not configured")

    redirect_uri = f"http://localhost:4000/connections/callback/facebook"
    scopes = "pages_show_list,pages_manage_posts,pages_read_engagement,pages_messaging,pages_manage_metadata"

    url = (
        f"https://www.facebook.com/v21.0/dialog/oauth"
        f"?client_id={settings.facebook_app_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={scopes}"
        f"&state={brand_id}"
        f"&response_type=code"
    )
    return {"auth_url": url}


# ── Facebook OAuth — Step 2: Exchange code for token ──
@router.post("/facebook/callback")
async def facebook_callback(
    body: dict,
    user: User = Depends(RequirePermission("brands.update")),
    session: AsyncSession = Depends(get_session),
):
    code = body.get("code")
    brand_id = body.get("brand_id")
    if not code or not brand_id:
        raise InvalidInputError("code and brand_id required")

    redirect_uri = "http://localhost:4000/connections/callback/facebook"

    async with httpx.AsyncClient(timeout=30) as client:
        # Exchange code for short-lived token
        resp = await client.get(
            "https://graph.facebook.com/v21.0/oauth/access_token",
            params={
                "client_id": settings.facebook_app_id,
                "client_secret": settings.facebook_app_secret,
                "redirect_uri": redirect_uri,
                "code": code,
            },
        )
        if resp.status_code != 200:
            raise InvalidInputError(f"Facebook OAuth failed: {resp.text[:200]}")
        token_data = resp.json()
        short_token = token_data["access_token"]

        # Exchange for long-lived token (60 days)
        resp2 = await client.get(
            "https://graph.facebook.com/v21.0/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": settings.facebook_app_id,
                "client_secret": settings.facebook_app_secret,
                "fb_exchange_token": short_token,
            },
        )
        long_token = resp2.json().get("access_token", short_token)
        expires_in = resp2.json().get("expires_in", 5184000)

        # Get user's pages
        resp3 = await client.get(
            "https://graph.facebook.com/v21.0/me/accounts",
            params={"access_token": long_token, "fields": "id,name,access_token,category,picture"},
        )
        pages = resp3.json().get("data", [])

        if not pages:
            raise InvalidInputError("Aucune page Facebook trouvée. Vérifiez vos permissions.")

        # Save each page as a social account
        created = []
        for page in pages:
            # Check if already connected
            exists = await session.execute(
                select(SocialAccount).where(
                    SocialAccount.tenant_id == user.tenant_id,
                    SocialAccount.platform == Platform.FACEBOOK,
                    SocialAccount.platform_account_id == page["id"],
                )
            )
            if exists.scalar_one_or_none():
                continue

            account = SocialAccount(
                tenant_id=user.tenant_id,
                brand_id=uuid.UUID(brand_id),
                platform=Platform.FACEBOOK,
                platform_account_id=page["id"],
                account_name=page["name"],
                access_token_encrypted=encrypt_token(page["access_token"]),
                token_expires_at=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
                is_active=True,
                scopes=["pages_manage_posts", "pages_read_engagement", "pages_messaging"],
                capabilities={
                    "publish": True,
                    "comments": True,
                    "messaging": True,
                    "insights": True,
                },
                metadata_={
                    "category": page.get("category"),
                    "picture": page.get("picture", {}).get("data", {}).get("url"),
                },
            )
            session.add(account)
            created.append(page["name"])

        await session.commit()
        return {"connected": created, "total_pages": len(pages)}


# ── WhatsApp manual config ──
@router.post("/whatsapp/connect")
async def connect_whatsapp(
    body: dict,
    user: User = Depends(RequirePermission("brands.update")),
    session: AsyncSession = Depends(get_session),
):
    phone_number_id = body.get("phone_number_id")
    access_token = body.get("access_token")
    business_name = body.get("business_name", "WhatsApp Business")
    brand_id = body.get("brand_id")

    if not phone_number_id or not access_token or not brand_id:
        raise InvalidInputError("phone_number_id, access_token and brand_id required")

    # Verify token works
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"https://graph.facebook.com/v21.0/{phone_number_id}",
            params={"access_token": access_token, "fields": "display_phone_number,verified_name"},
        )
        if resp.status_code != 200:
            raise InvalidInputError("Token WhatsApp invalide ou phone_number_id incorrect")
        wa_data = resp.json()

    account = SocialAccount(
        tenant_id=user.tenant_id,
        brand_id=uuid.UUID(brand_id),
        platform=Platform.WHATSAPP,
        platform_account_id=phone_number_id,
        account_name=wa_data.get("verified_name", business_name),
        access_token_encrypted=encrypt_token(access_token),
        is_active=True,
        scopes=["whatsapp_business_messaging"],
        capabilities={"messaging": True, "templates": True, "media": True},
        metadata_={
            "phone_number": wa_data.get("display_phone_number"),
            "verified_name": wa_data.get("verified_name"),
        },
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)

    return {
        "id": str(account.id),
        "platform": "whatsapp",
        "account_name": account.account_name,
        "phone_number": wa_data.get("display_phone_number"),
    }


# ── Disconnect / delete account ──
@router.delete("/{account_id}", status_code=204)
async def disconnect_account(
    account_id: uuid.UUID,
    user: User = Depends(RequirePermission("brands.update")),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(SocialAccount).where(
        SocialAccount.tenant_id == user.tenant_id,
        SocialAccount.id == account_id,
    )
    result = await session.execute(stmt)
    account = result.scalar_one_or_none()
    if not account:
        raise NotFoundError("Social account not found")
    await session.delete(account)
    await session.commit()


# ── Toggle active state ──
@router.post("/{account_id}/toggle")
async def toggle_account(
    account_id: uuid.UUID,
    user: User = Depends(RequirePermission("brands.update")),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(SocialAccount).where(
        SocialAccount.tenant_id == user.tenant_id,
        SocialAccount.id == account_id,
    )
    result = await session.execute(stmt)
    account = result.scalar_one_or_none()
    if not account:
        raise NotFoundError("Social account not found")
    account.is_active = not account.is_active
    await session.commit()
    return {"id": str(account.id), "is_active": account.is_active}
