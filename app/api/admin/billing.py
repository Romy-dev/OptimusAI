"""Admin Billing — plan management, subscriptions, MRR tracking."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_session
from app.models.user import User
from app.models.billing import BillingPlan, Subscription, UsageRecord
from app.models.tenant import Tenant

router = APIRouter(prefix="/billing", tags=["admin-billing"])


def _require_superadmin(user: User = Depends(get_current_user)) -> User:
    if not user.is_superadmin:
        from fastapi import HTTPException
        raise HTTPException(403, "Superadmin required")
    return user


@router.get("/plans")
async def list_plans(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(_require_superadmin),
):
    """List all billing plans."""
    result = await session.execute(select(BillingPlan).order_by(BillingPlan.created_at))
    plans = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "price_monthly": p.price_monthly,
            "price_yearly": p.price_yearly,
            "currency": p.currency,
            "features": p.features,
            "limits": p.limits,
            "is_active": p.is_active,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in plans
    ]


@router.get("/subscriptions")
async def list_subscriptions(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(_require_superadmin),
):
    """List all active subscriptions with tenant info."""
    result = await session.execute(
        select(Subscription, Tenant, BillingPlan)
        .join(Tenant, Subscription.tenant_id == Tenant.id)
        .outerjoin(BillingPlan, Subscription.plan_id == BillingPlan.id)
        .order_by(Subscription.created_at.desc())
    )
    rows = result.all()
    return [
        {
            "id": str(sub.id),
            "tenant": {"id": str(tenant.id), "name": tenant.name},
            "plan": {"id": str(plan.id), "name": plan.name} if plan else None,
            "status": sub.status,
            "current_period_start": sub.current_period_start.isoformat() if sub.current_period_start else None,
            "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
            "created_at": sub.created_at.isoformat() if sub.created_at else None,
        }
        for sub, tenant, plan in rows
    ]


@router.get("/mrr")
async def get_mrr(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(_require_superadmin),
):
    """Calculate Monthly Recurring Revenue."""
    result = await session.execute(
        select(
            func.count(Subscription.id).label("total_subscriptions"),
        ).where(Subscription.status == "active")
    )
    row = result.first()

    # Get plan-based revenue
    revenue_result = await session.execute(
        select(
            BillingPlan.name,
            func.count(Subscription.id).label("count"),
            BillingPlan.price_monthly,
        )
        .join(BillingPlan, Subscription.plan_id == BillingPlan.id)
        .where(Subscription.status == "active")
        .group_by(BillingPlan.name, BillingPlan.price_monthly)
    )
    plan_breakdown = [
        {"plan": r.name, "count": r.count, "price": r.price_monthly, "subtotal": r.count * (r.price_monthly or 0)}
        for r in revenue_result.all()
    ]

    total_mrr = sum(p["subtotal"] for p in plan_breakdown)

    return {
        "total_mrr": total_mrr,
        "currency": "XOF",
        "total_subscriptions": row.total_subscriptions if row else 0,
        "plan_breakdown": plan_breakdown,
    }


@router.get("/usage")
async def get_usage_overview(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(_require_superadmin),
):
    """Get aggregated usage across all tenants."""
    result = await session.execute(
        select(
            UsageRecord.feature,
            func.sum(UsageRecord.count).label("total_usage"),
            func.count(func.distinct(UsageRecord.tenant_id)).label("tenant_count"),
        )
        .group_by(UsageRecord.feature)
    )
    return [
        {"feature": r.feature, "total_usage": r.total_usage, "tenant_count": r.tenant_count}
        for r in result.all()
    ]
