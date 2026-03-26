# OptimusAI — API Design

## Conventions

- Base URL : `/api/v1/`
- Auth : Bearer JWT token dans le header `Authorization`
- Pagination : cursor-based pour les listes (`?cursor=xxx&limit=20`)
- Filtering : query params (`?status=published&platform=facebook`)
- Sorting : `?sort=-created_at` (préfixe `-` pour desc)
- Réponses : JSON, enveloppées dans `{"data": ..., "meta": {...}}`
- Erreurs : `{"error": {"code": "...", "message": "...", "details": [...]}}`
- Rate limiting : `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- Tenant isolation : automatique via le JWT (tenant_id dans le token)

---

## Auth (`/api/v1/auth`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| POST | `/auth/register` | Inscription + création tenant | Public |
| POST | `/auth/login` | Login → JWT access + refresh | Public |
| POST | `/auth/refresh` | Refresh token | Authenticated |
| POST | `/auth/logout` | Blacklist le token | Authenticated |
| POST | `/auth/forgot-password` | Envoi email reset | Public |
| POST | `/auth/reset-password` | Reset avec token | Public |
| GET | `/auth/me` | Profil utilisateur courant | Authenticated |
| PUT | `/auth/me` | Update profil | Authenticated |
| POST | `/auth/oauth/{provider}/authorize` | Initier OAuth (pour connexion sociale) | Authenticated |
| GET | `/auth/oauth/{provider}/callback` | Callback OAuth | Authenticated |

### Payload examples

```python
# POST /auth/register
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    company_name: str
    phone: str | None = None
    country: str = "BF"
    language: str = "fr"

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
```

---

## Tenants (`/api/v1/tenants`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/tenants/current` | Tenant courant | Authenticated |
| PUT | `/tenants/current` | Update settings tenant | Owner, Admin |
| GET | `/tenants/current/members` | Liste des membres | Admin+ |
| POST | `/tenants/current/members` | Inviter un membre | Admin+ |
| PUT | `/tenants/current/members/{user_id}` | Changer rôle | Owner |
| DELETE | `/tenants/current/members/{user_id}` | Retirer un membre | Owner |
| GET | `/tenants/current/usage` | Usage courant vs limites | Authenticated |

---

## Brands (`/api/v1/brands`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/brands` | Liste des marques du tenant | Viewer+ |
| POST | `/brands` | Créer une marque | Editor+ |
| GET | `/brands/{id}` | Détail marque | Viewer+ |
| PUT | `/brands/{id}` | Update marque | Editor+ |
| DELETE | `/brands/{id}` | Supprimer marque | Admin+ |
| PUT | `/brands/{id}/guidelines` | Update guidelines | Editor+ |

```python
class BrandCreate(BaseModel):
    name: str = Field(max_length=255)
    description: str | None = None
    industry: str | None = None
    logo_url: str | None = None
    colors: dict = Field(default_factory=dict)
    tone: str = "professional"
    language: str = "fr"
    target_country: str = "BF"
    guidelines: dict = Field(default_factory=dict)
```

---

## Social Accounts (`/api/v1/social-accounts`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/social-accounts` | Liste comptes connectés | Viewer+ |
| POST | `/social-accounts/connect/facebook` | Initier connexion Facebook | Admin+ |
| POST | `/social-accounts/connect/whatsapp` | Connecter WhatsApp | Admin+ |
| GET | `/social-accounts/{id}` | Détail compte | Viewer+ |
| PUT | `/social-accounts/{id}` | Update settings | Admin+ |
| DELETE | `/social-accounts/{id}` | Déconnecter | Admin+ |
| POST | `/social-accounts/{id}/refresh-token` | Refresh token | Admin+ |
| GET | `/social-accounts/{id}/health` | Vérifier santé connexion | Viewer+ |

---

## Posts (`/api/v1/posts`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/posts` | Liste des posts | Viewer+ |
| POST | `/posts` | Créer un post manuellement | Editor+ |
| POST | `/posts/generate` | Générer un post via IA | Editor+ |
| GET | `/posts/{id}` | Détail post | Viewer+ |
| PUT | `/posts/{id}` | Éditer un post | Editor+ |
| DELETE | `/posts/{id}` | Supprimer un post | Editor+ |
| POST | `/posts/{id}/publish` | Publier immédiatement | Manager+ |
| POST | `/posts/{id}/schedule` | Planifier publication | Manager+ |
| GET | `/posts/{id}/analytics` | Métriques du post | Viewer+ |
| GET | `/posts/{id}/comments` | Commentaires du post | Viewer+ |

```python
class PostGenerateRequest(BaseModel):
    brand_id: UUID
    brief: str = Field(min_length=10, max_length=2000)
    channels: list[str]  # ["facebook", "instagram"]
    campaign_id: UUID | None = None
    generate_image: bool = False
    image_style: str | None = None
    variants_count: int = Field(default=1, ge=1, le=3)
    scheduled_at: datetime | None = None
    language: str = "fr"

class PostResponse(BaseModel):
    id: UUID
    content_text: str | None
    hashtags: list[str]
    status: PostStatus
    channel_variants: dict
    target_channels: list[dict]
    assets: list[PostAssetResponse]
    ai_generated: bool
    ai_confidence_score: float | None
    scheduled_at: datetime | None
    published_at: datetime | None
    created_at: datetime
    created_by: UUID
```

---

## Campaigns (`/api/v1/campaigns`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/campaigns` | Liste campagnes | Viewer+ |
| POST | `/campaigns` | Créer campagne | Manager+ |
| GET | `/campaigns/{id}` | Détail campagne | Viewer+ |
| PUT | `/campaigns/{id}` | Update campagne | Manager+ |
| DELETE | `/campaigns/{id}` | Supprimer | Admin+ |
| GET | `/campaigns/{id}/posts` | Posts de la campagne | Viewer+ |
| GET | `/campaigns/{id}/analytics` | Métriques campagne | Viewer+ |

