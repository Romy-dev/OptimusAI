"""Support agent — answers customer questions using RAG knowledge base."""

import json

import structlog

from app.agents.base import AgentResult, BaseAgent
from app.core.security import PromptSecurity

logger = structlog.get_logger()


def _get_prompts():
    """Lazy-load prompt manager to avoid circular imports."""
    from app.prompts.loader import get_prompt_manager
    return get_prompt_manager()


class SupportAgent(BaseAgent):
    name = "support"
    description = "Answers customer questions using the knowledge base"
    max_retries = 1
    confidence_threshold = 0.5

    async def execute(self, context: dict) -> AgentResult:
        from app.integrations.llm import get_llm_router

        brand = context.get("brand_context", {})
        customer_message = context.get("customer_message", context.get("content", ""))
        knowledge_results = context.get("knowledge_results", [])
        conversation_history = context.get("conversation_history", [])

        # Sanitize input
        if PromptSecurity.check_injection(customer_message):
            return AgentResult(
                success=True,
                output={
                    "response": "Je suis désolé, je n'ai pas compris votre message. Pouvez-vous reformuler ?",
                    "should_escalate": True,
                    "escalation_reason": "suspicious_input",
                },
                confidence_score=0.0,
                should_escalate=True,
                escalation_reason="Potential prompt injection detected",
                agent_name=self.name,
            )

        # Format knowledge context
        knowledge_context = "Aucune information trouvée dans la base de connaissances."
        if knowledge_results:
            docs = []
            for r in knowledge_results[:5]:
                title = r.get("document_title", "Document")
                section = r.get("section_title", "")
                content = r.get("content", "")
                score = r.get("score", 0)
                docs.append(f"[{title} - {section}] (pertinence: {score:.2f})\n{content}")
            knowledge_context = "\n\n---\n\n".join(docs)

        # Format conversation history
        history_text = ""
        if conversation_history:
            lines = []
            for msg in conversation_history[-10:]:  # Last 10 messages
                role = "Client" if msg.get("direction") == "inbound" else "Support"
                lines.append(f"{role}: {msg.get('content', '')}")
            history_text = "\n".join(lines)

        # Business context
        business_lines = []
        if brand.get("products"):
            for p in brand["products"][:5]:
                business_lines.append(
                    f"- {p.get('name', '')}: {p.get('description', '')} "
                    f"({p.get('price', 'prix non communiqué')})"
                )
        if brand.get("business_hours"):
            business_lines.append(f"Horaires: {json.dumps(brand['business_hours'], ensure_ascii=False)}")
        if brand.get("contact_info"):
            business_lines.append(f"Contact: {json.dumps(brand['contact_info'], ensure_ascii=False)}")
        business_context = "\n".join(business_lines) if business_lines else "Pas d'informations supplémentaires."

        greeting = ""
        if brand.get("greeting_style"):
            greeting = f"## Style d'ouverture\n{brand['greeting_style']}"
        closing = ""
        if brand.get("closing_style"):
            closing = f"## Style de clôture\n{brand['closing_style']}"

        pm = _get_prompts()
        system = pm.get_prompt(
            "support", "system",
            brand_name=brand.get("brand_name", "l'entreprise"),
            tone=brand.get("tone", "professionnel"),
            language=brand.get("language", "français"),
            greeting_style=greeting,
            closing_style=closing,
            business_context=business_context,
            knowledge_context=knowledge_context,
            conversation_history=history_text,
        )

        user_msg = pm.get_prompt(
            "support", "user",
            customer_message=PromptSecurity.sanitize_for_prompt(customer_message),
        )

        llm = get_llm_router()
        response = await llm.generate(
            task_type="support",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
        )

        # Parse response
        try:
            parsed = json.loads(response.content)
            reply = parsed.get("response", response.content)
            confidence = float(parsed.get("confidence", 0.5))
            should_escalate = parsed.get("should_escalate", False)
            escalation_reason = parsed.get("escalation_reason")
            sources = parsed.get("sources_used", [])
        except (json.JSONDecodeError, ValueError):
            reply = response.content
            confidence = 0.5
            should_escalate = False
            escalation_reason = None
            sources = []

        # Override escalation based on rules
        if confidence < 0.4:
            should_escalate = True
            escalation_reason = escalation_reason or "low_confidence"

        # Check for sensitive topics
        for topic in brand.get("sensitive_topics", []):
            if topic.lower() in customer_message.lower():
                should_escalate = True
                escalation_reason = f"sensitive_topic:{topic}"
                break

        return AgentResult(
            success=True,
            output={
                "response": reply,
                "sources": sources,
                "channel": context.get("channel", "whatsapp"),
            },
            confidence_score=confidence,
            should_escalate=should_escalate,
            escalation_reason=escalation_reason,
            agent_name=self.name,
            tokens_used=response.tokens_used,
            model_used=response.model,
        )

    async def validate_output(self, result: AgentResult) -> bool:
        response = result.output.get("response", "")
        return bool(response and len(response) > 5)
