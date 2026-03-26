# OptimusAI — Stratégie IA & Modèles

## Principes

1. **Open source first** — self-hosted quand c'est viable
2. **Fallback cloud** — pour la fiabilité quand le self-hosted est down
3. **Model routing** — le bon modèle pour la bonne tâche
4. **Coût-efficace** — modèle léger quand c'est suffisant, gros modèle quand c'est critique
5. **Multilingue** — français prioritaire, langues africaines en bonus

---

## Matrice des modèles par tâche

| Tâche | Modèle recommandé (self-hosted) | Fallback cloud | Justification |
|-------|--------------------------------|----------------|---------------|
| **Copywriting** (posts) | Mistral-7B-Instruct / Qwen2.5-7B | Claude Haiku / GPT-4o-mini | Bonne qualité FR, coût modéré |
| **Support client** | Mistral-7B-Instruct | Claude Haiku | Besoin de précision + contexte KB |
| **Réponses commentaires** | Mistral-7B-Instruct | Claude Haiku | Réponses courtes, rapides |
| **Classification** (routing) | Qwen2.5-1.5B / distilbert | — | Ultra rapide, léger |
| **Sentiment analysis** | camembert-base fine-tuné | — | Spécialisé FR, léger |
| **Modération** | Mistral-7B + classifier | Claude Haiku | Double vérification |
| **Embeddings** | BGE-M3 / multilingual-e5-large | — | Toujours self-hosted, pas d'API |
| **Image generation** | Stable Diffusion XL (ComfyUI) | — | Self-hosted obligatoire pour le coût |
| **Résumé** | Mistral-7B-Instruct | Claude Haiku | Résumés d'escalade |
| **Extraction entités** | Qwen2.5-1.5B / spaCy | — | Léger, rapide |
| **Reranking** | bge-reranker-v2-m3 | — | Améliore la qualité RAG |

---

## Architecture LLM Provider

```python
# app/integrations/llm.py

from abc import ABC, abstractmethod
from pydantic import BaseModel
from enum import Enum

class LLMProvider(str, Enum):
    OLLAMA = "ollama"       # Self-hosted via Ollama
    VLLM = "vllm"          # Self-hosted via vLLM
    ANTHROPIC = "anthropic" # Claude API
    OPENAI = "openai"       # OpenAI API

class LLMRequest(BaseModel):
    messages: list[dict]  # [{"role": "system", "content": "..."}, ...]
    model: str | None = None  # Override model
    temperature: float = 0.7
    max_tokens: int = 1024
    stop: list[str] | None = None

class LLMResponse(BaseModel):
    content: str
    model: str
    provider: str
    tokens_used: int
    latency_ms: int
    finish_reason: str

class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...

class LLMRouter:
    """Routes LLM requests to the appropriate provider based on task type."""

    def __init__(self, providers: dict[str, BaseLLMProvider], config: dict):
        self.providers = providers
        self.config = config
        # config: {
        #   "copywriting": {"primary": "ollama", "model": "mistral", "fallback": "anthropic"},
        #   "support": {"primary": "ollama", "model": "mistral", "fallback": "anthropic"},
        #   "classification": {"primary": "ollama", "model": "qwen2.5:1.5b"},
        #   ...
        # }

    async def generate(self, task_type: str, request: LLMRequest) -> LLMResponse:
        task_config = self.config[task_type]
        primary = task_config["primary"]
        request.model = request.model or task_config.get("model")

        try:
            provider = self.providers[primary]
            if await provider.health_check():
                return await provider.generate(request)
        except Exception:
            pass

        # Fallback
        if fallback := task_config.get("fallback"):
            provider = self.providers[fallback]
            return await provider.generate(request)

        raise LLMUnavailableError(f"No provider available for {task_type}")
```

---

## Embeddings

### Modèle recommandé : BGE-M3

- **Dimensions** : 1024 (ou 768 avec multilingual-e5-large)
- **Multilingue** : 100+ langues dont le français
- **Performance** : Top-tier pour le retrieval multilingue
- **Self-hosted** : Oui, via sentence-transformers
- **GPU requis** : ~2GB VRAM, utilisable aussi sur CPU (plus lent)

```python
# app/integrations/embeddings.py

from sentence_transformers import SentenceTransformer

class EmbeddingService:
    def __init__(self, model_name: str = "BAAI/bge-m3"):
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts."""
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=32,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        """Embed a single query (with instruction prefix for bge)."""
        instruction = "Represent this sentence for searching relevant passages: "
        return self.model.encode(
            instruction + query,
            normalize_embeddings=True,
        ).tolist()
```

