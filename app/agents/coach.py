"""Coach Marketing Agent — proactive suggestions and activity analysis."""

import structlog
from app.agents.base import AgentResult, BaseAgent
from app.integrations.llm import get_llm_router

logger = structlog.get_logger()

SYSTEM_PROMPT = """Tu es un coach marketing IA expert. Tu analyses l'activité d'une entreprise sur les réseaux sociaux et proposes des suggestions concrètes et actionnables.

Contexte de la marque :
- Nom : {brand_name}
- Secteur : {industry}
- Pays : {country}
- Langue : {language}

Activité récente :
{activity_summary}

Analyse cette activité et propose 3 à 5 suggestions ordonnées par priorité.

Pour chaque suggestion, retourne un JSON avec :
- priority : "high", "medium" ou "low"
- category : "content", "engagement", "setup", "optimization", "growth"
- title : titre court et accrocheur (max 60 caractères)
- description : explication en 1-2 phrases de pourquoi c'est important
- action : l'action à exécuter (ex: "create_post", "connect_social", "add_knowledge", "complete_brand", "generate_poster", "optimize_timing", "add_products")
- action_params : paramètres de l'action (dict)
- quick_action_label : texte du bouton d'action (max 25 caractères)

Ajoute aussi :
- health_score : score global de santé marketing de 0 à 100
- summary : résumé en 1 phrase de la situation

Réponds UNIQUEMENT en JSON valide :
{
  "suggestions": [...],
  "health_score": 72,
  "summary": "..."
}
"""


