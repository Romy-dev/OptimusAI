"""Content strategist agent — plans content calendars and suggests what to post."""

import json
import re
from datetime import datetime

import structlog

from app.agents.base import AgentResult, BaseAgent
from app.core.security import PromptSecurity

logger = structlog.get_logger()


# Content mix targets: ~20% promo, ~25% educational, ~25% engagement,
# ~15% storytelling, ~15% product showcase
CONTENT_MIX_TARGETS = {
    "promo": 0.20,
    "educational": 0.25,
    "engagement": 0.25,
    "storytelling": 0.15,
    "product_showcase": 0.15,
}

VALID_CONTENT_TYPES = [
    "promo",
    "educational",
    "engagement",
    "storytelling",
    "product_showcase",
    "behind_the_scenes",
    "testimonial",
]

VALID_CHANNELS = ["facebook", "instagram", "whatsapp"]

# Major West African events and holidays (month-day or variable)
WEST_AFRICAN_EVENTS = {
    "BF": [
        ("01-03", "Anniversaire de l'insurrection populaire"),
        ("03-08", "Journée internationale de la femme"),
        ("05-01", "Fête du travail"),
        ("08-05", "Fête nationale du Burkina Faso"),
        ("11-01", "Toussaint"),
        ("12-11", "Proclamation de la République"),
    ],
    "CI": [
        ("03-08", "Journée internationale de la femme"),
        ("05-01", "Fête du travail"),
        ("08-07", "Fête de l'indépendance de la Côte d'Ivoire"),
        ("11-15", "Journée nationale de la paix"),
        ("12-25", "Noël"),
    ],
    "SN": [
        ("04-04", "Fête de l'indépendance du Sénégal"),
        ("05-01", "Fête du travail"),
        ("03-08", "Journée internationale de la femme"),
        ("12-25", "Noël"),
    ],
    "ML": [
        ("01-20", "Journée de l'armée"),
        ("03-26", "Journée des martyrs"),
        ("05-01", "Fête du travail"),
        ("09-22", "Fête de l'indépendance du Mali"),
    ],
    "CM": [
        ("02-11", "Fête de la jeunesse"),
        ("05-01", "Fête du travail"),
        ("05-20", "Fête nationale du Cameroun"),
        ("12-25", "Noël"),
    ],
}

# Shared events (Islamic holidays are approximate — vary by year)
SHARED_EVENTS = [
    ("variable", "Ramadan (environ 30 jours de jeûne — adapter le contenu)"),
    ("variable", "Eid al-Fitr / Fête de Ramadan"),
    ("variable", "Eid al-Adha / Tabaski"),
    ("variable", "Mawlid / Maouloud"),
    ("05-last-sunday", "Fête des mères"),
    ("06-third-sunday", "Fête des pères"),
    ("12-31", "Réveillon du Nouvel An"),
    ("01-01", "Jour de l'An"),
]


def _get_prompts():
    """Lazy-load prompt manager to avoid circular imports."""
    from app.prompts.loader import get_prompt_manager
    return get_prompt_manager()


