"""Concierge Agent — conversational AI assistant that understands and EXECUTES actions.

The user talks naturally, the Concierge:
1. Understands the intent (NLU via LLM)
2. Executes the action (calls services/agents directly)
3. Returns a natural response + action buttons
"""

import json
import uuid
from datetime import datetime, timezone

import structlog

from app.agents.base import AgentResult, BaseAgent

logger = structlog.get_logger()

def _get_prompts():
    """Lazy-load prompt manager to avoid circular imports."""
    from app.prompts.loader import get_prompt_manager
    return get_prompt_manager()


class ConciergeAgent(BaseAgent):
    name = "concierge"
    description = "Conversational AI assistant that understands and executes user actions"
    max_retries = 1
    confidence_threshold = 0.3

    async def execute(self, context: dict) -> AgentResult:
        from app.integrations.llm import get_llm_router

        user_message = context.get("user_message", "")
        user_name = context.get("user_name", "")
        user_role = context.get("user_role", "owner")
        tenant_name = context.get("tenant_name", "")
        brand_info = context.get("brand_info", "Aucune marque configuree")
        language = context.get("language", "francais")
        history = context.get("history", [])

        # Format history
        history_text = ""
        if history:
            lines = []
            for msg in history[-10:]:
                role = "User" if msg.get("role") == "user" else "Optimus"
                lines.append(f"{role}: {msg.get('content', '')}")
            history_text = "\n".join(lines)

        pm = _get_prompts()
        system = pm.get_prompt(
            "concierge", "system",
            language=language,
            user_name=user_name,
            user_role=user_role,
            tenant_name=tenant_name,
            brand_info=brand_info,
        )

        user_prompt = pm.get_prompt(
            "concierge", "user",
            history=history_text or "Pas d'historique",
            user_message=user_message,
        )

        llm = get_llm_router()
        response = await llm.generate(
            task_type="support",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
        )

        # Parse response
        from app.agents.output_parser import parse_llm_output
        from pydantic import BaseModel, Field

        class ConciergeOutput(BaseModel):
            message: str = ""
            action: str | None = None
            action_params: dict = Field(default_factory=dict)
            buttons: list[dict] = Field(default_factory=list)
            needs_confirmation: bool = False
            follow_up_question: str | None = None

        parsed = parse_llm_output(response.content, ConciergeOutput)

        # Execute action if specified and not needing confirmation
        action_result = None
        if parsed.action and not parsed.needs_confirmation:
            action_result = await self._execute_action(
                parsed.action, parsed.action_params, context
            )

        return AgentResult(
            success=True,
            output={
                "message": parsed.message,
                "action": parsed.action,
                "action_params": parsed.action_params,
                "action_result": action_result,
                "buttons": parsed.buttons,
                "needs_confirmation": parsed.needs_confirmation,
                "follow_up_question": parsed.follow_up_question,
            },
            confidence_score=0.9,
            agent_name=self.name,
        )

    async def _execute_action(self, action: str, params: dict, context: dict) -> dict | None:
        """Execute an action via internal services."""
        tenant_id = context.get("tenant_id")
        user_id = context.get("user_id")
        brand_id = context.get("brand_id")

        if not tenant_id:
            return {"error": "No tenant context"}

        try:
            if action == "create_post":
                return await self._action_create_post(params, tenant_id, user_id, brand_id)
            elif action == "create_poster":
                return await self._action_create_poster(params, tenant_id, brand_id)
            elif action == "generate_image":
                return await self._action_generate_image(params, tenant_id, brand_id)
            elif action == "get_analytics":
                return await self._action_analytics(params, tenant_id)
            elif action == "get_strategy":
                return await self._action_strategy(params, tenant_id, brand_id)
            elif action == "best_time":
                return await self._action_best_time(params)
            elif action in ("explain", "help", "chat"):
                return None  # No action to execute, just a response
            else:
                logger.info("concierge_unknown_action", action=action)
                return None
        except Exception as e:
            logger.error("concierge_action_failed", action=action, error=str(e))
            return {"error": str(e)[:200]}

    async def _action_create_post(self, params: dict, tenant_id: str, user_id: str, brand_id: str) -> dict:
        from app.agents.registry import get_orchestrator
        orchestrator = get_orchestrator()
        result = await orchestrator.execute({
            "task_type": "generate_post",
            "brand_id": brand_id,
            "brief": params.get("brief", ""),
            "channel": params.get("channel", "facebook"),
            "language": params.get("language", "fr"),
            "tenant_id": tenant_id,
            "user_id": user_id,
        })
        if result.success:
            return {"status": "created", "content_preview": result.output.get("content", "")[:100]}
        return {"error": result.output.get("error", "Generation failed")}

    async def _action_create_poster(self, params: dict, tenant_id: str, brand_id: str) -> dict:
        from app.agents.registry import get_orchestrator
        orchestrator = get_orchestrator()
        result = await orchestrator.execute({
            "task_type": "generate_poster",
            "brief": params.get("brief", ""),
            "brand_id": brand_id,
            "tenant_id": tenant_id,
        })
        if result.success:
            return {"status": "created", "image_url": result.output.get("image_url")}
        return {"error": result.output.get("error", "Poster generation failed")}

    async def _action_generate_image(self, params: dict, tenant_id: str, brand_id: str) -> dict:
        from app.agents.registry import get_orchestrator
        orchestrator = get_orchestrator()
        result = await orchestrator.execute({
            "task_type": "generate_image",
            "media_suggestion": params.get("description", params.get("brief", "")),
            "brand_id": brand_id,
            "tenant_id": tenant_id,
        })
        if result.success:
            return {"status": "created", "image_url": result.output.get("image_url")}
        return {"error": result.output.get("error", "Image generation failed")}

    async def _action_analytics(self, params: dict, tenant_id: str) -> dict:
        from app.agents.registry import get_orchestrator
        orchestrator = get_orchestrator()
        result = await orchestrator.execute({
            "task_type": "analyze_performance",
            "report_type": params.get("report_type", "weekly"),
            "tenant_id": tenant_id,
        })
        if result.success:
            return {"status": "ok", "report": result.output.get("report_text", "")}
        return {"error": "Analytics failed"}

    async def _action_strategy(self, params: dict, tenant_id: str, brand_id: str) -> dict:
        from app.agents.registry import get_orchestrator
        orchestrator = get_orchestrator()
        result = await orchestrator.execute({
            "task_type": "content_strategy",
            "brand_id": brand_id,
            "tenant_id": tenant_id,
            "period": params.get("period", "week"),
        })
        if result.success:
            return {"status": "ok", "calendar": result.output.get("calendar", [])}
        return {"error": "Strategy failed"}

    async def _action_best_time(self, params: dict) -> dict:
        from app.agents.registry import get_orchestrator
        orchestrator = get_orchestrator()
        result = await orchestrator.execute({
            "task_type": "optimize_timing",
            "platform": params.get("platform", "facebook"),
            "target_country": params.get("country", "BF"),
            "content_type": params.get("content_type", "engagement"),
        })
        if result.success:
            return {
                "status": "ok",
                "time": result.output.get("recommended_time"),
                "day": result.output.get("recommended_day"),
            }
        return {"error": "Timing failed"}

    async def validate_output(self, result: AgentResult) -> bool:
        return result.success and bool(result.output.get("message"))
