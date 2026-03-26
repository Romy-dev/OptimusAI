"""Admin agents monitoring — performance, logs, costs."""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_auth import require_superadmin
from app.core.database import get_session
from app.models.user import User
from app.models.agent_run import AgentRun

router = APIRouter(prefix="/agents")


@router.get("/stats")
async def agent_stats(
    user: User = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Get aggregated stats for all agents."""
    # Agent runs by name
    rows = await session.execute(
        select(
            AgentRun.agent_name,
            func.count().label("total_runs"),
            func.avg(AgentRun.execution_time_ms).label("avg_latency_ms"),
            func.sum(AgentRun.tokens_used).label("total_tokens"),
        )
        .group_by(AgentRun.agent_name)
        .order_by(func.count().desc())
    )

    agents = []
    for row in rows:
        agents.append({
            "agent_name": row.agent_name,
            "total_runs": row.total_runs,
            "avg_latency_ms": round(float(row.avg_latency_ms or 0), 1),
            "total_tokens": int(row.total_tokens or 0),
        })

    return {"agents": agents}


@router.get("/recent")
async def recent_agent_runs(
    limit: int = 50,
    agent_name: str | None = None,
    user: User = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Get recent agent executions."""
    stmt = select(AgentRun).order_by(AgentRun.created_at.desc()).limit(limit)
    if agent_name:
        stmt = stmt.where(AgentRun.agent_name == agent_name)

    result = await session.execute(stmt)
    runs = result.scalars().all()

    return [
        {
            "id": str(r.id),
            "agent_name": r.agent_name,
            "tenant_id": str(r.tenant_id) if r.tenant_id else None,
            "success": r.success,
            "confidence_score": r.confidence_score,
            "execution_time_ms": r.execution_time_ms,
            "tokens_used": r.tokens_used,
            "model_used": r.model_used,
            "error": r.error_message,
            "created_at": r.created_at.isoformat(),
        }
        for r in runs
    ]


@router.get("/registry")
async def agent_registry(
    user: User = Depends(require_superadmin),
):
    """List all registered agents and their config."""
    from app.agents.registry import create_agent_registry

    registry = create_agent_registry()
    return [
        {
            "name": agent.name,
            "description": agent.description,
            "max_retries": agent.max_retries,
            "confidence_threshold": agent.confidence_threshold,
        }
        for agent in registry.values()
    ]
