"""Story Agent — generates multi-slide Instagram/Facebook/WhatsApp stories.

Produces a complete story sequence (3-5 slides) with:
- Hook slide (attention grabber)
- Detail slides (product, offer, benefits)
- Social proof / urgency slide
- CTA slide (call to action)

Each slide is rendered as a 1080x1920 (9:16) image.
Optionally assembled into a 15s video with transitions and music.
"""

import json
import uuid
import random
import structlog

from app.agents.base import AgentResult, BaseAgent
from app.integrations.llm import get_llm_router

logger = structlog.get_logger()

# Slide roles and their purpose
SLIDE_ROLES = {
    "hook": {
        "purpose": "Capturer l'attention en 1 seconde",
        "max_words": 5,
        "text_size": "extra_large",
        "duration_s": 3,
    },
    "detail": {
        "purpose": "Présenter le produit/service/offre",
        "max_words": 15,
        "text_size": "large",
        "duration_s": 4,
    },
    "proof": {
        "purpose": "Preuve sociale, témoignage, chiffres",
        "max_words": 20,
        "text_size": "medium",
        "duration_s": 3,
    },
    "urgency": {
        "purpose": "Créer l'urgence (countdown, stock limité)",
        "max_words": 10,
        "text_size": "large",
        "duration_s": 3,
    },
    "cta": {
        "purpose": "Appel à l'action clair",
        "max_words": 8,
        "text_size": "extra_large",
        "duration_s": 3,
    },
}

STORY_PLANNER_PROMPT = """Tu es un expert en création de Stories pour les réseaux sociaux.
Tu crées des séquences de slides captivantes qui génèrent de l'engagement.

## CONTEXTE
- Marque : {brand_name}
- Secteur : {industry}
- Pays : {country}
- Langue : {language}
- Plateforme : {platform}

## BRIEF
{brief}

## RÈGLES
1. Chaque story fait 3 à 5 slides
2. Slide 1 = HOOK (5 mots max, gros texte, accrocheur)
3. Slides intermédiaires = DETAIL ou PROOF (produit, offre, témoignage)
4. Dernier slide = CTA (appel à l'action clair)
5. Le texte doit être COURT et IMPACTANT (format vertical, on lit vite)
6. Utilise des emojis avec pertinence
7. Adapte le ton à la plateforme ({platform})
8. Pense MOBILE FIRST — gros texte, couleurs vives

## FORMAT JSON OBLIGATOIRE
```json
{{
  "story_title": "titre interne de la story",
  "total_slides": 4,
  "mood": "energetic | elegant | warm | urgent | playful",
  "color_scheme": {{
    "primary": "#hex",
    "secondary": "#hex",
    "text": "#hex",
    "accent": "#hex"
  }},
  "music_mood": "upbeat | chill | dramatic | inspiring | festive",
  "slides": [
    {{
      "role": "hook | detail | proof | urgency | cta",
      "headline": "TEXTE PRINCIPAL",
      "subtext": "texte secondaire optionnel",
      "background_prompt": "description de l'image de fond pour cette slide",
      "emoji": "🔥",
      "text_position": "center | top | bottom",
      "animation": "fade_in | slide_up | zoom_in | bounce | none",
      "sticker": "countdown | poll | swipe_up | none",
      "duration_s": 3
    }}
  ]
}}
```"""


