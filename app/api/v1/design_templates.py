"""Design templates API — upload reference posters, analyze with VLM, manage Design DNA."""

import uuid

from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_session
from app.core.exceptions import NotFoundError, InvalidInputError
from app.core.permissions import RequirePermission
from app.core.storage import storage_service
from app.models.design_template import DesignTemplate, BrandDesignDNA
from app.models.user import User

router = APIRouter(prefix="/design-templates", tags=["design-templates"])


@router.get("")
async def list_templates(
    brand_id: str | None = None,
    user: User = Depends(RequirePermission("brands.read")),
    session: AsyncSession = Depends(get_session),
):
    """List all design templates for the tenant."""
    stmt = select(DesignTemplate).where(DesignTemplate.tenant_id == user.tenant_id)
    if brand_id:
        stmt = stmt.where(DesignTemplate.brand_id == uuid.UUID(brand_id))
    stmt = stmt.order_by(DesignTemplate.created_at.desc())
    result = await session.execute(stmt)
    templates = result.scalars().all()
    return [
        {
            "id": str(t.id),
            "brand_id": str(t.brand_id),
            "name": t.name,
            "image_url": t.image_url,
            "analysis_status": t.analysis_status,
            "design_dna": t.design_dna,
            "is_primary": t.is_primary,
            "weight": t.weight,
            "created_at": t.created_at.isoformat(),
        }
        for t in templates
    ]