class ContentStrategistAgent(BaseAgent):
    name = "strategist"
    description = "Plans content strategy, editorial calendars, and suggests post ideas"
    max_retries = 1
    confidence_threshold = 0.5

    async def execute(self, context: dict) -> AgentResult:
        from app.integrations.llm import get_llm_router

        brand = context.get("brand_context", {})
        recent_posts = context.get("recent_posts", [])
        target_country = context.get("target_country", "BF")
        period = context.get("period", "week")
        current_date = context.get("current_date", datetime.now().strftime("%Y-%m-%d"))

        # Sanitize any user-provided additional instructions
        additional = context.get("additional_instructions", "")
        if additional and PromptSecurity.check_injection(additional):
            return AgentResult(
                success=False,
                output={"error": "Suspicious input detected"},
                confidence_score=0.0,
                agent_name=self.name,
            )
        if additional:
            additional = PromptSecurity.sanitize_for_prompt(additional)

        # Build products section
        products_section = ""
        if brand.get("products"):
            prods = brand["products"][:5]
            lines = "\n".join(
                f'- {p.get("name", "")}: {p.get("description", "")}'
                for p in prods
            )
            products_section = f"## Produits/Services\n{lines}"

        # Build recent posts section
        recent_posts_section = "Aucun post récent disponible."
        if recent_posts:
            lines = []
            for post in recent_posts[:20]:
                status = post.get("status", "unknown")
                content_preview = (post.get("content", "") or "")[:80]
                channel = post.get("channel", "?")
                published = post.get("published_at", "?")
                engagement = post.get("engagement", {})
                eng_str = ""
                if engagement:
                    parts = []
                    for k, v in engagement.items():
                        parts.append(f"{k}:{v}")
                    eng_str = f" | engagement: {', '.join(parts)}"
                lines.append(
                    f"- [{published}] ({channel}, {status}) \"{content_preview}...\"{eng_str}"
                )
            recent_posts_section = "\n".join(lines)

        # Build events section
        events_section = self._build_events_section(target_country, current_date)

        # Format system prompt
        pm = _get_prompts()
        system = pm.get_prompt(
            "strategist", "system",
            brand_name=brand.get("brand_name", "la marque"),
            industry=brand.get("industry", "non spécifié"),
            tone=brand.get("tone", "professionnel"),
            target_country=target_country,
            language=brand.get("language", "français"),
            products_section=products_section,
            current_date=current_date,
            period=period,
            recent_posts_section=recent_posts_section,
            events_section=events_section,
        )

        additional_text = ""
        if additional:
            additional_text = f"\nInstructions supplémentaires: {additional}"

        user_msg = pm.get_prompt(
            "strategist", "user",
            period=period,
            current_date=current_date,
            additional_instructions=additional_text,
        )

        llm = get_llm_router()
        response = await llm.generate(
            task_type="strategy",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
        )

        # Parse LLM response
        calendar, content_mix, tips = self._parse_llm_output(response.content)

        # Compute confidence
        confidence = self._compute_confidence(calendar, content_mix)

        return AgentResult(
            success=True,
            output={
                "calendar": calendar,
                "content_mix": content_mix,
                "tips": tips,
                "period": period,
                "target_country": target_country,
            },
            confidence_score=confidence,
            agent_name=self.name,
            tokens_used=response.tokens_used,
            model_used=response.model,
        )

    @staticmethod
    def _build_events_section(country: str, current_date: str) -> str:
        """Build a section listing relevant events and holidays."""
        lines = []

        # Country-specific events
        country_events = WEST_AFRICAN_EVENTS.get(country, [])
        if country_events:
            lines.append(f"### Fêtes nationales ({country})")
            for date_str, name in country_events:
                lines.append(f"- {date_str}: {name}")
        else:
            lines.append(f"### Fêtes nationales ({country})")
            lines.append("- Adapte le calendrier aux fêtes et événements locaux du pays cible.")

        # Shared / Islamic events
        lines.append("\n### Fêtes religieuses et partagées")
        for date_str, name in SHARED_EVENTS:
            lines.append(f"- {date_str}: {name}")

        # Awareness based on current month
        try:
            dt = datetime.strptime(current_date, "%Y-%m-%d")
            month = dt.month
            month_tips = {
                1: "Début d'année: résolutions, objectifs, promotions de rentrée",
                2: "Saint-Valentin (14 fév), événements locaux du pays cible",
                3: "Journée de la femme (8 mars), événements religieux éventuels",
                4: "Pâques, événements religieux éventuels (Ramadan selon le calendrier)",
                5: "Fête du travail, Fête des mères (dernier dimanche)",
                6: "Fête des pères, début de saison selon le pays",
                7: "Vacances scolaires, événements religieux éventuels",
                8: "Fêtes nationales selon le pays, rentrée en approche",
                9: "Rentrée scolaire, événements locaux",
                10: "Préparation fêtes de fin d'année",
                11: "Black Friday, préparation Noël",
                12: "Noël, Réveillon, bilan annuel",
            }
            if month in month_tips:
                lines.append(f"\n### Contexte du mois\n{month_tips[month]}")
        except ValueError:
            pass

        return "\n".join(lines)

    @staticmethod
    def _parse_llm_output(raw: str) -> tuple[list[dict], dict, list[str]]:
        """Parse the LLM JSON response into calendar, content_mix, and tips."""
        calendar: list[dict] = []
        content_mix: dict = {}
        tips: list[str] = []

        # Strip markdown code fences
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to find JSON object in text
            json_match = re.search(r"\{[\s\S]*\}", cleaned)
            if json_match:
                try:
                    parsed = json.loads(json_match.group())
                except json.JSONDecodeError:
                    return calendar, content_mix, tips
            else:
                return calendar, content_mix, tips

        if not isinstance(parsed, dict):
            return calendar, content_mix, tips

        # Extract calendar
        raw_calendar = parsed.get("calendar", [])
        if isinstance(raw_calendar, list):
            for entry in raw_calendar:
                if isinstance(entry, dict):
                    calendar.append({
                        "day": str(entry.get("day", "")),
                        "time": str(entry.get("time", "10:00")),
                        "content_type": str(entry.get("content_type", "engagement")),
                        "brief": str(entry.get("brief", "")),
                        "channel": str(entry.get("channel", "facebook")),
                        "reason": str(entry.get("reason", "")),
                    })

        # Extract content mix
        raw_mix = parsed.get("content_mix", {})
        if isinstance(raw_mix, dict):
            content_mix = {str(k): int(v) for k, v in raw_mix.items() if isinstance(v, (int, float))}

        # Extract tips
        raw_tips = parsed.get("tips", [])
        if isinstance(raw_tips, list):
            tips = [str(t) for t in raw_tips if t]

        return calendar, content_mix, tips

    @staticmethod
    def _compute_confidence(calendar: list[dict], content_mix: dict) -> float:
        """Score the quality of the generated strategy."""
        score = 0.7  # Base confidence

        # Must have at least 5 entries
        if len(calendar) < 5:
            score -= 0.2
        elif len(calendar) > 7:
            score -= 0.1

        # Check that entries have all required fields
        required_fields = {"day", "time", "content_type", "brief", "channel", "reason"}
        for entry in calendar:
            missing = required_fields - set(entry.keys())
            if missing:
                score -= 0.05

        # Check content type validity
        for entry in calendar:
            if entry.get("content_type") not in VALID_CONTENT_TYPES:
                score -= 0.05

        # Check channel validity
        for entry in calendar:
            if entry.get("channel") not in VALID_CHANNELS:
                score -= 0.05

        # Check content mix diversity (at least 3 different types)
        types_used = {e.get("content_type") for e in calendar}
        if len(types_used) < 3:
            score -= 0.15

        # Check we have a content_mix dict
        if not content_mix:
            score -= 0.1

        # Briefs should be meaningful (> 20 chars)
        short_briefs = sum(1 for e in calendar if len(e.get("brief", "")) < 20)
        if short_briefs > 0:
            score -= 0.05 * short_briefs

        return max(0.0, min(1.0, score))

    async def validate_output(self, result: AgentResult) -> bool:
        calendar = result.output.get("calendar", [])
        if not calendar or len(calendar) < 3:
            return False
        # Each entry must have a non-empty brief
        for entry in calendar:
            if not entry.get("brief"):
                return False
        if result.confidence_score is not None and result.confidence_score < 0.3:
            return False
        return True
