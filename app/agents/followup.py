"""Follow-up agent — manages proactive customer follow-ups and re-engagement."""

import json
import re
from datetime import datetime, timedelta

import structlog

from app.agents.base import AgentResult, BaseAgent

logger = structlog.get_logger()


def _get_prompts():
    """Lazy-load prompt manager to avoid circular imports."""
    from app.prompts.loader import get_prompt_manager
    return get_prompt_manager()


# Template fallbacks for speed when LLM is slow or unavailable
TEMPLATE_FALLBACKS: dict[str, str] = {
    "post_purchase": (
        "Bonjour {name} ! Nous espérons que vous êtes satisfait(e) de votre achat. "
        "N'hésitez pas à nous contacter si vous avez des questions. Bonne journée !"
    ),
    "issue_resolution": (
        "Bonjour {name}, nous voulions vérifier que votre problème a bien été résolu. "
        "Si vous avez encore besoin d'aide, nous sommes là pour vous !"
    ),
    "re_engagement": (
        "Bonjour {name} ! Cela fait un moment que nous n'avons pas eu de vos nouvelles. "
        "Nous espérons que tout va bien. Découvrez nos dernières nouveautés !"
    ),
    "abandoned_cart": (
        "Bonjour {name} ! Vous aviez repéré des articles qui vous plaisaient — "
        "ils sont toujours disponibles. N'hésitez pas si vous avez des questions !"
    ),
    "birthday": (
        "Joyeux anniversaire {name} ! \U0001f382 Toute l'équipe vous souhaite une merveilleuse journée. "
        "Profitez de -10% avec le code ANNIVERSAIRE !"
    ),
    "seasonal": (
        "Bonjour {name} ! En cette période spéciale, nous avons pensé à vous. "
        "Découvrez nos offres du moment !"
    ),
}

# Default next followup intervals in days per type
DEFAULT_NEXT_FOLLOWUP_DAYS: dict[str, int] = {
    "post_purchase": 14,
    "issue_resolution": 7,
    "re_engagement": 30,
    "abandoned_cart": 3,
    "birthday": 365,
    "seasonal": 30,
}

# Default priority per type
DEFAULT_PRIORITY: dict[str, str] = {
    "post_purchase": "medium",
    "issue_resolution": "high",
    "re_engagement": "low",
    "abandoned_cart": "high",
    "birthday": "medium",
    "seasonal": "low",
}


FOLLOWUP_INSTRUCTIONS: dict[str, str] = {
    "post_purchase": (
        "Le client a fait un achat récemment. Prends de ses nouvelles, "
        "demande s'il est satisfait, et rappelle que tu es disponible pour l'aider. "
        "NE PAS essayer de vendre autre chose maintenant."
    ),
    "issue_resolution": (
        "Le client avait un problème récemment résolu. Vérifie que tout est bien réglé, "
        "montre que tu te soucies de son expérience. "
        "Si le problème était: {last_issue}"
    ),
    "re_engagement": (
        "Le client n'a pas interagi depuis {days_since_contact} jours. "
        "Reprends contact de manière naturelle. Tu peux mentionner des nouveautés ou "
        "des promotions en cours, mais sans pression."
    ),
    "abandoned_cart": (
        "Le client avait des articles dans son panier mais n'a pas finalisé. "
        "Rappelle-lui de manière douce, propose ton aide si besoin. "
        "Articles abandonnés: {abandoned_items}"
    ),
    "birthday": (
        "C'est l'anniversaire du client ! Souhaite-lui un joyeux anniversaire "
        "de manière chaleureuse. Tu peux inclure une offre spéciale (code promo, réduction)."
    ),
    "seasonal": (
        "C'est une période spéciale: {season_context}. "
        "Adapte aux fêtes et événements du pays cible ({country}). "
        "Propose des produits/offres pertinents pour la saison."
    ),
}


