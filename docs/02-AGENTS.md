# OptimusAI — Design des Agents

## Philosophie

Chaque agent est un **spécialiste** avec un rôle bien défini, des outils limités, et un niveau de confiance explicite. L'**orchestrateur** est le chef d'orchestre qui route les requêtes vers le bon agent.

**Principes clés :**
- Un agent ne fait qu'une chose, bien
- Chaque agent a un score de confiance sur ses outputs
- Si le score est bas → escalade humaine
- Chaque agent écrit un log d'exécution (`agent_run`)
- Les agents ne s'appellent pas entre eux directement — ils passent par l'orchestrateur
- Les agents n'ont pas accès direct à la DB — ils utilisent des tools/services

---

## Agent 1 : Orchestrateur (`OrchestratorAgent`)

| Attribut | Valeur |
|----------|--------|
| **Rôle** | Router la requête vers le bon agent spécialisé. Décomposer les tâches complexes en sous-tâches. Agréger les résultats. |
| **Inputs** | Requête utilisateur ou événement système (webhook, cron, action UI) |
| **Outputs** | Plan d'exécution → résultats agrégés des sous-agents |
| **Tools autorisés** | `route_to_agent`, `decompose_task`, `aggregate_results`, `check_permissions` |
| **Contraintes** | Ne génère jamais de contenu lui-même. N'a pas accès aux API sociales directement. |
| **Niveau de confiance** | N/A (il route, ne produit pas) |
| **Règles d'escalade** | Si aucun agent ne match → escalade humaine. Si la tâche est ambiguë → demander clarification via UI. |
| **Mémoire** | Historique des tâches récentes du tenant, préférences de routing |
| **Erreurs possibles** | Agent cible indisponible, tâche non reconnue, permissions insuffisantes |
| **Fallback** | File la requête dans une queue humaine avec le contexte |

### Logique de routing

```python
class TaskType(str, Enum):
    GENERATE_POST = "generate_post"
    GENERATE_IMAGE = "generate_image"
    PUBLISH_POST = "publish_post"
    REPLY_COMMENT = "reply_comment"
    REPLY_MESSAGE = "reply_message"
    SUPPORT_QUERY = "support_query"
    SEARCH_KNOWLEDGE = "search_knowledge"
    ANALYZE_PERFORMANCE = "analyze_performance"
    MODERATE_CONTENT = "moderate_content"
    ESCALATE_TO_HUMAN = "escalate_to_human"

ROUTING_TABLE = {
    TaskType.GENERATE_POST: "copywriter",
    TaskType.GENERATE_IMAGE: "image_gen",
    TaskType.PUBLISH_POST: "publisher",
    TaskType.REPLY_COMMENT: "social_reply",
    TaskType.REPLY_MESSAGE: "support",       # Messages = support
    TaskType.SUPPORT_QUERY: "support",
    TaskType.SEARCH_KNOWLEDGE: "knowledge_retriever",
    TaskType.ANALYZE_PERFORMANCE: "analytics",
    TaskType.MODERATE_CONTENT: "moderator",
    TaskType.ESCALATE_TO_HUMAN: "escalation",
}
```

### Flux multi-agents (exemple : génération + publication)

```
User: "Crée un post pour promouvoir notre nouveau tissu wax et publie-le sur Facebook"

Orchestrator:
  1. Détecte 2 tâches: GENERATE_POST + PUBLISH_POST
  2. GENERATE_POST → CopywriterAgent
     → Output: texte du post + hashtags
  3. MODERATE_CONTENT → ModeratorAgent
     → Output: score=0.95, approved=true
  4. Demande validation humaine (si config l'exige)
  5. PUBLISH_POST → PublisherAgent
     → Output: post_id Facebook, status=published
  6. Retourne résultat consolidé à l'utilisateur
```

---

## Agent 2 : Copywriter (`CopywriterAgent`)

