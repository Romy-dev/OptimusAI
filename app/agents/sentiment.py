"""Sentiment agent — real-time sentiment analysis and brand health monitoring."""

import json
import re
from datetime import datetime

import structlog

from app.agents.base import AgentResult, BaseAgent

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Rule-based keyword dictionaries (French + Mooré + Dioula basics)
# ---------------------------------------------------------------------------

POSITIVE_KEYWORDS = {
    # French
    "merci", "excellent", "super", "bravo", "génial", "parfait", "content",
    "satisfait", "formidable", "magnifique", "bien", "bon", "bonne", "top",
    "rapide", "efficace", "recommande", "adore", "aime", "fantastique",
    "incroyable", "qualité", "fiable", "heureux", "heureuse", "félicitations",
    # Mooré
    "barka", "bark wusgo", "nonglem", "laafi", "sãn-sãn",
    # Dioula
    "i ni cé", "i ni baaraji", "a ka di", "aw ni cé", "diyara",
}

NEGATIVE_KEYWORDS = {
    # French
    "nul", "horrible", "arnaque", "voleur", "voleurs", "honte", "scandale",
    "inacceptable", "furieux", "furieuse", "déçu", "déçue", "colère",
    "déteste", "mécontent", "plainte", "rembourse", "remboursement",
    "escroquerie", "menteur", "faux", "mauvais", "mauvaise", "lent",
    "pire", "catastrophe", "honteux", "inadmissible", "dégueulasse",
    # Mooré
    "ka nonglem", "yel-beed", "ka sõng ye", "sũuri",
    # Dioula
    "a man di", "a ka jugu", "jugu", "kunko",
}

URGENCY_KEYWORDS = {
    "urgent", "urgence", "immédiatement", "tout de suite", "maintenant",
    "vite", "en attente depuis", "ça fait longtemps", "toujours pas",
    "personne ne répond", "dernier avertissement",
}

CRISIS_KEYWORDS = {
    # Threats to go public / legal
    "avocat", "justice", "tribunal", "plainte officielle", "porter plainte",
    "réseaux sociaux", "je vais publier", "faire savoir", "média", "presse",
    "scandale public", "association de consommateurs", "droit des consommateurs",
}

EMOTION_PATTERNS: dict[str, list[str]] = {
    "joy": [
        r"\b(merci|bravo|super|génial|excellent|content|satisfait|adore|barka|i ni cé)\b",
        r"[😊😍🥰❤️👍🎉]+",
    ],
    "frustration": [
        r"\b(encore|toujours pas|ça fait \d+|attend|lent|bug)\b",
        r"\b(en attente|pas de réponse|personne)\b",
    ],
    "anger": [
        r"\b(furieux|colère|inacceptable|honte|scandale|arnaque)\b",
        r"[😡🤬💢]+",
        r"!{2,}",
    ],
    "confusion": [
        r"\b(comprends pas|comment|pourquoi|c'est quoi|pas clair)\b",
        r"\?{2,}",
    ],
    "satisfaction": [
        r"\b(parfait|exactement|très bien|nickel|impeccable|efficace)\b",
    ],
    "urgency": [
        r"\b(urgent|vite|maintenant|immédiat|tout de suite)\b",
        r"!{3,}",
    ],
}


