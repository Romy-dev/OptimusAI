"""Brand service — manages brand profiles and provides context to agents."""

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.brand import Brand
from app.models.brand_profile import BrandProfile
from app.repositories.base import BaseRepository

logger = structlog.get_logger()


class BrandRepository(BaseRepository[Brand]):
    model = Brand


class BrandProfileRepository(BaseRepository[BrandProfile]):
    model = BrandProfile

    async def get_by_brand_id(self, brand_id: uuid.UUID) -> BrandProfile | None:
        stmt = self._base_query().where(BrandProfile.brand_id == brand_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class BrandService:
    """Business logic for brand management and profile configuration."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id
        self.brand_repo = BrandRepository(session, tenant_id)
        self.profile_repo = BrandProfileRepository(session, tenant_id)

    async def get_brand_with_profile(self, brand_id: uuid.UUID) -> dict:
        """Get brand + its full profile, merged into a single context dict."""
        brand = await self.brand_repo.get_by_id(brand_id)
        if not brand:
            raise NotFoundError("Brand not found")

        profile = await self.profile_repo.get_by_brand_id(brand_id)

        return {
            "brand_name": brand.name,
            "industry": brand.industry,
            "description": brand.description,
            "tone": profile.default_tone if profile else brand.tone,
            "language": profile.primary_language if profile else brand.language,
            "country": brand.target_country,
            "colors": profile.colors if profile else brand.colors,
            "guidelines": brand.guidelines,
            "tone_description": profile.tone_description if profile else None,
            "products": profile.products if profile else [],
            "services": profile.services if profile else [],
            "greeting_style": profile.greeting_style if profile else None,
            "closing_style": profile.closing_style if profile else None,
            "response_rules": profile.response_rules if profile else [],
            "banned_words": profile.banned_words if profile else [],
            "banned_topics": profile.banned_topics if profile else [],
            "sensitive_topics": profile.sensitive_topics if profile else [],
            "example_posts": profile.example_posts if profile else [],
            "example_replies": profile.example_replies if profile else [],
            "business_hours": profile.business_hours if profile else {},
            "contact_info": profile.contact_info if profile else {},
            "image_style": profile.image_style if profile else None,
        }

    async def get_channel_context(
        self, brand_id: uuid.UUID, channel: str
    ) -> dict:
        """Get brand context tailored for a specific channel."""
        base_context = await self.get_brand_with_profile(brand_id)
        profile = await self.profile_repo.get_by_brand_id(brand_id)

        if profile:
            # Override tone for this channel
            channel_tone = profile.tone_by_channel.get(channel)
            if channel_tone:
                base_context["tone"] = channel_tone

            # Add channel-specific settings
            channel_config = profile.channel_profiles.get(channel, {})
            base_context["max_length"] = channel_config.get("max_length", 2000)
            base_context["use_hashtags"] = channel_config.get("use_hashtags", False)
            base_context["use_emojis"] = channel_config.get("use_emojis", True)
            base_context["emoji_level"] = channel_config.get("emoji_level", "moderate")

        return base_context

    async def create_or_update_profile(
        self, brand_id: uuid.UUID, **profile_data
    ) -> BrandProfile:
        """Create or update the brand profile."""
        # Verify brand exists
        brand = await self.brand_repo.get_by_id(brand_id)
        if not brand:
            raise NotFoundError("Brand not found")

        existing = await self.profile_repo.get_by_brand_id(brand_id)
        if existing:
            for key, value in profile_data.items():
                if hasattr(existing, key) and value is not None:
                    setattr(existing, key, value)
            await self.session.flush()
            await self.session.refresh(existing)
            return existing
        else:
            return await self.profile_repo.create(
                brand_id=brand_id,
                **profile_data,
            )

    async def add_product(
        self, brand_id: uuid.UUID, product: dict
    ) -> BrandProfile:
        """Add a product to the brand profile."""
        profile = await self._ensure_profile(brand_id)
        products = list(profile.products)
        products.append(product)
        profile.products = products
        await self.session.flush()
        return profile

    async def add_example_post(
        self, brand_id: uuid.UUID, example: dict
    ) -> BrandProfile:
        """Add an approved example post for AI to learn from."""
        profile = await self._ensure_profile(brand_id)
        examples = list(profile.example_posts)
        examples.append(example)
        profile.example_posts = examples
        await self.session.flush()
        return profile

    async def _ensure_profile(self, brand_id: uuid.UUID) -> BrandProfile:
        """Get or create a brand profile."""
        profile = await self.profile_repo.get_by_brand_id(brand_id)
        if not profile:
            profile = await self.profile_repo.create(brand_id=brand_id)
        return profile
