"""ARQ worker for Design Template VLM analysis.

Replaces asyncio.create_task with persistent, retryable ARQ job.
On completion, notifies the frontend via WebSocket.
"""

import uuid

import structlog
from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.storage import storage_service
from app.models.design_template import DesignTemplate

logger = structlog.get_logger()


async def analyze_design_template(
    ctx: dict,
    template_id: str,
    tenant_id: str,
    brand_id: str,
    s3_key: str,
) -> dict:
    """ARQ job: download image from S3, run VLM analysis, update DB, notify via WS."""

    template_uuid = uuid.UUID(template_id)
    tenant_uuid = uuid.UUID(tenant_id)
    brand_uuid = uuid.UUID(brand_id)

    logger.info("design_analysis_started", template_id=template_id)

    async with async_session_factory() as session:
        # Fetch template
        stmt = select(DesignTemplate).where(DesignTemplate.id == template_uuid)
        result = await session.execute(stmt)
        tpl = result.scalar_one_or_none()

        if not tpl:
            logger.error("design_analysis_template_not_found", template_id=template_id)
            return {"success": False, "error": "Template not found"}

        try:
            # Download image from S3
            image_data = await storage_service.download_file(s3_key)
            logger.info("design_analysis_image_downloaded", size=len(image_data))

            # Run VLM analysis
            from app.agents.design_analyzer import DesignAnalyzerAgent
            analyzer = DesignAnalyzerAgent()
            analysis = await analyzer.run({"image_data": image_data})

            if analysis.success:
                tpl.design_dna = analysis.output["design_dna"]
                tpl.analysis_status = "completed"
                tpl.analysis_error = None
                await session.commit()

                # Update merged brand DNA
                from app.api.v1.design_templates import _update_brand_dna
                await _update_brand_dna(session, tenant_uuid, brand_uuid)

                logger.info("design_analysis_completed", template_id=template_id)

                # Notify frontend via WebSocket
                try:
                    from app.core.websocket import notify
                    await notify(
                        tenant_id=tenant_id,
                        event_type="design_analysis_complete",
                        data={
                            "template_id": template_id,
                            "status": "completed",
                            "message": f"Analyse Design DNA terminee",
                        },
                    )
                except Exception:
                    pass  # WS notification is best-effort

                return {"success": True, "template_id": template_id}

            else:
                tpl.analysis_status = "failed"
                tpl.analysis_error = analysis.output.get("error", "Analysis failed")[:500]
                await session.commit()

                logger.error("design_analysis_failed", template_id=template_id, error=tpl.analysis_error)

                try:
                    from app.core.websocket import notify
                    await notify(
                        tenant_id=tenant_id,
                        event_type="design_analysis_complete",
                        data={
                            "template_id": template_id,
                            "status": "failed",
                            "message": tpl.analysis_error,
                        },
                    )
                except Exception:
                    pass

                return {"success": False, "error": tpl.analysis_error}

        except Exception as e:
            tpl.analysis_status = "failed"
            tpl.analysis_error = str(e)[:500]
            await session.commit()
            logger.error("design_analysis_exception", template_id=template_id, error=str(e))
            return {"success": False, "error": str(e)[:200]}
