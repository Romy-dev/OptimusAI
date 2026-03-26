"""Design DNA service — manages template analysis, DNA merging, and brand visual identity.

Extracted from design_analyzer.py for proper separation of concerns.
"""

import uuid
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.design_template import DesignTemplate, BrandDesignDNA

logger = structlog.get_logger()


class DesignDNAService:
    """Manages Design DNA operations for a brand."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def get_brand_dna(self, brand_id: uuid.UUID) -> dict:
        """Get the merged Design DNA for a brand."""
        stmt = select(BrandDesignDNA).where(
            BrandDesignDNA.tenant_id == self.tenant_id,
            BrandDesignDNA.brand_id == brand_id,
        )
        result = await self.session.execute(stmt)
        dna = result.scalar_one_or_none()
        return dna.merged_dna if dna else {}

    async def get_templates(self, brand_id: uuid.UUID) -> list[DesignTemplate]:
        """Get all completed templates for a brand."""
        stmt = (
            select(DesignTemplate)
            .where(
                DesignTemplate.tenant_id == self.tenant_id,
                DesignTemplate.brand_id == brand_id,
                DesignTemplate.analysis_status == "completed",
            )
            .order_by(DesignTemplate.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_brand_dna(self, brand_id: uuid.UUID) -> dict:
        """Recalculate merged brand DNA from all completed templates."""
        templates = await self.get_templates(brand_id)
        dnas = [t.design_dna for t in templates if t.design_dna]
        weights = [t.weight for t in templates if t.design_dna]

        if not dnas:
            # Delete brand DNA if no templates
            stmt = select(BrandDesignDNA).where(
                BrandDesignDNA.tenant_id == self.tenant_id,
                BrandDesignDNA.brand_id == brand_id,
            )
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                await self.session.delete(existing)
                await self.session.commit()
            return {}

        merged = self.merge_dnas(dnas, weights)

        # Upsert brand DNA
        stmt = select(BrandDesignDNA).where(
            BrandDesignDNA.tenant_id == self.tenant_id,
            BrandDesignDNA.brand_id == brand_id,
        )
        result = await self.session.execute(stmt)
        brand_dna = result.scalar_one_or_none()

        if brand_dna:
            brand_dna.merged_dna = merged
            brand_dna.template_count = len(dnas)
        else:
            brand_dna = BrandDesignDNA(
                tenant_id=self.tenant_id,
                brand_id=brand_id,
                merged_dna=merged,
                template_count=len(dnas),
            )
            self.session.add(brand_dna)

        # Extract useful shortcuts
        brand_dna.preferred_fonts = self._extract_fonts(dnas)
        brand_dna.color_palette = merged.get("colors", {}).get("palette", [])
        brand_dna.layout_preferences = self._extract_layouts(dnas)
        brand_dna.mood_keywords = merged.get("mood_and_style", {}).get("mood_keywords", [])

        await self.session.commit()
        return merged

    @staticmethod
    def merge_dnas(dnas: list[dict], weights: list[float] | None = None) -> dict:
        """Merge multiple Design DNAs into a unified brand DNA."""
        if not dnas:
            return {}
        if len(dnas) == 1:
            return dnas[0]

        if not weights:
            weights = [1.0] * len(dnas)

        merged = {}

        # Layout — pick most common type
        layout_types = [d.get("layout", {}).get("type", "") for d in dnas]
        merged["layout"] = dnas[0].get("layout", {}).copy()
        if layout_types:
            merged["layout"]["preferred_type"] = max(set(layout_types), key=layout_types.count)

        # Typography — pick most common font
        merged["typography"] = dnas[0].get("typography", {}).copy()
        fonts = [d.get("typography", {}).get("headline", {}).get("estimated_font", "") for d in dnas]
        fonts = [f for f in fonts if f]
        if fonts:
            merged["typography"]["preferred_headline_font"] = max(set(fonts), key=fonts.count)

        # Colors — aggregate palette
        all_colors = []
        for dna in dnas:
            palette = dna.get("colors", {}).get("palette", [])
            all_colors.extend(palette)

        color_by_role: dict[str, list[str]] = {}
        for c in all_colors:
            role = c.get("role", "unknown")
            color_by_role.setdefault(role, []).append(c.get("hex", "#000000"))

        merged["colors"] = dnas[0].get("colors", {}).copy()
        merged["colors"]["aggregated_palette"] = {
            role: max(set(hexes), key=hexes.count) for role, hexes in color_by_role.items()
        }

        # Moods
        moods = [d.get("mood_and_style", {}).get("overall_mood", "") for d in dnas]
        moods = [m for m in moods if m]
        merged["mood_and_style"] = dnas[0].get("mood_and_style", {}).copy()
        merged["mood_and_style"]["mood_keywords"] = list(set(moods))

        # Elements, composition, photography — use first as base
        merged["elements"] = dnas[0].get("elements", {}).copy()
        merged["composition"] = dnas[0].get("composition", {}).copy()

        photo_styles = [d.get("photography", {}).get("style", "") for d in dnas]
        photo_styles = [s for s in photo_styles if s]
        merged["photography"] = dnas[0].get("photography", {}).copy()
        if photo_styles:
            merged["photography"]["preferred_styles"] = list(set(photo_styles))

        merged["template_count"] = len(dnas)
        return merged

    @staticmethod
    def _extract_fonts(dnas: list[dict]) -> list[str]:
        return list({
            d.get("typography", {}).get("headline", {}).get("estimated_font", "")
            for d in dnas
            if d.get("typography", {}).get("headline", {}).get("estimated_font")
        })

    @staticmethod
    def _extract_layouts(dnas: list[dict]) -> list[str]:
        return list({
            d.get("layout", {}).get("type", "")
            for d in dnas
            if d.get("layout", {}).get("type")
        })
