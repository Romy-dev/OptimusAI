"""Default Design DNA profiles — fallback when no client templates exist.

Each profile defines a complete visual identity that the PosterAgent uses
to compose professional marketing posters without any client reference images.
Profiles are organized by industry so the output matches the business sector.
"""

# Generic fallback — clean, modern, professional
GENERIC = {
    "merged_dna": {
        "layout": {
            "type": "text_bottom_overlay",
            "text_position": "bottom",
            "alignment": "left",
            "has_border": False,
        },
        "typography": {
            "headline_style": "bold uppercase sans-serif",
            "headline_size_ratio": 0.07,
            "subheadline_style": "light sentence case",
            "body_style": "regular",
        },
        "colors": {
            "dominant": "#1a1a2e",
            "accent": "#e94560",
            "text_primary": "#ffffff",
            "text_secondary": "#e0e0e0",
            "overlay_type": "gradient_bottom_dark",
            "overlay_opacity": 0.7,
        },
        "elements": {
            "has_cta_button": True,
            "cta_style": "rounded_filled_accent",
            "decorative": ["thin_line_separator"],
        },
        "composition": {
            "background_style": "professional photography",
        },
        "mood": "modern, clean, professional",
    },
    "preferred_fonts": ["Montserrat", "Helvetica", "DejaVuSans"],
    "color_palette": ["#1a1a2e", "#e94560", "#ffffff", "#16213e"],
    "layout_preferences": ["text_bottom_overlay", "center_overlay"],
    "mood_keywords": ["modern", "clean", "professional"],
    "template_count": 0,
}

# Fashion / Textile / Mode
FASHION = {
    "merged_dna": {
        "layout": {
            "type": "text_bottom_overlay",
            "text_position": "bottom",
            "alignment": "center",
            "has_border": True,
            "border_style": "thin_gold_1px",
        },
        "typography": {
            "headline_style": "bold uppercase serif",
            "headline_size_ratio": 0.08,
            "subheadline_style": "italic light",
            "body_style": "light",
        },
        "colors": {
            "dominant": "#2d1810",
            "accent": "#d4a574",
            "text_primary": "#ffffff",
            "text_secondary": "#d4a574",
            "overlay_type": "gradient_bottom_dark",
            "overlay_opacity": 0.75,
        },
        "elements": {
            "has_cta_button": True,
            "cta_style": "outlined_gold",
            "has_price_badge": True,
            "badge_style": "circle_accent",
            "decorative": ["thin_line_separator", "corner_ornaments"],
        },
        "composition": {
            "background_style": "fashion photography, model wearing clothes, natural light",
        },
        "mood": "elegant, premium, luxurious",
    },
    "preferred_fonts": ["Playfair Display", "Montserrat", "DejaVuSans"],
    "color_palette": ["#2d1810", "#d4a574", "#ffffff", "#8b6914"],
    "layout_preferences": ["text_bottom_overlay", "split_left_text_right_image"],
    "mood_keywords": ["elegant", "premium", "luxurious", "chic"],
    "template_count": 0,
}

# Restaurant / Alimentation / Food
FOOD = {
    "merged_dna": {
        "layout": {
            "type": "text_top_overlay",
            "text_position": "top",
            "alignment": "center",
            "has_border": False,
        },
        "typography": {
            "headline_style": "bold uppercase rounded sans-serif",
            "headline_size_ratio": 0.09,
            "subheadline_style": "regular sentence case",
            "body_style": "medium",
        },
        "colors": {
            "dominant": "#c62828",
            "accent": "#ff8f00",
            "text_primary": "#ffffff",
            "text_secondary": "#fff3e0",
            "overlay_type": "gradient_top_dark",
            "overlay_opacity": 0.65,
        },
        "elements": {
            "has_cta_button": True,
            "cta_style": "rounded_filled_red",
            "has_price_badge": True,
            "badge_style": "starburst_yellow",
            "decorative": ["food_splash_effect", "rounded_corners"],
        },
        "composition": {
            "background_style": "food photography, close-up, warm lighting, steam, appetizing",
        },
        "mood": "warm, appetizing, vibrant, energetic",
    },
    "preferred_fonts": ["Poppins", "Montserrat", "DejaVuSans"],
    "color_palette": ["#c62828", "#ff8f00", "#ffffff", "#1b5e20"],
    "layout_preferences": ["text_top_overlay", "center_bold"],
    "mood_keywords": ["warm", "appetizing", "vibrant", "delicious"],
    "template_count": 0,
}

