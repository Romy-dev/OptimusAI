"""Copywriter agent — generates marketing content tailored to brand and channel."""

import json

import structlog

from app.agents.base import AgentResult, BaseAgent
from app.core.security import PromptSecurity
from app.prompts.loader import get_prompt_manager

logger = structlog.get_logger()


class CopywriterAgent(BaseAgent):
    name = "copywriter"
    description = "Generates marketing content tailored to brand and channel"
    max_retries = 2
    confidence_threshold = 0.5

    async def execute(self, context: dict) -> AgentResult:
        from app.integrations.llm import get_llm_router

        brand = context.get("brand_context", {})
        brief = context.get("brief", "")
        channel = context.get("channel", "facebook")
        objective = context.get("objective", "engagement")

        # Sanitize user input
        if PromptSecurity.check_injection(brief):
            return AgentResult(
                success=False,
                output={"error": "Suspicious input detected"},
                confidence_score=0.0,
                agent_name=self.name,
            )
        brief = PromptSecurity.sanitize_for_prompt(brief)

        # Build prompt sections
        banned_words_section = ""
        if brand.get("banned_words"):
            words = ", ".join(brand["banned_words"])
            banned_words_section = f"## Mots interdits\nNe JAMAIS utiliser: {words}"

        examples_section = ""
        if brand.get("example_posts"):
            examples = brand["example_posts"][:3]
            lines = "\n".join(f'- "{e.get("content", "")}"' for e in examples)
            examples_section = f"## Exemples de posts approuvés (pour cohérence)\n{lines}"

        products_section = ""
        if brand.get("products"):
            prods = brand["products"][:5]
            lines = "\n".join(
                f'- {p.get("name", "")}: {p.get("description", "")}'
                for p in prods
            )
            products_section = f"## Produits/Services\n{lines}"

        # Channel-specific max length
        max_lengths = {"facebook": 2000, "instagram": 2200, "whatsapp": 1000, "tiktok": 300}
        max_length = brand.get("max_length", max_lengths.get(channel, 2000))

        greeting = ""
        if brand.get("greeting_style"):
            greeting = f"## Style d'ouverture\n{brand['greeting_style']}"
        closing = ""
        if brand.get("closing_style"):
            closing = f"## Style de clôture\n{brand['closing_style']}"

        closing = ""
        if brand.get("closing_style"):
            closing = f"## Style de clôture\n{brand['closing_style']}"

        prompt_mgr = get_prompt_manager()
        system = prompt_mgr.get_prompt(
            agent_name="copywriter",
            prompt_type="system",
            brand_name=brand.get("brand_name", ""),
            industry=brand.get("industry", ""),
            tone=brand.get("tone", "professional"),
            language=brand.get("language", "fr"),
            country=brand.get("country", "BF"),
            channel=channel,
            max_length=max_length,
            tone_description=brand.get("tone_description", ""),
            greeting_style=greeting,
            closing_style=closing,
            banned_words_section=banned_words_section,
            examples_section=examples_section,
            products_section=products_section,
        )

        user_msg = prompt_mgr.get_prompt(
            agent_name="copywriter",
            prompt_type="user",
            channel=channel,
            objective=objective,
            brief=brief,
            additional_instructions=context.get("additional_instructions", ""),
        )

        llm = get_llm_router()
        response = await llm.generate(
            task_type="copywriting",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
        )

        # Parse JSON response — robust extraction
        content, hashtags, media_suggestion = self._parse_llm_output(response.content)

        # Confidence scoring
        confidence = self._compute_confidence(content, brand, channel, max_length)

        return AgentResult(
            success=True,
            output={
                "content": content,
                "hashtags": hashtags,
                "media_suggestion": media_suggestion,
                "channel": channel,
            },
            confidence_score=confidence,
            agent_name=self.name,
            tokens_used=response.tokens_used,
            model_used=response.model,
        )

    @staticmethod
    def _parse_llm_output(raw: str) -> tuple[str, list[str], str]:
        """Robustly extract content, hashtags and media_suggestion from LLM output.

        Handles: valid JSON, JSON wrapped in markdown, raw text with HTML tags, etc.
        """
        import re

        content = ""
        hashtags: list[str] = []
        media_suggestion = ""

        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        # Try JSON parsing
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                content = parsed.get("content", "")
                hashtags = parsed.get("hashtags", [])
                media_suggestion = parsed.get("media_suggestion", "")
        except json.JSONDecodeError:
            # Try to find JSON object inside the text
            json_match = re.search(r'\{[^{}]*"content"\s*:\s*"[^"]*"[^{}]*\}', cleaned, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group())
                    content = parsed.get("content", "")
                    hashtags = parsed.get("hashtags", [])
                    media_suggestion = parsed.get("media_suggestion", "")
                except json.JSONDecodeError:
                    content = cleaned
            else:
                content = cleaned

        # Clean HTML tags from content
        content = re.sub(r"<[^>]+>", "", content)
        # Clean weird emoji placeholders like <nos.emoji.xxx>
        content = re.sub(r"<nos\.emoji\.\w+>", "", content)
        # Clean excessive whitespace
        content = re.sub(r"\n{3,}", "\n\n", content).strip()
        # Strip markdown bold/italic if raw
        content = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", content)

        # Clean hashtags — ensure they're strings without #
        clean_hashtags = []
        for h in hashtags:
            h_clean = str(h).strip().lstrip("#").strip()
            if h_clean:
                clean_hashtags.append(h_clean)

        return content, clean_hashtags, media_suggestion

    def _compute_confidence(
        self, content: str, brand: dict, channel: str, max_length: int
    ) -> float:
        """Score the generated content quality."""
        score = 0.7  # Base confidence

        # Length check
        if len(content) > max_length:
            score -= 0.2
        elif len(content) < 20:
            score -= 0.3

        # Banned words check
        for word in brand.get("banned_words", []):
            if word.lower() in content.lower():
                score -= 0.3

        # Has content
        if not content.strip():
            score = 0.0

        return max(0.0, min(1.0, score))

    async def validate_output(self, result: AgentResult) -> bool:
        content = result.output.get("content", "")
        if not content or len(content) < 10:
            return False
        if result.confidence_score is not None and result.confidence_score < 0.3:
            return False
        return True