class CoachAgent(BaseAgent):
    """Proactive marketing coach that analyzes tenant activity and suggests actions."""

    name = "coach"
    description = "Analyse l'activité marketing et propose des suggestions proactives"
    max_retries = 1
    confidence_threshold = 0.5

    async def execute(self, context: dict) -> AgentResult:
        llm = get_llm_router()

        # Build activity summary from context
        activity_parts = []

        posts_count = context.get("posts_count", 0)
        posts_last_7d = context.get("posts_last_7d", 0)
        activity_parts.append(f"- Posts totaux : {posts_count} (dont {posts_last_7d} ces 7 derniers jours)")

        conversations_count = context.get("conversations_count", 0)
        conversations_open = context.get("conversations_open", 0)
        activity_parts.append(f"- Conversations : {conversations_count} totales ({conversations_open} ouvertes)")

        connected_platforms = context.get("connected_platforms", [])
        if connected_platforms:
            activity_parts.append(f"- Réseaux connectés : {', '.join(connected_platforms)}")
        else:
            activity_parts.append("- Réseaux connectés : AUCUN")

        kb_docs = context.get("knowledge_docs", 0)
        activity_parts.append(f"- Documents base de connaissance : {kb_docs}")

        brand_completeness = context.get("brand_completeness", 0)
        activity_parts.append(f"- Complétude du profil marque : {brand_completeness}%")

        products_count = context.get("products_count", 0)
        activity_parts.append(f"- Produits/services référencés : {products_count}")

        images_count = context.get("images_count", 0)
        activity_parts.append(f"- Images générées : {images_count}")

        templates_count = context.get("templates_count", 0)
        activity_parts.append(f"- Templates design : {templates_count}")

        last_post_date = context.get("last_post_date", "jamais")
        activity_parts.append(f"- Dernier post : {last_post_date}")

        activity_summary = "\n".join(activity_parts)

        prompt = SYSTEM_PROMPT.format(
            brand_name=context.get("brand_name", "Non défini"),
            industry=context.get("industry", "Non défini"),
            country=context.get("country", "Non défini"),
            language=context.get("language", "français"),
            activity_summary=activity_summary,
        )

        response = await llm.generate(
            task_type="support",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Analyse mon activité et propose des suggestions concrètes."},
            ],
            temperature=0.6,
            max_tokens=1200,
        )

        try:
            import json
            # Try to extract JSON from response
            content = response.content
            # Handle markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            parsed = json.loads(content.strip())

            suggestions = parsed.get("suggestions", [])
            health_score = parsed.get("health_score", 50)
            summary = parsed.get("summary", "")

            return AgentResult(
                success=True,
                output={
                    "suggestions": suggestions,
                    "health_score": health_score,
                    "summary": summary,
                },
                confidence_score=0.8,
                agent_name=self.name,
                tokens_used=response.tokens_used,
                model_used=response.model,
            )

        except Exception as e:
            logger.warning("coach_parse_error", error=str(e), raw=response.content[:200])
            # Return rule-based fallback suggestions
            suggestions = self._fallback_suggestions(context)
            return AgentResult(
                success=True,
                output={
                    "suggestions": suggestions,
                    "health_score": self._compute_health(context),
                    "summary": "Analyse basée sur les métriques d'activité.",
                },
                confidence_score=0.5,
                agent_name=self.name,
            )

    def _fallback_suggestions(self, context: dict) -> list[dict]:
        """Rule-based suggestions when LLM fails."""
        suggestions = []

        if not context.get("connected_platforms"):
            suggestions.append({
                "priority": "high",
                "category": "setup",
                "title": "Connectez vos réseaux sociaux",
                "description": "Sans connexion, impossible de publier automatiquement. Connectez Facebook, Instagram ou WhatsApp.",
                "action": "navigate",
                "action_params": {"page": "/connections"},
                "quick_action_label": "Connecter",
            })

        if context.get("brand_completeness", 0) < 50:
            suggestions.append({
                "priority": "high",
                "category": "setup",
                "title": "Complétez votre profil de marque",
                "description": "Un profil complet permet à l'IA de générer du contenu plus pertinent et personnalisé.",
                "action": "navigate",
                "action_params": {"page": "/brands"},
                "quick_action_label": "Compléter",
            })

        if context.get("knowledge_docs", 0) == 0:
            suggestions.append({
                "priority": "high",
                "category": "setup",
                "title": "Ajoutez une FAQ ou un catalogue",
                "description": "La base de connaissance permet au support IA de répondre aux questions de vos clients.",
                "action": "navigate",
                "action_params": {"page": "/knowledge"},
                "quick_action_label": "Ajouter",
            })

        if context.get("posts_last_7d", 0) == 0:
            suggestions.append({
                "priority": "high",
                "category": "content",
                "title": "Publiez du contenu cette semaine",
                "description": "Aucun post depuis 7 jours. La régularité est clé pour l'engagement.",
                "action": "create_post",
                "action_params": {},
                "quick_action_label": "Créer un post",
            })

        if context.get("posts_last_7d", 0) > 0 and context.get("images_count", 0) == 0:
            suggestions.append({
                "priority": "medium",
                "category": "content",
                "title": "Générez des visuels pour vos posts",
                "description": "Les posts avec images obtiennent 2x plus d'engagement.",
                "action": "navigate",
                "action_params": {"page": "/gallery"},
                "quick_action_label": "Générer",
            })

        if context.get("templates_count", 0) == 0:
            suggestions.append({
                "priority": "medium",
                "category": "optimization",
                "title": "Uploadez des affiches de référence",
                "description": "L'IA analysera vos designs existants pour créer des affiches dans votre style.",
                "action": "navigate",
                "action_params": {"page": "/templates"},
                "quick_action_label": "Uploader",
            })

        if context.get("products_count", 0) == 0:
            suggestions.append({
                "priority": "medium",
                "category": "setup",
                "title": "Ajoutez vos produits/services",
                "description": "L'IA pourra recommander vos produits dans les conversations clients.",
                "action": "navigate",
                "action_params": {"page": "/brands"},
                "quick_action_label": "Ajouter",
            })

        return suggestions[:5]

    def _compute_health(self, context: dict) -> int:
        """Compute a health score 0-100 based on activity metrics."""
        score = 0
        # Brand setup (30 points)
        score += min(30, int(context.get("brand_completeness", 0) * 0.3))
        # Content activity (25 points)
        posts_7d = context.get("posts_last_7d", 0)
        score += min(25, posts_7d * 8)
        # Connectivity (20 points)
        platforms = len(context.get("connected_platforms", []))
        score += min(20, platforms * 10)
        # Knowledge base (15 points)
        docs = context.get("knowledge_docs", 0)
        score += min(15, docs * 5)
        # Visual content (10 points)
        images = context.get("images_count", 0)
        score += min(10, images * 2)

        return min(100, score)