class FollowUpAgent(BaseAgent):
    name = "followup"
    description = "Generates proactive follow-up messages for customer retention"
    max_retries = 1
    confidence_threshold = 0.5

    async def execute(self, context: dict) -> AgentResult:
        followup_type = context.get("followup_type", "re_engagement")
        customer_profile = context.get("customer_profile", {})
        brand = context.get("brand_context", {})
        channel = context.get("channel", "whatsapp")
        days_since_contact = context.get("days_since_contact", 0)

        # Validate followup_type
        valid_types = {
            "post_purchase", "issue_resolution", "re_engagement",
            "abandoned_cart", "birthday", "seasonal",
        }
        if followup_type not in valid_types:
            followup_type = "re_engagement"

        # Build customer profile section
        customer_profile_section = self._format_customer_profile(customer_profile)

        # Build followup-specific instructions
        followup_instructions = self._build_followup_instructions(
            followup_type, customer_profile, context, days_since_contact, brand
        )

        # Try LLM generation first, fall back to templates
        try:
            result = await self._generate_with_llm(
                followup_type=followup_type,
                customer_profile_section=customer_profile_section,
                followup_instructions=followup_instructions,
                brand=brand,
                channel=channel,
                days_since_contact=days_since_contact,
                context=context,
            )
        except Exception as e:
            logger.warning(
                "followup_llm_failed_using_template",
                error=str(e),
                followup_type=followup_type,
            )
            result = self._generate_from_template(
                followup_type, customer_profile, brand
            )

        message = result.get("message", "")
        suggested_next_days = result.get(
            "suggested_next_days",
            DEFAULT_NEXT_FOLLOWUP_DAYS.get(followup_type, 14),
        )
        priority = result.get(
            "priority",
            DEFAULT_PRIORITY.get(followup_type, "medium"),
        )

        # Validate priority
        if priority not in ("high", "medium", "low"):
            priority = DEFAULT_PRIORITY.get(followup_type, "medium")

        # Compute next followup datetime
        next_followup_at = (
            datetime.utcnow() + timedelta(days=suggested_next_days)
        ).isoformat()

        # Confidence based on personalization quality
        confidence = self._compute_confidence(message, customer_profile)

        return AgentResult(
            success=True,
            output={
                "message": message,
                "followup_type": followup_type,
                "next_followup_at": next_followup_at,
                "priority": priority,
                "channel": channel,
            },
            confidence_score=confidence,
            agent_name=self.name,
            tokens_used=result.get("tokens_used"),
            model_used=result.get("model_used"),
        )

    async def _generate_with_llm(
        self,
        followup_type: str,
        customer_profile_section: str,
        followup_instructions: str,
        brand: dict,
        channel: str,
        days_since_contact: int,
        context: dict,
    ) -> dict:
        """Generate a personalized follow-up message using LLM."""
        from app.integrations.llm import get_llm_router

        # Additional context for the user prompt
        additional_context_parts = []
        customer_profile = context.get("customer_profile", {})
        if customer_profile.get("purchase_history"):
            recent = customer_profile["purchase_history"][:3]
            items = [p.get("product", "inconnu") for p in recent]
            additional_context_parts.append(f"Achats récents: {', '.join(items)}")
        if context.get("abandoned_items"):
            items = [i.get("name", "") for i in context["abandoned_items"]]
            additional_context_parts.append(f"Articles abandonnés: {', '.join(items)}")
        if context.get("season_context"):
            additional_context_parts.append(f"Contexte saisonnier: {context['season_context']}")

        additional_context = "\n".join(additional_context_parts)

        pm = _get_prompts()
        system = pm.get_prompt(
            "followup", "system",
            brand_name=brand.get("brand_name", "l'entreprise"),
            tone=brand.get("tone", "professionnel et chaleureux"),
            language=brand.get("language", "français"),
            market=brand.get("market", "international"),
            country=brand.get("country", "non spécifié"),
            followup_type=followup_type,
            followup_instructions=followup_instructions,
            customer_profile_section=customer_profile_section,
            industry=brand.get("industry", ""),
        )

        user_msg = pm.get_prompt(
            "followup", "user",
            followup_type=followup_type,
            channel=channel,
            days_since_contact=days_since_contact,
            additional_context=additional_context,
        )

        llm = get_llm_router()
        response = await llm.generate(
            task_type="followup",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
        )

        parsed = self._parse_llm_output(response.content)
        parsed["tokens_used"] = response.tokens_used
        parsed["model_used"] = response.model
        return parsed

    def _generate_from_template(
        self, followup_type: str, customer_profile: dict, brand: dict
    ) -> dict:
        """Fast template-based fallback when LLM is unavailable."""
        name = customer_profile.get("name", "")
        if not name:
            name = "cher(e) client(e)"

        template = TEMPLATE_FALLBACKS.get(followup_type, TEMPLATE_FALLBACKS["re_engagement"])
        message = template.format(name=name)

        return {
            "message": message,
            "suggested_next_days": DEFAULT_NEXT_FOLLOWUP_DAYS.get(followup_type, 14),
            "priority": DEFAULT_PRIORITY.get(followup_type, "medium"),
        }

    @staticmethod
    def _format_customer_profile(customer_profile: dict) -> str:
        """Format customer profile for the prompt."""
        lines = []
        if customer_profile.get("name"):
            lines.append(f"Nom: {customer_profile['name']}")
        if customer_profile.get("segment"):
            lines.append(f"Segment: {customer_profile['segment']}")
        if customer_profile.get("last_contact"):
            lines.append(f"Dernier contact: {customer_profile['last_contact']}")
        if customer_profile.get("purchase_history"):
            recent = customer_profile["purchase_history"][:5]
            items = []
            for p in recent:
                product = p.get("product", "inconnu")
                date = p.get("date", "")
                items.append(f"{product} ({date})" if date else product)
            lines.append(f"Achats récents: {', '.join(items)}")
        if customer_profile.get("preferred_products"):
            lines.append(
                f"Produits préférés: {', '.join(customer_profile['preferred_products'])}"
            )
        if customer_profile.get("last_issue"):
            lines.append(f"Dernier problème: {customer_profile['last_issue']}")
        return "\n".join(lines) if lines else "Nouveau client — pas d'historique."

    @staticmethod
    def _build_followup_instructions(
        followup_type: str,
        customer_profile: dict,
        context: dict,
        days_since_contact: int,
        brand: dict | None = None,
    ) -> str:
        """Build type-specific instructions with context interpolation."""
        template = FOLLOWUP_INSTRUCTIONS.get(
            followup_type, FOLLOWUP_INSTRUCTIONS["re_engagement"]
        )

        # Build interpolation values with safe defaults
        last_issue = customer_profile.get("last_issue", "non spécifié")
        abandoned_items_raw = context.get("abandoned_items", [])
        abandoned_items = ", ".join(
            i.get("name", "") for i in abandoned_items_raw
        ) if abandoned_items_raw else "articles non spécifiés"
        season_context = context.get("season_context", "période en cours")
        country = (brand or {}).get("country", "non spécifié")

        try:
            return template.format(
                days_since_contact=days_since_contact,
                last_issue=last_issue,
                abandoned_items=abandoned_items,
                season_context=season_context,
                country=country,
            )
        except KeyError:
            # Template doesn't use all variables — that's fine
            return template

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

        logger.warning("followup_agent_parse_failed", raw_length=len(raw))
        # Return the raw text as the message
        return {"message": cleaned}

    @staticmethod
    def _compute_confidence(message: str, customer_profile: dict) -> float:
        """Score the follow-up message quality based on personalization."""
        score = 0.6  # Base confidence

        if not message or len(message) < 10:
            return 0.0

        # Bonus for using customer name
        name = customer_profile.get("name", "")
        if name and name.lower() in message.lower():
            score += 0.15

        # Bonus for reasonable length
        if 30 < len(message) < 500:
            score += 0.1

        # Penalty for very short messages
        if len(message) < 20:
            score -= 0.2

        return max(0.0, min(1.0, score))

    async def validate_output(self, result: AgentResult) -> bool:
        """Validate that the output has the required structure."""
        output = result.output
        message = output.get("message", "")
        if not message or len(message) < 10:
            return False
        if output.get("followup_type") not in {
            "post_purchase", "issue_resolution", "re_engagement",
            "abandoned_cart", "birthday", "seasonal",
        }:
            return False
        if output.get("priority") not in ("high", "medium", "low"):
            return False
        return True
