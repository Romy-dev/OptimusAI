"""Schemas for brand profile management."""

import uuid
from pydantic import BaseModel, Field


class ProductItem(BaseModel):
    name: str
    description: str | None = None
    price: str | None = None
    category: str | None = None


class ServiceItem(BaseModel):
    name: str
    description: str | None = None
    zones: list[str] = Field(default_factory=list)


class ResponseRule(BaseModel):
    trigger: str  # keyword or topic
    rule: str  # instruction for the AI


class ExamplePost(BaseModel):
    channel: str
    content: str
    approved: bool = True


class ExampleReply(BaseModel):
    scenario: str
    reply: str


class ChannelProfile(BaseModel):
    max_length: int | None = None
    use_hashtags: bool = False
    hashtag_count: int | None = None
    use_emojis: bool = True
    emoji_level: str = "moderate"  # none, moderate, heavy
    formal: bool | None = None


class BrandProfileUpdate(BaseModel):
    """Update any subset of the brand profile."""
    default_tone: str | None = None
    tone_by_channel: dict | None = None
    tone_description: str | None = None
    primary_language: str | None = None
    secondary_languages: list[str] | None = None
    language_notes: str | None = None
    products: list[ProductItem] | None = None
    services: list[ServiceItem] | None = None
    greeting_style: str | None = None
    closing_style: str | None = None
    response_rules: list[ResponseRule] | None = None
    banned_words: list[str] | None = None
    banned_topics: list[str] | None = None
    sensitive_topics: list[str] | None = None
    colors: dict | None = None
    image_style: str | None = None
    example_posts: list[ExamplePost] | None = None
    example_replies: list[ExampleReply] | None = None
    example_support_responses: list[ExampleReply] | None = None
    business_hours: dict | None = None
    locations: list[dict] | None = None
    contact_info: dict | None = None
    channel_profiles: dict[str, ChannelProfile] | None = None


class BrandProfileResponse(BaseModel):
    id: uuid.UUID
    brand_id: uuid.UUID
    default_tone: str
    tone_by_channel: dict
    tone_description: str | None
    primary_language: str
    products: list
    services: list
    response_rules: list
    banned_words: list
    banned_topics: list
    sensitive_topics: list
    example_posts: list
    channel_profiles: dict
    business_hours: dict
    contact_info: dict

    model_config = {"from_attributes": True}


class BrandContextResponse(BaseModel):
    """The full brand context as consumed by agents."""
    brand_name: str
    industry: str | None
    tone: str
    language: str
    country: str
    colors: dict
    products: list
    services: list
    greeting_style: str | None
    closing_style: str | None
    response_rules: list
    banned_words: list
    banned_topics: list
    example_posts: list
    business_hours: dict
    contact_info: dict
    max_length: int | None = None
    use_hashtags: bool = False
    use_emojis: bool = True
