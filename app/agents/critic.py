"""Critic agent — auto-validates generated content before publication.

Reviews posts against a strict ScoreCard: tone, language, relevance,
brand compliance, engagement potential, and cultural sensitivity.
"""

import json

import structlog

from app.agents.base import AgentResult, BaseAgent

logger = structlog.get_logger()

def _get_prompts():
    """Lazy-load prompt manager to avoid circular imports."""
    from app.prompts.loader import get_prompt_manager
    return get_prompt_manager()


class CriticAgent(BaseAgent):
    name = "critic"
    description = "Reviews and scores generated content against a strict ScoreCard"
    max_retries = 1
    confidence_threshold = 0.5

    async def execute(self, context: dict) -> AgentResult:
        from app.integrations.llm import get_llm_router

        content = context.get("content", "")
        hashtags = context.get("hashtags", [])
        brief = context.get("brief", "")
        brand = context.get("brand_context", {})
        channel = context.get("channel", "facebook")

        if not content:
            return AgentResult(
                success=False,
                output={"error": "No content to review"},
                agent_name=self.name,
            )

        brand_name = brand.get("brand_name", "la marque")
        tone = brand.get("tone", "professionnel")
        banned_words = brand.get("banned_words", [])
        country = context.get("target_country", brand.get("country", "international"))

        pm = _get_prompts()
        system = pm.get_prompt(
            "critic", "system",
            tone=tone,
            channel=channel,
            brand_name=brand_name,
            country=country,
            language=brand.get("language", "français"),
        )

        user_msg = f"""## Contenu a evaluer

**Brief original**: {brief}
**Canal**: {channel}
**Marque**: {brand_name}
**Ton attendu**: {tone}
**Mots bannis**: {', '.join(banned_words) if banned_words else 'aucun'}

**Contenu**:
{content}

**Hashtags**: {', '.join(hashtags) if hashtags else 'aucun'}
"""

        llm = get_llm_router()
        response = await llm.generate(
            task_type="support",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
        )

        # Parse response
        from app.agents.output_parser import parse_llm_output
        from pydantic import BaseModel, Field

        class CriticOutput(BaseModel):
            scores: dict[str, int] = Field(default_factory=dict)
            total_score: int = 0
            grade: str = "C"
            approved: bool = False
            issues: list[str] = Field(default_factory=list)
            suggestions: list[str] = Field(default_factory=list)
            revised_content: str = ""

        result = parse_llm_output(response.content, CriticOutput)

        # Recalculate total from scores to avoid LLM errors
        if result.scores:
            result.total_score = sum(result.scores.values())
            result.approved = result.total_score >= 65

        # Grade mapping
        s = result.total_score
        result.grade = "A+" if s >= 90 else "A" if s >= 85 else "B+" if s >= 75 else "B" if s >= 65 else "C" if s >= 50 else "D"

        logger.info(
            "critic_review",
            total_score=result.total_score,
            grade=result.grade,
            approved=result.approved,
            issues_count=len(result.issues),
        )

        return AgentResult(
            success=True,
            output={
                "scores": result.scores,
                "total_score": result.total_score,
                "grade": result.grade,
                "approved": result.approved,
                "issues": result.issues,
                "suggestions": result.suggestions,
                "revised_content": result.revised_content,
            },
            confidence_score=result.total_score / 100.0,
            agent_name=self.name,
        )

    async def validate_output(self, result: AgentResult) -> bool:
        return result.success and "total_score" in result.output
