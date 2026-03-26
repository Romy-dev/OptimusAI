"""Trend Surfer Agent — monitors trending topics and generates timely content.

Scans trending hashtags, events, and cultural moments to create
viral content that ties the brand to current conversations.
"""

import json
from datetime import datetime, timezone

import structlog

from app.agents.base import AgentResult, BaseAgent
from app.integrations.llm import get_llm_router

logger = structlog.get_logger()

# Cultural calendar for West Africa
CULTURAL_CALENDAR = {
    "01-01": {"event": "Nouvel An", "mood": "festive", "type": "celebration"},
    "01-03": {"event": "Anniversaire Insurrection populaire BF", "mood": "patriotic", "type": "national"},
    "02-14": {"event": "Saint-Valentin", "mood": "romantic", "type": "commercial"},
    "03-08": {"event": "Journée de la Femme", "mood": "inspiring", "type": "social"},
    "03-10": {"event": "Ramadan (approx)", "mood": "spiritual", "type": "religious"},
    "04-10": {"event": "Eid al-Fitr (approx)", "mood": "festive", "type": "religious"},
    "05-01": {"event": "Fête du Travail", "mood": "solidarity", "type": "national"},
    "05-25": {"event": "Journée de l'Afrique", "mood": "patriotic", "type": "continental"},
    "06-17": {"event": "Eid al-Adha (approx)", "mood": "festive", "type": "religious"},
    "08-05": {"event": "Fête de l'Indépendance BF", "mood": "patriotic", "type": "national"},
    "08-07": {"event": "Fête de l'Indépendance CI", "mood": "patriotic", "type": "national"},
    "09-01": {"event": "Rentrée scolaire", "mood": "dynamic", "type": "commercial"},
    "10-15": {"event": "FESPACO (approx)", "mood": "cultural", "type": "cultural"},
    "10-31": {"event": "Halloween", "mood": "playful", "type": "commercial"},
    "11-01": {"event": "Toussaint", "mood": "solemn", "type": "religious"},
    "11-25": {"event": "Black Friday", "mood": "urgent", "type": "commercial"},
    "12-25": {"event": "Noël", "mood": "festive", "type": "celebration"},
    "12-31": {"event": "Saint-Sylvestre", "mood": "festive", "type": "celebration"},
}

TREND_PROMPT = """Tu es un expert en marketing viral et tendances sur les réseaux sociaux en Afrique de l'Ouest.

## CONTEXTE
- Marque: {brand_name}
- Secteur: {industry}
- Pays: {country}
- Date: {today}
- Plateforme: {platform}

## ÉVÉNEMENT / TENDANCE DÉTECTÉE
{trend_info}

## MISSION
Crée un contenu marketing qui surfe sur cette tendance tout en restant pertinent pour la marque.
Le contenu doit être naturel, pas forcé — le lien avec la marque doit sembler évident.

## FORMAT JSON
```json
{{
  "post_text": "texte du post (max 200 caractères)",
  "hashtags": ["#hashtag1", "#hashtag2"],
  "image_brief": "description de l'image à générer pour accompagner le post",
  "story_brief": "brief pour une story de 4 slides sur ce sujet",
  "relevance_score": 0.8,
  "timing": "publier maintenant | publier demain matin | planifier pour le jour J",
  "tone": "description du ton à utiliser"
}}
```"""


class TrendSurferAgent(BaseAgent):
    """Detects trends and generates timely content tied to the brand."""

    name = "trend_surfer"
    description = "Détecte les tendances et génère du contenu viral contextuel"
    max_retries = 1
    confidence_threshold = 0.5

    async def execute(self, context: dict) -> AgentResult:
        llm = get_llm_router()

        brand_name = context.get("brand_name", "")
        industry = context.get("industry", "")
        country = context.get("country", "Burkina Faso")
        platform = context.get("platform", "facebook")

        # Detect current and upcoming trends
        trends = self._detect_trends(country)

        if not trends:
            return AgentResult(
                success=True,
                output={"trends": [], "suggestions": [], "message": "Aucune tendance détectée aujourd'hui"},
                confidence_score=0.5,
                agent_name=self.name,
            )

        # Generate content for each trend
        suggestions = []
        for trend in trends[:3]:  # Top 3 trends
            try:
                response = await llm.generate(
                    task_type="copywriting",
                    messages=[
                        {"role": "system", "content": TREND_PROMPT.format(
                            brand_name=brand_name,
                            industry=industry,
                            country=country,
                            today=datetime.now().strftime("%d/%m/%Y"),
                            platform=platform,
                            trend_info=json.dumps(trend, ensure_ascii=False),
                        )},
                        {"role": "user", "content": f"Crée un contenu pour surfer sur: {trend['event']}"},
                    ],
                    temperature=0.8,
                )

                raw = response.content.strip()
                if "```json" in raw:
                    raw = raw.split("```json")[1].split("```")[0]
                elif "```" in raw:
                    raw = raw.split("```")[1].split("```")[0]

                suggestion = json.loads(raw)
                suggestion["trend"] = trend
                suggestions.append(suggestion)
            except Exception as e:
                logger.warning("trend_content_failed", trend=trend["event"], error=str(e)[:80])

        return AgentResult(
            success=True,
            output={
                "trends": trends,
                "suggestions": suggestions,
                "upcoming_events": self._get_upcoming_events(7),
            },
            confidence_score=0.8,
            agent_name=self.name,
        )

    def _detect_trends(self, country: str) -> list[dict]:
        """Detect current trends based on cultural calendar + date."""
        now = datetime.now(timezone.utc)
        today_key = now.strftime("%m-%d")
        trends = []

        # Check today's events
        if today_key in CULTURAL_CALENDAR:
            event = CULTURAL_CALENDAR[today_key]
            trends.append({
                **event,
                "urgency": "now",
                "days_until": 0,
            })

        # Check upcoming events (next 3 days)
        for offset in range(1, 4):
            from datetime import timedelta
            future = now + timedelta(days=offset)
            future_key = future.strftime("%m-%d")
            if future_key in CULTURAL_CALENDAR:
                event = CULTURAL_CALENDAR[future_key]
                trends.append({
                    **event,
                    "urgency": "upcoming",
                    "days_until": offset,
                })

        # Day-of-week trends
        weekday = now.weekday()
        if weekday == 4:  # Friday
            trends.append({
                "event": "Djouma / Vendredi",
                "mood": "spiritual",
                "type": "weekly",
                "urgency": "now",
                "days_until": 0,
            })
        elif weekday == 5:  # Saturday
            trends.append({
                "event": "Weekend Shopping",
                "mood": "commercial",
                "type": "weekly",
                "urgency": "now",
                "days_until": 0,
            })

        # Beginning/End of month
        if now.day <= 3:
            trends.append({
                "event": "Début de mois / Paie",
                "mood": "commercial",
                "type": "monthly",
                "urgency": "now",
                "days_until": 0,
            })
        elif now.day >= 28:
            trends.append({
                "event": "Fin de mois",
                "mood": "urgent",
                "type": "monthly",
                "urgency": "now",
                "days_until": 0,
            })

        return trends

    def _get_upcoming_events(self, days: int = 7) -> list[dict]:
        """Get events in the next N days."""
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        events = []
        for offset in range(days):
            d = now + timedelta(days=offset)
            key = d.strftime("%m-%d")
            if key in CULTURAL_CALENDAR:
                events.append({
                    **CULTURAL_CALENDAR[key],
                    "date": d.strftime("%d/%m/%Y"),
                    "days_until": offset,
                })
        return events
