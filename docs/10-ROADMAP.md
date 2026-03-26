# OptimusAI — Roadmap & Plan d'Implémentation

---

## Phase 1 : MVP (8-10 semaines)

### Objectif
Un produit fonctionnel qui permet à une entreprise de connecter Facebook, générer des posts IA, les publier, et recevoir/répondre aux messages WhatsApp avec un bot IA.

### Fonctionnalités

| Feature | Détail |
|---------|--------|
| ✅ Auth + multi-tenant | Register, login, JWT, tenant isolation |
| ✅ Gestion marques | CRUD Brand, guidelines, tone |
| ✅ Connexion Facebook | OAuth2, Pages, publish, webhooks |
| ✅ Connexion WhatsApp | Cloud API, webhooks, send/receive |
| ✅ Génération de posts IA | Copywriter agent, prompts, variations |
| ✅ Publication Facebook | Texte + image, scheduling |
| ✅ Inbox unifiée (basic) | Conversations WhatsApp + Messenger |
| ✅ Support client IA | RAG basique, réponses auto WhatsApp |
| ✅ Knowledge base | Upload docs, chunking, embedding, search |
| ✅ Validation humaine | Approval flow pour les posts |
| ✅ Escalade humaine | Handoff IA → humain pour le support |
| ✅ Dashboard basic | KPIs, posts récents, conversations |
| ✅ Billing basic | Plans, quotas, check usage |

### Ce qu'on reporte
- Génération d'images IA (templates avec texte overlay en attendant)
- Instagram publication (read-only dans un premier temps)
- TikTok
- Analytics avancé
- Workflows/automation
- White-label
- App mobile native

### Risques MVP
| Risque | Probabilité | Impact | Mitigation |
|--------|------------|--------|------------|
| Facebook App Review lent | Haute | Bloquant | Commencer la demande dès J1 |
| WhatsApp Business verification | Haute | Bloquant | Préparer les docs entreprise tôt |
| Qualité LLM en français | Moyenne | Modéré | Prompts itératifs + fallback Claude API |
| Complexité OAuth Facebook | Moyenne | Modéré | Bien documenter le flow, tester tôt |

---

## Phase 2 : V1 (semaines 11-18)

### Fonctionnalités ajoutées

| Feature | Détail |
|---------|--------|
| ✅ Instagram publish | Graph API, images, Reels |
| ✅ Réponse aux commentaires | Facebook + Instagram, auto-reply |
| ✅ Génération d'images IA | SDXL via ComfyUI, brand-aware |
| ✅ Campagnes | Regroupement de posts, objectifs, dates |
| ✅ Analytics v1 | Engagement, reach, response time, trends |
| ✅ Templates | Bibliothèque de prompts et formats pré-faits |
| ✅ Billing complet | Paiement Mobile Money, factures |
| ✅ Notifications | Email + push pour approvals, escalations |
| ✅ Multi-utilisateurs | Invitation, rôles, permissions complètes |
| ✅ Audit trail | Log de toutes les actions |

### Ce qu'on reporte
- TikTok
- Workflows automation
- Voice notes
- Vidéo generation
- White-label
- API publique

---

## Phase 3 : V2 (semaines 19-30)

### Fonctionnalités ajoutées

| Feature | Détail |
|---------|--------|
| ✅ TikTok | Publication vidéo, lecture commentaires |
| ✅ Workflows automation | Règles if/then pour auto-réponses, séquences |
| ✅ Analytics agent | Insights IA, recommandations |
| ✅ A/B testing | Variantes de posts, mesure performance |
| ✅ Sentiment tracking | Dashboard sentiment par canal, par période |
| ✅ API publique | REST API documentée pour intégrations tierces |
| ✅ White-label basic | Custom domain, logo |
| ✅ Multi-langue | Anglais en plus du français |
| ✅ Modèle agence | Dashboard multi-tenant pour les agences |
| ✅ Reporting | Export PDF/CSV, rapports périodiques |

