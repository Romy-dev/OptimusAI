
"""Design Analyzer agent — uses VLM to extract comprehensive Design DNA from reference posters.

Extracts EVERYTHING: layout, typography, colors, decorative elements, composition rules,
visual hierarchy, mood, spacing, effects, and more. This DNA is then used by the
PosterAgent to generate new posters that match the client's visual identity.
"""

import json
import re

import structlog

from app.agents.base import AgentResult, BaseAgent

logger = structlog.get_logger()

# Maximum extraction prompt — we want EVERYTHING from the image
ANALYSIS_SYSTEM = """Tu es un directeur artistique senior spécialisé en design publicitaire.
Tu analyses des affiches marketing avec une précision chirurgicale pour en extraire
CHAQUE détail de design qui pourrait être reproduit.

Tu dois être EXHAUSTIF — chaque pixel compte."""

ANALYSIS_PROMPT = """Analyse cette affiche/poster marketing en profondeur et retourne un JSON complet.

## INSTRUCTIONS CRITIQUES
- Analyse CHAQUE aspect visuel de cette image
- Sois PRÉCIS sur les positions (pourcentages), les tailles (ratios), les couleurs (hex)
- Si tu n'es pas sûr d'un élément, donne ta meilleure estimation avec un champ "confidence"

## JSON À RETOURNER (respecte EXACTEMENT cette structure)

```json
{
  "layout": {
    "type": "text_over_image | text_beside_image | text_below_image | split_layout | framed | floating_text | full_overlay",
    "orientation": "portrait | landscape | square",
    "text_zone": {
      "position": "top | center | bottom | left | right | top_left | top_right | bottom_left | bottom_right",
      "coverage_percent": 30,
      "alignment": "left | center | right"
    },
    "image_zone": {
      "coverage_percent": 70,
      "position": "background | left | right | top | center",
      "cropping": "full_bleed | contained | circular | masked"
    },
    "margins": {
      "top_percent": 5,
      "bottom_percent": 5,
      "left_percent": 5,
      "right_percent": 5
    },
    "grid": "single_column | two_columns | asymmetric | free_form",
    "visual_weight": "top_heavy | bottom_heavy | centered | balanced"
  },

  "typography": {
    "headline": {
      "font_category": "sans_serif | serif | display | handwritten | slab",
      "font_weight": "thin | light | regular | medium | semibold | bold | black",
      "font_style": "normal | italic | uppercase | small_caps",
      "size_ratio": 0.08,
      "letter_spacing": "tight | normal | wide | very_wide",
      "line_height": "compact | normal | relaxed",
      "estimated_font": "Montserrat | Poppins | Playfair Display | Oswald | Roboto | Lora | Bebas Neue | Impact | autre",
      "max_words": 6,
      "text_transform": "uppercase | capitalize | none"
    },
    "subheadline": {
      "font_category": "sans_serif | serif",
      "font_weight": "light | regular | medium",
      "size_ratio": 0.04,
      "letter_spacing": "normal | wide",
      "estimated_font": "string",
      "max_words": 15
    },
    "body_text": {
      "present": true,
      "font_category": "sans_serif | serif",
      "size_ratio": 0.025,
      "max_lines": 3
    },
    "cta_text": {
      "present": true,
      "font_weight": "semibold | bold",
      "text_transform": "uppercase | capitalize | none",
      "max_words": 4
    },
    "hierarchy_levels": 3,
    "contrast_with_background": "high | medium | low"
  },

  "colors": {
    "palette": [
      {"hex": "#FFFFFF", "role": "text_primary", "coverage_percent": 10},
      {"hex": "#000000", "role": "background", "coverage_percent": 40},
      {"hex": "#D4A574", "role": "accent", "coverage_percent": 5}
    ],
    "dominant_color": "#hex",
    "accent_color": "#hex",
    "text_color_primary": "#hex",
    "text_color_secondary": "#hex",
    "background_treatment": "solid | gradient | image | pattern",
    "gradient_direction": "top_to_bottom | left_to_right | diagonal | radial | none",
    "overlay": {
      "type": "gradient | solid | none",
      "color": "#000000",
      "opacity_percent": 50,
      "direction": "bottom_to_top | top_to_bottom | left | right | center_out"
    },
    "color_temperature": "warm | cool | neutral",
    "color_harmony": "complementary | analogous | triadic | monochromatic | split_complementary"
  },

  "elements": {
    "logo": {
      "present": true,
      "position": "top_left | top_right | top_center | bottom_left | bottom_right | bottom_center | center",
      "size_ratio": 0.05,
      "style": "full_color | monochrome | reversed"
    },
    "cta_button": {
      "present": true,
      "style": "filled | outlined | text_only | pill | rectangle | rounded",
      "color": "#hex",
      "text_color": "#hex",
      "position": "bottom_center | bottom_left | center",
      "has_shadow": false,
      "has_icon": false
    },
    "price_badge": {
      "present": false,
      "style": "circle | starburst | rectangle | ribbon | slash",
      "color": "#hex",
      "position": "top_right | top_left | center"
    },
    "decorative": {
      "lines": {"present": false, "style": "thin | thick | dotted | double", "position": "separator | border | accent"},
      "shapes": {"present": false, "types": ["circle", "rectangle", "triangle", "blob"]},
      "patterns": {"present": false, "type": "geometric | organic | dots | stripes"},
      "icons": {"present": false, "style": "outline | filled | emoji"},
      "borders": {"present": false, "style": "solid | dashed | double | rounded", "radius": "none | small | medium | large"},
      "shadows": {"present": false, "type": "drop | inner | text | box"}
    },
    "social_media_handles": {"present": false, "position": "bottom"},
    "qr_code": {"present": false},
    "contact_info": {"present": false, "type": "phone | email | website | address"}
  },

  "composition": {
    "rule_of_thirds": true,
    "focal_point": "center | top_third | bottom_third | left_third | right_third",
    "visual_flow": "top_to_bottom | left_to_right | Z_pattern | F_pattern | circular",
    "whitespace_percent": 20,
    "density": "minimal | balanced | dense | cluttered",
    "symmetry": "symmetric | asymmetric | radial",
    "depth": "flat | layered | 3d_effect"
  },

  "photography": {
    "present": true,
    "style": "studio | lifestyle | product | portrait | landscape | abstract | flat_lay",
    "lighting": "natural | studio | dramatic | soft | backlit | golden_hour",
    "subject": "description of the main subject",
    "background_blur": "none | subtle | heavy",
    "color_grading": "natural | vintage | high_contrast | muted | vibrant | warm_tone | cool_tone",
    "filter_effect": "none | grain | vignette | desaturated | duotone"
  },

  "mood_and_style": {
    "overall_mood": "luxury | playful | urgent | professional | warm | minimalist | bold | festive | elegant | edgy",
    "energy_level": "calm | moderate | high | explosive",
    "target_audience": "young_adults | professionals | families | luxury | mass_market",
    "industry_fit": "fashion | food | tech | beauty | real_estate | events | retail | services",
    "design_era": "modern | retro | vintage | futuristic | classic | trendy",
    "cultural_context": "african | western | universal | local"
  },

  "text_content_detected": {
    "headline": "texte du titre detecte",
    "subheadline": "texte du sous-titre",
    "cta": "texte du bouton",
    "other_text": ["liste", "des", "autres", "textes"],
    "language": "fr | en | mixed"
  },

  "quality_assessment": {
    "overall_score": 8,
    "strengths": ["good typography", "strong color contrast"],
    "weaknesses": ["text slightly hard to read"],
    "professional_level": "amateur | semi_pro | professional | agency"
  }
}
```

RETOURNE UNIQUEMENT LE JSON — pas de texte avant ou après."""


