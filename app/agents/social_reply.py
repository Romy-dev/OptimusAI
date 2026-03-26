"""Social reply agent — generates contextual replies to social media comments."""

import json

import structlog

from app.agents.base import AgentResult, BaseAgent
from app.core.security import PromptSecurity

logger = structlog.get_logger()


def _get_prompts():
    """Lazy-load prompt manager to avoid circular imports."""
    from app.prompts.loader import get_prompt_manager
    return get_prompt_manager()

# Strategy instructions per comment type
STRATEGY_MAP = {
    "positive": (
        "Le commentaire est positif. Réponds avec chaleur et gratitude.\n"
        "- Remercie le client sincèrement\n"
        "- Utilise un ou deux emojis appropriés (ex: 🙏, ❤️, 😊)\n"
        "- Parfois, ajoute une question de suivi pour encourager l'engagement\n"
        "- Mentionne le prénom du client si disponible"
    ),
    "negative": (
        "Le commentaire est négatif ou une réclamation. Réponds avec empathie.\n"
        "- Commence par reconnaître le ressenti du client\n"
        "- Présente des excuses sincères si approprié\n"
        "- Propose de résoudre le problème en message privé (DM)\n"
        "- Ne sois JAMAIS sur la défensive\n"
        "- action doit être 'reply'"
    ),
    "question": (
        "Le commentaire est une question. Réponds de manière utile.\n"
        "- Si la réponse est dans le contexte de la marque, réponds directement\n"
        "- Si la question est complexe ou concerne un prix/disponibilité spécifique, "
        "propose de continuer en DM\n"
        "- Sois concis et précis"
    ),
    "spam": (
        "Le commentaire semble être du spam.\n"
        "- Ne réponds PAS au commentaire\n"
        "- reply_text doit être vide\n"
        "- action doit être 'hide'\n"
        "- should_escalate doit être false"
    ),
    "neutral": (
        "Le commentaire est neutre. Engage légèrement.\n"
        "- Réponds de manière amicale et légère\n"
        "- Encourage l'interaction avec une question ou un appel à l'action doux\n"
        "- Un emoji peut aider à rendre la réponse chaleureuse"
    ),
}


class SocialReplyAgent(BaseAgent):
    name = "social_reply"
    description = "Generates intelligent replies to social media comments"
    max_retries = 2
    confidence_threshold = 0.5

    async def execute(self, context: dict) -> AgentResult:
        from app.integrations.llm import get_llm_router

        comment_text = context.get("comment_text", "")
        comment_type = context.get("comment_type")
        post_content = context.get("post_content", "")
        brand = context.get("brand_context", {})
        platform = context.get("platform", "facebook")
        customer_name = context.get("customer_name", "")

        # Sanitize input
        if PromptSecurity.check_injection(comment_text):
            return AgentResult(
                success=True,
                output={
                    "reply_text": "",
                    "comment_type": "spam",
                    "action": "hide",
                    "should_escalate": True,
                    "escalation_reason": "suspicious_input",
                },
                confidence_score=0.0,
                should_escalate=True,
                escalation_reason="Potential prompt injection detected in comment",
                agent_name=self.name,
            )

        llm = get_llm_router()

        # === 1. Classify comment if type not provided ===
        if not comment_type:
            comment_type = await self._classify_comment(
                llm, comment_text, post_content
            )

        # === 2. Handle spam immediately ===
        if comment_type == "spam":
            return AgentResult(
                success=True,
                output={
                    "reply_text": "",
                    "comment_type": "spam",
                    "action": "hide",
                    "should_escalate": False,
                    "should_moderate": True,
                },
                confidence_score=0.9,
                agent_name=self.name,
            )

        # === 3. Generate reply ===
        strategy_instructions = STRATEGY_MAP.get(comment_type, STRATEGY_MAP["neutral"])

        pm = _get_prompts()
        system = pm.get_prompt(
            "social_reply", "system",
            brand_name=brand.get("brand_name", "l'entreprise"),
            tone=brand.get("tone", "professionnel et chaleureux"),
            industry=brand.get("industry", ""),
            market=brand.get("market", "international"),
            language=brand.get("language", "français"),
            post_content=post_content[:500] if post_content else "Non disponible",
        )

        user_msg = pm.get_prompt(
            "social_reply", "reply",
            comment_type=comment_type,
            customer_name=customer_name or "un utilisateur",
            comment_text=PromptSecurity.sanitize_for_prompt(comment_text),
            platform=platform,
            strategy_instructions=strategy_instructions,
        )

        response = await llm.generate(
            task_type="reply",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
        )

        # === 4. Parse response ===
        try:
            parsed = json.loads(response.content)
            reply_text = parsed.get("reply_text", response.content)
            action = parsed.get("action", "reply")
            should_escalate = parsed.get("should_escalate", False)
            escalation_reason = parsed.get("escalation_reason")
            confidence = float(parsed.get("confidence", 0.6))
        except (json.JSONDecodeError, ValueError):
            reply_text = response.content
            action = "reply"
            should_escalate = False
            escalation_reason = None
            confidence = 0.5

        # Override escalation for negative comments with low confidence
        if comment_type == "negative" and confidence < 0.5:
            should_escalate = True
            escalation_reason = escalation_reason or "negative_comment_low_confidence"

        return AgentResult(
            success=True,
            output={
                "reply_text": reply_text,
                "comment_type": comment_type,
                "action": action,
                "should_escalate": should_escalate,
                "escalation_reason": escalation_reason,
                "platform": platform,
            },
            confidence_score=confidence,
            should_escalate=should_escalate,
            escalation_reason=escalation_reason,
            agent_name=self.name,
            tokens_used=response.tokens_used,
            model_used=response.model,
        )

    async def _classify_comment(self, llm, comment_text: str, post_content: str) -> str:
        """Classify a comment using the LLM."""
        try:
            pm = _get_prompts()
            prompt = pm.get_prompt(
                "social_reply", "classify",
                comment_text=PromptSecurity.sanitize_for_prompt(comment_text),
                post_content=post_content[:300] if post_content else "Non disponible",
            )

            response = await llm.generate(
                task_type="classification",
                messages=[
                    {"role": "user", "content": prompt},
                ],
            )

            parsed = json.loads(response.content)
            comment_type = parsed.get("comment_type", "neutral")

            # Validate comment_type
            valid_types = {"positive", "negative", "question", "spam", "neutral"}
            if comment_type not in valid_types:
                comment_type = "neutral"

            return comment_type

        except Exception as e:
            logger.warning("comment_classification_failed", error=str(e))
            return "neutral"

    async def validate_output(self, result: AgentResult) -> bool:
        """Validate the reply output."""
        comment_type = result.output.get("comment_type", "")
        action = result.output.get("action", "")

        # Spam should have hide action and no reply
        if comment_type == "spam":
            return action == "hide"

        # Non-spam replies should have text
        reply_text = result.output.get("reply_text", "")
        return bool(reply_text and len(reply_text) > 3)
