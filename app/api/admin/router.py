"""Admin API — superadmin-only endpoints for platform management."""

from fastapi import APIRouter

from app.api.admin.overview import router as overview_router
from app.api.admin.tenants import router as tenants_router
from app.api.admin.users import router as users_router
from app.api.admin.agents import router as agents_router
from app.api.admin.moderation import router as moderation_router
from app.api.admin.content import router as content_router
from app.api.admin.audit import router as audit_router
from app.api.admin.config import router as config_router
from app.api.admin.system import router as system_router
from app.api.admin.billing import router as billing_router
from app.api.admin.notifications import router as notifications_router
from app.api.admin.feature_flags import router as feature_flags_router

admin_router = APIRouter(prefix="/admin", tags=["admin"])
admin_router.include_router(overview_router)
admin_router.include_router(tenants_router)
admin_router.include_router(users_router)
admin_router.include_router(agents_router)
admin_router.include_router(moderation_router)
admin_router.include_router(content_router)
admin_router.include_router(audit_router)
admin_router.include_router(config_router)
admin_router.include_router(system_router)
admin_router.include_router(billing_router)
admin_router.include_router(notifications_router)
admin_router.include_router(feature_flags_router)