class DesignAnalyzerAgent(BaseAgent):
    name = "design_analyzer"
    description = "Extracts comprehensive Design DNA from reference posters using VLM"
    max_retries = 1
    confidence_threshold = 0.4

    async def execute(self, context: dict) -> AgentResult:
        from app.integrations.vlm import get_vlm_router
        import time

        image_data = context.get("image_data")  # bytes
        image_url = context.get("image_url")  # URL to download

        if not image_data and not image_url:
            return AgentResult(
                success=False,
                output={"error": "No image provided (image_data or image_url required)"},
                agent_name=self.name,
            )

        # Download image if URL provided
        if not image_data and image_url:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(image_url)
                resp.raise_for_status()
                image_data = resp.content

        start = time.perf_counter()

        # Call VLM for deep analysis
        vlm = get_vlm_router()
        response = await vlm.analyze_image(
            image_data=image_data,
            prompt=ANALYSIS_PROMPT,
            system=ANALYSIS_SYSTEM,
        )

        latency = int((time.perf_counter() - start) * 1000)

        # Parse JSON from VLM response
        design_dna = self._parse_dna(response.content)

        if not design_dna:
            logger.warning("design_dna_parse_failed", raw=response.content[:500])
            return AgentResult(
                success=False,
                output={"error": "Failed to parse design DNA from VLM response", "raw": response.content[:1000]},
                agent_name=self.name,
            )

        logger.info(
            "design_dna_extracted",
            layout_type=design_dna.get("layout", {}).get("type"),
            mood=design_dna.get("mood_and_style", {}).get("overall_mood"),
            elements=len(design_dna.get("elements", {})),
            latency_ms=latency,
        )

        return AgentResult(
            success=True,
            output={
                "design_dna": design_dna,
                "model_used": response.model,
                "tokens_used": response.tokens_used,
            },
            confidence_score=self._compute_confidence(design_dna),
            agent_name=self.name,
            execution_time_ms=latency,
        )

    def _parse_dna(self, raw: str) -> dict | None:
        """Robustly extract JSON from VLM response."""
        cleaned = raw.strip()

        # Strip markdown fences
        if "```" in cleaned:
            parts = cleaned.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    try:
                        return json.loads(part)
                    except json.JSONDecodeError:
                        continue

        # Try direct parse
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Find JSON object in text
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        return None

    def _compute_confidence(self, dna: dict) -> float:
        """Score completeness of extracted DNA."""
        score = 0.5  # base

        # Check key sections are present and populated
        sections = ["layout", "typography", "colors", "elements", "composition", "mood_and_style"]
        for section in sections:
            if section in dna and isinstance(dna[section], dict) and len(dna[section]) > 0:
                score += 0.08

        # Bonus for detailed sub-sections
        if dna.get("typography", {}).get("headline", {}).get("estimated_font"):
            score += 0.05
        if dna.get("colors", {}).get("palette") and len(dna["colors"]["palette"]) >= 3:
            score += 0.05
        if dna.get("text_content_detected", {}).get("headline"):
            score += 0.03

        return min(1.0, score)

    async def validate_output(self, result: AgentResult) -> bool:
        if not result.success:
            return False
        dna = result.output.get("design_dna", {})
        return bool(dna.get("layout")) and bool(dna.get("colors"))


