"""Poster/Affiche agent — generates marketing visuals guided by brand Design DNA.

When a brand has a Design DNA (extracted from reference posters via VLM), the agent
uses it to drive *every* composition decision: overlay, palette, typography, layout,
decorative elements, and CTA style.  When no DNA exists it falls back to an LLM-planned
layout with sensible defaults.

Combines AI-generated background images with professional text overlays,
brand colors, logos, and call-to-actions using Pillow compositing.
"""

import io
import math
import os
import uuid
from pathlib import Path
from typing import Any

import structlog
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from sqlalchemy import select

from app.agents.base import AgentResult, BaseAgent
from app.core.database import async_session_factory
from app.core.storage import storage_service
from app.integrations.image_gen import get_image_gen_client, ImageGenRequest, download_image

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Prompt — DNA-aware
# ---------------------------------------------------------------------------

def _get_poster_prompt(language: str = "français") -> str:
    """Load the poster system prompt from the Jinja2 template."""
    from app.prompts.loader import get_prompt_manager
    return get_prompt_manager().get_prompt("poster", "system", language=language)

DNA_STYLE_SECTION = """

=== DESIGN DNA ===
Cette marque a un style visuel précis. Adapte ta réponse en conséquence:
- Ambiance / mood: {mood}
- Style typographique: {typo_style}
- Positionnement du texte: {text_position}
- Style du CTA: {cta_style}
- Éléments décoratifs: {decorative}
- Palette dominante: {palette_summary}

Le "background_prompt" doit refléter cette ambiance.  Le "layout" doit correspondre
au positionnement du texte ({text_position}).
"""

# ---------------------------------------------------------------------------
# Font resolution
# ---------------------------------------------------------------------------

_FONT_SEARCH_PATHS: list[tuple[str, str]] = [
    # Linux / Docker (DejaVu)
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    # macOS system fonts
    ("/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Helvetica.ttc"),
    ("/System/Library/Fonts/SFNSDisplay.ttf", "/System/Library/Fonts/SFNSText.ttf"),
]


def _resolve_fonts() -> tuple[str | None, str | None]:
    """Return (bold_path, regular_path) or (None, None) for default fallback."""
    for bold, regular in _FONT_SEARCH_PATHS:
        if os.path.isfile(bold) and os.path.isfile(regular):
            return bold, regular
    return None, None


def _load_font(path: str | None, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if path is None:
        return ImageFont.load_default()
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return (13, 148, 136)  # default teal
    return (int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))


def _hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    r, g, b = _hex_to_rgb(hex_color)
    return (r, g, b, alpha)


def _darken(rgb: tuple[int, int, int], factor: float = 0.6) -> tuple[int, int, int]:
    r, g, b = rgb
    return (max(0, int(r * factor)), max(0, int(g * factor)), max(0, int(b * factor)))


def _lighten(rgb: tuple[int, int, int], factor: float = 0.4) -> tuple[int, int, int]:
    r, g, b = rgb
    return (min(255, int(r + (255 - r) * factor)), min(255, int(g + (255 - g) * factor)), min(255, int(b + (255 - b) * factor)))


def _luminance(rgb: tuple[int, int, int]) -> float:
    """Relative luminance per WCAG."""
    r, g, b = [c / 255.0 for c in rgb]
    r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
    g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
    b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_text_color(bg_rgb: tuple[int, int, int]) -> tuple[int, int, int, int]:
    """Return white or dark text for best contrast on *bg_rgb*."""
    if _luminance(bg_rgb) > 0.45:
        return (30, 30, 30, 255)
    return (255, 255, 255, 255)


# ---------------------------------------------------------------------------
# DNA helpers — safely extract nested keys
# ---------------------------------------------------------------------------

def _dna_get(dna: dict, *keys: str, default: Any = None) -> Any:
    """Drill into nested dict: _dna_get(dna, 'layout', 'text_position', default='bottom')."""
    node = dna
    for k in keys:
        if not isinstance(node, dict):
            return default
        node = node.get(k)
        if node is None:
            return default
    return node


# ---------------------------------------------------------------------------
# PosterAgent
# ---------------------------------------------------------------------------

