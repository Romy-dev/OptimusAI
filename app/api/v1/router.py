from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.tenants import router as tenants_router
from app.api.v1.brands import router as brands_router
from app.api.v1.posts import router as posts_router
from app.api.v1.approvals import router as approvals_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.webhooks import router as webhooks_router
from app.api.v1.gallery import router as gallery_router
from app.api.v1.social_accounts import router as social_accounts_router
from app.api.v1.intelligence import router as intelligence_router
from app.api.v1.design_templates import router as design_templates_router
from app.api.v1.chat import router as chat_router
from app.api.v1.coach import router as coach_router
from app.api.v1.stories import router as stories_router
from app.api.v1.commerce import router as commerce_router
from app.api.v1.roi import router as roi_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(tenants_router)
api_v1_router.include_router(brands_router)
api_v1_router.include_router(posts_router)
api_v1_router.include_router(approvals_router)
api_v1_router.include_router(conversations_router)
api_v1_router.include_router(knowledge_router)
api_v1_router.include_router(webhooks_router)
api_v1_router.include_router(gallery_router)
api_v1_router.include_router(social_accounts_router)
api_v1_router.include_router(intelligence_router)
api_v1_router.include_router(design_templates_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(coach_router)
api_v1_router.include_router(stories_router)
api_v1_router.include_router(commerce_router)
api_v1_router.include_router(roi_router)

# Future routers:
# from app.api.v1.social_accounts import router as social_accounts_router
# from app.api.v1.campaigns import router as campaigns_router
# from app.api.v1.analytics import router as analytics_router
# from app.api.v1.billing import router as billing_router
# from app.api.v1.audit import router as audit_router
# from app.api.v1.admin import router as admin_router
