import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant


class TenantRepository:
    """Tenant repo — no tenant isolation filter (it IS the tenant)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: uuid.UUID) -> Tenant | None:
        stmt = select(Tenant).where(Tenant.id == id, Tenant.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Tenant | None:
        stmt = select(Tenant).where(Tenant.slug == slug, Tenant.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> Tenant:
        tenant = Tenant(**kwargs)
        self.session.add(tenant)
        await self.session.flush()
        await self.session.refresh(tenant)
        return tenant

    async def update(self, id: uuid.UUID, **kwargs) -> Tenant | None:
        tenant = await self.get_by_id(id)
        if tenant is None:
            return None
        for key, value in kwargs.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)
        await self.session.flush()
        await self.session.refresh(tenant)
        return tenant
