"""Analytics agent — performance analysis and strategic recommendations."""

import json
from datetime import datetime

import structlog

from app.agents.base import AgentResult, BaseAgent

logger = structlog.get_logger()


class AnalyticsAgent(BaseAgent):
    name = "analytics"
    description = "Analyzes content performance and generates strategic recommendations"
    max_retries = 1
    confidence_threshold = 0.5

    @staticmethod
    def _get_prompt_manager():
        """Lazy-load prompt manager to avoid circular imports."""
        from app.prompts.loader import get_prompt_manager
        return get_prompt_manager()

    # ------------------------------------------------------------------
    # Main execute
    # ------------------------------------------------------------------

    async def execute(self, context: dict) -> AgentResult:
        report_type = context.get("report_type", "weekly")
        posts = context.get("posts", [])
        conversations = context.get("conversations", [])
        brand = context.get("brand_context", {})
        period_start = context.get("period_start", "")
        period_end = context.get("period_end", "")

        if report_type == "weekly":
            return await self._weekly_report(posts, conversations, brand, period_start, period_end)
        elif report_type == "post_performance":
            return await self._post_performance(posts, brand)
        elif report_type == "channel_comparison":
            return await self._channel_comparison(posts, brand)
        elif report_type == "recommendations":
            return await self._generate_recommendations(posts, conversations, brand, period_start, period_end)
        else:
            return AgentResult(
                success=False,
                output={"error": f"Unknown report_type: {report_type}"},
                confidence_score=0.0,
                agent_name=self.name,
            )

    # ------------------------------------------------------------------
    # Weekly report
    # ------------------------------------------------------------------

    async def _weekly_report(
        self,
        posts: list[dict],
        conversations: list[dict],
        brand: dict,
        period_start: str,
        period_end: str,
    ) -> AgentResult:
        # --- Post metrics ---
        total_created = len(posts)
        published = [p for p in posts if p.get("status") == "published"]
        total_published = len(published)

        # Engagement aggregation
        total_likes = sum(p.get("engagement", {}).get("likes", 0) for p in published)
        total_comments = sum(p.get("engagement", {}).get("comments", 0) for p in published)
        total_shares = sum(p.get("engagement", {}).get("shares", 0) for p in published)
        total_reach = sum(p.get("engagement", {}).get("reach", 0) for p in published)

        # Best / worst by engagement total
        best_post = self._find_best_post(published)
        worst_post = self._find_worst_post(published)

        # --- Conversation metrics ---
        total_conversations = len(conversations)
        resolved = [c for c in conversations if c.get("status") == "resolved"]
        resolution_rate = round(len(resolved) / total_conversations * 100, 1) if total_conversations else 0.0

        # Average response time (seconds)
        response_times: list[float] = []
        for c in conversations:
            rt = c.get("resolution_time")
            if rt is not None:
                response_times.append(float(rt))
        avg_response_time = round(sum(response_times) / len(response_times), 1) if response_times else 0.0

        # Average sentiment
        sentiments = [c.get("sentiment") for c in conversations if c.get("sentiment") is not None]
        avg_sentiment = round(sum(sentiments) / len(sentiments), 2) if sentiments else None

        summary = {
            "period_start": period_start,
            "period_end": period_end,
            "posts_created": total_created,
            "posts_published": total_published,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_shares": total_shares,
            "total_reach": total_reach,
            "total_conversations": total_conversations,
            "resolution_rate": resolution_rate,
            "avg_response_time_seconds": avg_response_time,
            "avg_sentiment": avg_sentiment,
        }

        # Trends (simple: compare first half vs second half of posts by date)
        trends = self._compute_trends(posts, conversations)

        # Generate LLM summary
        llm_result = await self._llm_weekly_summary(summary, best_post, worst_post, brand)
        report_text = ""
        recommendations: list[dict] = []
        tokens_used = None
        model_used = None

        if llm_result:
            report_text = llm_result.get("report_text", "")
            recommendations = llm_result.get("recommendations", [])
            tokens_used = llm_result.get("tokens_used")
            model_used = llm_result.get("model")

        if not report_text:
            report_text = self._fallback_report_text(summary, best_post, worst_post)

        return AgentResult(
            success=True,
            output={
                "summary": summary,
                "best_post": best_post,
                "worst_post": worst_post,
                "recommendations": recommendations,
                "trends": trends,
                "report_text": report_text,
            },
            confidence_score=0.7 if llm_result else 0.45,
            agent_name=self.name,
            tokens_used=tokens_used,
            model_used=model_used,
        )

    # ------------------------------------------------------------------
    # Post performance analysis
    # ------------------------------------------------------------------

    async def _post_performance(self, posts: list[dict], brand: dict) -> AgentResult:
        if not posts:
            return AgentResult(
                success=True,
                output={
                    "summary": {"total_posts": 0},
                    "best_post": None,
                    "worst_post": None,
                    "recommendations": [],
                    "trends": {},
                    "report_text": "Aucun post à analyser pour cette période.",
                },
                confidence_score=0.3,
                agent_name=self.name,
            )

        published = [p for p in posts if p.get("status") == "published"]
        best_post = self._find_best_post(published)
        worst_post = self._find_worst_post(published)

        # Per-channel breakdown
        channels: dict[str, dict] = {}
        for p in published:
            ch = p.get("channel", "unknown")
            if ch not in channels:
                channels[ch] = {"count": 0, "engagement_total": 0}
            channels[ch]["count"] += 1
            channels[ch]["engagement_total"] += self._engagement_score(p)

        summary = {
            "total_posts": len(posts),
            "published_posts": len(published),
            "channels": channels,
        }

        # LLM for insights
        llm_result = await self._llm_post_insights(posts, brand)
        recommendations = llm_result.get("recommendations", []) if llm_result else []
        report_text = llm_result.get("report_text", "") if llm_result else ""
        tokens_used = llm_result.get("tokens_used") if llm_result else None
        model_used = llm_result.get("model") if llm_result else None

        return AgentResult(
            success=True,
            output={
                "summary": summary,
                "best_post": best_post,
                "worst_post": worst_post,
                "recommendations": recommendations,
                "trends": {},
                "report_text": report_text,
            },
            confidence_score=0.65 if llm_result else 0.4,
            agent_name=self.name,
            tokens_used=tokens_used,
            model_used=model_used,
        )

    # ------------------------------------------------------------------
    # Channel comparison
    # ------------------------------------------------------------------

    async def _channel_comparison(self, posts: list[dict], brand: dict) -> AgentResult:
        published = [p for p in posts if p.get("status") == "published"]
        channels: dict[str, list[dict]] = {}
        for p in published:
            ch = p.get("channel", "unknown")
            channels.setdefault(ch, []).append(p)

        comparison: dict[str, dict] = {}
        for ch, ch_posts in channels.items():
            eng_scores = [self._engagement_score(p) for p in ch_posts]
            comparison[ch] = {
                "count": len(ch_posts),
                "avg_engagement": round(sum(eng_scores) / len(eng_scores), 2) if eng_scores else 0.0,
                "total_engagement": sum(eng_scores),
                "best_post": self._find_best_post(ch_posts),
            }

        # Sort channels by average engagement
        sorted_channels = sorted(comparison.items(), key=lambda x: x[1]["avg_engagement"], reverse=True)
        best_channel = sorted_channels[0][0] if sorted_channels else None

        summary = {
            "channels": comparison,
            "best_channel": best_channel,
            "total_posts": len(published),
        }

        return AgentResult(
            success=True,
            output={
                "summary": summary,
                "best_post": None,
                "worst_post": None,
                "recommendations": [],
                "trends": {},
                "report_text": "",
            },
            confidence_score=0.6,
            agent_name=self.name,
        )

    # ------------------------------------------------------------------
    # Recommendations
    # ------------------------------------------------------------------

    async def _generate_recommendations(
        self,
        posts: list[dict],
        conversations: list[dict],
        brand: dict,
        period_start: str,
        period_end: str,
    ) -> AgentResult:
        published = [p for p in posts if p.get("status") == "published"]
        best_post = self._find_best_post(published)
        worst_post = self._find_worst_post(published)

        # Build analytics snapshot for LLM
        snapshot = {
            "total_posts": len(posts),
            "published": len(published),
            "total_conversations": len(conversations),
            "period": f"{period_start} — {period_end}",
            "best_post": best_post,
            "worst_post": worst_post,
        }

        # Channel distribution
        channel_counts: dict[str, int] = {}
        for p in published:
            ch = p.get("channel", "unknown")
            channel_counts[ch] = channel_counts.get(ch, 0) + 1
        snapshot["channel_distribution"] = channel_counts

        # Day of week distribution
        day_counts: dict[str, int] = {}
        for p in published:
            published_at = p.get("published_at", "")
            if published_at:
                try:
                    dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                    day_name = dt.strftime("%A")
                    day_counts[day_name] = day_counts.get(day_name, 0) + 1
                except (ValueError, TypeError):
                    pass
        snapshot["day_distribution"] = day_counts

        llm_result = await self._llm_recommendations(snapshot, posts, brand)
        recommendations: list[dict] = []
        report_text = ""
        tokens_used = None
        model_used = None

        if llm_result:
            recommendations = llm_result.get("recommendations", [])
            report_text = llm_result.get("report_text", "")
            tokens_used = llm_result.get("tokens_used")
            model_used = llm_result.get("model")

        if not recommendations:
            recommendations = self._fallback_recommendations(published, conversations)

        summary = {
            "total_posts": len(posts),
            "total_conversations": len(conversations),
            "period_start": period_start,
            "period_end": period_end,
        }

        return AgentResult(
            success=True,
            output={
                "summary": summary,
                "best_post": best_post,
                "worst_post": worst_post,
                "recommendations": recommendations,
                "trends": self._compute_trends(posts, conversations),
                "report_text": report_text,
            },
            confidence_score=0.7 if llm_result else 0.4,
            agent_name=self.name,
            tokens_used=tokens_used,
            model_used=model_used,
        )

    # ------------------------------------------------------------------
    # Helpers — post scoring
    # ------------------------------------------------------------------

    @staticmethod
    def _engagement_score(post: dict) -> float:
        """Compute a composite engagement score for a post."""
        eng = post.get("engagement", {})
        likes = eng.get("likes", 0)
        comments = eng.get("comments", 0)
        shares = eng.get("shares", 0)
        reach = eng.get("reach", 0)
        # Weighted: comments and shares are higher value
        return likes + comments * 2 + shares * 3 + reach * 0.01

    def _find_best_post(self, posts: list[dict]) -> dict | None:
        if not posts:
            return None
        # Prefer engagement score; fall back to confidence
        scored = [(p, self._engagement_score(p) or p.get("confidence", 0)) for p in posts]
        best = max(scored, key=lambda x: x[1])
        return self._post_summary(best[0])

    def _find_worst_post(self, posts: list[dict]) -> dict | None:
        if not posts:
            return None
        scored = [(p, self._engagement_score(p) or p.get("confidence", 0)) for p in posts]
        worst = min(scored, key=lambda x: x[1])
        return self._post_summary(worst[0])

    @staticmethod
    def _post_summary(post: dict) -> dict:
        """Extract a concise summary dict from a post."""
        return {
            "id": post.get("id"),
            "content": (post.get("content", "") or "")[:200],
            "channel": post.get("channel"),
            "status": post.get("status"),
            "published_at": post.get("published_at"),
            "engagement": post.get("engagement", {}),
        }

    # ------------------------------------------------------------------
    # Helpers — trends
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_trends(posts: list[dict], conversations: list[dict]) -> dict:
        """Compute simple trend directions for key metrics."""
        published = [p for p in posts if p.get("status") == "published"]

        # Split posts by time (first half vs second half)
        def _trend(first_vals: list[float], second_vals: list[float]) -> str:
            avg_first = sum(first_vals) / len(first_vals) if first_vals else 0
            avg_second = sum(second_vals) / len(second_vals) if second_vals else 0
            diff = avg_second - avg_first
            if abs(diff) < 0.05 * max(abs(avg_first), 1):
                return "stable"
            return "up" if diff > 0 else "down"

        mid = len(published) // 2
        first_half = published[:mid] if mid > 0 else []
        second_half = published[mid:] if mid > 0 else published

        eng_first = [
            p.get("engagement", {}).get("likes", 0)
            + p.get("engagement", {}).get("comments", 0)
            for p in first_half
        ]
        eng_second = [
            p.get("engagement", {}).get("likes", 0)
            + p.get("engagement", {}).get("comments", 0)
            for p in second_half
        ]

        conv_mid = len(conversations) // 2
        rt_first = [
            float(c.get("resolution_time", 0))
            for c in conversations[:conv_mid]
            if c.get("resolution_time") is not None
        ]
        rt_second = [
            float(c.get("resolution_time", 0))
            for c in conversations[conv_mid:]
            if c.get("resolution_time") is not None
        ]

        return {
            "engagement": _trend(eng_first, eng_second) if published else "stable",
            "response_time": _trend(rt_first, rt_second) if conversations else "stable",
            "post_volume": _trend(
                [len(first_half)], [len(second_half)]
            ) if published else "stable",
        }

    # ------------------------------------------------------------------
    # Fallback text generation (no LLM)
    # ------------------------------------------------------------------

    @staticmethod
    def _fallback_report_text(summary: dict, best_post: dict | None, worst_post: dict | None) -> str:
        lines = [
            f"📊 Rapport hebdomadaire ({summary.get('period_start', '?')} — {summary.get('period_end', '?')})",
            "",
            f"Posts créés: {summary.get('posts_created', 0)} | Publiés: {summary.get('posts_published', 0)}",
            f"Likes: {summary.get('total_likes', 0)} | Commentaires: {summary.get('total_comments', 0)} | Partages: {summary.get('total_shares', 0)}",
            f"Portée totale: {summary.get('total_reach', 0)}",
            "",
            f"Conversations: {summary.get('total_conversations', 0)} | Taux de résolution: {summary.get('resolution_rate', 0)}%",
            f"Temps de réponse moyen: {summary.get('avg_response_time_seconds', 0)}s",
        ]

        if best_post:
            lines.append(f"\nMeilleur post: {best_post.get('content', '')[:80]}...")
        if worst_post:
            lines.append(f"Post à améliorer: {worst_post.get('content', '')[:80]}...")

        return "\n".join(lines)

    @staticmethod
    def _fallback_recommendations(posts: list[dict], conversations: list[dict]) -> list[dict]:
        """Generate basic rule-based recommendations when LLM is unavailable."""
        recs: list[dict] = []

        published = [p for p in posts if p.get("status") == "published"]
        if len(published) < 3:
            recs.append({
                "title": "Augmenter la fréquence de publication",
                "description": "Vous avez publié peu de contenu cette période. Visez au moins 3 posts par semaine.",
                "priority": "high",
            })

        resolved = [c for c in conversations if c.get("status") == "resolved"]
        if conversations and len(resolved) / len(conversations) < 0.7:
            recs.append({
                "title": "Améliorer le taux de résolution",
                "description": "Moins de 70% des conversations sont résolues. Renforcez la base de connaissances.",
                "priority": "high",
            })

        if not recs:
            recs.append({
                "title": "Continuer les efforts actuels",
                "description": "Vos indicateurs sont bons. Maintenez le rythme de publication et de réponse.",
                "priority": "low",
            })

        return recs

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    async def _llm_weekly_summary(
        self,
        summary: dict,
        best_post: dict | None,
        worst_post: dict | None,
        brand: dict,
    ) -> dict | None:
        """Use LLM to generate a natural-language weekly summary and recommendations."""
        try:
            from app.integrations.llm import get_llm_router

            data_block = json.dumps(
                {"summary": summary, "best_post": best_post, "worst_post": worst_post},
                ensure_ascii=False,
                default=str,
            )

            llm = get_llm_router()
            response = await llm.generate(
                task_type="analysis",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_prompt_manager().get_prompt(
                            "analytics", "weekly_summary",
                            brand_name=brand.get("brand_name", "une entreprise"),
                            industry=brand.get("industry", ""),
                            country=brand.get("country", "international"),
                            language=brand.get("language", "français"),
                        ),
                    },
                    {"role": "user", "content": data_block},
                ],
            )
            parsed = json.loads(response.content)
            parsed["tokens_used"] = response.tokens_used
            parsed["model"] = response.model
            return parsed
        except Exception as e:
            logger.warning("llm_weekly_summary_failed", error=str(e))
            return None

    async def _llm_post_insights(self, posts: list[dict], brand: dict) -> dict | None:
        """Use LLM to extract post performance insights."""
        try:
            from app.integrations.llm import get_llm_router

            # Send a condensed version of posts (limit to 20)
            condensed = []
            for p in posts[:20]:
                condensed.append({
                    "content": (p.get("content", "") or "")[:150],
                    "channel": p.get("channel"),
                    "status": p.get("status"),
                    "engagement": p.get("engagement", {}),
                })

            llm = get_llm_router()
            response = await llm.generate(
                task_type="analysis",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_prompt_manager().get_prompt(
                            "analytics", "post_insights",
                            brand_name=brand.get("brand_name", "une entreprise"),
                            language=brand.get("language", "français"),
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(condensed, ensure_ascii=False, default=str),
                    },
                ],
            )
            parsed = json.loads(response.content)
            parsed["tokens_used"] = response.tokens_used
            parsed["model"] = response.model
            return parsed
        except Exception as e:
            logger.warning("llm_post_insights_failed", error=str(e))
            return None

    async def _llm_recommendations(
        self, snapshot: dict, posts: list[dict], brand: dict
    ) -> dict | None:
        """Use LLM to generate strategic recommendations."""
        try:
            from app.integrations.llm import get_llm_router

            # Condense post content for the prompt
            post_samples = []
            for p in posts[:15]:
                post_samples.append({
                    "content": (p.get("content", "") or "")[:120],
                    "channel": p.get("channel"),
                    "status": p.get("status"),
                    "engagement": p.get("engagement", {}),
                    "published_at": p.get("published_at"),
                })

            llm = get_llm_router()
            response = await llm.generate(
                task_type="analysis",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_prompt_manager().get_prompt(
                            "analytics", "recommendations",
                            brand_name=brand.get("brand_name", "une entreprise"),
                            industry=brand.get("industry", ""),
                            country=brand.get("country", "international"),
                            language=brand.get("language", "français"),
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Snapshot: {json.dumps(snapshot, ensure_ascii=False, default=str)}\n\n"
                            f"Échantillon de posts:\n{json.dumps(post_samples, ensure_ascii=False, default=str)}"
                        ),
                    },
                ],
            )
            parsed = json.loads(response.content)
            parsed["tokens_used"] = response.tokens_used
            parsed["model"] = response.model
            return parsed
        except Exception as e:
            logger.warning("llm_recommendations_failed", error=str(e))
            return None

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    async def validate_output(self, result: AgentResult) -> bool:
        if not result.success:
            return False
        output = result.output
        # Must have a summary
        if "summary" not in output:
            return False
        # Must have report_text or recommendations
        if not output.get("report_text") and not output.get("recommendations"):
            return False
        return True
