"""Agent registry — instantiates and provides access to all agents."""

from app.agents.base import BaseAgent
from app.agents.analytics_agent import AnalyticsAgent
from app.agents.copywriter import CopywriterAgent
from app.agents.critic import CriticAgent
from app.agents.design_analyzer import DesignAnalyzerAgent
from app.agents.customer_memory import CustomerMemoryAgent
from app.agents.escalation import EscalationAgent
from app.agents.followup import FollowUpAgent
from app.agents.image_gen import ImageGenAgent
from app.agents.moderator import ModeratorAgent
from app.agents.orchestrator import OrchestratorAgent
from app.agents.poster import PosterAgent
from app.agents.sales import SalesAgent
from app.agents.sentiment import SentimentAgent
from app.agents.social_reply import SocialReplyAgent
from app.agents.strategist import ContentStrategistAgent
from app.agents.support import SupportAgent
from app.agents.timing import TimingAgent
from app.agents.coach import CoachAgent
from app.agents.story import StoryAgent


def create_agent_registry() -> dict[str, BaseAgent]:
    """Create all specialized agents."""
    return {
        # Content creation
        "copywriter": CopywriterAgent(),
        "image_gen": ImageGenAgent(),
        "poster": PosterAgent(),
        # Customer interaction
        "support": SupportAgent(),
        "social_reply": SocialReplyAgent(),
        "sales": SalesAgent(),
        "followup": FollowUpAgent(),
        "customer_memory": CustomerMemoryAgent(),
        # Safety & quality
        "moderator": ModeratorAgent(),
        "critic": CriticAgent(),
        "escalation": EscalationAgent(),
        # Intelligence & strategy
        "strategist": ContentStrategistAgent(),
        "timing": TimingAgent(),
        "sentiment": SentimentAgent(),
        "analytics": AnalyticsAgent(),
        # Design
        "design_analyzer": DesignAnalyzerAgent(),
        # Coach
        "coach": CoachAgent(),
        # Story
        "story": StoryAgent(),
    }


def create_orchestrator() -> OrchestratorAgent:
    """Create the orchestrator with all agents registered."""
    registry = create_agent_registry()
    return OrchestratorAgent(agent_registry=registry)


# Singleton
_orchestrator: OrchestratorAgent | None = None


def get_orchestrator() -> OrchestratorAgent:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = create_orchestrator()
    return _orchestrator
