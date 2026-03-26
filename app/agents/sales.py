"""Sales agent — detects purchase intent and generates natural product recommendations."""

import json
import re

import structlog

from app.agents.base import AgentResult, BaseAgent
from app.core.security import PromptSecurity

logger = structlog.get_logger()


def _get_prompts():
    """Lazy-load prompt manager to avoid circular imports."""
    from app.prompts.loader import get_prompt_manager
    return get_prompt_manager()


class SalesAgent(BaseAgent):
    name = "sales"
    description = "Detects purchase intent and generates natural product recommendations"
    max_retries = 1
    confidence_threshold = 0.5

    async def execute(self, context: dict) -> AgentResult:
        from app.integrations.llm import get_llm_router

        brand = context.get("brand_context", {})
        customer_message = context.get("customer_message", "")
        conversation_history = context.get("conversation_history", [])
        customer_profile = context.get("customer_profile", {})
        channel = context.get("channel", "whatsapp")

        # Sanitize input
        if PromptSecurity.check_injection(customer_message):
            return AgentResult(
                success=True,
                output={
                    "purchase_intent_score": 0.0,
                    "recommended_products": [],
                    "sales_message": "",
                    "action": "no_action",
                },
                confidence_score=0.0,
                should_escalate=True,
                escalation_reason="Potential prompt injection detected",
                agent_name=self.name,
            )

        # Format products section
        products_section = "Aucun produit disponible."
        if brand.get("products"):
            lines = []
            for p in brand["products"]:
                price_str = p.get("price", "prix non communiqué")
                desc = p.get("description", "")
                category = p.get("category", "")
                line = f"- {p.get('name', '')}: {desc}"
                if category:
                    line += f" (catégorie: {category})"
                line += f" — {price_str}"
                lines.append(line)
            products_section = "\n".join(lines)

        # Format customer profile section
        profile_lines = []
        if customer_profile.get("name"):
            profile_lines.append(f"Nom: {customer_profile['name']}")
        if customer_profile.get("interests"):
            profile_lines.append(
                f"Intérêts: {', '.join(customer_profile['interests'])}"
            )
        if customer_profile.get("preferred_products"):
            profile_lines.append(
                f"Produits préférés: {', '.join(customer_profile['preferred_products'])}"
            )
        if customer_profile.get("purchase_history"):
            recent = customer_profile["purchase_history"][:5]
            history_items = []
            for purchase in recent:
                item = purchase.get("product", "inconnu")
                date = purchase.get("date", "")
                history_items.append(f"{item} ({date})" if date else item)
            profile_lines.append(
                f"Achats récents: {', '.join(history_items)}"
            )
        if customer_profile.get("segment"):
            profile_lines.append(f"Segment: {customer_profile['segment']}")
        customer_profile_section = (
            "\n".join(profile_lines) if profile_lines else "Nouveau client — pas d'historique."
        )

        # Format conversation history
        history_text = ""
        if conversation_history:
            lines = []
            for msg in conversation_history[-10:]:
                role = "Client" if msg.get("direction") == "inbound" else "Support"
                lines.append(f"{role}: {msg.get('content', '')}")
            history_text = "\n".join(lines)

        pm = _get_prompts()
        system = pm.get_prompt(
            "sales", "system",
            brand_name=brand.get("brand_name", "l'entreprise"),
            tone=brand.get("tone", "professionnel et chaleureux"),
            language=brand.get("language", "français"),
            products_section=products_section,
            customer_profile_section=customer_profile_section,
            conversation_history=history_text,
        )

        user_msg = pm.get_prompt(
            "sales", "user",
            customer_message=PromptSecurity.sanitize_for_prompt(customer_message),
        )

        llm = get_llm_router()
        response = await llm.generate(
            task_type="sales",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
        )

        # Parse LLM response
        parsed = self._parse_llm_output(response.content)

        purchase_intent_score = parsed.get("purchase_intent_score", 0.0)
        recommended_products = parsed.get("recommended_products", [])
        sales_message = parsed.get("sales_message", "")
        action = parsed.get("action", "no_action")

        # Validate action value
        if action not in ("recommend", "upsell", "no_action"):
            action = "no_action"

        # Use intent score as confidence
        confidence = max(0.0, min(1.0, purchase_intent_score))

        return AgentResult(
            success=True,
            output={
                "purchase_intent_score": purchase_intent_score,
                "intent_signals": parsed.get("intent_signals", []),
                "recommended_products": recommended_products,
                "sales_message": sales_message,
                "action": action,
                "channel": channel,
            },
            confidence_score=confidence,
            agent_name=self.name,
            tokens_used=response.tokens_used,
            model_used=response.model,
        )

    @staticmethod
    def _parse_llm_output(raw: str) -> dict:
        """Robustly parse LLM JSON output with fallbacks."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # Try to find JSON object in the text
        json_match = re.search(r"\{[\s\S]*\}", cleaned)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

        logger.warning("sales_agent_parse_failed", raw_length=len(raw))
        return {
            "purchase_intent_score": 0.0,
            "recommended_products": [],
            "sales_message": "",
            "action": "no_action",
        }

    async def validate_output(self, result: AgentResult) -> bool:
        """Validate that the output has the required structure."""
        output = result.output
        if "purchase_intent_score" not in output:
            return False
        if "action" not in output:
            return False
        if output["action"] not in ("recommend", "upsell", "no_action"):
            return False
        # If action is recommend/upsell, we need a message
        if output["action"] in ("recommend", "upsell"):
            if not output.get("sales_message"):
                return False
            if not output.get("recommended_products"):
                return False
        return True
