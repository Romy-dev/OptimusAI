import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_session
from app.core.exceptions import NotFoundError
from app.core.permissions import RequirePermission
from app.models.brand import Brand
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.brand import BrandCreate, BrandResponse, BrandUpdate
from app.schemas.brand_profile import (
    BrandContextResponse,
    BrandProfileResponse,
    BrandProfileUpdate,
    ProductItem,
    ExamplePost,
)
from app.services.brand_service import BrandService

router = APIRouter(prefix="/brands", tags=["brands"])


class BrandRepository(BaseRepository[Brand]):
    model = Brand


def get_brand_repo(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> BrandRepository:
    return BrandRepository(session, tenant_id=user.tenant_id)


@router.get("", response_model=list[BrandResponse])
async def list_brands(
    user: User = Depends(RequirePermission("brands.read")),
    repo: BrandRepository = Depends(get_brand_repo),
):
    brands = await repo.list(limit=50)
    return brands


@router.post("", response_model=BrandResponse, status_code=201)
async def create_brand(
    body: BrandCreate,
    user: User = Depends(RequirePermission("brands.write")),
    repo: BrandRepository = Depends(get_brand_repo),
):
    brand = await repo.create(**body.model_dump())
    return brand


@router.get("/{brand_id}", response_model=BrandResponse)
async def get_brand(
    brand_id: uuid.UUID,
    user: User = Depends(RequirePermission("brands.read")),
    repo: BrandRepository = Depends(get_brand_repo),
):
    brand = await repo.get_by_id(brand_id)
    if not brand:
        raise NotFoundError("Brand not found")
    return brand


@router.put("/{brand_id}", response_model=BrandResponse)
async def update_brand(
    brand_id: uuid.UUID,
    body: BrandUpdate,
    user: User = Depends(RequirePermission("brands.write")),
    repo: BrandRepository = Depends(get_brand_repo),
):
    update_data = body.model_dump(exclude_unset=True)
    brand = await repo.update(brand_id, **update_data)
    if not brand:
        raise NotFoundError("Brand not found")
    return brand


@router.delete("/{brand_id}", status_code=204)
async def delete_brand(
    brand_id: uuid.UUID,
    user: User = Depends(RequirePermission("brands.delete")),
    repo: BrandRepository = Depends(get_brand_repo),
):
    deleted = await repo.delete(brand_id)
    if not deleted:
        raise NotFoundError("Brand not found")


# === Brand Profile endpoints ===


def get_brand_service(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> BrandService:
    return BrandService(session, tenant_id=user.tenant_id)


@router.get("/{brand_id}/profile", response_model=BrandProfileResponse)
async def get_brand_profile(
    brand_id: uuid.UUID,
    user: User = Depends(RequirePermission("brands.read")),
    service: BrandService = Depends(get_brand_service),
):
    profile = await service.profile_repo.get_by_brand_id(brand_id)
    if not profile:
        raise NotFoundError("Brand profile not found. Create one first.")
    return profile


@router.put("/{brand_id}/profile", response_model=BrandProfileResponse)
async def update_brand_profile(
    brand_id: uuid.UUID,
    body: BrandProfileUpdate,
    user: User = Depends(RequirePermission("brands.write")),
    service: BrandService = Depends(get_brand_service),
):
    profile = await service.create_or_update_profile(
        brand_id, **body.model_dump(exclude_unset=True)
    )
    return profile


@router.get("/{brand_id}/context", response_model=BrandContextResponse)
async def get_brand_context(
    brand_id: uuid.UUID,
    channel: str | None = None,
    user: User = Depends(RequirePermission("brands.read")),
    service: BrandService = Depends(get_brand_service),
):
    """Get the full brand context as agents would see it."""
    if channel:
        return await service.get_channel_context(brand_id, channel)
    return await service.get_brand_with_profile(brand_id)


@router.post("/{brand_id}/products", response_model=BrandProfileResponse)
async def add_product(
    brand_id: uuid.UUID,
    body: ProductItem,
    user: User = Depends(RequirePermission("brands.write")),
    service: BrandService = Depends(get_brand_service),
):
    return await service.add_product(brand_id, body.model_dump())


@router.post("/{brand_id}/example-posts", response_model=BrandProfileResponse)
async def add_example_post(
    brand_id: uuid.UUID,
    body: ExamplePost,
    user: User = Depends(RequirePermission("brands.write")),
    service: BrandService = Depends(get_brand_service),
):
    return await service.add_example_post(brand_id, body.model_dump())