# Tech / Startup / Digital
TECH = {
    "merged_dna": {
        "layout": {
            "type": "center_overlay",
            "text_position": "center",
            "alignment": "center",
            "has_border": False,
        },
        "typography": {
            "headline_style": "bold uppercase geometric sans-serif",
            "headline_size_ratio": 0.07,
            "subheadline_style": "light monospace",
            "body_style": "regular",
        },
        "colors": {
            "dominant": "#0f0f23",
            "accent": "#00d4ff",
            "text_primary": "#ffffff",
            "text_secondary": "#80deea",
            "overlay_type": "solid_dark",
            "overlay_opacity": 0.85,
        },
        "elements": {
            "has_cta_button": True,
            "cta_style": "rounded_filled_neon",
            "decorative": ["gradient_mesh_background", "subtle_grid"],
        },
        "composition": {
            "background_style": "abstract tech, gradient mesh, dark futuristic, minimal",
        },
        "mood": "futuristic, innovative, clean, tech",
    },
    "preferred_fonts": ["Inter", "JetBrains Mono", "DejaVuSans"],
    "color_palette": ["#0f0f23", "#00d4ff", "#ffffff", "#7c4dff"],
    "layout_preferences": ["center_overlay", "minimal_text"],
    "mood_keywords": ["futuristic", "innovative", "clean", "modern"],
    "template_count": 0,
}

# Beauty / Cosmetics / Salon
BEAUTY = {
    "merged_dna": {
        "layout": {
            "type": "text_bottom_overlay",
            "text_position": "bottom",
            "alignment": "center",
            "has_border": True,
            "border_style": "soft_rounded_white",
        },
        "typography": {
            "headline_style": "elegant serif",
            "headline_size_ratio": 0.07,
            "subheadline_style": "light italic",
            "body_style": "thin",
        },
        "colors": {
            "dominant": "#f5e6d3",
            "accent": "#c97b7b",
            "text_primary": "#2d2d2d",
            "text_secondary": "#8b6b6b",
            "overlay_type": "gradient_bottom_light",
            "overlay_opacity": 0.6,
        },
        "elements": {
            "has_cta_button": True,
            "cta_style": "rounded_outlined_rose",
            "decorative": ["floral_accent", "soft_shadow"],
        },
        "composition": {
            "background_style": "beauty photography, soft lighting, pastel tones, cosmetics close-up",
        },
        "mood": "soft, feminine, elegant, luxurious",
    },
    "preferred_fonts": ["Playfair Display", "Lato", "DejaVuSans"],
    "color_palette": ["#f5e6d3", "#c97b7b", "#2d2d2d", "#e8d5c4"],
    "layout_preferences": ["text_bottom_overlay", "elegant_center"],
    "mood_keywords": ["soft", "feminine", "elegant", "premium"],
    "template_count": 0,
}

# Real Estate / Immobilier
REALESTATE = {
    "merged_dna": {
        "layout": {
            "type": "text_bottom_overlay",
            "text_position": "bottom",
            "alignment": "left",
            "has_border": False,
        },
        "typography": {
            "headline_style": "bold uppercase sans-serif",
            "headline_size_ratio": 0.08,
            "subheadline_style": "medium",
            "body_style": "regular",
        },
        "colors": {
            "dominant": "#1a237e",
            "accent": "#ffc107",
            "text_primary": "#ffffff",
            "text_secondary": "#e3f2fd",
            "overlay_type": "gradient_bottom_dark",
            "overlay_opacity": 0.7,
        },
        "elements": {
            "has_cta_button": True,
            "cta_style": "bold_filled_blue",
            "has_price_badge": True,
            "badge_style": "banner_gold",
            "decorative": ["location_pin_icon", "price_banner"],
        },
        "composition": {
            "background_style": "real estate photography, building exterior, interior design, wide angle",
        },
        "mood": "trustworthy, professional, premium",
    },
    "preferred_fonts": ["Montserrat", "Roboto", "DejaVuSans"],
    "color_palette": ["#1a237e", "#ffc107", "#ffffff", "#0d47a1"],
    "layout_preferences": ["text_bottom_overlay", "split_with_price"],
    "mood_keywords": ["trustworthy", "professional", "premium", "solid"],
    "template_count": 0,
}