| Attribut | Valeur |
|----------|--------|
| **Rôle** | Générer du contenu textuel marketing (posts, captions, réponses) adapté à la marque, au canal et au contexte culturel |
| **Inputs** | `brand_context` (tone, industry, language), `channel` (facebook, instagram, whatsapp), `brief` (sujet, objectif, contraintes), `templates` optionnels, `past_posts` pour cohérence |
| **Outputs** | `content: str`, `hashtags: list[str]`, `suggested_media_prompt: str` (pour l'agent image), `confidence_score: float`, `variants: list[str]` (A/B testing) |
| **Tools autorisés** | `search_knowledge` (contexte entreprise), `get_brand_guidelines`, `get_past_posts`, `get_trending_topics` |
| **Contraintes** | Respecter la longueur max par canal. Pas de contenu offensant. Français par défaut, adaptable. Ne publie JAMAIS directement. |
| **Niveau de confiance** | 0.0-1.0 basé sur: pertinence du brief, qualité du contexte brand, longueur appropriée |
| **Règles d'escalade** | Score < 0.6 → rewrite auto (1 retry). Score < 0.4 après retry → escalade humaine. Brief trop vague → demander clarification. |
| **Mémoire** | Derniers posts générés (éviter répétition), brand voice, termes à éviter |
| **Erreurs possibles** | Brief incomplet, LLM indisponible, contenu généré hors sujet, langue incorrecte |
| **Fallback** | Proposer un template pré-rempli à compléter manuellement |

### Prompt strategy

```python
COPYWRITER_SYSTEM_PROMPT = """
Tu es un copywriter marketing expert pour les entreprises africaines.

## Contexte marque
- Nom: {brand_name}
- Secteur: {industry}
- Ton: {tone} (ex: professionnel, amical, inspirant)
- Langue: {language}
- Pays cible: {target_country}

## Règles
- Écris en {language}, avec un style naturel adapté au contexte local
- Respecte la longueur max: {max_length} caractères
- Inclus un appel à l'action clair
- Propose 3-5 hashtags pertinents
- Si le canal est WhatsApp, privilégie un ton conversationnel et court
- Si le canal est Facebook, tu peux être plus détaillé
- Ne mentionne JAMAIS de prix sauf si explicitement demandé
- N'invente JAMAIS de faits sur l'entreprise

## Contenu à générer
Canal: {channel}
Objectif: {objective}
Brief: {brief}
"""
```

---

## Agent 3 : Image Generator (`ImageGenAgent`)

| Attribut | Valeur |
|----------|--------|
| **Rôle** | Générer des visuels de marque à partir de prompts ou de briefs marketing |
| **Inputs** | `prompt: str` (description de l'image), `brand_colors: list[str]`, `brand_logo_url: str` (optionnel), `style: str` (photo, illustration, flat design), `aspect_ratio: str`, `channel: str` |
| **Outputs** | `image_url: str`, `prompt_used: str`, `confidence_score: float`, `variants: list[str]` (2-3 options) |
| **Tools autorisés** | `generate_image` (Stable Diffusion/DALL-E), `get_brand_assets`, `resize_for_channel` |
| **Contraintes** | Jamais de contenu NSFW. Respecter charte graphique. Résolution adaptée au canal. Ne publie jamais directement. |
| **Niveau de confiance** | 0.0-1.0 basé sur: clarté du prompt, cohérence avec la marque (vérifié par un classifier) |
| **Règles d'escalade** | Score < 0.5 → retry avec prompt amélioré. Après 2 retries → proposer image template + escalade humaine. |
| **Mémoire** | Style de la marque, dernières images générées, feedbacks utilisateur |
| **Erreurs possibles** | Prompt ambigu, modèle indisponible, image incohérente, NSFW détecté |
| **Fallback** | Bibliothèque de templates avec overlay texte/logo automatique |

---

## Agent 4 : Publisher (`PublisherAgent`)

| Attribut | Valeur |
|----------|--------|
| **Rôle** | Publier du contenu validé sur les plateformes sociales connectées |
| **Inputs** | `post_id: str` (post interne validé), `channels: list[Channel]`, `schedule_at: datetime` (optionnel), `approval_status: str` |
| **Outputs** | `published_ids: dict[channel, external_id]`, `status: str`, `errors: list[str]` |
| **Tools autorisés** | `publish_to_facebook`, `publish_to_instagram`, `publish_to_whatsapp_status`, `schedule_post`, `check_post_status` |
| **Contraintes** | **NE PUBLIE JAMAIS sans approval_status=APPROVED.** Respecte les rate limits par plateforme. Vérifie les permissions du social_account. |
| **Niveau de confiance** | N/A (exécution binaire : succès ou échec) |
| **Règles d'escalade** | Erreur API → retry (3x avec backoff). Après 3 échecs → notification humaine + mise en queue manuelle. Token expiré → notification admin. |
| **Mémoire** | Historique de publication récent (éviter doublons), derniers rate limits atteints |
| **Erreurs possibles** | Token expiré, rate limit, post rejeté par plateforme, média invalide, permissions insuffisantes |
| **Fallback** | Sauvegarder le post comme "pending_manual" + notification à l'utilisateur |

---

## Agent 5 : Social Reply (`SocialReplyAgent`)

| Attribut | Valeur |
|----------|--------|
| **Rôle** | Répondre aux commentaires sur les posts publiés, de manière contextuelle et on-brand |
| **Inputs** | `comment: Comment` (texte, auteur, post parent, plateforme), `brand_context`, `post_context` (le post original), `reply_policy: ReplyPolicy` |
| **Outputs** | `reply_text: str`, `should_reply: bool`, `sentiment: str`, `confidence_score: float`, `action: str` (reply/ignore/escalate/hide) |
| **Tools autorisés** | `search_knowledge`, `get_post_context`, `reply_to_comment`, `get_brand_guidelines`, `detect_sentiment` |
| **Contraintes** | Ne répond PAS aux trolls (ignore). Ne répond PAS si confidence < seuil. Certains types de commentaires → escalade obligatoire (plaintes, urgences). Rate limit de réponses par heure. |
| **Niveau de confiance** | 0.0-1.0 basé sur: clarté du commentaire, match avec knowledge base, sentiment |
| **Règles d'escalade** | Sentiment négatif fort → escalade humaine. Question technique complexe → escalade support. Commentaire en langue non supportée → escalade. Score < 0.5 → ne pas répondre automatiquement. |
| **Mémoire** | Historique des réponses au même auteur, politique de la marque sur les sujets sensibles |
| **Erreurs possibles** | Commentaire mal interprété, réponse hors sujet, réponse à un troll, API reply non supportée sur la plateforme |
| **Fallback** | Réaction emoji (like) + notification humaine |

### Limites par plateforme

| Plateforme | Réponse aux commentaires | Auto-reply DM |
|-----------|------------------------|----------------|
| Facebook | ✅ Oui (API Pages) | ✅ Messenger API |
| Instagram | ✅ Oui (Graph API) | ⚠️ Limité (24h rule) |
| TikTok | ❌ Non (pas d'API write) | ❌ Non |
| WhatsApp | N/A (pas de commentaires) | ✅ Oui |

---

## Agent 6 : Support Client (`SupportAgent`)

| Attribut | Valeur |
|----------|--------|
| **Rôle** | Répondre aux questions des clients via WhatsApp, Messenger et inbox unifiée, en utilisant la knowledge base de l'entreprise |
| **Inputs** | `conversation: Conversation`, `message: Message`, `customer_context: CustomerContext`, `knowledge_base: KnowledgeBase` |
| **Outputs** | `response: str`, `confidence_score: float`, `sources: list[Document]`, `suggested_actions: list[str]`, `should_escalate: bool`, `escalation_reason: str` |
| **Tools autorisés** | `search_knowledge`, `get_customer_history`, `get_product_info`, `send_message`, `create_ticket`, `escalate_to_human`, `tag_conversation` |
| **Contraintes** | Jamais de fausses promesses. Jamais de prix inventés. Toujours citer les sources. Si incertain → "je vérifie avec mon équipe". Temps de réponse < 30s. |
| **Niveau de confiance** | 0.0-1.0 basé sur: similarité question/knowledge base, spécificité de la réponse, historique conversation |
| **Règles d'escalade** | Score < 0.5 → escalade. Client mécontent (sentiment négatif 2x consécutif) → escalade. Demande de remboursement → escalade. Sujet non couvert par KB → escalade. Client demande explicitement un humain → escalade immédiate. |
| **Mémoire** | Historique conversation client, préférences client, tickets précédents, contexte entreprise |
| **Erreurs possibles** | Réponse incorrecte, hallucination sur les prix/produits, boucle conversationnelle, mauvaise langue |
| **Fallback** | Message type "Un de nos conseillers va vous répondre sous peu" + notification équipe |

### Flux support typique

```
Client WhatsApp: "Bonjour, combien coûte le tissu wax n°5?"

SupportAgent:
  1. Détecte: question produit + demande prix
  2. search_knowledge("tissu wax n°5 prix") → match document catalogue
  3. Confiance: 0.85 (prix trouvé dans KB)
  4. Réponse: "Bonjour ! Le tissu wax n°5 est à 3500 FCFA le mètre.
     Nous avons aussi le n°7 dans des coloris similaires.
     Souhaitez-vous commander ?"
  5. Log: agent_run avec sources, score, temps de réponse

Client: "Et pour livraison à Bobo-Dioulasso ?"

SupportAgent:
  1. search_knowledge("livraison Bobo-Dioulasso") → match partiel
  2. Confiance: 0.45 (pas d'info livraison Bobo)
  3. Escalade: "Je vérifie les détails de livraison pour Bobo-Dioulasso
     avec notre équipe et vous reviens très vite !"
  4. create_ticket(type="delivery_inquiry", priority="medium")
  5. escalate_to_human(reason="info livraison non disponible en KB")
```

---

## Agent 7 : Knowledge Retriever (`KnowledgeRetrieverAgent`)

| Attribut | Valeur |
|----------|--------|
| **Rôle** | Rechercher et retourner les informations pertinentes de la knowledge base de l'entreprise (RAG) |
| **Inputs** | `query: str`, `tenant_id: str`, `filters: dict` (type de doc, date, catégorie), `top_k: int` |
| **Outputs** | `documents: list[RetrievedDoc]`, `relevance_scores: list[float]`, `answer_synthesis: str` (optionnel) |
| **Tools autorisés** | `vector_search`, `keyword_search`, `hybrid_search`, `get_document_metadata` |
| **Contraintes** | Résultats strictement limités au tenant. Pas d'invention. Score de pertinence pour chaque résultat. |
| **Niveau de confiance** | Basé sur le meilleur score de similarité des résultats |
| **Règles d'escalade** | Aucun résultat avec score > 0.3 → "Information non trouvée". Résultats contradictoires → retourner les deux avec un flag. |
| **Mémoire** | Requêtes fréquentes (cache), documents récemment ingérés |
| **Erreurs possibles** | Embeddings corrompus, document obsolète, résultats hors sujet |
| **Fallback** | Recherche full-text PostgreSQL si vector search échoue |

### Pipeline RAG

```
Query → Rewrite (optionnel) → Embed → Vector Search (pgvector)
                                         ↓
                              Keyword Search (PostgreSQL FTS)
                                         ↓
                                   Hybrid Merge + Rerank
                                         ↓
                                  Top-K Documents
                                         ↓
                            LLM Synthesis (avec sources)
                                         ↓
                                    Response
```

---

## Agent 8 : Moderator (`ModeratorAgent`)

| Attribut | Valeur |
|----------|--------|
| **Rôle** | Vérifier que tout contenu généré ou reçu respecte les politiques de la marque et les règles de modération |
| **Inputs** | `content: str`, `content_type: str` (post, reply, message), `brand_policies: list[str]`, `image_url: str` (optionnel) |
| **Outputs** | `approved: bool`, `score: float`, `flags: list[str]`, `reason: str`, `suggested_edit: str` (optionnel) |
| **Tools autorisés** | `classify_content`, `check_profanity`, `check_brand_compliance`, `check_image_safety` |
| **Contraintes** | Aucun contenu ne sort sans passer par le moderator. Zéro tolérance NSFW, haine, discrimination. |
| **Niveau de confiance** | 0.0-1.0 |
| **Règles d'escalade** | Score < 0.7 → bloque automatiquement + notifie admin. Contenu ambiguë → flag pour review humaine. |
| **Mémoire** | Mots/sujets bannis par tenant, historique de modération |
| **Erreurs possibles** | Faux positif (contenu OK flaggé), faux négatif (contenu problématique non détecté) |
| **Fallback** | En cas de doute, bloquer et escalader (fail-safe) |

---

## Agent 9 : Analytics (`AnalyticsAgent`)

| Attribut | Valeur |
|----------|--------|
| **Rôle** | Analyser les performances marketing et support, proposer des optimisations |
| **Inputs** | `tenant_id: str`, `date_range: DateRange`, `metrics: list[str]`, `question: str` (optionnel, en langage naturel) |
| **Outputs** | `report: AnalyticsReport`, `insights: list[str]`, `recommendations: list[str]`, `charts_data: dict` |
| **Tools autorisés** | `query_analytics`, `compare_periods`, `get_top_posts`, `get_response_metrics`, `get_sentiment_trends` |
| **Contraintes** | Données strictement limitées au tenant. Pas de prédictions sans disclaimer. |
| **Niveau de confiance** | N/A (données factuelles) |
| **Règles d'escalade** | Anomalie détectée (chute >30% engagement) → alerte proactive |
| **Mémoire** | Benchmarks historiques, KPIs objectifs du tenant |
| **Erreurs possibles** | Données insuffisantes, métriques non disponibles pour un canal |
| **Fallback** | Retourner les données brutes sans interprétation |

---

## Agent 10 : Escalation (`EscalationAgent`)

| Attribut | Valeur |
|----------|--------|
| **Rôle** | Gérer le handoff propre entre IA et humain. Préparer le contexte pour l'agent humain. |
| **Inputs** | `conversation: Conversation`, `reason: str`, `priority: Priority`, `agent_context: dict` (ce que l'IA a tenté) |
| **Outputs** | `escalation_id: str`, `summary: str`, `assigned_to: User` (optionnel), `notification_sent: bool` |
| **Tools autorisés** | `create_escalation`, `assign_agent`, `notify_team`, `summarize_conversation`, `update_conversation_status` |
| **Contraintes** | Doit toujours résumer le contexte pour l'humain. Ne doit jamais perdre le contexte de la conversation. Le client doit être informé de l'escalade. |
| **Niveau de confiance** | N/A (processus, pas de génération) |
| **Règles d'escalade** | N/A (c'est l'agent d'escalade lui-même) |
| **Mémoire** | Disponibilité des agents humains, historique d'escalade, temps de réponse moyen par agent |
| **Erreurs possibles** | Aucun agent humain disponible, notification non reçue |
| **Fallback** | Message auto "Notre équipe vous contactera dans les plus brefs délais" + email au manager |

---

## Architecture d'exécution des agents

```python
from abc import ABC, abstractmethod
from pydantic import BaseModel
from enum import Enum

class AgentResult(BaseModel):
    success: bool
    output: dict
    confidence_score: float | None = None
    should_escalate: bool = False
    escalation_reason: str | None = None
    agent_name: str
    execution_time_ms: int
    tokens_used: int | None = None
    sources: list[str] = []

class BaseAgent(ABC):
    """Base class for all OptimusAI agents."""

    name: str
    description: str
    allowed_tools: list[str]
    max_retries: int = 2
    confidence_threshold: float = 0.6

    @abstractmethod
    async def execute(self, context: dict) -> AgentResult:
        """Execute the agent's main task."""
        ...

    @abstractmethod
    async def validate_output(self, result: AgentResult) -> bool:
        """Validate the agent's output before returning."""
        ...

    async def run(self, context: dict) -> AgentResult:
        """Run with retry logic and logging."""
        for attempt in range(self.max_retries + 1):
            result = await self.execute(context)
            if await self.validate_output(result):
                return result
            if attempt < self.max_retries:
                context["retry_feedback"] = f"Attempt {attempt+1} failed validation"

        # All retries exhausted → escalate
        return AgentResult(
            success=False,
            output={"message": "Agent could not produce valid output"},
            should_escalate=True,
            escalation_reason=f"{self.name} failed after {self.max_retries + 1} attempts",
            agent_name=self.name,
            execution_time_ms=0,
        )
```