class DesignDNAMerger:
    """Merges Design DNA from multiple templates into a unified brand DNA."""

    @staticmethod
    def merge(templates_dna: list[dict], weights: list[float] | None = None) -> dict:
        """Merge multiple Design DNAs into a unified brand DNA.

        Picks the most frequent values for categorical fields,
        averages numerical fields, and unions list fields.
        """
        if not templates_dna:
            return {}
        if len(templates_dna) == 1:
            return templates_dna[0]

        if not weights:
            weights = [1.0] * len(templates_dna)

        merged = {}

        # Layout — pick most common type
        layout_types = [d.get("layout", {}).get("type", "") for d in templates_dna]
        merged["layout"] = templates_dna[0].get("layout", {}).copy()
        if layout_types:
            merged["layout"]["preferred_type"] = max(set(layout_types), key=layout_types.count)

        # Typography — pick most common font suggestions
        merged["typography"] = templates_dna[0].get("typography", {}).copy()
        fonts = [d.get("typography", {}).get("headline", {}).get("estimated_font", "") for d in templates_dna]
        fonts = [f for f in fonts if f]
        if fonts:
            merged["typography"]["preferred_headline_font"] = max(set(fonts), key=fonts.count)

        # Colors — aggregate palette
        all_colors = []
        for dna in templates_dna:
            palette = dna.get("colors", {}).get("palette", [])
            all_colors.extend(palette)

        # Deduplicate colors by role
        color_by_role: dict[str, list[str]] = {}
        for c in all_colors:
            role = c.get("role", "unknown")
            color_by_role.setdefault(role, []).append(c.get("hex", "#000000"))

        merged["colors"] = templates_dna[0].get("colors", {}).copy()
        merged["colors"]["aggregated_palette"] = {
            role: max(set(hexes), key=hexes.count) for role, hexes in color_by_role.items()
        }

        # Moods — collect all
        moods = [d.get("mood_and_style", {}).get("overall_mood", "") for d in templates_dna]
        moods = [m for m in moods if m]
        merged["mood_and_style"] = templates_dna[0].get("mood_and_style", {}).copy()
        merged["mood_and_style"]["mood_keywords"] = list(set(moods))

        # Elements — union of decorative elements
        merged["elements"] = templates_dna[0].get("elements", {}).copy()

        # Composition
        merged["composition"] = templates_dna[0].get("composition", {}).copy()

        # Photography style
        photo_styles = [d.get("photography", {}).get("style", "") for d in templates_dna]
        photo_styles = [s for s in photo_styles if s]
        merged["photography"] = templates_dna[0].get("photography", {}).copy()
        if photo_styles:
            merged["photography"]["preferred_styles"] = list(set(photo_styles))

        merged["template_count"] = len(templates_dna)

        return merged