@router.post("/upload")
async def upload_template(
    file: UploadFile = File(...),
    brand_id: str = Form(...),
    name: str = Form(""),
    user: User = Depends(RequirePermission("brands.update")),
    session: AsyncSession = Depends(get_session),
):
    """Upload a reference poster image and trigger VLM analysis."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise InvalidInputError("Le fichier doit etre une image (PNG, JPG, WEBP)")

    # Read file
    image_data = await file.read()
    if len(image_data) > 10 * 1024 * 1024:  # 10MB max
        raise InvalidInputError("Image trop lourde (max 10 Mo)")

    filename = file.filename or "template.png"
    template_name = name or filename.rsplit(".", 1)[0]

    # Upload to S3
    s3_key = await storage_service.upload_file(
        file_data=image_data,
        filename=filename,
        content_type=file.content_type or "image/png",
        folder=f"brands/{brand_id}/templates",
    )
    image_url = storage_service.get_public_url(s3_key)

    # Create template record
    template = DesignTemplate(
        tenant_id=user.tenant_id,
        brand_id=uuid.UUID(brand_id),
        created_by=user.id,
        name=template_name,
        image_url=image_url,
        s3_key=s3_key,
        analysis_status="analyzing",
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)

    # Enqueue VLM analysis via ARQ — persistent, retryable, no data loss
    from app.core.queue import enqueue
    await enqueue(
        "analyze_design_template",
        str(template.id),
        str(user.tenant_id),
        brand_id,
        s3_key,
    )

    # Return immediately — frontend will poll for status
    return {
        "id": str(template.id),
        "name": template.name,
        "image_url": template.image_url,
        "analysis_status": "analyzing",
        "design_dna": {},
    }


@router.get("/{template_id}/status")
async def get_template_status(
    template_id: uuid.UUID,
    user: User = Depends(RequirePermission("brands.read")),
    session: AsyncSession = Depends(get_session),
):
    """Poll template analysis status."""
    stmt = select(DesignTemplate).where(
        DesignTemplate.tenant_id == user.tenant_id,
        DesignTemplate.id == template_id,
    )
    result = await session.execute(stmt)
    template = result.scalar_one_or_none()
    if not template:
        raise NotFoundError("Template not found")
    return {
        "id": str(template.id),
        "analysis_status": template.analysis_status,
        "analysis_error": template.analysis_error,
        "design_dna": template.design_dna,
    }


@router.post("/{template_id}/reanalyze")
async def reanalyze_template(
    template_id: uuid.UUID,
    user: User = Depends(RequirePermission("brands.update")),
    session: AsyncSession = Depends(get_session),
):
    """Re-run VLM analysis on a template."""
    stmt = select(DesignTemplate).where(
        DesignTemplate.tenant_id == user.tenant_id,
        DesignTemplate.id == template_id,
    )
    result = await session.execute(stmt)
    template = result.scalar_one_or_none()
    if not template:
        raise NotFoundError("Template not found")

    template.analysis_status = "analyzing"
    template.analysis_error = None
    await session.commit()

    # Enqueue via ARQ — persistent, retryable
    from app.core.queue import enqueue
    await enqueue(
        "analyze_design_template",
        str(template.id),
        str(user.tenant_id),
        str(template.brand_id),
        template.s3_key,
    )

    return {
        "id": str(template.id),
        "analysis_status": "analyzing",
        "design_dna": template.design_dna,
    }


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: uuid.UUID,
    user: User = Depends(RequirePermission("brands.update")),
    session: AsyncSession = Depends(get_session),
):
    """Delete a template."""
    stmt = select(DesignTemplate).where(
        DesignTemplate.tenant_id == user.tenant_id,
        DesignTemplate.id == template_id,
    )
    result = await session.execute(stmt)
    template = result.scalar_one_or_none()
    if not template:
        raise NotFoundError("Template not found")

    brand_id = template.brand_id
    try:
        await storage_service.delete_file(template.s3_key)
    except Exception:
        pass

    await session.delete(template)
    await session.commit()
    await _update_brand_dna(session, user.tenant_id, brand_id)


@router.get("/brand-dna/{brand_id}")
async def get_brand_dna(
    brand_id: uuid.UUID,
    user: User = Depends(RequirePermission("brands.read")),
    session: AsyncSession = Depends(get_session),
):
    """Get the merged Design DNA for a brand."""
    stmt = select(BrandDesignDNA).where(
        BrandDesignDNA.tenant_id == user.tenant_id,
        BrandDesignDNA.brand_id == brand_id,
    )
    result = await session.execute(stmt)
    dna = result.scalar_one_or_none()
    if not dna:
        return {"brand_id": str(brand_id), "merged_dna": {}, "template_count": 0}

    return {
        "brand_id": str(brand_id),
        "merged_dna": dna.merged_dna,
        "template_count": dna.template_count,
        "preferred_fonts": dna.preferred_fonts,
        "color_palette": dna.color_palette,
        "layout_preferences": dna.layout_preferences,
        "mood_keywords": dna.mood_keywords,
    }


async def _update_brand_dna(session: AsyncSession, tenant_id: uuid.UUID, brand_id: uuid.UUID):
    """Recalculate merged brand DNA from all completed templates."""
    from app.agents.design_analyzer import DesignDNAMerger

    # Get all completed templates for this brand
    stmt = select(DesignTemplate).where(
        DesignTemplate.tenant_id == tenant_id,
        DesignTemplate.brand_id == brand_id,
        DesignTemplate.analysis_status == "completed",
    )
    result = await session.execute(stmt)
    templates = result.scalars().all()

    dnas = [t.design_dna for t in templates if t.design_dna]
    weights = [t.weight for t in templates if t.design_dna]

    if not dnas:
        # Delete brand DNA if no templates
        stmt_del = select(BrandDesignDNA).where(
            BrandDesignDNA.tenant_id == tenant_id,
            BrandDesignDNA.brand_id == brand_id,
        )
        result = await session.execute(stmt_del)
        existing = result.scalar_one_or_none()
        if existing:
            await session.delete(existing)
            await session.commit()
        return

    merged = DesignDNAMerger.merge(dnas, weights)

    # Upsert brand DNA
    stmt_get = select(BrandDesignDNA).where(
        BrandDesignDNA.tenant_id == tenant_id,
        BrandDesignDNA.brand_id == brand_id,
    )
    result = await session.execute(stmt_get)
    brand_dna = result.scalar_one_or_none()

    if brand_dna:
        brand_dna.merged_dna = merged
        brand_dna.template_count = len(dnas)
    else:
        brand_dna = BrandDesignDNA(
            tenant_id=tenant_id,
            brand_id=brand_id,
            merged_dna=merged,
            template_count=len(dnas),
        )
        session.add(brand_dna)

    # Extract useful shortcuts
    brand_dna.preferred_fonts = list({
        d.get("typography", {}).get("headline", {}).get("estimated_font", "")
        for d in dnas if d.get("typography", {}).get("headline", {}).get("estimated_font")
    })
    brand_dna.color_palette = merged.get("colors", {}).get("palette", [])
    brand_dna.layout_preferences = list({
        d.get("layout", {}).get("type", "") for d in dnas if d.get("layout", {}).get("type")
    })
    brand_dna.mood_keywords = merged.get("mood_and_style", {}).get("mood_keywords", [])

    await session.commit()