---

## RAG Pipeline

```
                    ┌──────────────┐
                    │  User Query  │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ Query Rewrite │  (optionnel, LLM léger)
                    │ + Expansion  │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │                         │
       ┌──────▼───────┐         ┌──────▼───────┐
       │ Vector Search │         │ Keyword Search│
       │  (pgvector)   │         │ (PostgreSQL   │
       │  cosine sim   │         │  tsvector)    │
       └──────┬───────┘         └──────┬───────┘
              │                         │
              └────────────┬────────────┘
                           │
                    ┌──────▼───────┐
                    │ Hybrid Merge │  (RRF - Reciprocal Rank Fusion)
                    │ + Dedup      │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   Reranker   │  (bge-reranker-v2-m3)
                    │   Top-K      │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  LLM Answer  │  (avec sources citées)
                    │  Generation  │
                    └──────────────┘
```

### Implémentation RAG

```python
# app/services/knowledge_service.py

class KnowledgeService:
    async def search(
        self,
        query: str,
        tenant_id: UUID,
        brand_id: UUID,
        top_k: int = 5,
        min_score: float = 0.3,
    ) -> list[SearchResult]:
        # 1. Embed query
        query_embedding = self.embedding_service.embed_query(query)

        # 2. Vector search (pgvector)
        vector_results = await self.chunk_repo.vector_search(
            embedding=query_embedding,
            tenant_id=tenant_id,
            brand_id=brand_id,
            limit=top_k * 2,
        )

        # 3. Keyword search (PostgreSQL FTS)
        keyword_results = await self.chunk_repo.keyword_search(
            query=query,
            tenant_id=tenant_id,
            brand_id=brand_id,
            limit=top_k * 2,
        )

        # 4. Hybrid merge (Reciprocal Rank Fusion)
        merged = self._reciprocal_rank_fusion(vector_results, keyword_results)

        # 5. Filter by min_score
        filtered = [r for r in merged if r.score >= min_score]

        # 6. Return top_k
        return filtered[:top_k]

    @staticmethod
    def _reciprocal_rank_fusion(
        *result_lists: list, k: int = 60
    ) -> list:
        """RRF merge: score = sum(1 / (k + rank_i)) for each list."""
        scores = {}
        for results in result_lists:
            for rank, result in enumerate(results):
                doc_id = result.chunk_id
                if doc_id not in scores:
                    scores[doc_id] = {"result": result, "score": 0}
                scores[doc_id]["score"] += 1.0 / (k + rank + 1)

        sorted_results = sorted(scores.values(), key=lambda x: x["score"], reverse=True)
        for item in sorted_results:
            item["result"].score = item["score"]
        return [item["result"] for item in sorted_results]
```

---

## Image Generation

### Stack recommandée : ComfyUI + Stable Diffusion XL

