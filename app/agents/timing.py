"""Timing agent — optimizes publication times based on audience behavior."""

import json
import re
from datetime import datetime

import structlog

from app.agents.base import AgentResult, BaseAgent

logger = structlog.get_logger()


# Peak posting times per country group and platform (local time)
# Format: list of (start_hour, end_hour) tuples for peak windows
PEAK_TIMES: dict[str, dict[str, list[tuple[int, int]]]] = {
    # GMT+0 countries
    "BF": {
        "facebook": [(12, 14), (19, 21)],
        "instagram": [(11, 13), (18, 20)],
        "whatsapp": [(8, 10), (17, 19)],
    },
    "CI": {
        "facebook": [(12, 14), (19, 21)],
        "instagram": [(11, 13), (18, 20)],
        "whatsapp": [(8, 10), (17, 19)],
    },
    "SN": {
        "facebook": [(12, 14), (19, 21)],
        "instagram": [(11, 13), (18, 20)],
        "whatsapp": [(8, 10), (17, 19)],
    },
    "ML": {
        "facebook": [(12, 14), (19, 21)],
        "instagram": [(11, 13), (18, 20)],
        "whatsapp": [(8, 10), (17, 19)],
    },
    # GMT+1 countries
    "CM": {
        "facebook": [(13, 15), (20, 22)],
        "instagram": [(12, 14), (19, 21)],
        "whatsapp": [(9, 11), (18, 20)],
    },
    # GMT+1/+2 (Europe)
    "FR": {
        "facebook": [(12, 14), (20, 22)],
        "instagram": [(11, 13), (19, 21)],
        "whatsapp": [(8, 10), (18, 20)],
    },
}

TIMEZONES: dict[str, str] = {
    "BF": "GMT+0",
    "CI": "GMT+0",
    "SN": "GMT+0",
    "ML": "GMT+0",
    "CM": "GMT+1",
    "FR": "GMT+1",
}

# Content type time adjustments
# Maps content_type to preferred peak window index and offset
CONTENT_TYPE_PREFERENCES: dict[str, dict] = {
    "promo": {
        "preferred_windows": [0],  # First peak (morning/lunch)
        "offset_minutes": 0,
        "reason": "Les promotions fonctionnent mieux le matin/midi quand les gens planifient leurs achats",
    },
    "educational": {
        "preferred_windows": [0],  # First peak (mid-morning)
        "offset_minutes": -60,  # Slightly earlier
        "reason": "Le contenu éducatif est mieux reçu en milieu de matinée quand l'attention est maximale",
    },
    "engagement": {
        "preferred_windows": [1],  # Second peak (evening)
        "offset_minutes": 0,
        "reason": "L'engagement est plus fort le soir quand les gens sont détendus et disponibles",
    },
    "storytelling": {
        "preferred_windows": [1],  # Second peak (evening)
        "offset_minutes": 30,
        "reason": "Le storytelling fonctionne bien en soirée quand les gens prennent le temps de lire",
    },
    "product_showcase": {
        "preferred_windows": [0],  # First peak
        "offset_minutes": 30,
        "reason": "La vitrine produit fonctionne bien à l'heure du déjeuner",
    },
    "behind_the_scenes": {
        "preferred_windows": [0, 1],  # Either peak
        "offset_minutes": 0,
        "reason": "Le contenu coulisses fonctionne à tout moment de forte audience",
    },
    "testimonial": {
        "preferred_windows": [1],  # Evening
        "offset_minutes": -30,
        "reason": "Les témoignages sont mieux reçus en début de soirée",
    },
}

