# OptimusAI — Architecture Globale

## 1. Vision Produit

### Proposition de valeur
OptimusAI est le **cerveau digital des entreprises africaines**. Une plateforme SaaS qui unifie marketing, support client et gestion communautaire via des agents IA spécialisés, avec WhatsApp et Facebook comme canaux prioritaires.

**En une phrase** : "Votre équipe marketing + support client IA, disponible 24h/24, qui parle français et comprend votre business."

### Utilisateurs cibles
| Segment | Exemple | Besoin principal |
|---------|---------|-----------------|
| PME africaines | Boutique textile Ouaga | Présence sociale + répondre aux clients WhatsApp |
| Agences marketing | Agence digitale Abidjan | Gérer 20+ clients depuis un seul dashboard |
| E-commerce | Marketplace BF | Support client IA + gestion commandes |
| Institutions | ONG, banque | Communication multicanale + FAQ automatisée |
| Franchises | Chaîne de restaurants | Contenu local par point de vente |

### Cas d'usage prioritaires (MVP)
1. **Génération de posts** — L'entreprise décrit son produit, l'agent crée le post Facebook/Instagram
2. **Support client WhatsApp** — Les clients écrivent sur WhatsApp, l'IA répond avec le contexte de l'entreprise
3. **Réponse aux messages Facebook** — Messenger/DM automatisé avec escalade humaine
4. **Knowledge base** — L'entreprise uploade ses docs/FAQ, l'IA s'en sert pour répondre
5. **Publication planifiée** — Calendrier éditorial avec validation humaine

### Opportunités Afrique
- **WhatsApp = canal #1** : 90%+ de pénétration dans le business en Afrique de l'Ouest
- **Facebook dominant** : Principal réseau social, loin devant Instagram/TikTok
- **Peu de solutions locales** : Les outils existants (Hootsuite, Buffer) ne sont pas adaptés au contexte
- **Coût main d'œuvre CM** : Les entreprises paient 150-300k FCFA/mois pour un CM humain
- **Français** : Peu d'outils IA maîtrisent le français africain et les spécificités locales
- **Mobile-first** : Tout doit fonctionner sur mobile, connexion limitée

### Risques techniques majeurs
| Risque | Impact | Mitigation |
|--------|--------|------------|
| Limites API Facebook/Meta | Ne peut pas tout automatiser | Mode hybride humain+IA |
| WhatsApp Business API payante | Coût par message | Templates optimisés, session messaging |
| Qualité LLM en français africain | Réponses inadaptées | Fine-tuning, prompts contextuels, review humain |
| Connexion internet instable | Timeout, pertes de données | Queue persistante, retry, mode offline partiel |
| Coût GPU pour self-hosted | Peut être prohibitif au début | Commencer cloud API, migrer progressivement |

---

## 2. Architecture Globale

### Décision : Monolithe Modulaire

**Choix : Monolithe modulaire FastAPI**, pas de microservices.

**Pourquoi :**
- Équipe petite (1-3 devs au début)
- Un seul déploiement à gérer
- Pas de complexité réseau inter-services
- Refactoring facile en microservices plus tard si nécessaire
- Les modules sont isolés par convention, pas par infrastructure

**Quand passer en microservices :**
- Quand un module a des besoins de scaling radicalement différents (ex: workers IA)
- Quand l'équipe dépasse 5-8 devs travaillant en parallèle

### Diagramme logique

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENTS                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
│  │ Web App  │  │ Mobile   │  │ WhatsApp │  │ FB Webhooks  │    │
│  │ (React)  │  │ (PWA)    │  │ Webhooks │  │              │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘    │
└───────┼──────────────┼─────────────┼───────────────┼────────────┘
        │              │             │               │
        ▼              ▼             ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API GATEWAY / LOAD BALANCER                  │
