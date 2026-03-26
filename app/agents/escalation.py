"""Escalation agent — handles handoff from AI to human."""

import structlog

from app.agents.base import AgentResult, BaseAgent

logger = structlog.get_logger()


class EscalationAgent(BaseAgent):
    name = "escalation"
    description = "Manages AI-to-human handoff with full context"
    max_retries = 0

    async def execute(self, context: dict) -> AgentResult:
        reason = context.get("escalation_reason", "unknown")
        conversation_id = context.get("conversation_id")
        brand = context.get("brand_context", {})
        conversation_history = context.get("conversation_history", [])

        # Generate summary for the human agent
        summary = await self._generate_summary(context)

        # Determine priority
        priority = self._determine_priority(reason, context)

        # Customer-facing message
        customer_message = self._get_customer_message(brand, priority)

        return AgentResult(
            success=True,
            output={
                "escalation_summary": summary,
                "priority": priority,
                "reason": reason,
                "customer_message": customer_message,
                "conversation_id": conversation_id,
                "context_for_human": {
                    "customer_name": context.get("customer_name"),
                    "channel": context.get("channel"),
                    "last_messages": conversation_history[-5:] if conversation_history else [],
                    "ai_attempts": context.get("ai_attempts", []),
                    "knowledge_results": context.get("knowledge_results", []),
                },
            },
            confidence_score=None,
            agent_name=self.name,
        )

    async def _generate_summary(self, context: dict) -> str:
        """Generate a concise summary for the human agent."""
        try:
            from app.integrations.llm import get_llm_router

            history = context.get("conversation_history", [])
            if not history:
                return f"Escalade: {context.get('escalation_reason', 'raison non spécifiée')}"

            history_text = "\n".join(
                f"{'Client' if m.get('direction') == 'inbound' else 'IA'}: {m.get('content', '')}"
                for m in history[-10:]
            )

            llm = get_llm_router()
            reason = context.get("escalation_reason", "non specifiee")
            brand_name = context.get("brand_context", {}).get("brand_name", "")
            customer_name = context.get("customer_name", "le client")
            channel = context.get("channel", "whatsapp")

            from app.prompts.loader import get_prompt_manager
            system_content = get_prompt_manager().get_prompt(
                "escalation", "system",
                brand_name=brand_name,
                customer_name=customer_name,
                channel=channel,
                reason=reason,
            )

            response = await llm.generate(
                task_type="summary",
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": f"Historique de la conversation:\n\n{history_text}"},
                ],
                temperature=0.2,
            )
            return response.content
        except Exception:
            return f"Escalade: {context.get('escalation_reason', 'raison non spécifiée')}"

    def _determine_priority(self, reason: str, context: dict) -> str:
        """Determine escalation priority."""
        urgent_reasons = {"customer_request", "complaint", "refund", "legal"}
        high_reasons = {"customer_unhappy", "low_confidence", "sensitive_topic"}

        if any(r in reason for r in urgent_reasons):
            return "urgent"
        if any(r in reason for r in high_reasons):
            return "high"
        return "medium"

    def _get_customer_message(self, brand: dict, priority: str) -> str:
        """Message to send to the customer during escalation."""
        brand_name = brand.get("brand_name", "notre équipe")
        if priority == "urgent":
            return (
                f"Un membre de {brand_name} va prendre le relais immédiatement. "
                "Merci de votre patience."
            )
        return (
            f"Je transfère votre demande à un conseiller de {brand_name} "
            "qui pourra mieux vous aider. Merci de votre patience !"
        )
