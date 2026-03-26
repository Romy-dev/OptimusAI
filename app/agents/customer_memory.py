"""Customer memory agent — builds and maintains enriched customer profiles from conversations."""

import json
from datetime import datetime, timezone

import structlog
from sqlalchemy import select

from app.agents.base import AgentResult, BaseAgent
from app.core.security import PromptSecurity

logger = structlog.get_logger()


def _get_prompts():
    """Lazy-load prompt manager to avoid circular imports."""
    from app.prompts.loader import get_prompt_manager
    return get_prompt_manager()


class CustomerMemoryAgent(BaseAgent):
    name = "customer_memory"
    description = "Builds and maintains enriched customer profiles from conversations"
    max_retries = 1
    confidence_threshold = 0.5

    async def execute(self, context: dict) -> AgentResult:
        from app.core.database import async_session_factory
        from app.integrations.llm import get_llm_router
        from app.models.customer_profile import CustomerProfile

        customer_message = context.get("customer_message", "")
        conversation_history = context.get("conversation_history", [])
        platform = context.get("platform", "whatsapp")
        platform_user_id = context.get("platform_user_id", "")
        customer_name = context.get("customer_name", "Client")
        brand = context.get("brand_context", {})
        tenant_id = context.get("tenant_id", "")

        # Sanitize input
        if PromptSecurity.check_injection(customer_message):
            return AgentResult(
                success=False,
                output={"error": "suspicious_input"},
                confidence_score=0.0,
                should_escalate=True,
                escalation_reason="Potential prompt injection detected in customer message",
                agent_name=self.name,
            )

        # === 1. Query existing profile ===
        profile = None
        async with async_session_factory() as session:
            stmt = (
                select(CustomerProfile)
                .where(
                    CustomerProfile.tenant_id == tenant_id,
                    CustomerProfile.platform == platform,
                    CustomerProfile.platform_user_id == platform_user_id,
                )
            )
            result = await session.execute(stmt)
            profile = result.scalar_one_or_none()

            is_new_profile = profile is None

            # === 2. Create new profile if not found ===
            if is_new_profile:
                profile = CustomerProfile(
                    tenant_id=tenant_id,
                    brand_id=brand.get("brand_id"),
                    platform=platform,
                    platform_user_id=platform_user_id,
                    display_name=customer_name,
                    first_contact_at=datetime.now(timezone.utc),
                    language=brand.get("language", "fr"),
                    segment="new",
                    sentiment_trend="neutral",
                )
                session.add(profile)

            # === 3. Use LLM to analyze conversation ===
            # Format conversation history
            history_text = ""
            if conversation_history:
                lines = []
                for msg in conversation_history[-10:]:
                    role = "Client" if msg.get("direction") == "inbound" else "Support"
                    lines.append(f"{role}: {msg.get('content', '')}")
                history_text = "\n".join(lines)

            # Format products
            products_text = "Non spécifié"
            if brand.get("products"):
                product_names = [p.get("name", "") for p in brand["products"][:10]]
                products_text = ", ".join(product_names)

            pm = _get_prompts()
            system = pm.get_prompt(
                "customer_memory", "system",
                brand_name=brand.get("brand_name", "l'entreprise"),
                industry=brand.get("industry", "Non spécifié"),
                products=products_text,
                conversation_history=history_text,
                language=brand.get("language", "fr"),
            )

            user_msg = pm.get_prompt(
                "customer_memory", "user",
                customer_name=customer_name,
                platform=platform,
                customer_message=PromptSecurity.sanitize_for_prompt(customer_message),
            )

            llm = get_llm_router()
            response = await llm.generate(
                task_type="summary",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_msg},
                ],
            )

            # === 4. Parse LLM output ===
            try:
                parsed = json.loads(response.content)
                interests = parsed.get("interests", [])
                sentiment = parsed.get("sentiment", "neutral")
                segment = parsed.get("segment", "new")
                purchase_intent = float(parsed.get("purchase_intent", 0.0))
                issues = parsed.get("issues", [])
                tags = parsed.get("tags", [])
                preferred_language = parsed.get("preferred_language", "fr")
                notes_text = parsed.get("notes", "")
            except (json.JSONDecodeError, ValueError):
                logger.warning(
                    "customer_memory_parse_failed",
                    raw_response=response.content[:200],
                )
                interests = []
                sentiment = "neutral"
                segment = "new" if is_new_profile else profile.segment
                purchase_intent = 0.0
                issues = []
                tags = []
                preferred_language = "fr"
                notes_text = ""

            # === 5. Update profile ===
            # Merge interests (keep existing + add new)
            existing_interests = profile.interests or []
            merged_interests = list(set(existing_interests + interests))
            profile.interests = merged_interests

            # Update sentiment
            profile.sentiment_trend = sentiment

            # Update segment (only upgrade, don't downgrade unless at_risk)
            segment_priority = {"new": 0, "regular": 1, "vip": 2, "at_risk": -1}
            current_priority = segment_priority.get(profile.segment, 0)
            new_priority = segment_priority.get(segment, 0)
            if segment == "at_risk" or new_priority > current_priority:
                profile.segment = segment

            # Merge tags
            existing_tags = profile.tags or []
            merged_tags = list(set(existing_tags + tags))
            profile.tags = merged_tags

            # Update preferred language
            profile.preferred_language = preferred_language

            # Update issues
            if issues:
                profile.last_issue = issues[0]
                profile.last_issue_resolved = False

            # Add note
            if notes_text:
                existing_notes = profile.notes or []
                existing_notes.append({
                    "date": datetime.now(timezone.utc).isoformat(),
                    "note": notes_text,
                    "source": "customer_memory_agent",
                })
                profile.notes = existing_notes

            # Update counters
            profile.total_messages = (profile.total_messages or 0) + 1
            profile.last_contact_at = datetime.now(timezone.utc)

            await session.commit()
            await session.refresh(profile)

            # === 6. Return result ===
            profile_data = {
                "profile_id": str(profile.id),
                "is_new_profile": is_new_profile,
                "display_name": profile.display_name,
                "platform": profile.platform,
                "segment": profile.segment,
                "sentiment_trend": profile.sentiment_trend,
                "interests": profile.interests,
                "tags": profile.tags,
                "preferred_language": profile.preferred_language,
                "purchase_intent": purchase_intent,
                "issues": issues,
                "total_messages": profile.total_messages,
                "last_issue": profile.last_issue,
                "last_issue_resolved": profile.last_issue_resolved,
            }

            # Determine confidence based on conversation length
            confidence = min(0.5 + len(conversation_history) * 0.05, 0.95)

            return AgentResult(
                success=True,
                output=profile_data,
                confidence_score=confidence,
                agent_name=self.name,
                tokens_used=response.tokens_used,
                model_used=response.model,
            )

    async def validate_output(self, result: AgentResult) -> bool:
        """Validate that we got a profile back."""
        return result.success and bool(result.output.get("profile_id"))