# Cultural adjustments
CULTURAL_FACTORS: dict[str, list[dict]] = {
    # Muslim-majority countries
    "BF": [
        {"day": "friday", "avoid_start": 12, "avoid_end": 15, "reason": "Prière du vendredi"},
    ],
    "SN": [
        {"day": "friday", "avoid_start": 12, "avoid_end": 15, "reason": "Prière du vendredi"},
    ],
    "ML": [
        {"day": "friday", "avoid_start": 12, "avoid_end": 15, "reason": "Prière du vendredi"},
    ],
    "CI": [
        {"day": "friday", "avoid_start": 12, "avoid_end": 15, "reason": "Prière du vendredi (zones musulmanes)"},
        {"day": "sunday", "avoid_start": 8, "avoid_end": 12, "reason": "Offices religieux du dimanche"},
    ],
    "CM": [
        {"day": "sunday", "avoid_start": 8, "avoid_end": 12, "reason": "Offices religieux du dimanche"},
        {"day": "friday", "avoid_start": 12, "avoid_end": 15, "reason": "Prière du vendredi (zones musulmanes)"},
    ],
    "FR": [
        {"day": "sunday", "avoid_start": 9, "avoid_end": 11, "reason": "Matinée dimanche moins active"},
    ],
}

# Best days by engagement (general West African patterns)
DAY_RANKINGS: dict[str, list[str]] = {
    "facebook": ["mercredi", "jeudi", "mardi", "vendredi", "lundi", "samedi", "dimanche"],
    "instagram": ["mardi", "mercredi", "jeudi", "vendredi", "lundi", "samedi", "dimanche"],
    "whatsapp": ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"],
}

DAY_NAME_TO_ENGLISH: dict[str, str] = {
    "lundi": "monday",
    "mardi": "tuesday",
    "mercredi": "wednesday",
    "jeudi": "thursday",
    "vendredi": "friday",
    "samedi": "saturday",
    "dimanche": "sunday",
}


