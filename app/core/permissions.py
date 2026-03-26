from fastapi import Depends, HTTPException, status

from app.core.auth import get_current_user
from app.models.user import User, UserRole

# Permission matrix: role -> set of permissions
ROLE_PERMISSIONS: dict[UserRole, set[str]] = {
    UserRole.VIEWER: {
        "brands.read", "posts.read", "knowledge.read", "analytics.read",
        "conversations.read",
    },
    UserRole.SUPPORT_AGENT: {
        "brands.read", "posts.read", "knowledge.read", "analytics.read",
        "conversations.read", "conversations.reply", "escalations.read",
        "escalations.manage",
    },
    UserRole.EDITOR: {
        "brands.read", "brands.write", "posts.read", "posts.create", "posts.update",
        "knowledge.read", "knowledge.write", "analytics.read",
        "campaigns.read", "campaigns.write", "templates.read", "templates.write",
        "conversations.read",
    },
    UserRole.MANAGER: {
        "brands.read", "brands.write", "posts.read", "posts.create", "posts.update",
        "posts.publish", "posts.delete", "knowledge.read", "knowledge.write",
        "analytics.read", "campaigns.read", "campaigns.write", "campaigns.delete",
        "templates.read", "templates.write",
        "approvals.read", "approvals.review",
        "conversations.read", "conversations.reply", "conversations.assign",
        "escalations.read", "escalations.manage",
    },
    UserRole.ADMIN: {
        "brands.read", "brands.write", "brands.delete",
        "posts.read", "posts.create", "posts.update", "posts.publish", "posts.delete",
        "knowledge.read", "knowledge.write", "knowledge.delete",
        "analytics.read", "analytics.export",
        "campaigns.read", "campaigns.write", "campaigns.delete",
        "templates.read", "templates.write", "templates.delete",
        "approvals.read", "approvals.review",
        "conversations.read", "conversations.reply", "conversations.assign",
        "escalations.read", "escalations.manage",
        "social.connect", "social.disconnect",
        "members.read", "members.manage",
        "audit.read",
    },
    UserRole.OWNER: {
        "*",  # All permissions
    },
}


def get_permissions_for_role(role: UserRole) -> set[str]:
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(user: User, permission: str) -> bool:
    if user.is_superadmin:
        return True
    permissions = get_permissions_for_role(user.role)
    return "*" in permissions or permission in permissions


class RequirePermission:
    """FastAPI dependency that checks if the current user has a specific permission."""

    def __init__(self, permission: str):
        self.permission = permission

    async def __call__(self, user: User = Depends(get_current_user)) -> User:
        if not has_permission(user, self.permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {self.permission}",
            )
        return user