---

## Conversations & Messages (`/api/v1/conversations`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/conversations` | Inbox unifiée | Support+ |
| GET | `/conversations?status=escalated` | Conversations escaladées | Support+ |
| GET | `/conversations/{id}` | Détail conversation | Support+ |
| PUT | `/conversations/{id}` | Update status, assign | Support+ |
| GET | `/conversations/{id}/messages` | Messages de la conversation | Support+ |
| POST | `/conversations/{id}/messages` | Envoyer un message (humain) | Support+ |
| POST | `/conversations/{id}/close` | Fermer conversation | Support+ |
| POST | `/conversations/{id}/escalate` | Escalader manuellement | Support+ |

```python
class SendMessageRequest(BaseModel):
    content: str = Field(max_length=4096)
    content_type: str = "text"  # text, image, document, template
    media_url: str | None = None

class ConversationListResponse(BaseModel):
    id: UUID
    customer_name: str | None
    platform: str
    status: ConversationStatus
    last_message_preview: str | None
    last_message_at: datetime | None
    message_count: int
    sentiment: str | None
    assigned_to: UUID | None
    tags: list[str]
```

---

## Knowledge (`/api/v1/knowledge`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/knowledge/documents` | Liste documents | Viewer+ |
| POST | `/knowledge/documents` | Upload document | Editor+ |
| POST | `/knowledge/documents/url` | Importer depuis URL | Editor+ |
| GET | `/knowledge/documents/{id}` | Détail document | Viewer+ |
| DELETE | `/knowledge/documents/{id}` | Supprimer document | Admin+ |
| POST | `/knowledge/documents/{id}/reindex` | Réindexer | Editor+ |
| POST | `/knowledge/search` | Recherche RAG | Authenticated |

```python
class KnowledgeSearchRequest(BaseModel):
    query: str
    brand_id: UUID
    top_k: int = Field(default=5, ge=1, le=20)
    doc_types: list[str] | None = None  # filter by type
    min_score: float = Field(default=0.3, ge=0.0, le=1.0)

class KnowledgeSearchResponse(BaseModel):
    results: list[SearchResult]
    synthesis: str | None  # LLM-generated answer from results

class SearchResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_title: str
    content: str
    score: float
    section_title: str | None
```

---

## Approvals (`/api/v1/approvals`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/approvals` | Liste approbations en attente | Manager+ |
| GET | `/approvals/{id}` | Détail approbation | Manager+ |
| POST | `/approvals/{id}/approve` | Approuver | Manager+ |
| POST | `/approvals/{id}/reject` | Rejeter (avec note) | Manager+ |

---

## Escalations (`/api/v1/escalations`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/escalations` | Liste escalations | Support+ |
| GET | `/escalations/{id}` | Détail escalation | Support+ |
| PUT | `/escalations/{id}/assign` | Assigner agent | Manager+ |
| POST | `/escalations/{id}/resolve` | Résoudre | Support+ |

---

## Analytics (`/api/v1/analytics`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/analytics/overview` | KPIs globaux | Viewer+ |
| GET | `/analytics/posts` | Métriques posts | Viewer+ |
| GET | `/analytics/conversations` | Métriques support | Viewer+ |
| GET | `/analytics/agents` | Métriques agents IA | Admin+ |
| GET | `/analytics/usage` | Consommation ressources | Admin+ |

```python
class AnalyticsOverviewResponse(BaseModel):
    period: str  # "2024-01", "last_7_days", etc.
    posts_published: int
    total_engagement: int
    messages_received: int
    messages_ai_handled: int
    messages_human_handled: int
    avg_response_time_seconds: float
    escalation_rate: float
    ai_confidence_avg: float
    top_performing_channel: str
```

---

## Billing (`/api/v1/billing`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/billing/plans` | Plans disponibles | Public |
| GET | `/billing/subscription` | Abonnement courant | Owner+ |
| POST | `/billing/subscribe` | Souscrire à un plan | Owner |
| PUT | `/billing/subscription` | Changer de plan | Owner |
| POST | `/billing/subscription/cancel` | Annuler | Owner |
| GET | `/billing/invoices` | Historique factures | Owner+ |
| GET | `/billing/usage` | Usage détaillé du mois | Owner+ |

---

## Webhooks entrants (`/api/v1/webhooks`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/webhooks/facebook` | Vérification webhook Meta (challenge) |
| POST | `/webhooks/facebook` | Événements Facebook/Instagram/Messenger |
| GET | `/webhooks/whatsapp` | Vérification webhook WhatsApp |
| POST | `/webhooks/whatsapp` | Messages WhatsApp entrants |
| POST | `/webhooks/tiktok` | Événements TikTok |

**Important** : Les webhooks doivent retourner 200 en < 5 secondes.
Le traitement réel se fait en queue.

---

## Audit (`/api/v1/audit`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/audit/events` | Journal d'audit | Admin+ |
| GET | `/audit/events/{id}` | Détail événement | Admin+ |

---

## Admin (`/api/v1/admin`)

*Uniquement pour les superadmins de la plateforme.*

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/admin/tenants` | Liste tous les tenants | Superadmin |
| GET | `/admin/tenants/{id}` | Détail tenant | Superadmin |
| PUT | `/admin/tenants/{id}` | Modifier tenant | Superadmin |
| POST | `/admin/tenants/{id}/suspend` | Suspendre | Superadmin |
| GET | `/admin/stats` | Stats globales plateforme | Superadmin |
| GET | `/admin/agent-runs` | Logs d'exécution agents | Superadmin |