# Education / Formation
EDUCATION = {
    "merged_dna": {
        "layout": {
            "type": "text_top_overlay",
            "text_position": "top",
            "alignment": "left",
            "has_border": False,
        },
        "typography": {
            "headline_style": "bold rounded sans-serif",
            "headline_size_ratio": 0.07,
            "subheadline_style": "medium",
            "body_style": "regular",
        },
        "colors": {
            "dominant": "#1565c0",
            "accent": "#4caf50",
            "text_primary": "#ffffff",
            "text_secondary": "#e3f2fd",
            "overlay_type": "gradient_diagonal",
            "overlay_opacity": 0.8,
        },
        "elements": {
            "has_cta_button": True,
            "cta_style": "rounded_filled_green",
            "decorative": ["graduation_cap_icon", "book_elements"],
        },
        "composition": {
            "background_style": "education, classroom, students, learning, bright colors",
        },
        "mood": "inspiring, accessible, dynamic, youthful",
    },
    "preferred_fonts": ["Nunito", "Poppins", "DejaVuSans"],
    "color_palette": ["#1565c0", "#4caf50", "#ffffff", "#ff9800"],
    "layout_preferences": ["text_top_overlay", "center_inspiring"],
    "mood_keywords": ["inspiring", "accessible", "dynamic", "youthful"],
    "template_count": 0,
}

# Health / Santé / Pharmacie
HEALTH = {
    "merged_dna": {
        "layout": {
            "type": "center_overlay",
            "text_position": "center",
            "alignment": "center",
            "has_border": False,
        },
        "typography": {
            "headline_style": "bold clean sans-serif",
            "headline_size_ratio": 0.06,
            "subheadline_style": "light",
            "body_style": "regular",
        },
        "colors": {
            "dominant": "#00695c",
            "accent": "#26a69a",
            "text_primary": "#ffffff",
            "text_secondary": "#b2dfdb",
            "overlay_type": "solid_teal",
            "overlay_opacity": 0.75,
        },
        "elements": {
            "has_cta_button": True,
            "cta_style": "rounded_filled_teal",
            "decorative": ["medical_cross", "clean_lines"],
        },
        "composition": {
            "background_style": "healthcare, clean, white space, medical, wellness",
        },
        "mood": "trustworthy, calm, clean, reassuring",
    },
    "preferred_fonts": ["Open Sans", "Roboto", "DejaVuSans"],
    "color_palette": ["#00695c", "#26a69a", "#ffffff", "#e0f2f1"],
    "layout_preferences": ["center_overlay", "clean_minimal"],
    "mood_keywords": ["trustworthy", "calm", "clean", "healthcare"],
    "template_count": 0,
}

# Agriculture / Farming
AGRICULTURE = {
    "merged_dna": {
        "layout": {
            "type": "text_bottom_overlay",
            "text_position": "bottom",
            "alignment": "left",
            "has_border": False,
        },
        "typography": {
            "headline_style": "bold slab serif",
            "headline_size_ratio": 0.08,
            "subheadline_style": "regular",
            "body_style": "medium",
        },
        "colors": {
            "dominant": "#33691e",
            "accent": "#f9a825",
            "text_primary": "#ffffff",
            "text_secondary": "#c5e1a5",
            "overlay_type": "gradient_bottom_dark",
            "overlay_opacity": 0.7,
        },
        "elements": {
            "has_cta_button": True,
            "cta_style": "rounded_filled_green",
            "decorative": ["leaf_accent", "earth_tones"],
        },
        "composition": {
            "background_style": "agriculture, farm, crops, harvest, golden hour, green fields",
        },
        "mood": "natural, authentic, earthy, abundant",
    },
    "preferred_fonts": ["Merriweather", "Lato", "DejaVuSans"],
    "color_palette": ["#33691e", "#f9a825", "#ffffff", "#795548"],
    "layout_preferences": ["text_bottom_overlay"],
    "mood_keywords": ["natural", "authentic", "earthy", "fresh"],
    "template_count": 0,
}