│                        (Traefik / Nginx)                         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASTAPI APPLICATION                            │
│                                                                   │
│  ┌─────────┐ ┌──────────┐ ┌───────────┐ ┌──────────────────┐   │
│  │  Auth   │ │  API     │ │ Webhooks  │ │   Admin API      │   │
│  │  Module │ │  Routes  │ │ Handlers  │ │                  │   │
│  └────┬────┘ └────┬─────┘ └─────┬─────┘ └────────┬─────────┘   │
│       │           │             │                 │              │
│       ▼           ▼             ▼                 ▼              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   SERVICE LAYER                           │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │   │
│  │  │ Content  │ │ Social   │ │ Support  │ │ Knowledge  │  │   │
│  │  │ Service  │ │ Service  │ │ Service  │ │ Service    │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │   │
│  │  │ Campaign │ │ Analytics│ │ Billing  │ │ Approval   │  │   │
│  │  │ Service  │ │ Service  │ │ Service  │ │ Service    │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   AGENT LAYER                             │   │
│  │  ┌─────────────┐  ┌──────────┐  ┌──────────────────┐    │   │
│  │  │Orchestrator │  │ Content  │  │ Support Agent    │    │   │
│  │  │   Agent     │──│ Agent    │  │                  │    │   │
│  │  └─────────────┘  └──────────┘  └──────────────────┘    │   │
│  │  ┌─────────────┐  ┌──────────┐  ┌──────────────────┐    │   │
│  │  │  Image      │  │ Reply    │  │ Moderation      │    │   │
│  │  │  Agent      │  │ Agent    │  │ Agent           │    │   │
│  │  └─────────────┘  └──────────┘  └──────────────────┘    │   │
│  └──────────────────────────────────────────────────────────┘   │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                CONNECTOR LAYER                            │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │   │
│  │  │ Facebook │ │Instagram │ │ WhatsApp │ │  TikTok    │  │   │
│  │  │Connector │ │Connector │ │Connector │ │ Connector  │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                 DATA LAYER                                │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │   │
│  │  │Repository│ │ Models   │ │ Schemas  │ │ Migrations │  │   │
│  │  │ Pattern  │ │SQLAlchemy│ │ Pydantic │ │  Alembic   │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
        │              │              │              │
        ▼              ▼              ▼              ▼
┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────────┐
│ PostgreSQL │ │   Redis    │ │ Qdrant/    │ │ S3/MinIO       │
│ (primary)  │ │ (cache +   │ │ pgvector   │ │ (files/media)  │
│            │ │  queue)    │ │ (vectors)  │ │                │
└────────────┘ └────────────┘ └────────────┘ └────────────────┘
                    │
                    ▼
            ┌────────────────┐
            │  ARQ Workers   │
            │  (background)  │
            └────────────────┘
