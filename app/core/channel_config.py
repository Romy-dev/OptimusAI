"""Centralized channel configuration — DRY constants for all agents and services."""

from pydantic import BaseModel


class ChannelConfig(BaseModel):
    """Configuration for a social media channel."""
    name: str
    max_length: int
    hashtag_limit: int
    emoji_style: str  # "heavy", "moderate", "minimal"
    tone_hint: str
    supports_images: bool = True
    supports_video: bool = False
    supports_stories: bool = False
    supports_reels: bool = False


CHANNEL_CONFIGS: dict[str, ChannelConfig] = {
    "facebook": ChannelConfig(
        name="Facebook",
        max_length=2000,
        hashtag_limit=5,
        emoji_style="moderate",
        tone_hint="Professionnel mais accessible. Posts plus longs acceptes.",
        supports_images=True,
        supports_video=True,
    ),
    "instagram": ChannelConfig(
        name="Instagram",
        max_length=1500,
        hashtag_limit=15,
        emoji_style="heavy",
        tone_hint="Visuel et engageant. Hashtags importants. Stories et Reels.",
        supports_images=True,
        supports_video=True,
        supports_stories=True,
        supports_reels=True,
    ),
    "whatsapp": ChannelConfig(
        name="WhatsApp",
        max_length=1000,
        hashtag_limit=0,
        emoji_style="moderate",
        tone_hint="Direct et conversationnel. Messages courts. Pas de hashtags.",
        supports_images=True,
    ),
    "tiktok": ChannelConfig(
        name="TikTok",
        max_length=300,
        hashtag_limit=5,
        emoji_style="heavy",
        tone_hint="Fun, tendance, jeune. Tres court. Video-first.",
        supports_video=True,
        supports_reels=True,
    ),
    "linkedin": ChannelConfig(
        name="LinkedIn",
        max_length=3000,
        hashtag_limit=5,
        emoji_style="minimal",
        tone_hint="Professionnel et expert. Contenu de valeur. Thought leadership.",
        supports_images=True,
        supports_video=True,
    ),
}


def get_channel_config(channel: str) -> ChannelConfig:
    """Get config for a channel, with sensible defaults."""
    return CHANNEL_CONFIGS.get(channel, CHANNEL_CONFIGS["facebook"])