class TimingAgent(BaseAgent):
    name = "timing"
    description = "Optimizes post publication timing for maximum engagement"
    max_retries = 0
    confidence_threshold = 0.5

    @staticmethod
    def _get_prompt_manager():
        """Lazy-load prompt manager to avoid circular imports."""
        from app.prompts.loader import get_prompt_manager
        return get_prompt_manager()

    async def execute(self, context: dict) -> AgentResult:
        platform = context.get("platform", "facebook")
        target_country = context.get("target_country", "BF")
        content_type = context.get("content_type", "engagement")
        brand = context.get("brand_context", {})
        recent_posts = context.get("recent_posts", [])

        # Step 1: Get base peak windows for country + platform
        country_peaks = PEAK_TIMES.get(target_country, PEAK_TIMES["BF"])
        platform_peaks = country_peaks.get(platform, country_peaks.get("facebook", [(12, 14), (19, 21)]))

        # Step 2: Determine preferred window based on content type
        type_pref = CONTENT_TYPE_PREFERENCES.get(content_type, CONTENT_TYPE_PREFERENCES["engagement"])
        preferred_indices = type_pref["preferred_windows"]
        offset_minutes = type_pref["offset_minutes"]
        base_reason = type_pref["reason"]

        # Pick the best matching peak window
        window_idx = preferred_indices[0] if preferred_indices[0] < len(platform_peaks) else 0
        peak_start, peak_end = platform_peaks[window_idx]

        # Calculate recommended time (middle of peak window + offset)
        mid_hour = (peak_start + peak_end) / 2
        total_minutes = int(mid_hour * 60) + offset_minutes
        rec_hour = max(6, min(23, total_minutes // 60))
        rec_minute = total_minutes % 60
        # Round to nearest 15 minutes
        rec_minute = (rec_minute // 15) * 15
        recommended_time = f"{rec_hour:02d}:{rec_minute:02d}"

        # Step 3: Determine best day
        day_ranking = DAY_RANKINGS.get(platform, DAY_RANKINGS["facebook"])
        recommended_day = day_ranking[0]

        # Step 4: Apply cultural adjustments
        cultural_adjustments = CULTURAL_FACTORS.get(target_country, [])
        cultural_notes: list[str] = []

        for factor in cultural_adjustments:
            day_en = DAY_NAME_TO_ENGLISH.get(recommended_day, "")
            if day_en == factor["day"]:
                if factor["avoid_start"] <= rec_hour < factor["avoid_end"]:
                    # Shift to after the avoidance window
                    rec_hour = factor["avoid_end"]
                    rec_minute = 0
                    recommended_time = f"{rec_hour:02d}:{rec_minute:02d}"
                    cultural_notes.append(factor["reason"])

        # Step 5: Learn from recent posts if engagement data available
        learned_adjustment = self._learn_from_history(recent_posts, platform, content_type)
        if learned_adjustment:
            cultural_notes.append(learned_adjustment["note"])
            # If historical data strongly suggests a different time, use it
            if learned_adjustment.get("confidence", 0) > 0.7:
                recommended_time = learned_adjustment["time"]
                recommended_day = learned_adjustment.get("day", recommended_day)

        # Step 6: Build alternative times
        alternative_times = self._build_alternatives(
            platform_peaks, recommended_time, offset_minutes, target_country
        )

        # Step 7: Compute confidence
        confidence = self._compute_confidence(recent_posts, platform, target_country)

        # Build reasoning
        timezone = TIMEZONES.get(target_country, "GMT+0")
        reasoning_parts = [
            f"Plateforme {platform} en {target_country} ({timezone}).",
            base_reason + ".",
            f"Fenêtre de pic: {peak_start}h-{peak_end}h.",
            f"Meilleur jour général: {recommended_day}.",
        ]
        if cultural_notes:
            reasoning_parts.append("Ajustements culturels: " + "; ".join(cultural_notes) + ".")
        if learned_adjustment:
            reasoning_parts.append(f"Apprentissage historique: {learned_adjustment['note']}.")

        reasoning = " ".join(reasoning_parts)

        # Step 8: For edge cases or if confidence is low, optionally consult LLM
        if confidence < 0.4 and recent_posts:
            llm_suggestion = await self._llm_refinement(
                context, recommended_time, recommended_day, reasoning
            )
            if llm_suggestion:
                reasoning += f" Affinement LLM: {llm_suggestion.get('note', '')}."
                if llm_suggestion.get("time"):
                    alternative_times.insert(0, llm_suggestion["time"])

        return AgentResult(
            success=True,
            output={
                "recommended_time": recommended_time,
                "recommended_day": recommended_day,
                "timezone": timezone,
                "reasoning": reasoning,
                "alternative_times": alternative_times[:5],
            },
            confidence_score=confidence,
            agent_name=self.name,
        )

    @staticmethod
    def _learn_from_history(
        recent_posts: list[dict],
        platform: str,
        content_type: str,
    ) -> dict | None:
        """Analyze recent post performance to find optimal times."""
        if not recent_posts:
            return None

        # Filter posts with engagement data on the same platform
        relevant = []
        for post in recent_posts:
            if post.get("channel") != platform:
                continue
            engagement = post.get("engagement", {})
            if not engagement:
                continue
            published_at = post.get("published_at", "")
            if not published_at:
                continue
            # Sum engagement metrics
            total_eng = sum(
                v for v in engagement.values() if isinstance(v, (int, float))
            )
            relevant.append({
                "published_at": published_at,
                "content_type": post.get("content_type", ""),
                "total_engagement": total_eng,
            })

        if len(relevant) < 3:
            return None

        # Sort by engagement and take top performers
        relevant.sort(key=lambda x: x["total_engagement"], reverse=True)
        top = relevant[:3]

        # Try to extract common patterns from top performers
        hours = []
        days = []
        day_names_fr = {
            0: "lundi", 1: "mardi", 2: "mercredi", 3: "jeudi",
            4: "vendredi", 5: "samedi", 6: "dimanche",
        }

        for post in top:
            try:
                # Handle various datetime formats
                pub = post["published_at"]
                if isinstance(pub, str):
                    # Try ISO format
                    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
                        try:
                            dt = datetime.strptime(pub[:19], fmt[:len(pub[:19])])
                            hours.append(dt.hour)
                            days.append(day_names_fr[dt.weekday()])
                            break
                        except ValueError:
                            continue
            except (KeyError, ValueError):
                continue

        if not hours:
            return None

        # Find most common hour and day from top performers
        avg_hour = round(sum(hours) / len(hours))
        # Most frequent day
        from collections import Counter
        day_counts = Counter(days)
        best_day = day_counts.most_common(1)[0][0] if day_counts else None

        result: dict = {
            "time": f"{avg_hour:02d}:00",
            "note": f"Basé sur les {len(relevant)} posts récents, les meilleurs résultats sont vers {avg_hour}h",
            "confidence": min(0.8, len(relevant) / 10),
        }
        if best_day:
            result["day"] = best_day
            result["note"] += f" le {best_day}"

        return result

    @staticmethod
    def _build_alternatives(
        platform_peaks: list[tuple[int, int]],
        recommended_time: str,
        offset_minutes: int,
        target_country: str,
    ) -> list[str]:
        """Build a list of alternative posting times."""
        alternatives: list[str] = []

        for peak_start, peak_end in platform_peaks:
            # Start of peak
            alt_time = f"{peak_start:02d}:00"
            if alt_time != recommended_time:
                alternatives.append(alt_time)

            # Middle of peak
            mid = (peak_start + peak_end) // 2
            alt_time = f"{mid:02d}:30"
            if alt_time != recommended_time:
                alternatives.append(alt_time)

            # End of peak minus 30 min
            end_h = peak_end - 1
            alt_time = f"{end_h:02d}:30"
            if alt_time != recommended_time and alt_time not in alternatives:
                alternatives.append(alt_time)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for t in alternatives:
            if t not in seen:
                seen.add(t)
                unique.append(t)

        return unique[:5]

    @staticmethod
    def _compute_confidence(
        recent_posts: list[dict],
        platform: str,
        target_country: str,
    ) -> float:
        """Compute confidence score for the timing recommendation."""
        score = 0.6  # Base: rule-based is reasonably confident

        # Known country
        if target_country in PEAK_TIMES:
            score += 0.1

        # Known platform
        if platform in ("facebook", "instagram", "whatsapp"):
            score += 0.05

        # Historical data available
        posts_with_engagement = [
            p for p in recent_posts
            if p.get("engagement") and p.get("channel") == platform
        ]
        if len(posts_with_engagement) >= 5:
            score += 0.15
        elif len(posts_with_engagement) >= 2:
            score += 0.05

        return max(0.0, min(1.0, score))

    async def _llm_refinement(
        self,
        context: dict,
        recommended_time: str,
        recommended_day: str,
        reasoning: str,
    ) -> dict | None:
        """Use LLM for edge-case refinement when rule-based confidence is low."""
        try:
            from app.integrations.llm import get_llm_router

            brand = context.get("brand_context", {})
            platform = context.get("platform", "facebook")
            target_country = context.get("target_country", "BF")

            llm = get_llm_router()
            response = await llm.generate(
                task_type="timing",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_prompt_manager().get_prompt("timing", "system"),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Marque: {brand.get('brand_name', '?')} ({brand.get('industry', '?')})\n"
                            f"Plateforme: {platform}, Pays: {target_country}\n"
                            f"Recommandation actuelle: {recommended_day} à {recommended_time}\n"
                            f"Raisonnement: {reasoning}\n\n"
                            "Y a-t-il un meilleur créneau ? Retourne uniquement le JSON."
                        ),
                    },
                ],
            )

            # Parse response
            cleaned = response.content.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                cleaned = re.sub(r"\s*```$", "", cleaned)

            parsed = json.loads(cleaned)
            return {
                "time": parsed.get("time", recommended_time),
                "note": parsed.get("note", ""),
            }
        except Exception as e:
            logger.warning("timing_llm_refinement_failed", error=str(e))
            return None

    async def validate_output(self, result: AgentResult) -> bool:
        time_str = result.output.get("recommended_time", "")
        if not time_str or not re.match(r"^\d{2}:\d{2}$", time_str):
            return False
        day = result.output.get("recommended_day", "")
        if not day:
            return False
        return True