---

## Phase 4 : V3 (semaines 31-52)

### Fonctionnalités ajoutées

| Feature | Détail |
|---------|--------|
| ✅ Voice notes | Transcription + réponse vocale WhatsApp |
| ✅ Vidéo generation | Clips courts pour Reels/TikTok |
| ✅ LinkedIn | Connexion + publication |
| ✅ CRM intégration | Sync contacts, historique client |
| ✅ E-commerce intégration | WooCommerce, Shopify connectors |
| ✅ Chatbot builder | No-code flow builder pour le support |
| ✅ Advanced AI | Fine-tuning sur données client, model personnalisé |
| ✅ White-label complet | Zéro mention OptimusAI |
| ✅ Mobile app | React Native / PWA avancée |
| ✅ Marketplace | Templates, workflows partagés entre tenants |

---

## Plan d'Implémentation Détaillé (MVP)

### Semaine 1-2 : Fondation

```
Jour 1-3 : Setup projet
├── Initialiser repo Git
├── Structure FastAPI (app/, core/, models/, etc.)
├── Docker Compose (PostgreSQL, Redis, MinIO)
├── Configuration Pydantic Settings
├── Alembic setup
├── CI/CD basique (GitHub Actions: lint + tests)
└── Makefile / scripts de dev

Jour 4-7 : Auth + Multi-tenant
├── Modèles User, Tenant, Permission
├── Register / Login endpoints
├── JWT (access + refresh tokens)
├── Middleware tenant context
├── Password hashing (bcrypt)
├── Tests auth
└── Seed superadmin script

Jour 8-10 : Base repository + service pattern
├── BaseRepository (CRUD générique avec tenant isolation)
├── Service layer pattern
├── Error handling + custom exceptions
├── Pagination (cursor-based)
├── Logging structuré (structlog)
└── Tests repository
```

### Semaine 3-4 : Entités métier + Connecteurs

```
Jour 11-14 : Brand + Social Accounts
├── Modèles Brand, SocialAccount, Channel
├── CRUD Brands
├── OAuth2 flow Facebook
│   ├── Authorize endpoint → redirect
│   ├── Callback endpoint → token exchange
│   ├── Page listing + selection
│   └── Webhook registration
├── Facebook connector (publish, read)
├── Token encryption (Fernet)
└── Tests

Jour 15-20 : WhatsApp
├── WhatsApp Cloud API connector
│   ├── Send text message
│   ├── Send template message
│   ├── Receive message (webhook)
│   ├── Media download
│   └── Delivery status
├── Webhook handler (Facebook + WhatsApp)
├── Event normalizer
├── Webhook signature verification
└── Tests avec mocks
```

### Semaine 5-6 : Knowledge Base + RAG

```
Jour 21-25 : Document ingestion
├── Modèles KnowledgeDoc, Chunk
├── Upload endpoint (S3/MinIO)
├── Document parsing (PDF, DOCX, TXT, CSV)
├── Chunking (RecursiveCharacterTextSplitter)
├── pgvector setup
├── Embedding service (sentence-transformers)
├── Ingestion worker (ARQ)
└── Tests

Jour 26-30 : RAG pipeline
├── Vector search (pgvector cosine)
├── Keyword search (PostgreSQL tsvector)
├── Hybrid merge (RRF)
├── Knowledge search endpoint
├── LLM integration (Ollama/Claude)
├── LLM Router (primary + fallback)
└── Tests RAG quality
```

### Semaine 7-8 : Agents IA

```
Jour 31-35 : Agent framework
├── BaseAgent class
├── AgentRun model + logging
├── Orchestrator agent
├── Copywriter agent
│   ├── Prompts copywriting
│   ├── Brand context injection
│   ├── JSON output parsing
│   └── Confidence scoring
├── Content generation endpoint
├── Content generation worker
└── Tests agents

Jour 36-40 : Support + Inbox
├── Modèles Conversation, Message, Escalation
├── Support agent
│   ├── Context retrieval (conversation history + KB)
│   ├── Response generation
│   ├── Confidence scoring
│   └── Escalation logic
├── Moderator agent (basic)
├── Escalation agent
├── Inbox endpoints (list, detail, reply)
├── Webhook → Support pipeline
└── Tests support flow
```

