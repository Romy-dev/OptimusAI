"""Orchestrator agent — routes tasks to the correct specialized agent."""

import uuid
from enum import Enum

import structlog

from app.agents.base import AgentResult, BaseAgent

logger = structlog.get_logger()


class TaskType(str, Enum):
    # Content creation
    GENERATE_POST = "generate_post"
    GENERATE_IMAGE = "generate_image"
    GENERATE_POSTER = "generate_poster"
    # Customer interaction
    REPLY_COMMENT = "reply_comment"
    REPLY_MESSAGE = "reply_message"
    SUPPORT_QUERY = "support_query"
    SALES_ASSIST = "sales_assist"
    FOLLOWUP = "followup"
    UPDATE_CUSTOMER_MEMORY = "update_customer_memory"
    # Safety & quality
    MODERATE_CONTENT = "moderate_content"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    # Intelligence & strategy
    CONTENT_STRATEGY = "content_strategy"
    OPTIMIZE_TIMING = "optimize_timing"
    ANALYZE_SENTIMENT = "analyze_sentiment"
    ANALYZE_PERFORMANCE = "analyze_performance"
    # Design
    ANALYZE_DESIGN = "analyze_design"
    # Coach
    COACH = "coach"
    # Story
    GENERATE_STORY = "generate_story"


ROUTING_TABLE: dict[TaskType, str] = {
    # Content creation
    TaskType.GENERATE_POST: "copywriter",
    TaskType.GENERATE_IMAGE: "image_gen",
    TaskType.GENERATE_POSTER: "poster",
    # Customer interaction
    TaskType.REPLY_COMMENT: "social_reply",
    TaskType.REPLY_MESSAGE: "support",
    TaskType.SUPPORT_QUERY: "support",
    TaskType.SALES_ASSIST: "sales",
    TaskType.FOLLOWUP: "followup",
    TaskType.UPDATE_CUSTOMER_MEMORY: "customer_memory",
    # Safety & quality
    TaskType.MODERATE_CONTENT: "moderator",
    TaskType.ESCALATE_TO_HUMAN: "escalation",
    # Intelligence & strategy
    TaskType.CONTENT_STRATEGY: "strategist",
    TaskType.OPTIMIZE_TIMING: "timing",
    TaskType.ANALYZE_SENTIMENT: "sentiment",
    TaskType.ANALYZE_PERFORMANCE: "analytics",
    # Design
    TaskType.ANALYZE_DESIGN: "design_analyzer",
    TaskType.COACH: "coach",
    TaskType.GENERATE_STORY: "story",
}


class OrchestratorAgent(BaseAgent):
    """Routes incoming requests to the correct specialized agent.

    Does NOT generate content itself — it decomposes and delegates.
    """

    name = "orchestrator"
    description = "Routes tasks to specialized agents"
    max_retries = 0  # Orchestrator doesn't retry, sub-agents do

    def __init__(self, agent_registry: dict[str, BaseAgent]):
        self.agents = agent_registry

    async def classify_task(self, context: dict) -> TaskType:
        """Determine the task type from the context.

        Uses simple rule-based matching first, falls back to LLM classification.
        """
        # Explicit task type provided
        if "task_type" in context:
            return TaskType(context["task_type"])

        # Rule-based classification from context
        source = context.get("source", "")
        action = context.get("action", "")

        if source == "webhook" and context.get("event_type") == "message":
            return TaskType.SUPPORT_QUERY
        if source == "webhook" and context.get("event_type") == "comment":
            return TaskType.REPLY_COMMENT
        if action == "generate_post":
            return TaskType.GENERATE_POST
        if action == "analyze_design":
            return TaskType.ANALYZE_DESIGN

        # LLM-based classification as fallback
        if "user_input" in context:
            return await self._classify_with_llm(context["user_input"])

        return TaskType.SUPPORT_QUERY  # Safe default

    async def _classify_with_llm(self, user_input: str) -> TaskType:
        """Use LLM to classify ambiguous requests."""
        from app.integrations.llm import get_llm_router

        # Build valid categories from current TaskType enum
        valid_categories = [t.value for t in TaskType]

        router = get_llm_router()
        response = await router.generate(
            task_type="classification",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es un routeur de taches pour une plateforme de marketing IA.\n"
                        "Classe cette requete dans EXACTEMENT une categorie.\n"
                        "Reponds avec UNIQUEMENT le nom de la categorie, rien d'autre.\n\n"
                        f"Categories valides:\n{chr(10).join(f'- {c}' for c in valid_categories)}\n\n"
                        "Regles:\n"
                        "- Si la demande concerne la creation de texte/post → generate_post\n"
                        "- Si la demande concerne une image/photo → generate_image\n"
                        "- Si la demande concerne une affiche/poster/promo visuelle → generate_poster\n"
                        "- Si c'est une question client ou support → support_query\n"
                        "- Si c'est une demande de strategie/calendrier → content_strategy\n"
                        "- Si c'est une demande d'analyse/rapport → analyze_performance\n"
                        "- Si c'est flou ou ambigu → support_query\n"
                    ),
                },
                {"role": "user", "content": user_input},
            ],
            temperature=0.1,
        )
        raw = response.content.strip().lower().replace('"', '').replace("'", "")
        try:
            return TaskType(raw)
        except ValueError:
            logger.warning("orchestrator_classify_fallback", raw=raw, input=user_input[:100])
            return TaskType.SUPPORT_QUERY

    async def execute(self, context: dict) -> AgentResult:
        """Route the task to the correct sub-agent."""
        task_type = await self.classify_task(context)
        agent_name = ROUTING_TABLE.get(task_type)

        if not agent_name or agent_name not in self.agents:
            return AgentResult(
                success=False,
                output={"error": f"No agent found for task: {task_type}"},
                should_escalate=True,
                escalation_reason=f"Unknown task type: {task_type}",
                agent_name=self.name,
            )

        agent = self.agents[agent_name]
        context["task_type"] = task_type.value

        logger.info(
            "task_routed",
            task_type=task_type.value,
            target_agent=agent_name,
        )

        # Execute the sub-agent
        result = await agent.run(context)
        result.output["routed_by"] = self.name
        result.output["task_type"] = task_type.value

        # ── Critic review for generated posts ───────────────────
        if (
            task_type == TaskType.GENERATE_POST
            and result.success
            and "critic" in self.agents
        ):
            critic = self.agents["critic"]
            critic_context = {**context, **result.output}
            critic_result = await critic.run(critic_context)

            if critic_result.success:
                review = critic_result.output
                # If critic rejected and provided a revision, swap content
                if not review.get("approved") and review.get("revised_content"):
                    result.output["original_content"] = result.output.get("content", "")
                    result.output["content"] = review["revised_content"]
                result.output["critic_review"] = review
            else:
                logger.warning(
                    "critic_review_failed",
                    error=critic_result.output.get("error"),
                )
                result.output["critic_review"] = None

        return result

    async def execute_pipeline(
        self, steps: list[dict], context: dict
    ) -> list[AgentResult]:
        """Execute a multi-step pipeline (e.g., generate → moderate → publish).

        Each step's output is merged into the context for the next step.
        Stops on first failure or escalation.
        """
        results = []
        for step in steps:
            step_context = {**context, **step}
            result = await self.execute(step_context)
            results.append(result)

            if not result.success or result.should_escalate:
                logger.warning(
                    "pipeline_stopped",
                    step=step.get("task_type", "unknown"),
                    reason="failure" if not result.success else "escalation",
                )
                break

            # Merge result output into context for next step
            context.update(result.output)

        return results