# Events / Événementiel
EVENTS = {
    "merged_dna": {
        "layout": {
            "type": "center_overlay",
            "text_position": "center",
            "alignment": "center",
            "has_border": True,
            "border_style": "double_line_white",
        },
        "typography": {
            "headline_style": "extra bold uppercase display",
            "headline_size_ratio": 0.1,
            "subheadline_style": "light uppercase",
            "body_style": "medium",
        },
        "colors": {
            "dominant": "#311b92",
            "accent": "#ff6f00",
            "text_primary": "#ffffff",
            "text_secondary": "#ffcc80",
            "overlay_type": "gradient_radial_dark",
            "overlay_opacity": 0.8,
        },
        "elements": {
            "has_cta_button": True,
            "cta_style": "bold_filled_orange",
            "decorative": ["confetti", "spotlight_effect", "date_badge"],
        },
        "composition": {
            "background_style": "event, concert, celebration, lights, crowd, vibrant energy",
        },
        "mood": "exciting, festive, dynamic, energetic",
    },
    "preferred_fonts": ["Impact", "Bebas Neue", "DejaVuSans"],
    "color_palette": ["#311b92", "#ff6f00", "#ffffff", "#e91e63"],
    "layout_preferences": ["center_overlay", "bold_impact"],
    "mood_keywords": ["exciting", "festive", "dynamic", "energetic"],
    "template_count": 0,
}


# ---------------------------------------------------------------------------
# Industry → DNA mapping
# ---------------------------------------------------------------------------

_INDUSTRY_MAP: dict[str, dict] = {
    # Fashion
    "mode": FASHION, "textile": FASHION, "fashion": FASHION, "vêtements": FASHION,
    "clothing": FASHION, "wax": FASHION, "couture": FASHION, "prêt-à-porter": FASHION,
    # Food
    "restaurant": FOOD, "alimentation": FOOD, "food": FOOD, "cuisine": FOOD,
    "boulangerie": FOOD, "pâtisserie": FOOD, "traiteur": FOOD, "café": FOOD,
    "bar": FOOD, "fast-food": FOOD,
    # Tech
    "tech": TECH, "technologie": TECH, "startup": TECH, "digital": TECH,
    "informatique": TECH, "logiciel": TECH, "saas": TECH, "fintech": TECH,
    "mobile": TECH,
    # Beauty
    "beauté": BEAUTY, "beauty": BEAUTY, "cosmétique": BEAUTY, "salon": BEAUTY,
    "coiffure": BEAUTY, "spa": BEAUTY, "maquillage": BEAUTY, "parfum": BEAUTY,
    # Real estate
    "immobilier": REALESTATE, "real estate": REALESTATE, "construction": REALESTATE,
    "btp": REALESTATE, "architecture": REALESTATE,
    # Education
    "éducation": EDUCATION, "education": EDUCATION, "formation": EDUCATION,
    "école": EDUCATION, "université": EDUCATION, "training": EDUCATION,
    # Health
    "santé": HEALTH, "health": HEALTH, "pharmacie": HEALTH, "médecine": HEALTH,
    "clinique": HEALTH, "hôpital": HEALTH, "wellness": HEALTH,
    # Agriculture
    "agriculture": AGRICULTURE, "farming": AGRICULTURE, "agro": AGRICULTURE,
    "élevage": AGRICULTURE, "bio": AGRICULTURE,
    # Events
    "événementiel": EVENTS, "events": EVENTS, "spectacle": EVENTS,
    "concert": EVENTS, "festival": EVENTS, "mariage": EVENTS,
}


def get_default_dna(industry: str | None = None) -> dict:
    """Return a default Design DNA profile matching the industry.

    Falls back to GENERIC if no industry match.
    """
    if not industry:
        return GENERIC

    key = industry.lower().strip()
    return _INDUSTRY_MAP.get(key, GENERIC)
