import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class TenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    is_active: bool
    settings: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class TenantSettingsUpdate(BaseModel):
    settings: dict = Field(
        ...,
        examples=[{
            "language": "fr",
            "timezone": "Africa/Ouagadougou",
            "human_in_loop": {
                "require_approval_for_posts": True,
                "auto_reply_comments_threshold": 0.7,
                "auto_reply_messages_threshold": 0.6,
            },
        }],
    )


class MemberInviteRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    role: UserRole = UserRole.EDITOR


class MemberRoleUpdate(BaseModel):
    role: UserRole


class MemberResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
    role: str
    is_active: bool
    avatar_url: str | None
    last_login_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UsageSummaryResponse(BaseModel):
    usage: dict