class StoryAgent(BaseAgent):
    """Generates complete multi-slide story sequences."""

    name = "story"
    description = "Crée des séquences de stories multi-slides pour Instagram, Facebook et WhatsApp"
    max_retries = 1
    confidence_threshold = 0.5

    async def execute(self, context: dict) -> AgentResult:
        llm = get_llm_router()

        brief = context.get("brief", "")
        brand = context.get("brand_context", {})
        platform = context.get("platform", "instagram")

        if not brief:
            return AgentResult(
                success=False,
                output={"error": "Brief requis pour générer une story"},
                agent_name=self.name,
            )

        prompt = STORY_PLANNER_PROMPT.format(
            brand_name=brand.get("brand_name", context.get("brand_name", "")),
            industry=brand.get("industry", context.get("industry", "")),
            country=brand.get("target_country", context.get("country", "")),
            language=brand.get("language", context.get("language", "français")),
            platform=platform,
            brief=brief,
        )

        response = await llm.generate(
            task_type="copywriting",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Crée une story complète pour: {brief}"},
            ],
            temperature=0.8,
        )

        # Parse the story plan
        try:
            raw = response.content.strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0]
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0]
            story_plan = json.loads(raw)
        except Exception as e:
            logger.warning("story_plan_parse_failed", error=str(e))
            # Fallback plan
            story_plan = self._fallback_plan(brief, brand)

        # Validate and enrich slides
        slides = story_plan.get("slides", [])
        if len(slides) < 3:
            slides = self._fallback_plan(brief, brand)["slides"]
        if len(slides) > 6:
            slides = slides[:6]

        # Ensure each slide has required fields
        for i, slide in enumerate(slides):
            slide.setdefault("role", "detail" if 0 < i < len(slides) - 1 else ("hook" if i == 0 else "cta"))
            slide.setdefault("headline", brief[:30])
            slide.setdefault("subtext", "")
            slide.setdefault("background_prompt", f"Professional {brand.get('industry', 'business')} photo")
            slide.setdefault("text_position", "center")
            slide.setdefault("animation", "fade_in")
            slide.setdefault("duration_s", SLIDE_ROLES.get(slide["role"], {}).get("duration_s", 3))
            slide.setdefault("sticker", "none")

        story_plan["slides"] = slides
        total_duration = sum(s.get("duration_s", 3) for s in slides)

        return AgentResult(
            success=True,
            output={
                "story_plan": story_plan,
                "total_slides": len(slides),
                "total_duration_s": total_duration,
                "platform": platform,
                "music_mood": story_plan.get("music_mood", "upbeat"),
            },
            confidence_score=0.85,
            agent_name=self.name,
            tokens_used=response.tokens_used,
            model_used=response.model,
        )

    def _fallback_plan(self, brief: str, brand: dict) -> dict:
        """Generate a basic story plan without LLM."""
        brand_name = brand.get("brand_name", "")
        words = brief.split()
        hook = " ".join(words[:4]).upper() if len(words) >= 4 else brief[:20].upper()

        return {
            "story_title": brief[:50],
            "total_slides": 4,
            "mood": "energetic",
            "color_scheme": {
                "primary": "#0D9488",
                "secondary": "#1a1a2e",
                "text": "#FFFFFF",
                "accent": "#F59E0B",
            },
            "music_mood": "upbeat",
            "slides": [
                {
                    "role": "hook",
                    "headline": f"🔥 {hook}",
                    "subtext": "",
                    "background_prompt": f"Dynamic {brand.get('industry', 'business')} photo, vibrant",
                    "text_position": "center",
                    "animation": "zoom_in",
                    "duration_s": 3,
                    "sticker": "none",
                },
                {
                    "role": "detail",
                    "headline": brief[:40],
                    "subtext": brand_name,
                    "background_prompt": f"Product showcase for {brand_name}",
                    "text_position": "bottom",
                    "animation": "slide_up",
                    "duration_s": 4,
                    "sticker": "none",
                },
                {
                    "role": "urgency",
                    "headline": "⏰ Offre limitée !",
                    "subtext": "Ne ratez pas cette opportunité",
                    "background_prompt": "Countdown timer background, urgent colors",
                    "text_position": "center",
                    "animation": "bounce",
                    "duration_s": 3,
                    "sticker": "countdown",
                },
                {
                    "role": "cta",
                    "headline": "👉 Commander maintenant",
                    "subtext": f"@{brand_name.lower().replace(' ', '')}",
                    "background_prompt": f"Call to action background, {brand.get('industry', '')} theme",
                    "text_position": "center",
                    "animation": "fade_in",
                    "duration_s": 3,
                    "sticker": "swipe_up",
                },
            ],
        }
