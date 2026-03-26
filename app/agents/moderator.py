"""Moderation agent — checks content safety before any output."""

import json
import re

import structlog

from app.agents.base import AgentResult, BaseAgent

logger = structlog.get_logger()


# Basic French profanity/toxicity patterns (extend as needed)
TOXIC_PATTERNS = [
    r"\b(merde|putain|connard|salaud|enculé|nique)\b",
    r"\b(kill|murder|suicide|bomb)\b",
    r"\b(nigger|negro)\b",
]


class ModeratorAgent(BaseAgent):
    name = "moderator"
    description = "Checks content safety and brand compliance"
    max_retries = 0  # Moderation is a single pass
    confidence_threshold = 0.5

    async def execute(self, context: dict) -> AgentResult:
        content = context.get("content", "")
        content_type = context.get("content_type", "post")
        brand = context.get("brand_context", {})

        flags: list[str] = []
        score = 1.0  # Start at 100% safe

        # === 1. Toxicity check (regex-based, fast) ===
        for pattern in TOXIC_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                flags.append("toxicity")
                score -= 0.5
                break

        # === 2. Brand banned words ===
        for word in brand.get("banned_words", []):
            if word.lower() in content.lower():
                flags.append(f"banned_word:{word}")
                score -= 0.3

        # === 3. Brand banned topics ===
        for topic in brand.get("banned_topics", []):
            if topic.lower() in content.lower():
                flags.append(f"banned_topic:{topic}")
                score -= 0.3

        # === 4. Sensitive topics (flag but don't block) ===
        for topic in brand.get("sensitive_topics", []):
            if topic.lower() in content.lower():
                flags.append(f"sensitive_topic:{topic}")
                score -= 0.1

        # === 5. Personal data patterns ===
        # Phone numbers (African format)
        if re.search(r"\b\d{8,}\b", content):
            flags.append("possible_phone_number")
            score -= 0.1

        # Email in public posts
        if content_type == "post" and re.search(r"\b[\w.-]+@[\w.-]+\.\w+\b", content):
            flags.append("email_in_public_post")
            score -= 0.1

        # === 6. LLM moderation for borderline cases ===
        if 0.4 < score < 0.8 and not flags:
            llm_result = await self._llm_moderation(content, brand)
            if llm_result:
                flags.extend(llm_result.get("flags", []))
                score = min(score, llm_result.get("score", score))

        # Clamp score
        score = max(0.0, min(1.0, score))

        # Determine action
        if score >= 0.7:
            action = "approved"
        elif score >= 0.4:
            action = "flagged"  # Needs human review
        else:
            action = "blocked"

        approved = action == "approved"

        return AgentResult(
            success=True,
            output={
                "approved": approved,
                "action": action,
                "moderation_score": score,
                "flags": flags,
                "requires_human_review": action == "flagged",
            },
            confidence_score=score,
            agent_name=self.name,
        )

    async def _llm_moderation(self, content: str, brand: dict) -> dict | None:
        """Use LLM for nuanced moderation of borderline content."""
        try:
            from app.integrations.llm import get_llm_router

            brand_name = brand.get("brand_name", "la marque")
            industry = brand.get("industry", "")
            banned_words = ", ".join(brand.get("banned_words", [])) or "aucun"
            banned_topics = ", ".join(brand.get("banned_topics", [])) or "aucun"

            from app.prompts.loader import get_prompt_manager
            system_prompt = get_prompt_manager().get_prompt(
                "moderation", "system",
                brand_name=brand_name,
                industry=industry,
                banned_words=banned_words,
                banned_topics=banned_topics,
            )

            llm = get_llm_router()
            response = await llm.generate(
                task_type="moderation",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Contenu a moderer:\n\n{content}"},
                ],
                temperature=0.1,
            )

            from app.agents.output_parser import parse_llm_output
            from pydantic import BaseModel, Field

            class ModerationResult(BaseModel):
                safe: bool = True
                score: float = 0.7
                flags: list[str] = Field(default_factory=list)
                details: str = ""
                suggestion: str = ""

            result = parse_llm_output(response.content, ModerationResult)
            return {"safe": result.safe, "score": result.score, "flags": result.flags, "suggestion": result.suggestion}

        except Exception as e:
            logger.warning("llm_moderation_failed", error=str(e))
            return None
