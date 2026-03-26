"""Base agent class for all OptimusAI agents."""

import time
import uuid
from abc import ABC, abstractmethod

import structlog
from pydantic import BaseModel

logger = structlog.get_logger()


class AgentResult(BaseModel):
    success: bool
    output: dict
    confidence_score: float | None = None
    should_escalate: bool = False
    escalation_reason: str | None = None
    agent_name: str
    execution_time_ms: int = 0
    tokens_used: int | None = None
    model_used: str | None = None
    sources: list[str] = []


class BaseAgent(ABC):
    """Base class for all OptimusAI agents.

    Each agent has:
    - A specific role and set of allowed tools
    - Retry logic with validation
    - Automatic logging of execution
    - Confidence scoring and escalation rules
    """

    name: str = "base"
    description: str = ""
    max_retries: int = 2
    confidence_threshold: float = 0.6

    @abstractmethod
    async def execute(self, context: dict) -> AgentResult:
        """Execute the agent's main task. Implement in subclass."""
        ...

    async def validate_output(self, result: AgentResult) -> bool:
        """Validate the agent's output. Override for custom validation."""
        return result.success

    async def run(self, context: dict) -> AgentResult:
        """Run the agent with retry logic, logging, and error handling."""
        start = time.perf_counter()
        run_id = str(uuid.uuid4())

        logger.info(
            "agent_run_started",
            agent=self.name,
            run_id=run_id,
            context_keys=list(context.keys()),
        )

        last_result = None
        for attempt in range(self.max_retries + 1):
            try:
                result = await self.execute(context)
                result.execution_time_ms = int((time.perf_counter() - start) * 1000)

                if await self.validate_output(result):
                    logger.info(
                        "agent_run_completed",
                        agent=self.name,
                        run_id=run_id,
                        success=True,
                        confidence=result.confidence_score,
                        duration_ms=result.execution_time_ms,
                    )
                    return result

                last_result = result
                context["retry_feedback"] = (
                    f"Attempt {attempt + 1} failed validation. "
                    f"Output: {result.output}"
                )

            except Exception as e:
                logger.error(
                    "agent_run_error",
                    agent=self.name,
                    run_id=run_id,
                    attempt=attempt + 1,
                    error=str(e),
                )
                last_result = AgentResult(
                    success=False,
                    output={"error": str(e)},
                    agent_name=self.name,
                )

        # All retries exhausted
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.warning(
            "agent_run_exhausted",
            agent=self.name,
            run_id=run_id,
            attempts=self.max_retries + 1,
        )

        return AgentResult(
            success=False,
            output=last_result.output if last_result else {"error": "Unknown failure"},
            should_escalate=True,
            escalation_reason=f"{self.name} failed after {self.max_retries + 1} attempts",
            agent_name=self.name,
            execution_time_ms=elapsed_ms,
        )