class SentimentAgent(BaseAgent):
    name = "sentiment"
    description = "Analyzes sentiment in real-time and monitors brand health"
    max_retries = 0
    confidence_threshold = 0.3

    @staticmethod
    def _get_prompts():
        """Lazy-load prompt manager to avoid circular imports."""
        from app.prompts.loader import get_prompt_manager
        return get_prompt_manager()

    # ------------------------------------------------------------------
    # Main execute
    # ------------------------------------------------------------------

    async def execute(self, context: dict) -> AgentResult:
        analysis_type = context.get("analysis_type", "single_message")
        brand = context.get("brand_context", {})
        messages = context.get("messages", [])

        if analysis_type == "single_message":
            return await self._analyze_single(messages, brand)
        elif analysis_type == "conversation":
            return await self._analyze_conversation(messages, brand)
        elif analysis_type == "daily_report":
            return await self._generate_daily_report(messages, brand)
        else:
            return AgentResult(
                success=False,
                output={"error": f"Unknown analysis_type: {analysis_type}"},
                confidence_score=0.0,
                agent_name=self.name,
            )

    # ------------------------------------------------------------------
    # Single message analysis
    # ------------------------------------------------------------------

    async def _analyze_single(self, messages: list[dict], brand: dict) -> AgentResult:
        msg = messages[0] if messages else {}
        content = msg.get("content", "")

        # Fast rule-based pass
        rule_score = self._keyword_sentiment_score(content)
        emotions = self._detect_emotions(content)
        crisis = self._detect_crisis(content)

        # LLM refinement for nuance
        llm_result = await self._llm_sentiment(content, brand)
        if llm_result:
            # Blend: 40% rule-based, 60% LLM for more nuanced result
            sentiment_score = round(rule_score * 0.4 + llm_result["score"] * 0.6, 3)
            emotions = list(set(emotions) | set(llm_result.get("emotions", [])))
            if llm_result.get("crisis_detected"):
                crisis = True
        else:
            sentiment_score = rule_score

        alert_level = self._score_to_alert(sentiment_score)

        return AgentResult(
            success=True,
            output={
                "sentiment_score": sentiment_score,
                "emotions": emotions,
                "health_score": self._sentiment_to_health(sentiment_score),
                "alert_level": alert_level,
                "crisis_detected": crisis,
                "themes": {"positive": [], "negative": []},
                "recommended_actions": self._single_actions(sentiment_score, crisis, emotions),
            },
            confidence_score=0.7 if llm_result else 0.4,
            agent_name=self.name,
            tokens_used=llm_result.get("tokens_used") if llm_result else None,
            model_used=llm_result.get("model") if llm_result else None,
        )

    # ------------------------------------------------------------------
    # Conversation analysis
    # ------------------------------------------------------------------

    async def _analyze_conversation(self, messages: list[dict], brand: dict) -> AgentResult:
        if not messages:
            return AgentResult(
                success=False,
                output={"error": "No messages provided"},
                confidence_score=0.0,
                agent_name=self.name,
            )

        # Score each message chronologically
        scores: list[float] = []
        all_emotions: list[str] = []
        any_crisis = False

        for msg in messages:
            content = msg.get("content", "")
            s = self._keyword_sentiment_score(content)
            scores.append(s)
            all_emotions.extend(self._detect_emotions(content))
            if self._detect_crisis(content):
                any_crisis = True

        # Determine trend
        if len(scores) >= 2:
            first_half = sum(scores[: len(scores) // 2]) / max(len(scores) // 2, 1)
            second_half = sum(scores[len(scores) // 2 :]) / max(len(scores) - len(scores) // 2, 1)
            diff = second_half - first_half
            if diff > 0.15:
                trend = "improving"
            elif diff < -0.15:
                trend = "degrading"
            else:
                trend = "stable"
        else:
            trend = "stable"

        avg_score = round(sum(scores) / len(scores), 3) if scores else 0.0
        health = self._sentiment_to_health(avg_score)

        # LLM summary for conversation
        llm_result = await self._llm_conversation_summary(messages, brand)
        tokens_used = None
        model_used = None
        if llm_result:
            tokens_used = llm_result.get("tokens_used")
            model_used = llm_result.get("model")

        return AgentResult(
            success=True,
            output={
                "sentiment_score": avg_score,
                "emotions": list(set(all_emotions)),
                "health_score": health,
                "alert_level": self._score_to_alert(avg_score),
                "crisis_detected": any_crisis,
                "trend": trend,
                "message_scores": scores,
                "themes": {"positive": [], "negative": []},
                "recommended_actions": self._conversation_actions(trend, any_crisis, avg_score),
                "llm_summary": llm_result.get("summary", "") if llm_result else "",
            },
            confidence_score=0.6 if llm_result else 0.35,
            agent_name=self.name,
            tokens_used=tokens_used,
            model_used=model_used,
        )

    # ------------------------------------------------------------------
    # Daily report
    # ------------------------------------------------------------------

    async def _generate_daily_report(self, messages: list[dict], brand: dict) -> AgentResult:
        if not messages:
            return AgentResult(
                success=True,
                output={
                    "sentiment_score": 0.0,
                    "emotions": [],
                    "health_score": 50,
                    "alert_level": "yellow",
                    "crisis_detected": False,
                    "themes": {"positive": [], "negative": []},
                    "recommended_actions": ["Pas assez de données pour générer un rapport."],
                },
                confidence_score=0.2,
                agent_name=self.name,
            )

        scores: list[float] = []
        all_emotions: list[str] = []
        any_crisis = False
        positive_contents: list[str] = []
        negative_contents: list[str] = []

        for msg in messages:
            content = msg.get("content", "")
            s = self._keyword_sentiment_score(content)
            scores.append(s)
            all_emotions.extend(self._detect_emotions(content))
            if self._detect_crisis(content):
                any_crisis = True
            if s > 0.2:
                positive_contents.append(content)
            elif s < -0.2:
                negative_contents.append(content)

        avg_score = round(sum(scores) / len(scores), 3)
        health = self._sentiment_to_health(avg_score)
        alert = self._score_to_alert(avg_score)

        # Use LLM for theme extraction and report generation
        llm_report = await self._llm_daily_report(
            messages, brand, avg_score, health, positive_contents, negative_contents
        )

        themes = {"positive": [], "negative": []}
        recommended_actions: list[str] = []
        tokens_used = None
        model_used = None

        if llm_report:
            themes = llm_report.get("themes", themes)
            recommended_actions = llm_report.get("recommended_actions", [])
            tokens_used = llm_report.get("tokens_used")
            model_used = llm_report.get("model")

        if not recommended_actions:
            recommended_actions = self._daily_actions(health, any_crisis, alert)

        return AgentResult(
            success=True,
            output={
                "sentiment_score": avg_score,
                "emotions": list(set(all_emotions)),
                "health_score": health,
                "alert_level": alert,
                "crisis_detected": any_crisis,
                "themes": themes,
                "recommended_actions": recommended_actions,
                "total_messages": len(messages),
                "positive_count": len(positive_contents),
                "negative_count": len(negative_contents),
                "neutral_count": len(messages) - len(positive_contents) - len(negative_contents),
            },
            confidence_score=0.65 if llm_report else 0.35,
            agent_name=self.name,
            tokens_used=tokens_used,
            model_used=model_used,
        )

    # ------------------------------------------------------------------
    # Rule-based helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _keyword_sentiment_score(text: str) -> float:
        """Fast rule-based sentiment score using keyword dictionaries."""
        text_lower = text.lower()
        words = set(re.findall(r"\w+", text_lower))

        pos_count = len(words & POSITIVE_KEYWORDS)
        neg_count = len(words & NEGATIVE_KEYWORDS)

        # Also check multi-word phrases
        for phrase in POSITIVE_KEYWORDS:
            if " " in phrase and phrase in text_lower:
                pos_count += 1
        for phrase in NEGATIVE_KEYWORDS:
            if " " in phrase and phrase in text_lower:
                neg_count += 1

        total = pos_count + neg_count
        if total == 0:
            return 0.0

        # Score between -1 and +1
        raw = (pos_count - neg_count) / total
        return round(max(-1.0, min(1.0, raw)), 3)

    @staticmethod
    def _detect_emotions(text: str) -> list[str]:
        """Detect emotions using regex patterns."""
        detected: list[str] = []
        for emotion, patterns in EMOTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    detected.append(emotion)
                    break
        return detected

    @staticmethod
    def _detect_crisis(text: str) -> bool:
        """Check for crisis signals in text."""
        text_lower = text.lower()
        for keyword in CRISIS_KEYWORDS:
            if keyword in text_lower:
                return True
        return False

    @staticmethod
    def _sentiment_to_health(score: float) -> int:
        """Convert sentiment score (-1 to +1) to health score (0 to 100)."""
        return int(round((score + 1) / 2 * 100))

    @staticmethod
    def _score_to_alert(score: float) -> str:
        """Convert sentiment score to alert level."""
        health = int(round((score + 1) / 2 * 100))
        if health > 70:
            return "green"
        elif health >= 50:
            return "yellow"
        return "red"

    # ------------------------------------------------------------------
    # Action generators
    # ------------------------------------------------------------------

    @staticmethod
    def _single_actions(score: float, crisis: bool, emotions: list[str]) -> list[str]:
        actions: list[str] = []
        if crisis:
            actions.append("Alerte crise : escalader immédiatement à un responsable.")
        if score < -0.5:
            actions.append("Client très mécontent — prioriser une réponse empathique rapide.")
        if "anger" in emotions:
            actions.append("Colère détectée — adopter un ton calme et proposer une solution.")
        if "urgency" in emotions:
            actions.append("Urgence signalée — répondre dans les plus brefs délais.")
        if not actions:
            if score > 0.3:
                actions.append("Sentiment positif — remercier le client et renforcer la relation.")
            else:
                actions.append("Sentiment neutre — aucune action immédiate requise.")
        return actions

    @staticmethod
    def _conversation_actions(trend: str, crisis: bool, avg_score: float) -> list[str]:
        actions: list[str] = []
        if crisis:
            actions.append("Crise détectée dans la conversation — escalader immédiatement.")
        if trend == "degrading":
            actions.append("Le sentiment se dégrade — intervenir pour redresser la situation.")
        if avg_score < -0.3:
            actions.append("Conversation globalement négative — proposer un geste commercial.")
        if trend == "improving":
            actions.append("Bonne évolution — continuer dans cette direction.")
        if not actions:
            actions.append("Conversation stable — aucune action urgente.")
        return actions

    @staticmethod
    def _daily_actions(health: int, crisis: bool, alert: str) -> list[str]:
        actions: list[str] = []
        if crisis:
            actions.append("Signaux de crise détectés aujourd'hui — vérifier les plaintes récurrentes.")
        if alert == "red":
            actions.append("Santé de marque critique — réunion d'urgence recommandée.")
            actions.append("Identifier les causes principales de mécontentement.")
        elif alert == "yellow":
            actions.append("Santé de marque modérée — surveiller de près les retours négatifs.")
        else:
            actions.append("Bonne santé de marque — maintenir les efforts actuels.")
        return actions

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    async def _llm_sentiment(self, content: str, brand: dict) -> dict | None:
        """Use LLM for nuanced sentiment analysis on a single message."""
        try:
            from app.integrations.llm import get_llm_router

            llm = get_llm_router()
            response = await llm.generate(
                task_type="analysis",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_prompts().get_prompt(
                            "sentiment", "system",
                            brand_name=brand.get("brand_name", ""),
                            industry=brand.get("industry", ""),
                        ),
                    },
                    {"role": "user", "content": content},
                ],
            )
            parsed = json.loads(response.content)
            parsed["tokens_used"] = response.tokens_used
            parsed["model"] = response.model
            return parsed
        except Exception as e:
            logger.warning("llm_sentiment_failed", error=str(e))
            return None

    async def _llm_conversation_summary(self, messages: list[dict], brand: dict) -> dict | None:
        """Use LLM to summarize conversation sentiment."""
        try:
            from app.integrations.llm import get_llm_router

            formatted = []
            for msg in messages[-20:]:
                direction = msg.get("direction", "unknown")
                role = "Client" if direction == "inbound" else "Support"
                ts = msg.get("timestamp", "")
                formatted.append(f"[{ts}] {role}: {msg.get('content', '')}")
            conversation_text = "\n".join(formatted)

            llm = get_llm_router()
            response = await llm.generate(
                task_type="analysis",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_prompts().get_prompt(
                            "sentiment", "conversation",
                            brand_name=brand.get("brand_name", ""),
                        ),
                    },
                    {"role": "user", "content": conversation_text},
                ],
            )
            parsed = json.loads(response.content)
            parsed["tokens_used"] = response.tokens_used
            parsed["model"] = response.model
            return parsed
        except Exception as e:
            logger.warning("llm_conversation_summary_failed", error=str(e))
            return None

    async def _llm_daily_report(
        self,
        messages: list[dict],
        brand: dict,
        avg_score: float,
        health: int,
        positive_contents: list[str],
        negative_contents: list[str],
    ) -> dict | None:
        """Use LLM to extract themes and generate daily report insights."""
        try:
            from app.integrations.llm import get_llm_router

            # Provide a sample of messages for theme extraction
            positive_sample = positive_contents[:10]
            negative_sample = negative_contents[:10]

            llm = get_llm_router()
            response = await llm.generate(
                task_type="analysis",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_prompts().get_prompt(
                            "sentiment", "daily_report",
                            brand_name=brand.get("brand_name", ""),
                            industry=brand.get("industry", ""),
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Score moyen: {avg_score}, Santé: {health}/100\n"
                            f"Total messages: {len(messages)}\n"
                            f"Positifs ({len(positive_contents)}): "
                            + json.dumps(positive_sample, ensure_ascii=False)
                            + f"\nNégatifs ({len(negative_contents)}): "
                            + json.dumps(negative_sample, ensure_ascii=False)
                        ),
                    },
                ],
            )
            parsed = json.loads(response.content)
            parsed["tokens_used"] = response.tokens_used
            parsed["model"] = response.model
            return parsed
        except Exception as e:
            logger.warning("llm_daily_report_failed", error=str(e))
            return None

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    async def validate_output(self, result: AgentResult) -> bool:
        if not result.success:
            return False
        output = result.output
        # Must have a sentiment score
        if "sentiment_score" not in output:
            return False
        return True
