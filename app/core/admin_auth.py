"""Admin authentication — superadmin access control.

Checks in order:
1. User email in SUPERADMIN_EMAILS env/config
2. User has role "owner" (tenant owners can access admin for their data)
"""

from fastapi import Depends, HTTPException, status

from app.core.auth import get_current_user
from app.config import settings
from app.models.user import User

# Default superadmin emails — override via SUPERADMIN_EMAILS env var
_DEFAULT_SUPERADMINS = {"admin@optimusai.app"}


def _get_superadmin_emails() -> set[str]:
    """Get superadmin emails from settings or env."""
    emails = _DEFAULT_SUPERADMINS.copy()
    # Add from env if configured
    raw = getattr(settings, "superadmin_emails", "")
    if raw:
        emails.update(e.strip() for e in raw.split(",") if e.strip())
    return emails


async def require_superadmin(user: User = Depends(get_current_user)) -> User:
    """Dependency that ensures the user is a superadmin or owner."""
    superadmins = _get_superadmin_emails()

    if user.email in superadmins:
        return user

    # Owners can access admin panel (they see only their tenant data)
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    if role == "owner":
        return user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Acces administrateur requis",
    )
