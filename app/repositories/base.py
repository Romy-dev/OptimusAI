import uuid
from typing import Generic, TypeVar

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Generic repository with automatic tenant isolation."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    def _base_query(self):
        """Base query with tenant filter."""
        return select(self.model).where(self.model.tenant_id == self.tenant_id)

    async def get_by_id(self, id: uuid.UUID) -> ModelT | None:
        stmt = self._base_query().where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        order_by: str = "created_at",
        desc: bool = True,
        **filters,
    ) -> list[ModelT]:
        stmt = self._base_query()

        for key, value in filters.items():
            if value is not None and hasattr(self.model, key):
                stmt = stmt.where(getattr(self.model, key) == value)

        col = getattr(self.model, order_by, self.model.created_at)
        stmt = stmt.order_by(col.desc() if desc else col.asc())
        stmt = stmt.offset(offset).limit(limit + 1)  # +1 for has_more check

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, **filters) -> int:
        stmt = select(func.count()).select_from(self.model).where(
            self.model.tenant_id == self.tenant_id
        )
        for key, value in filters.items():
            if value is not None and hasattr(self.model, key):
                stmt = stmt.where(getattr(self.model, key) == value)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def create(self, **kwargs) -> ModelT:
        kwargs["tenant_id"] = self.tenant_id
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, id: uuid.UUID, **kwargs) -> ModelT | None:
        instance = await self.get_by_id(id)
        if instance is None:
            return None
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, id: uuid.UUID) -> bool:
        instance = await self.get_by_id(id)
        if instance is None:
            return False
        await self.session.delete(instance)
        await self.session.flush()
        return True
