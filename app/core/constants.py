"""Centralized constants for OptimusAI."""

# Maximum content length per social channel
CHANNEL_MAX_LENGTHS = {
    "facebook": 2000,
    "instagram": 2200,
    "whatsapp": 1000,
    "tiktok": 300,
    "twitter": 280,
    "linkedin": 3000,
    "messenger": 2000,
}

# Default hashtag counts per channel
CHANNEL_HASHTAG_COUNTS = {
    "facebook": 5,
    "instagram": 15,
    "whatsapp": 0,
    "tiktok": 5,
    "twitter": 3,
    "linkedin": 5,
}

# Emoji usage level per channel (0-3)
CHANNEL_EMOJI_LEVEL = {
    "facebook": 2,
    "instagram": 3,
    "whatsapp": 2,
    "tiktok": 3,
    "twitter": 1,
    "linkedin": 1,
}

# Supported platforms
PLATFORMS = ["facebook", "instagram", "whatsapp", "tiktok", "linkedin", "twitter"]

# Content types for strategy agent
CONTENT_TYPES = [
    "promo",
    "educational",
    "engagement",
    "storytelling",
    "product",
    "testimonial",
    "announcement",
    "behind_the_scenes",
]

# Default content mix percentages
DEFAULT_CONTENT_MIX = {
    "promo": 20,
    "educational": 25,
    "engagement": 25,
    "storytelling": 15,
    "product": 15,
}
