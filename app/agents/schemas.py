"""Pydantic schemas for structured agent outputs.

These replace manual JSON parsing (_parse_llm_output, _parse_dna, etc.)
with type-safe, validated models.
"""

from pydantic import BaseModel, Field


# ── Copywriter ───────────────────────────────────────

class CopywriterOutput(BaseModel):
    """Structured output from the Copywriter agent."""
    content: str = Field(..., min_length=10, description="Le texte du post")
    hashtags: list[str] = Field(default_factory=list, description="Liste de hashtags sans #")
    media_suggestion: str = Field(default="", description="Suggestion de visuel pour accompagner le post")


# ── Support ──────────────────────────────────────────

class SupportOutput(BaseModel):
    """Structured output from the Support agent."""
    response: str = Field(..., description="La reponse au client")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Score de confiance 0-1")
    should_escalate: bool = Field(default=False, description="Faut-il transferer a un humain")
    escalation_reason: str | None = Field(default=None, description="Raison de l'escalade")
    sources_used: list[str] = Field(default_factory=list, description="Sources KB utilisees")


# ── Social Reply ─────────────────────────────────────

class SocialReplyOutput(BaseModel):
    """Structured output from the Social Reply agent."""
    reply_text: str = Field(..., description="Texte de la reponse au commentaire")
    comment_type: str = Field(default="neutral", description="positive/negative/question/spam/neutral")
    action: str = Field(default="reply", description="reply/hide/escalate")
    tone: str = Field(default="friendly", description="Ton utilise")


# ── Sales ────────────────────────────────────────────

class SalesOutput(BaseModel):
    """Structured output from the Sales agent."""
    purchase_intent_score: float = Field(default=0.0, ge=0.0, le=1.0)
    intent_signals: list[str] = Field(default_factory=list)
    recommended_products: list[dict] = Field(default_factory=list)
    sales_message: str = Field(default="")
    action: str = Field(default="no_action", description="recommend/upsell/no_action")


# ── Follow-up ────────────────────────────────────────

class FollowUpOutput(BaseModel):
    """Structured output from the FollowUp agent."""
    message: str = Field(..., description="Message de suivi")
    followup_type: str = Field(default="re_engagement")
    suggested_next_days: int = Field(default=7, description="Jours avant prochain suivi")
    priority: str = Field(default="medium", description="high/medium/low")


# ── Strategist ───────────────────────────────────────

class CalendarEntry(BaseModel):
    """Single entry in a content calendar."""
    day: str = Field(..., description="Jour de la semaine")
    time: str = Field(default="10:00", description="Heure de publication HH:MM")
    content_type: str = Field(default="engagement")
    brief: str = Field(..., description="Brief du post")
    channel: str = Field(default="facebook")
    reason: str = Field(default="", description="Pourquoi ce post a ce moment")


class StrategistOutput(BaseModel):
    """Structured output from the Strategist agent."""
    calendar: list[CalendarEntry] = Field(default_factory=list)
    content_mix: dict[str, float] = Field(default_factory=dict)
    tips: list[str] = Field(default_factory=list)


# ── Sentiment ────────────────────────────────────────

class SentimentOutput(BaseModel):
    """Structured output from the Sentiment agent."""
    sentiment_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    emotions: list[str] = Field(default_factory=list)
    health_score: int = Field(default=50, ge=0, le=100)
    alert_level: str = Field(default="green", description="green/yellow/red")
    crisis_detected: bool = Field(default=False)
    themes: dict = Field(default_factory=lambda: {"positive": [], "negative": []})
    recommended_actions: list[str] = Field(default_factory=list)


# ── Poster Plan ──────────────────────────────────────

class PosterPlan(BaseModel):
    """LLM-generated plan for a marketing poster."""
    background_prompt: str = Field(..., description="Prompt technique EN pour generer le fond")
    headline: str = Field(default="", max_length=60, description="Titre accrocheur court")
    subheadline: str = Field(default="", max_length=120, description="Sous-titre explicatif")
    cta_text: str = Field(default="", max_length=30, description="Texte du bouton CTA")
    layout: str = Field(default="bottom", description="top/center/bottom")


# ── Customer Memory ──────────────────────────────────

class CustomerAnalysis(BaseModel):
    """VLM analysis of customer from conversation."""
    interests: list[str] = Field(default_factory=list)
    sentiment: str = Field(default="neutral", description="positive/neutral/negative")
    segment: str = Field(default="new", description="new/regular/vip/at_risk")
    purchase_intent: bool = Field(default=False)
    issues: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    preferred_language: str = Field(default="fr")


# ── Analytics ────────────────────────────────────────

class AnalyticsRecommendation(BaseModel):
    """Single recommendation from Analytics agent."""
    title: str
    description: str
    priority: str = Field(default="medium", description="high/medium/low")


class AnalyticsOutput(BaseModel):
    """Structured output from the Analytics agent."""
    summary: dict = Field(default_factory=dict)
    best_post: dict | None = None
    worst_post: dict | None = None
    recommendations: list[AnalyticsRecommendation] = Field(default_factory=list)
    trends: dict = Field(default_factory=dict)
    report_text: str = Field(default="")


# ── Design DNA ───────────────────────────────────────

class DesignLayout(BaseModel):
    type: str = Field(default="text_over_image")
    text_position: str = Field(default="bottom")
    alignment: str = Field(default="left")

class DesignTypography(BaseModel):
    headline_style: str = Field(default="bold_uppercase_sans_serif")
    headline_size_ratio: float = Field(default=0.08)
    estimated_font: str = Field(default="Montserrat")

class DesignColors(BaseModel):
    dominant: str = Field(default="#000000")
    accent: str = Field(default="#D4A574")
    text_primary: str = Field(default="#FFFFFF")
    palette: list[dict] = Field(default_factory=list)
    overlay_type: str = Field(default="gradient")
    overlay_opacity: int = Field(default=50)

class DesignDNA(BaseModel):
    """Complete Design DNA extracted from a reference poster."""
    layout: DesignLayout = Field(default_factory=DesignLayout)
    typography: DesignTypography = Field(default_factory=DesignTypography)
    colors: DesignColors = Field(default_factory=DesignColors)
    elements: dict = Field(default_factory=dict)
    composition: dict = Field(default_factory=dict)
    mood_and_style: dict = Field(default_factory=dict)
    photography: dict = Field(default_factory=dict)
    text_content_detected: dict = Field(default_factory=dict)
    quality_assessment: dict = Field(default_factory=dict)
