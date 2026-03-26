"""Quota enforcement service — checks and tracks usage against plan limits."""

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import QuotaExceededError
from app.models.billing import BillingPlan, Subscription, UsageRecord

logger = structlog.get_logger()

# Default limits for the free/trial tier
DEFAULT_LIMITS = {
    "max_brands": 1,
    "max_social_accounts": 3,
    "max_posts_per_month": 20,
    "max_ai_generations": 50,
    "max_support_conversations": 200,
    "max_documents": 5,
    "max_storage_mb": 500,
    "max_users": 2,
    "max_whatsapp_messages": 50,
}


class QuotaService:
    """Checks tenant usage against their plan limits."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_tenant_limits(self, tenant_id: uuid.UUID) -> dict:
        """Get the plan limits for a tenant."""
        stmt = (
            select(BillingPlan.limits)
            .join(Subscription, Subscription.plan_id == BillingPlan.id)
            .where(
                Subscription.tenant_id == tenant_id,
                Subscription.status.in_(["active", "trial"]),
            )
        )
        result = await self.session.execute(stmt)
        limits = result.scalar_one_or_none()
        return limits or DEFAULT_LIMITS

    async def get_current_usage(self, tenant_id: uuid.UUID, metric: str) -> int:
        """Get current month's usage for a specific metric."""
        now = datetime.now(timezone.utc)
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        stmt = select(func.coalesce(func.sum(UsageRecord.quantity), 0)).where(
            UsageRecord.tenant_id == tenant_id,
            UsageRecord.metric == metric,
            UsageRecord.period_start >= period_start,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def check_quota(self, tenant_id: uuid.UUID, metric: str) -> bool:
        """Check if the tenant is within their quota. Returns True if OK."""
        limits = await self.get_tenant_limits(tenant_id)
        limit_key = f"max_{metric}"
        limit_value = limits.get(limit_key)

        if limit_value is None:
            return True  # No limit defined = unlimited

        current = await self.get_current_usage(tenant_id, metric)
        return current < limit_value

    async def enforce_quota(self, tenant_id: uuid.UUID, metric: str) -> None:
        """Check quota and raise QuotaExceededError if exceeded."""
        if not await self.check_quota(tenant_id, metric):
            limits = await self.get_tenant_limits(tenant_id)
            limit_value = limits.get(f"max_{metric}", 0)
            raise QuotaExceededError(
                message=f"Quota exceeded for {metric}. Limit: {limit_value}",
                details={"metric": metric, "limit": limit_value},
            )

    async def record_usage(
        self,
        tenant_id: uuid.UUID,
        metric: str,
        quantity: int = 1,
    ) -> None:
        """Record usage for the current billing period."""
        now = datetime.now(timezone.utc)
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Approximate period end as start of next month
        if period_start.month == 12:
            period_end = period_start.replace(year=period_start.year + 1, month=1)
        else:
            period_end = period_start.replace(month=period_start.month + 1)

        record = UsageRecord(
            tenant_id=tenant_id,
            metric=metric,
            quantity=quantity,
            period_start=period_start,
            period_end=period_end,
        )
        self.session.add(record)
        await self.session.flush()

        logger.info(
            "usage_recorded",
            tenant_id=str(tenant_id),
            metric=metric,
            quantity=quantity,
        )

    async def get_usage_summary(self, tenant_id: uuid.UUID) -> dict:
        """Get full usage summary vs limits for the tenant dashboard."""
        limits = await self.get_tenant_limits(tenant_id)
        summary = {}

        for limit_key, limit_value in limits.items():
            metric = limit_key.replace("max_", "")
            current = await self.get_current_usage(tenant_id, metric)
            summary[metric] = {
                "used": current,
                "limit": limit_value,
                "remaining": max(0, limit_value - current),
                "percentage": round((current / limit_value * 100), 1) if limit_value else 0,
            }

        return summary