**Pourquoi ComfyUI :**
- API HTTP (pas besoin d'UI)
- Workflows en JSON (versionnable, reproductible)
- Supporte tous les modèles SD
- Extensible (ControlNet, LoRA, IP-Adapter)
- Self-hosted

**Workflow type pour marketing :**

```
Prompt → SDXL Base → SDXL Refiner → Upscale → Output
         │
         ├── Positive: "{brand_name} product photo, {style}, professional"
         ├── Negative: "text, watermark, blurry, nsfw, deformed"
         └── Seed: random ou fixé pour reproductibilité
```

### GPU Requirements

| Modèle | VRAM min | Génération |
|--------|----------|------------|
| SDXL | 8 GB | ~15-30s/image |
| SD 1.5 | 4 GB | ~5-10s/image |
| FLUX.1-dev | 12 GB | ~20-40s/image |

**Recommandation MVP** : SDXL sur un GPU cloud A10 (~$0.50/h). Pas de GPU dédié au début.

---

## Prompt Management

```python
# app/prompts/copywriting.py

from jinja2 import Template

COPYWRITING_SYSTEM = Template("""
Tu es un copywriter marketing expert pour les entreprises africaines.

## Contexte marque
- Nom: {{ brand_name }}
- Secteur: {{ industry }}
- Ton: {{ tone }}
- Langue: {{ language }}
- Pays: {{ country }}

## Règles
- Écris en {{ language }} avec un style naturel adapté au contexte local
- Longueur max: {{ max_length }} caractères
- Inclus un appel à l'action clair
- Propose 3-5 hashtags pertinents en fin de post
- Si WhatsApp: ton conversationnel, court, avec emojis
- Si Facebook: plus détaillé, structure claire
- Ne mentionne JAMAIS de prix sauf si dans le brief
- N'invente AUCUN fait sur l'entreprise
- Si des documents de référence sont fournis, base-toi dessus

{% if reference_docs %}
## Documents de référence
{% for doc in reference_docs %}
---
{{ doc.content }}
---
{% endfor %}
{% endif %}

{% if past_posts %}
## Exemples de posts précédents (pour cohérence de style)
{% for post in past_posts[:3] %}
- {{ post }}
{% endfor %}
{% endif %}
""")

COPYWRITING_USER = Template("""
Canal: {{ channel }}
Objectif: {{ objective }}
Brief: {{ brief }}

{% if additional_instructions %}
Instructions supplémentaires: {{ additional_instructions }}
{% endif %}

Génère le post maintenant. Retourne en JSON:
{
  "content": "...",
  "hashtags": ["...", "..."],
  "media_suggestion": "description d'une image qui accompagnerait bien ce post"
}
""")
```

---

## Modération

### Pipeline de modération

```
Contenu généré
    │
    ├─ 1. Classifier rapide (toxicité, NSFW)
    │     │ → Modèle: multilingual toxicity classifier
    │     │ → Si score > 0.8 → BLOQUÉ immédiatement
    │
    ├─ 2. Brand compliance check
    │     │ → Mots interdits (brand.guidelines.banned_words)
    │     │ → Sujets interdits
    │     │ → Vérification de tone
    │
    ├─ 3. LLM modération (si étapes 1-2 passent)
    │     │ → Prompt: "Ce contenu est-il approprié pour {brand}?"
    │     │ → Score 0-1
    │
    └─ Résultat final
        ├─ approved (score > 0.7, aucun flag)
        ├─ flagged (score 0.4-0.7, review humaine suggérée)
        └─ blocked (score < 0.4, ou flag critique)
```

---

## Model Routing Configuration

```yaml
# config/models.yaml

models:
  copywriting:
    primary:
      provider: ollama
      model: mistral:7b-instruct-v0.3
      temperature: 0.8
      max_tokens: 1500
    fallback:
      provider: anthropic
      model: claude-haiku-4-5-20251001
      temperature: 0.8
      max_tokens: 1500

  support:
    primary:
      provider: ollama
      model: mistral:7b-instruct-v0.3
      temperature: 0.3  # Plus conservateur pour le support
      max_tokens: 500
    fallback:
      provider: anthropic
      model: claude-haiku-4-5-20251001

  classification:
    primary:
      provider: ollama
      model: qwen2.5:1.5b
      temperature: 0.0  # Déterministe
      max_tokens: 50

  sentiment:
    primary:
      provider: local
      model: camembert-base-sentiment

  embeddings:
    primary:
      provider: local
      model: BAAI/bge-m3

  reranking:
    primary:
      provider: local
      model: BAAI/bge-reranker-v2-m3

  image:
    primary:
      provider: comfyui
      model: stabilityai/stable-diffusion-xl-base-1.0
      steps: 30
      cfg_scale: 7.5

  moderation:
    primary:
      provider: local
      model: unitary/toxic-bert
    secondary:
      provider: ollama
      model: mistral:7b-instruct-v0.3
```

---

## Coûts estimés (self-hosted)

### Infrastructure GPU (production minimale)

| Composant | Spec | Coût estimé/mois |
|-----------|------|-------------------|
| Serveur LLM (Mistral 7B) | 1x A10 (24GB) | ~$150-300 |
| Serveur Image (SDXL) | 1x A10 (24GB) | ~$150-300 (partagé ou on-demand) |
| Embeddings + Reranker | CPU ou T4 | ~$50-100 |

**Total GPU** : ~$350-700/mois en production

### Avec fallback cloud uniquement (pas de GPU)

| Service | Coût estimé/1000 tenants |
|---------|--------------------------|
| Claude Haiku API | ~$100-300/mois |
| Pas d'image gen self-hosted | Limitation ou API tiers |

**Recommandation MVP** : Commencer 100% cloud API (Claude Haiku), migrer vers self-hosted à 100+ tenants payants.