class PosterAgent(BaseAgent):
    name = "poster"
    description = "Creates marketing posters with text overlays guided by brand Design DNA"
    max_retries = 1
    confidence_threshold = 0.5

    # ------------------------------------------------------------------
    # DB lookup
    # ------------------------------------------------------------------

    @staticmethod
    async def _fetch_design_dna(brand_id: str, tenant_id: str) -> dict | None:
        """Load the aggregated BrandDesignDNA for *brand_id* from the database."""
        from app.models.design_template import BrandDesignDNA

        try:
            async with async_session_factory() as session:
                stmt = (
                    select(BrandDesignDNA)
                    .where(
                        BrandDesignDNA.brand_id == brand_id,
                        BrandDesignDNA.tenant_id == tenant_id,
                    )
                )
                result = await session.execute(stmt)
                row = result.scalar_one_or_none()
                if row is None:
                    return None

                return {
                    "merged_dna": row.merged_dna or {},
                    "preferred_fonts": row.preferred_fonts or [],
                    "color_palette": row.color_palette or [],
                    "layout_preferences": row.layout_preferences or [],
                    "mood_keywords": row.mood_keywords or [],
                    "template_count": row.template_count or 0,
                }
        except Exception as exc:
            logger.warning("design_dna_fetch_failed", brand_id=brand_id, error=str(exc))
            return None

    # ------------------------------------------------------------------
    # System template fallback
    # ------------------------------------------------------------------

    @staticmethod
    async def _get_system_template_bg(industry: str, tenant_id: str) -> bytes | None:
        """Download a random system template image matching the industry as background."""
        import random
        from app.models.design_template import DesignTemplate

        try:
            async with async_session_factory() as session:
                # Find system templates for this industry
                industry_key = (industry or "generic").lower().strip()
                stmt = (
                    select(DesignTemplate)
                    .where(
                        DesignTemplate.analysis_status == "system_default",
                        DesignTemplate.s3_key.ilike(f"%/{industry_key}/%"),
                    )
                )
                result = await session.execute(stmt)
                templates = result.scalars().all()

                # Fallback to generic if no match
                if not templates:
                    stmt = (
                        select(DesignTemplate)
                        .where(
                            DesignTemplate.analysis_status == "system_default",
                            DesignTemplate.s3_key.ilike("%/generic/%"),
                        )
                    )
                    result = await session.execute(stmt)
                    templates = result.scalars().all()

                if not templates:
                    return None

                # Pick a random template
                chosen = random.choice(templates)
                import asyncio
                data = await asyncio.to_thread(
                    lambda: storage_service.client.get_object(
                        Bucket=storage_service.bucket, Key=chosen.s3_key
                    )["Body"].read()
                )
                logger.info("system_template_bg_used", s3_key=chosen.s3_key, size=len(data))
                return data

        except Exception as e:
            logger.warning("system_template_bg_failed", error=str(e))
            return None

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_prompt(dna: dict | None) -> str:
        """Return the system prompt, optionally enriched with DNA style guidance."""
        base = _get_poster_prompt()
        if dna is None:
            return base

        merged = dna.get("merged_dna", {})
        mood = ", ".join(dna.get("mood_keywords", [])) or "professional"
        typo = _dna_get(merged, "typography", "headline_style", default="bold uppercase")
        text_pos = _dna_get(merged, "layout", "text_position", default="bottom")
        cta_style = _dna_get(merged, "elements", "cta_style", default="rounded button")
        decorative = ", ".join(
            d.get("type", d) if isinstance(d, dict) else str(d)
            for d in _dna_get(merged, "elements", "decorative", default=[])
        ) or "aucun"
        palette_colors = [
            c.get("hex", c) if isinstance(c, dict) else str(c)
            for c in dna.get("color_palette", [])
        ]
        palette_summary = ", ".join(palette_colors[:5]) or "non spécifié"

        section = DNA_STYLE_SECTION.format(
            mood=mood,
            typo_style=typo,
            text_position=text_pos,
            cta_style=cta_style,
            decorative=decorative,
            palette_summary=palette_summary,
        )
        return base + section

    # ------------------------------------------------------------------
    # execute()
    # ------------------------------------------------------------------

    async def execute(self, context: dict) -> AgentResult:
        from app.integrations.llm import get_llm_router
        import json

        brief = context.get("brief", "")
        brand = context.get("brand_context", {})
        aspect_ratio = context.get("aspect_ratio", "1:1")
        brand_id = context.get("brand_id", brand.get("id", ""))
        tenant_id = context.get("tenant_id", "")
        colors = brand.get("colors", {})
        primary_color = colors.get("primary", "#0D9488")
        brand_name = brand.get("brand_name", "")

        if not brief:
            return AgentResult(success=False, output={"error": "No brief provided"}, agent_name=self.name)

        # 0. Fetch Design DNA ------------------------------------------------
        dna: dict | None = None
        if brand_id and tenant_id:
            dna = await self._fetch_design_dna(brand_id, tenant_id)
            if dna:
                logger.info(
                    "design_dna_loaded",
                    brand_id=brand_id,
                    template_count=dna.get("template_count"),
                    mood=dna.get("mood_keywords"),
                )

        # Fallback to industry-based default DNA if no client templates
        if dna is None:
            from app.agents.default_design_dna import get_default_dna
            industry = brand.get("industry", context.get("industry", ""))
            dna = get_default_dna(industry)
            logger.info(
                "default_design_dna_used",
                industry=industry or "generic",
                mood=dna.get("mood_keywords"),
            )

        # 1. Ask LLM to create poster layout + background prompt -------------
        system_prompt = self._build_prompt(dna)
        llm = get_llm_router()
        llm_response = await llm.generate(
            task_type="support",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Brief: {brief}\n"
                        f"Marque: {brand_name}\n"
                        f"Industrie: {brand.get('industry', '')}"
                    ),
                },
            ],
            temperature=0.7,
        )

        # Parse JSON from LLM response
        raw = llm_response.content.strip()
        try:
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            poster_plan = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("poster_plan_parse_failed", raw=raw[:200])
            poster_plan = {
                "background_prompt": (
                    f"Professional marketing photograph for {brand_name}, "
                    "vibrant colors, modern style, bokeh, 8k"
                ),
                "headline": brief[:30],
                "subheadline": f"Par {brand_name}" if brand_name else "",
                "cta_text": "Découvrir",
                "layout": "bottom",
            }

        # Override layout from DNA if present
        if dna:
            dna_text_pos = _dna_get(dna.get("merged_dna", {}), "layout", "text_position")
            if dna_text_pos:
                mapped = {"top": "top", "bottom": "bottom", "center": "center",
                          "bottom_left": "bottom", "bottom_right": "bottom",
                          "top_left": "top", "top_right": "top",
                          "center_left": "center", "center_right": "center"}
                poster_plan["layout"] = mapped.get(dna_text_pos, poster_plan.get("layout", "bottom"))

        logger.info("poster_plan", plan=poster_plan, has_dna=dna is not None)

        # 2. Generate the background image -----------------------------------
        bg_bytes = None
        try:
            client = get_image_gen_client()
            gen_request = ImageGenRequest(
                prompt=poster_plan.get("background_prompt", brief),
                aspect_ratio=aspect_ratio,
            )
            gen_response = await client.generate(gen_request)

            if gen_response.local_path:
                with open(gen_response.local_path, "rb") as f:
                    bg_bytes = f.read()
            else:
                bg_bytes = await download_image(gen_response.filename)
        except Exception as e:
            logger.warning("poster_bg_generation_failed_trying_template", error=str(e))

        # Fallback: use a system template image as background
        if bg_bytes is None:
            bg_bytes = await self._get_system_template_bg(
                brand.get("industry", context.get("industry", "")), tenant_id
            )

        if bg_bytes is None:
            return AgentResult(
                success=False,
                output={"error": "No background image available (FLUX and template fallback both failed)"},
                agent_name=self.name,
            )

        # 3. Composite text overlays onto the image --------------------------
        try:
            poster_bytes = self._compose_poster(
                bg_bytes=bg_bytes,
                headline=poster_plan.get("headline", ""),
                subheadline=poster_plan.get("subheadline", ""),
                cta_text=poster_plan.get("cta_text", ""),
                layout=poster_plan.get("layout", "bottom"),
                primary_color=primary_color,
                brand_name=brand_name,
                dna=dna,
            )
        except Exception as e:
            logger.error("poster_compose_failed", error=str(e))
            poster_bytes = bg_bytes  # fallback: raw image

        # 4. Upload to S3 ---------------------------------------------------
        s3_key = await storage_service.upload_file(
            file_data=poster_bytes,
            filename=f"poster_{uuid.uuid4().hex}.png",
            content_type="image/png",
            folder=f"brands/{brand.get('id', 'general')}/posters",
        )
        full_url = storage_service.get_public_url(s3_key)

        return AgentResult(
            success=True,
            output={
                "image_url": full_url,
                "s3_key": s3_key,
                "poster_plan": poster_plan,
                "type": "poster",
                "design_dna_used": dna is not None,
            },
            confidence_score=0.95 if dna else 0.85,
            agent_name=self.name,
        )

    # ======================================================================
    # COMPOSITION ENGINE
    # ======================================================================

    def _compose_poster(
        self,
        bg_bytes: bytes,
        headline: str,
        subheadline: str,
        cta_text: str,
        layout: str,
        primary_color: str,
        brand_name: str,
        dna: dict | None = None,
    ) -> bytes:
        """Compose text overlays on the background image.

        When *dna* is provided the entire composition is driven by the Design DNA:
        overlay type/direction/opacity, palette, typography rules, element placement,
        and decorative additions.  Without DNA it falls back to gradient + defaults.
        """
        img = Image.open(io.BytesIO(bg_bytes)).convert("RGBA")
        w, h = img.size

        merged = (dna or {}).get("merged_dna", {})
        palette = (dna or {}).get("color_palette", [])
        mood_keywords = (dna or {}).get("mood_keywords", [])

        # --- Resolve palette colours ----------------------------------------
        resolved_palette = self._resolve_palette(palette, primary_color)
        pc = _hex_to_rgb(resolved_palette["primary"])
        sc = _hex_to_rgb(resolved_palette["secondary"])
        ac = _hex_to_rgb(resolved_palette["accent"])
        text_primary_color = _hex_to_rgba(resolved_palette["text_primary"])
        text_secondary_color = _hex_to_rgba(resolved_palette["text_secondary"])

        # --- Overlay --------------------------------------------------------
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        self._draw_overlay(draw_ov, w, h, layout, merged, pc)
        img = Image.alpha_composite(img, overlay)

        # --- Decorative background elements (DNA-driven) --------------------
        if dna:
            deco_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            deco_draw = ImageDraw.Draw(deco_layer)
            self._draw_decorative_elements(deco_draw, w, h, merged, pc, sc, ac)
            img = Image.alpha_composite(img, deco_layer)

        draw = ImageDraw.Draw(img)

        # --- Typography setup -----------------------------------------------
        bold_path, regular_path = _resolve_fonts()

        typo = merged.get("typography", {})
        size_ratio = float(typo.get("headline_size_ratio", 0.08))
        headline_size = max(int(w * size_ratio), 28)
        sub_ratio = size_ratio * 0.55
        sub_size = max(int(w * sub_ratio), 18)
        cta_size = max(int(w * sub_ratio * 0.9), 16)
        brand_size = max(int(w * 0.035), 14)

        headline_font = _load_font(bold_path, headline_size)
        sub_font = _load_font(regular_path, sub_size)
        cta_font = _load_font(bold_path, cta_size)
        brand_font = _load_font(bold_path, brand_size)

        # --- Typography transforms (DNA) ------------------------------------
        headline_style = typo.get("headline_style", "bold uppercase")
        uppercase = "uppercase" in headline_style.lower() if isinstance(headline_style, str) else True
        letter_spacing = int(typo.get("letter_spacing", 0))

        display_headline = headline.upper() if uppercase else headline

        # --- Layout geometry ------------------------------------------------
        margin_x, margin_y, text_y, alignment = self._compute_layout_geometry(
            w, h, layout, headline_size, merged,
        )

        # --- Draw headline --------------------------------------------------
        if display_headline:
            text_y = self._draw_text_with_spacing(
                draw, display_headline, margin_x, text_y, w,
                headline_font, text_primary_color, letter_spacing, alignment,
            )
            text_y += int(headline_size * 0.25)

        # --- Draw subheadline -----------------------------------------------
        if subheadline:
            text_y = self._draw_text_with_spacing(
                draw, subheadline, margin_x, text_y, w,
                sub_font, text_secondary_color, max(letter_spacing - 1, 0), alignment,
            )
            text_y += int(sub_size * 0.7)

        # --- Draw CTA -------------------------------------------------------
        if cta_text:
            cta_style = _dna_get(merged, "elements", "cta_style", default="rounded_button")
            text_y = self._draw_cta(
                draw, cta_text, margin_x, text_y, w,
                cta_font, cta_style, pc, ac, alignment,
            )

        # --- Brand watermark -------------------------------------------------
        if brand_name:
            logo_pos = _dna_get(merged, "elements", "logo_position", default="top_right")
            self._draw_brand_watermark(draw, brand_name, w, h, margin_x, brand_font, pc, logo_pos)

        # --- Border / frame (DNA) -------------------------------------------
        if dna:
            self._draw_border(draw, w, h, merged, pc, ac)

        # --- Final output ---------------------------------------------------
        result = img.convert("RGB")
        buf = io.BytesIO()
        result.save(buf, format="PNG", quality=95)
        return buf.getvalue()

    # ------------------------------------------------------------------
    # Palette resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_palette(palette: list, fallback_primary: str) -> dict:
        """Build a dict with primary/secondary/accent/text_primary/text_secondary
        from the DNA colour palette.  Falls back to the brand's primary colour
        if the palette is empty or incomplete."""
        result = {
            "primary": fallback_primary,
            "secondary": "#333333",
            "accent": "#FFFFFF",
            "text_primary": "#FFFFFF",
            "text_secondary": "#FFFFFFCC",
        }
        if not palette:
            return result

        # palette items: {"hex": "#...", "role": "dominant", "frequency": 0.4}
        role_map: dict[str, str] = {}
        for entry in palette:
            if isinstance(entry, dict):
                role = entry.get("role", "")
                hex_val = entry.get("hex", "")
                if hex_val:
                    role_map[role] = hex_val
            elif isinstance(entry, str) and entry.startswith("#"):
                if "primary" not in role_map:
                    role_map["primary"] = entry

        if "dominant" in role_map:
            result["primary"] = role_map["dominant"]
        elif "primary" in role_map:
            result["primary"] = role_map["primary"]

        if "accent" in role_map:
            result["accent"] = role_map["accent"]
        elif "secondary" in role_map:
            result["accent"] = role_map["secondary"]

        if "secondary" in role_map:
            result["secondary"] = role_map["secondary"]

        if "text_primary" in role_map:
            result["text_primary"] = role_map["text_primary"]
        if "text_secondary" in role_map:
            result["text_secondary"] = role_map["text_secondary"]

        # Derive text colour from DNA overlay colour if specified
        overlay_type = ""
        for entry in palette:
            if isinstance(entry, dict) and entry.get("role") == "overlay":
                overlay_hex = entry.get("hex", "")
                if overlay_hex:
                    bg_rgb = _hex_to_rgb(overlay_hex)
                    result["text_primary"] = "#FFFFFF" if _luminance(bg_rgb) < 0.45 else "#1E1E1E"
                break

        return result

    # ------------------------------------------------------------------
    # Overlay drawing
    # ------------------------------------------------------------------

    def _draw_overlay(
        self,
        draw: ImageDraw.ImageDraw,
        w: int,
        h: int,
        layout: str,
        merged: dict,
        primary_rgb: tuple[int, int, int],
    ) -> None:
        """Draw a semi-transparent overlay that makes text readable.

        DNA fields used:
          colors.overlay_type   — "gradient", "solid", "vignette", "split"
          colors.overlay_opacity — 0.0 .. 1.0
          layout.type           — "split", "full_bleed", "framed", etc.
        """
        overlay_type = _dna_get(merged, "colors", "overlay_type", default="gradient")
        raw_opacity = _dna_get(merged, "colors", "overlay_opacity", default=0.55)
        try:
            opacity = float(raw_opacity)
        except (TypeError, ValueError):
            opacity = 0.55
        max_alpha = int(min(max(opacity, 0.0), 1.0) * 255)

        layout_type = _dna_get(merged, "layout", "type", default="")

        if overlay_type == "solid" or layout_type == "framed":
            # Solid colour band behind text area
            band_h = h // 3
            if layout == "bottom":
                y0 = h - band_h
                y1 = h
            elif layout == "top":
                y0 = 0
                y1 = band_h
            else:
                y0 = (h - band_h) // 2
                y1 = y0 + band_h
            draw.rectangle([0, y0, w, y1], fill=(*_darken(primary_rgb, 0.3), max_alpha))

        elif overlay_type == "vignette":
            # Radial-ish vignette (approximated with concentric rectangles)
            cx, cy = w // 2, h // 2
            steps = 60
            for i in range(steps):
                t = i / steps
                inset = int((1.0 - t) * min(w, h) * 0.45)
                alpha = int(max_alpha * (t ** 1.8))
                draw.rectangle(
                    [inset, inset, w - inset, h - inset],
                    outline=(0, 0, 0, alpha),
                )

        elif overlay_type == "split":
            # Left or bottom half gets a colour block
            if layout in ("bottom", "center"):
                for y in range(h // 2, h):
                    frac = (y - h // 2) / (h // 2)
                    alpha = int(max_alpha * frac)
                    draw.line([(0, y), (w, y)], fill=(*_darken(primary_rgb, 0.25), alpha))
            else:
                for y in range(0, h // 2):
                    frac = 1.0 - y / (h // 2)
                    alpha = int(max_alpha * frac)
                    draw.line([(0, y), (w, y)], fill=(*_darken(primary_rgb, 0.25), alpha))

        else:
            # Default gradient overlay
            if layout == "bottom":
                for y in range(h // 3, h):
                    frac = (y - h // 3) / (h - h // 3)
                    alpha = int(max_alpha * (frac ** 1.2))
                    draw.line([(0, y), (w, y)], fill=(0, 0, 0, min(alpha, max_alpha)))
            elif layout == "top":
                for y in range(0, h * 2 // 3):
                    frac = 1.0 - y / (h * 2 // 3)
                    alpha = int(max_alpha * (frac ** 1.2))
                    draw.line([(0, y), (w, y)], fill=(0, 0, 0, min(alpha, max_alpha)))
            else:
                for y in range(h):
                    dist = abs(y - h // 2) / (h // 2)
                    alpha = int(max_alpha * 0.7 * (1 - dist * 0.5))
                    draw.line([(0, y), (w, y)], fill=(0, 0, 0, max(0, alpha)))

    # ------------------------------------------------------------------
    # Layout geometry
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_layout_geometry(
        w: int,
        h: int,
        layout: str,
        headline_size: int,
        merged: dict,
    ) -> tuple[int, int, int, str]:
        """Return (margin_x, margin_y, start_text_y, alignment).

        DNA fields used:
          layout.alignment  — "left", "center", "right"
          layout.margins    — float ratio 0..1
        """
        dna_margins = _dna_get(merged, "layout", "margins")
        if dna_margins and isinstance(dna_margins, (int, float)):
            margin_x = max(int(w * float(dna_margins)), 20)
        else:
            margin_x = w // 12

        margin_y = margin_x

        alignment = _dna_get(merged, "layout", "alignment", default="left")
        if alignment not in ("left", "center", "right"):
            alignment = "left"

        if layout == "bottom":
            text_y = h - int(h * 0.38)
        elif layout == "top":
            text_y = margin_y + int(h * 0.05)
        else:  # center
            text_y = int(h * 0.32)

        return margin_x, margin_y, text_y, alignment

    # ------------------------------------------------------------------
    # Text drawing with letter-spacing + alignment
    # ------------------------------------------------------------------

    @staticmethod
    def _draw_text_with_spacing(
        draw: ImageDraw.ImageDraw,
        text: str,
        margin_x: int,
        y: int,
        canvas_w: int,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        color: tuple[int, ...],
        letter_spacing: int,
        alignment: str,
    ) -> int:
        """Draw *text* respecting letter spacing and alignment. Returns new y."""
        if not text:
            return y

        # Measure total width with spacing
        total_w = 0
        char_widths: list[int] = []
        for ch in text:
            bbox = draw.textbbox((0, 0), ch, font=font)
            cw = bbox[2] - bbox[0]
            char_widths.append(cw)
            total_w += cw
        total_w += letter_spacing * max(len(text) - 1, 0)

        usable_w = canvas_w - 2 * margin_x

        # Word-wrap if total exceeds usable width
        if total_w > usable_w and len(text) > 1:
            return PosterAgent._draw_wrapped_text(
                draw, text, margin_x, y, canvas_w, font, color, letter_spacing, alignment,
            )

        # Determine x based on alignment
        if alignment == "center":
            x = (canvas_w - total_w) // 2
        elif alignment == "right":
            x = canvas_w - margin_x - total_w
        else:
            x = margin_x

        # Draw with shadow for legibility
        shadow_offset = max(2, font.size // 30) if hasattr(font, "size") else 2
        for ch, cw in zip(text, char_widths):
            # Shadow
            draw.text((x + shadow_offset, y + shadow_offset), ch, font=font, fill=(0, 0, 0, 100))
            # Main
            draw.text((x, y), ch, font=font, fill=color)
            x += cw + letter_spacing

        line_h = draw.textbbox((0, 0), text[0], font=font)[3]
        return y + line_h

    @staticmethod
    def _draw_wrapped_text(
        draw: ImageDraw.ImageDraw,
        text: str,
        margin_x: int,
        y: int,
        canvas_w: int,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        color: tuple[int, ...],
        letter_spacing: int,
        alignment: str,
    ) -> int:
        """Simple word-wrap: split by spaces, greedy line fill."""
        words = text.split()
        usable_w = canvas_w - 2 * margin_x
        lines: list[str] = []
        current_line = ""

        for word in words:
            test = f"{current_line} {word}".strip()
            bbox = draw.textbbox((0, 0), test, font=font)
            test_w = bbox[2] - bbox[0] + letter_spacing * max(len(test) - 1, 0)
            if test_w <= usable_w:
                current_line = test
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_w = bbox[2] - bbox[0] + letter_spacing * max(len(line) - 1, 0)
            line_h = bbox[3] - bbox[1]

            if alignment == "center":
                x = (canvas_w - line_w) // 2
            elif alignment == "right":
                x = canvas_w - margin_x - line_w
            else:
                x = margin_x

            shadow_offset = max(2, font.size // 30) if hasattr(font, "size") else 2
            # Shadow
            draw.text((x + shadow_offset, y + shadow_offset), line, font=font, fill=(0, 0, 0, 100))
            # Draw each char with spacing
            cx = x
            for ch in line:
                cbox = draw.textbbox((0, 0), ch, font=font)
                cw = cbox[2] - cbox[0]
                draw.text((cx, y), ch, font=font, fill=color)
                cx += cw + letter_spacing

            y += line_h + int(line_h * 0.2)

        return y

    # ------------------------------------------------------------------
    # CTA drawing
    # ------------------------------------------------------------------

    @staticmethod
    def _draw_cta(
        draw: ImageDraw.ImageDraw,
        cta_text: str,
        margin_x: int,
        y: int,
        canvas_w: int,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        cta_style: str,
        primary_rgb: tuple[int, int, int],
        accent_rgb: tuple[int, int, int],
        alignment: str,
    ) -> int:
        """Draw the CTA according to the DNA style.

        Supported styles:
          rounded_button, pill, sharp_button, underline, outline, text_only, badge
        """
        cta_style = (cta_style or "rounded_button").lower().replace(" ", "_").replace("-", "_")
        padding_x = 24
        padding_y = 12
        bbox = draw.textbbox((0, 0), cta_text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        btn_w = text_w + padding_x * 2
        btn_h = text_h + padding_y * 2

        # X position
        if alignment == "center":
            btn_x = (canvas_w - btn_w) // 2
        elif alignment == "right":
            btn_x = canvas_w - margin_x - btn_w
        else:
            btn_x = margin_x

        text_color = _contrast_text_color(primary_rgb)

        if cta_style in ("pill", "rounded_button"):
            radius = btn_h // 2 if cta_style == "pill" else btn_h // 4
            draw.rounded_rectangle(
                [btn_x, y, btn_x + btn_w, y + btn_h],
                radius=radius,
                fill=(*primary_rgb, 255),
            )
            draw.text(
                (btn_x + padding_x, y + padding_y),
                cta_text,
                font=font,
                fill=text_color,
            )

        elif cta_style == "sharp_button":
            draw.rectangle(
                [btn_x, y, btn_x + btn_w, y + btn_h],
                fill=(*primary_rgb, 255),
            )
            draw.text(
                (btn_x + padding_x, y + padding_y),
                cta_text,
                font=font,
                fill=text_color,
            )

        elif cta_style == "outline":
            border_w = max(2, btn_h // 20)
            draw.rounded_rectangle(
                [btn_x, y, btn_x + btn_w, y + btn_h],
                radius=btn_h // 4,
                outline=(*primary_rgb, 255),
                width=border_w,
            )
            draw.text(
                (btn_x + padding_x, y + padding_y),
                cta_text,
                font=font,
                fill=(*primary_rgb, 255),
            )

        elif cta_style == "underline":
            tx = btn_x
            if alignment == "center":
                tx = (canvas_w - text_w) // 2
            elif alignment == "right":
                tx = canvas_w - margin_x - text_w
            draw.text((tx, y), cta_text, font=font, fill=(255, 255, 255, 255))
            line_y = y + text_h + 4
            draw.line(
                [(tx, line_y), (tx + text_w, line_y)],
                fill=(*primary_rgb, 255),
                width=max(2, text_h // 10),
            )
            return line_y + 12

        elif cta_style == "badge":
            # Rotated-looking badge (diamond-ish rectangle)
            cx = btn_x + btn_w // 2
            cy = y + btn_h // 2
            r = max(btn_w, btn_h) // 2 + 8
            draw.regular_polygon(
                (cx, cy, r),
                n_sides=6,
                fill=(*accent_rgb, 230),
                rotation=30,
            )
            draw.text(
                (cx - text_w // 2, cy - text_h // 2),
                cta_text,
                font=font,
                fill=_contrast_text_color(accent_rgb),
            )

        else:
            # text_only or unknown
            tx = btn_x
            if alignment == "center":
                tx = (canvas_w - text_w) // 2
            elif alignment == "right":
                tx = canvas_w - margin_x - text_w
            draw.text((tx, y), cta_text, font=font, fill=(*primary_rgb, 255))
            return y + text_h + 8

        return y + btn_h + 16

    # ------------------------------------------------------------------
    # Brand watermark
    # ------------------------------------------------------------------

    @staticmethod
    def _draw_brand_watermark(
        draw: ImageDraw.ImageDraw,
        brand_name: str,
        w: int,
        h: int,
        margin: int,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        primary_rgb: tuple[int, int, int],
        position: str,
    ) -> None:
        """Place brand name at the DNA-specified logo_position."""
        bbox = draw.textbbox((0, 0), brand_name, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        position = (position or "top_right").lower().replace("-", "_").replace(" ", "_")

        positions_map = {
            "top_left": (margin, margin),
            "top_right": (w - margin - tw, margin),
            "top_center": ((w - tw) // 2, margin),
            "bottom_left": (margin, h - margin - th),
            "bottom_right": (w - margin - tw, h - margin - th),
            "bottom_center": ((w - tw) // 2, h - margin - th),
        }
        x, y = positions_map.get(position, (w - margin - tw, margin))

        # Draw with subtle background pill for readability
        pad = 6
        draw.rounded_rectangle(
            [x - pad, y - pad // 2, x + tw + pad, y + th + pad // 2],
            radius=pad,
            fill=(0, 0, 0, 60),
        )
        draw.text((x, y), brand_name, font=font, fill=(*primary_rgb, 210))

    # ------------------------------------------------------------------
    # Border / frame
    # ------------------------------------------------------------------

    @staticmethod
    def _draw_border(
        draw: ImageDraw.ImageDraw,
        w: int,
        h: int,
        merged: dict,
        primary_rgb: tuple[int, int, int],
        accent_rgb: tuple[int, int, int],
    ) -> None:
        """Draw a border/frame if the DNA specifies one."""
        has_border = _dna_get(merged, "layout", "has_border", default=False)
        if not has_border:
            return

        border_style = _dna_get(merged, "layout", "border_style", default="solid")
        thickness = max(3, min(w, h) // 100)
        inset = thickness

        color = (*accent_rgb, 200)

        if border_style == "double":
            # Outer
            draw.rectangle([inset, inset, w - inset, h - inset], outline=color, width=thickness)
            # Inner
            inner_inset = inset + thickness + 4
            draw.rectangle(
                [inner_inset, inner_inset, w - inner_inset, h - inner_inset],
                outline=color,
                width=max(1, thickness // 2),
            )
        elif border_style == "rounded":
            draw.rounded_rectangle(
                [inset, inset, w - inset, h - inset],
                radius=min(w, h) // 20,
                outline=color,
                width=thickness,
            )
        elif border_style == "dashed":
            dash_len = max(12, thickness * 4)
            gap_len = max(8, thickness * 2)
            for side_pts in [
                [(inset, inset), (w - inset, inset)],          # top
                [(w - inset, inset), (w - inset, h - inset)],  # right
                [(w - inset, h - inset), (inset, h - inset)],  # bottom
                [(inset, h - inset), (inset, inset)],          # left
            ]:
                PosterAgent._draw_dashed_line(draw, side_pts[0], side_pts[1], color, thickness, dash_len, gap_len)
        else:
            # solid
            draw.rectangle([inset, inset, w - inset, h - inset], outline=color, width=thickness)

    @staticmethod
    def _draw_dashed_line(
        draw: ImageDraw.ImageDraw,
        start: tuple[int, int],
        end: tuple[int, int],
        color: tuple[int, ...],
        width: int,
        dash_len: int,
        gap_len: int,
    ) -> None:
        """Draw a dashed line between two points."""
        x0, y0 = start
        x1, y1 = end
        dx = x1 - x0
        dy = y1 - y0
        length = math.hypot(dx, dy)
        if length == 0:
            return
        ux, uy = dx / length, dy / length
        pos = 0.0
        drawing = True
        while pos < length:
            seg = dash_len if drawing else gap_len
            seg = min(seg, length - pos)
            if drawing:
                sx = int(x0 + ux * pos)
                sy = int(y0 + uy * pos)
                ex = int(x0 + ux * (pos + seg))
                ey = int(y0 + uy * (pos + seg))
                draw.line([(sx, sy), (ex, ey)], fill=color, width=width)
            pos += seg
            drawing = not drawing

    # ------------------------------------------------------------------
    # Decorative elements
    # ------------------------------------------------------------------

    @staticmethod
    def _draw_decorative_elements(
        draw: ImageDraw.ImageDraw,
        w: int,
        h: int,
        merged: dict,
        primary_rgb: tuple[int, int, int],
        secondary_rgb: tuple[int, int, int],
        accent_rgb: tuple[int, int, int],
    ) -> None:
        """Render decorative elements specified in the DNA.

        DNA field: elements.decorative — list of:
          {"type": "line", "position": "top", "thickness": 4}
          {"type": "circle", "position": "top_right", "size": "small"}
          {"type": "dots", "position": "bottom"}
          {"type": "stripe", "position": "left", "width": 0.03}
          {"type": "corner_accent"}
        """
        decoratives = _dna_get(merged, "elements", "decorative", default=[])
        if not decoratives:
            return

        for deco in decoratives:
            if isinstance(deco, str):
                deco = {"type": deco}
            if not isinstance(deco, dict):
                continue

            dtype = deco.get("type", "").lower().replace("-", "_").replace(" ", "_")
            position = deco.get("position", "top").lower()

            if dtype == "line":
                thickness = int(deco.get("thickness", max(3, min(w, h) // 150)))
                color = (*accent_rgb, 180)
                if "top" in position:
                    y = min(w, h) // 30
                    draw.line([(0, y), (w, y)], fill=color, width=thickness)
                elif "bottom" in position:
                    y = h - min(w, h) // 30
                    draw.line([(0, y), (w, y)], fill=color, width=thickness)
                elif "left" in position:
                    x = min(w, h) // 30
                    draw.line([(x, 0), (x, h)], fill=color, width=thickness)
                elif "right" in position:
                    x = w - min(w, h) // 30
                    draw.line([(x, 0), (x, h)], fill=color, width=thickness)

            elif dtype == "stripe":
                stripe_ratio = float(deco.get("width", 0.03))
                stripe_w = max(4, int(min(w, h) * stripe_ratio))
                color = (*primary_rgb, 160)
                if "left" in position:
                    draw.rectangle([0, 0, stripe_w, h], fill=color)
                elif "right" in position:
                    draw.rectangle([w - stripe_w, 0, w, h], fill=color)
                elif "top" in position:
                    draw.rectangle([0, 0, w, stripe_w], fill=color)
                elif "bottom" in position:
                    draw.rectangle([0, h - stripe_w, w, h], fill=color)

            elif dtype == "circle":
                size_name = deco.get("size", "medium")
                size_map = {"small": 0.06, "medium": 0.12, "large": 0.2}
                radius = int(min(w, h) * size_map.get(size_name, 0.12))
                color = (*accent_rgb, 50)
                # Position
                cx, cy = w // 2, h // 2
                if "top" in position:
                    cy = radius
                if "bottom" in position:
                    cy = h - radius
                if "left" in position:
                    cx = radius
                if "right" in position:
                    cx = w - radius
                draw.ellipse(
                    [cx - radius, cy - radius, cx + radius, cy + radius],
                    fill=color,
                )

            elif dtype == "dots":
                dot_r = max(3, min(w, h) // 100)
                color = (*secondary_rgb, 80)
                spacing = dot_r * 5
                if "bottom" in position:
                    y_base = h - dot_r * 4
                elif "top" in position:
                    y_base = dot_r * 4
                else:
                    y_base = h // 2
                for dx in range(0, w, spacing):
                    draw.ellipse(
                        [dx, y_base - dot_r, dx + dot_r * 2, y_base + dot_r],
                        fill=color,
                    )

            elif dtype == "corner_accent":
                size = max(20, min(w, h) // 8)
                color = (*accent_rgb, 120)
                thickness = max(2, size // 15)
                # Top-left corner
                draw.line([(0, size), (0, 0), (size, 0)], fill=color, width=thickness, joint="curve")
                # Bottom-right corner
                draw.line(
                    [(w, h - size), (w, h), (w - size, h)],
                    fill=color, width=thickness, joint="curve",
                )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    async def validate_output(self, result: AgentResult) -> bool:
        return result.success and bool(result.output.get("image_url"))