### Semaine 9-10 : Publication + Polish

```
Jour 41-45 : Publication pipeline
├── Post model + CRUD
├── PostAsset model
├── Approval flow
│   ├── Submit for review
│   ├── Approve / reject
│   └── Auto-approve si config
├── Publisher agent
│   ├── Publish to Facebook
│   ├── Scheduling (scheduled_at)
│   ├── Retry logic
│   └── Status tracking
├── Scheduled posts worker (cron)
└── Tests publication

Jour 46-50 : Billing + Dashboard + Polish
├── BillingPlan, Subscription, UsageRecord
├── Quota checking middleware
├── Plans endpoint
├── Analytics basic (events + KPIs)
├── Dashboard endpoint (overview)
├── Error handling polish
├── API documentation (auto-generated OpenAPI)
├── Security review
├── Performance testing
├── Deploy staging
└── Smoke tests E2E
```

---

## Priorités techniques transversales

| Priorité | Quand | Détail |
|----------|-------|--------|
| **Tests** | Continu | Min 70% coverage. Chaque feature avec tests. |
| **CI/CD** | Semaine 1 | Lint (ruff), tests (pytest), build Docker |
| **Logging** | Semaine 1 | structlog, JSON, request_id correlation |
| **Monitoring** | Semaine 9 | Prometheus metrics + health endpoint |
| **Security** | Semaine 9 | Revue OWASP, injection, XSS, RBAC |
| **Documentation** | Continu | OpenAPI auto + CLAUDE.md pour le projet |
| **Facebook App Review** | Semaine 1 | Soumettre la demande ASAP |
| **WhatsApp Business** | Semaine 1 | Démarrer la vérification business |

---

## Conventions de code

```python
# Nommage
snake_case           # Variables, fonctions, modules
PascalCase           # Classes, modèles
UPPER_SNAKE_CASE     # Constantes
_private_method      # Méthodes privées

# Structure module
from app.services.content_service import ContentService  # Import absolu
from app.models.post import Post, PostStatus             # Import spécifique

# Type hints partout
async def create_post(
    brand_id: UUID,
    content: str,
    channels: list[str],
    *,  # keyword-only après
    campaign_id: UUID | None = None,
    scheduled_at: datetime | None = None,
) -> Post:
    ...

# Pydantic pour validation
class PostCreate(BaseModel):
    model_config = ConfigDict(strict=True)

    brand_id: UUID
    content_text: str = Field(min_length=1, max_length=5000)
    channels: list[str] = Field(min_length=1)

# Repository pattern
class PostRepository(BaseRepository[Post]):
    async def list_by_campaign(self, campaign_id: UUID) -> list[Post]:
        ...

# Service pattern
class ContentService:
    def __init__(self, post_repo: PostRepository, agent: CopywriterAgent):
        self.post_repo = post_repo
        self.agent = agent

    async def generate_post(self, request: PostGenerateRequest) -> Post:
        ...

# Gestion d'erreurs
class OptimusError(Exception):
    """Base exception."""
    status_code: int = 500
    error_code: str = "internal_error"

class NotFoundError(OptimusError):
    status_code = 404
    error_code = "not_found"

class QuotaExceededError(OptimusError):
    status_code = 429
    error_code = "quota_exceeded"

class PermissionDeniedError(OptimusError):
    status_code = 403
    error_code = "permission_denied"

# Logs structurés
import structlog
logger = structlog.get_logger()

logger.info(
    "post_published",
    post_id=str(post.id),
    tenant_id=str(tenant_id),
    channel="facebook",
    external_id=result.external_id,
)
```