```

### Flux synchrone vs asynchrone

| Opération | Mode | Raison |
|-----------|------|--------|
| Auth, CRUD simple | Synchrone | < 100ms, réponse immédiate |
| Génération de contenu IA | Asynchrone (queue) | 5-30s, coûteux en compute |
| Génération d'image | Asynchrone (queue) | 10-60s, très coûteux |
| Publication sociale | Asynchrone (queue) | Dépend d'API externe, retry nécessaire |
| Ingestion documents | Asynchrone (queue) | Parsing + chunking + embedding long |
| Webhooks entrants | Synchrone (réponse 200) + queue | Meta exige réponse < 5s |
| Analytics aggregation | Asynchrone (cron) | Batch processing |
| Envoi WhatsApp | Asynchrone (queue) | Rate limits, retry |

---

## 3. Stack Technique

### Stack principale

| Composant | Technologie | Justification |
|-----------|-------------|---------------|
| **Backend** | FastAPI + Python 3.12 | Async natif, typage, écosystème IA Python |
| **ORM** | SQLAlchemy 2.0 (async) | Mature, type-safe, migration Alembic |
| **Validation** | Pydantic v2 | Intégré FastAPI, performant |
| **DB principale** | PostgreSQL 16 | JSONB, full-text search, pgvector |
| **Vector store** | pgvector (MVP) → Qdrant (scale) | Commence simple, scale quand nécessaire |
| **Cache/Queue** | Redis + ARQ | Léger, Python natif, async |
| **Object storage** | MinIO (self) / S3 (cloud) | Compatible S3, stockage média |
| **LLM inference** | vLLM / Ollama (self) + API fallback | Self-hosted prioritaire, fallback cloud |
| **Embeddings** | sentence-transformers | Open source, multilingue |
| **Image gen** | Stable Diffusion (ComfyUI) | Open source, self-hostable |
| **Auth** | JWT + OAuth2 (built-in FastAPI) | Standard, pas de dépendance externe |
| **Migrations** | Alembic | Standard SQLAlchemy |
| **Tests** | pytest + httpx | Async testing natif |
| **Observabilité** | structlog + Prometheus + Grafana | Open source, standard |
| **Deploy** | Docker Compose → K8s | Simple au début, scalable |
| **Frontend** | React/Next.js (séparé) | Non dans le scope backend, mais prévu |

### Dépendances Python clés

```
fastapi[standard]>=0.115
sqlalchemy[asyncio]>=2.0
alembic>=1.14
pydantic>=2.10
pydantic-settings>=2.6
asyncpg>=0.30           # PostgreSQL async driver
redis>=5.2
arq>=0.26               # Async Redis Queue
httpx>=0.28             # Async HTTP client
python-jose[cryptography]>=3.3  # JWT
passlib[bcrypt]>=1.7    # Password hashing
python-multipart>=0.0.18
boto3>=1.35             # S3/MinIO
pillow>=11.0            # Image processing
langchain-core>=0.3     # Agent framework (core only)
sentence-transformers>=3.3
pgvector>=0.3
structlog>=24.4
prometheus-fastapi-instrumentator>=7.0
pytest>=8.3
pytest-asyncio>=0.24
httpx>=0.28             # Test client
factory-boy>=3.3        # Test factories
```

---

## 4. Découpage des Modules

```
app/
├── __init__.py
├── main.py                    # FastAPI app factory
├── config.py                  # Settings (pydantic-settings)
│
├── core/                      # Cross-cutting concerns
│   ├── __init__.py
│   ├── auth.py                # JWT, OAuth2, current_user
│   ├── permissions.py         # RBAC engine
│   ├── database.py            # Engine, session factory
│   ├── redis.py               # Redis connection
│   ├── storage.py             # S3/MinIO abstraction
│   ├── events.py              # Internal event bus
│   ├── exceptions.py          # Custom exceptions
│   ├── middleware.py          # Tenant context, logging, rate limit
│   ├── security.py            # Hashing, encryption, secrets
│   └── pagination.py          # Cursor/offset pagination
│
├── models/                    # SQLAlchemy models
│   ├── __init__.py
│   ├── base.py                # Base model with tenant_id, timestamps
│   ├── user.py
│   ├── tenant.py
│   ├── brand.py
│   ├── social_account.py
│   ├── channel.py
│   ├── post.py
│   ├── conversation.py
│   ├── message.py
│   ├── knowledge.py
│   ├── campaign.py
│   ├── approval.py
│   ├── billing.py
│   ├── analytics.py
│   ├── agent_run.py
│   └── audit.py
│
├── schemas/                   # Pydantic schemas (request/response)
│   ├── __init__.py
│   ├── auth.py
│   ├── user.py
│   ├── tenant.py
│   ├── brand.py
│   ├── social.py
│   ├── post.py
│   ├── conversation.py
│   ├── message.py
│   ├── knowledge.py
│   ├── campaign.py
│   ├── approval.py
│   ├── billing.py
│   └── analytics.py
│
├── repositories/              # Data access layer
│   ├── __init__.py
│   ├── base.py                # Generic CRUD repository
│   ├── user.py
│   ├── tenant.py
│   ├── post.py
│   ├── conversation.py
│   ├── knowledge.py
│   └── ...
│
├── services/                  # Business logic
│   ├── __init__.py
│   ├── auth_service.py
│   ├── tenant_service.py
│   ├── brand_service.py
│   ├── content_service.py     # Post creation, editing
│   ├── publishing_service.py  # Publication logic
│   ├── social_service.py      # Social account management
│   ├── conversation_service.py
│   ├── support_service.py     # Customer support logic
│   ├── knowledge_service.py   # Document ingestion, RAG
│   ├── campaign_service.py
│   ├── approval_service.py
│   ├── analytics_service.py
│   ├── billing_service.py
│   └── escalation_service.py
│
├── api/                       # FastAPI routes
│   ├── __init__.py
│   ├── deps.py                # Dependency injection
│   └── v1/
│       ├── __init__.py
│       ├── router.py          # Main v1 router
│       ├── auth.py
│       ├── tenants.py
│       ├── brands.py
│       ├── social_accounts.py
│       ├── posts.py
│       ├── campaigns.py
│       ├── conversations.py
│       ├── messages.py
│       ├── knowledge.py
│       ├── approvals.py
│       ├── analytics.py
│       ├── billing.py
│       ├── webhooks.py        # Social platform webhooks
│       ├── admin.py
│       └── audit.py
│
├── agents/                    # AI agents
│   ├── __init__.py
│   ├── base.py                # Base agent class
│   ├── orchestrator.py        # Routes to correct agent
│   ├── copywriter.py          # Content generation
│   ├── image_gen.py           # Image generation
│   ├── publisher.py           # Publication agent
│   ├── social_reply.py        # Comment/reply agent
│   ├── support.py             # Customer support agent
│   ├── knowledge_retriever.py # RAG agent
│   ├── moderator.py           # Content moderation
│   ├── analytics_agent.py     # Analytics insights
│   ├── escalation.py          # Human handoff
│   └── tools/                 # Agent tools
│       ├── __init__.py
│       ├── search_knowledge.py
│       ├── publish_post.py
│       ├── send_message.py
│       ├── get_analytics.py
│       └── escalate.py
│
├── connectors/                # Social platform adapters
│   ├── __init__.py
│   ├── base.py                # Abstract connector interface
│   ├── facebook.py
│   ├── instagram.py
│   ├── whatsapp.py
│   ├── messenger.py
│   ├── tiktok.py
│   └── normalizer.py          # Normalize events across platforms
│
├── workers/                   # Background tasks
│   ├── __init__.py
│   ├── settings.py            # ARQ worker settings
│   ├── content_generation.py
│   ├── image_generation.py
│   ├── publishing.py
│   ├── document_ingestion.py
│   ├── embedding.py
│   ├── analytics_aggregation.py
│   ├── webhook_processing.py
│   └── scheduled_posts.py
│
├── prompts/                   # Prompt templates
│   ├── __init__.py
│   ├── copywriting.py
│   ├── support.py
│   ├── reply.py
│   ├── moderation.py
│   ├── summary.py
│   └── templates/
│       ├── post_facebook.jinja2
│       ├── post_instagram.jinja2
│       ├── reply_comment.jinja2
│       ├── support_response.jinja2
│       └── escalation_summary.jinja2
│
├── integrations/              # External service clients
│   ├── __init__.py
│   ├── llm.py                 # LLM provider abstraction
│   ├── embeddings.py          # Embedding provider
│   ├── image_gen.py           # Image generation provider
│   ├── sms.py                 # SMS provider (fallback)
│   └── payment.py             # Payment provider
│
└── alembic/                   # Database migrations
    ├── env.py
    └── versions/
```

```
tests/
├── conftest.py                # Fixtures, test DB, test client
├── factories/                 # Factory Boy factories
│   ├── __init__.py
│   ├── user.py
│   ├── tenant.py
│   └── ...
├── unit/
│   ├── test_services/
│   ├── test_agents/
│   └── test_connectors/
├── integration/
│   ├── test_api/
│   ├── test_repositories/
│   └── test_workers/
└── e2e/
    └── test_flows/
```

```
scripts/
├── seed_db.py
├── create_superadmin.py
├── run_worker.py
└── migrate.py
```

```
deployments/
├── docker-compose.yml
├── docker-compose.prod.yml
├── Dockerfile
├── Dockerfile.worker
├── nginx.conf
└── k8s/
    ├── deployment.yaml
    ├── service.yaml
    └── ingress.yaml
```
