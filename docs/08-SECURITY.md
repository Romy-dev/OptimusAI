# OptimusAI — Sécurité & Gouvernance

## 1. Authentification

### JWT Strategy

```python
# Tokens
ACCESS_TOKEN_EXPIRE = 30 minutes
REFRESH_TOKEN_EXPIRE = 7 jours

# JWT Payload
{
    "sub": "user_uuid",
    "tenant_id": "tenant_uuid",
    "role": "admin",
    "permissions": ["posts.create", "posts.publish", ...],
    "iat": 1234567890,
    "exp": 1234567890,
    "jti": "unique_token_id"  # pour blacklisting
}
```

- **Access token** : court (30min), signé HS256 ou RS256
- **Refresh token** : long (7j), stocké en DB (révocable)
- **Blacklist** : Redis set pour les tokens révoqués
- **OAuth2** : pour la connexion des comptes sociaux (Facebook, Google login)

---

## 2. RBAC (Role-Based Access Control)

### Rôles

| Rôle | Niveau | Description |
|------|--------|-------------|
| **Owner** | 100 | Propriétaire du tenant. Tout accès. |
| **Admin** | 80 | Gestion complète sauf suppression tenant. |
| **Manager** | 60 | Approuver, publier, gérer campagnes. |
| **Editor** | 40 | Créer et éditer du contenu. Pas de publication. |
| **Support Agent** | 30 | Inbox, conversations, escalations. |
| **Viewer** | 10 | Lecture seule. Analytics. |

### Matrice des permissions

| Resource | Viewer | Editor | Support | Manager | Admin | Owner |
|----------|--------|--------|---------|---------|-------|-------|
| brands.read | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| brands.write | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ |
| brands.delete | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| posts.read | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| posts.create | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ |
| posts.publish | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| posts.delete | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| conversations.read | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| conversations.reply | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| knowledge.read | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| knowledge.write | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ |
| approvals.review | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| analytics.read | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| billing.manage | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| members.manage | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| social.connect | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| audit.read | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |

### Implémentation

```python
# app/core/permissions.py

from functools import wraps

class PermissionChecker:
    """Dependency injection pour vérifier les permissions."""

    def __init__(self, required: str):
        self.required = required  # e.g. "posts.publish"

    async def __call__(self, current_user: User = Depends(get_current_user)):
        if current_user.is_superadmin:
            return current_user

        user_permissions = get_permissions_for_role(current_user.role)
        if self.required not in user_permissions:
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {self.required} required"
            )
        return current_user

# Usage dans les routes
@router.post("/posts/{id}/publish")
async def publish_post(
    id: UUID,
    user: User = Depends(PermissionChecker("posts.publish")),
):
    ...
```

---

## 3. Isolation Multi-Tenant

### Stratégie : Row-Level Security (RLS)

Chaque requête SQL est automatiquement filtrée par `tenant_id`.

```python
# app/core/middleware.py

class TenantMiddleware:
    """Extrait le tenant_id du JWT et le met dans le context."""

    async def __call__(self, request: Request, call_next):
        token = extract_token(request)
        if token:
            payload = decode_jwt(token)
            request.state.tenant_id = payload.get("tenant_id")
        response = await call_next(request)
        return response

# app/repositories/base.py

class BaseRepository:
    """Toutes les queries sont automatiquement filtrées par tenant."""

    async def get_by_id(self, id: UUID) -> Model | None:
        stmt = select(self.model).where(
            self.model.id == id,
            self.model.tenant_id == self.tenant_id,  # ISOLATION
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self, **filters) -> list[Model]:
        stmt = select(self.model).where(
            self.model.tenant_id == self.tenant_id,  # ISOLATION
        )
        for key, value in filters.items():
            stmt = stmt.where(getattr(self.model, key) == value)
        result = await self.session.execute(stmt)
        return result.scalars().all()
```

### Protection supplémentaire : PostgreSQL RLS (defense in depth)

```sql
-- En plus du filtrage applicatif, activer RLS au niveau PostgreSQL
ALTER TABLE posts ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON posts
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

---

## 4. Secrets Management

| Secret | Stockage | Chiffrement |
|--------|----------|-------------|
| Mots de passe | PostgreSQL | bcrypt (passlib) |
| Tokens sociaux | PostgreSQL | AES-256-GCM (Fernet) |
| JWT secret key | Env var | N/A |
| API keys (LLM) | Env var | N/A |
| WhatsApp tokens | PostgreSQL | AES-256-GCM |

```python
# app/core/security.py
from cryptography.fernet import Fernet

class SecretManager:
    def __init__(self, encryption_key: str):
        self.cipher = Fernet(encryption_key)

    def encrypt(self, plaintext: str) -> str:
        return self.cipher.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self.cipher.decrypt(ciphertext.encode()).decode()
```

---

## 5. Rate Limiting

### Par tenant

| Ressource | Limite | Fenêtre |
|-----------|--------|---------|
| API globale | 1000 req | /minute |
| Génération IA | 60 req | /heure |
| Publication | 30 req | /heure |
| Upload documents | 20 req | /heure |
| Webhooks entrants | 5000 req | /minute |

### Implémentation

```python
# Redis-based sliding window rate limiter
import redis.asyncio as redis

class RateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def check(self, key: str, limit: int, window_seconds: int) -> bool:
        pipe = self.redis.pipeline()
        now = time.time()
        window_start = now - window_seconds

        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, window_seconds)

        results = await pipe.execute()
        current_count = results[2]
        return current_count <= limit
```

---

## 6. Quotas (liés au plan)

```python
class QuotaService:
    async def check_quota(self, tenant_id: UUID, metric: str) -> bool:
        """Vérifie si le tenant n'a pas dépassé son quota."""
        plan = await self.get_tenant_plan(tenant_id)
        limit = plan.limits.get(f"max_{metric}")
        if limit is None:
            return True  # Pas de limite

        current_usage = await self.usage_repo.get_current_month_usage(
            tenant_id=tenant_id, metric=metric
        )
        return current_usage < limit

    async def increment_usage(self, tenant_id: UUID, metric: str, quantity: int = 1):
        """Incrémente l'usage après une action."""
        await self.usage_repo.increment(
            tenant_id=tenant_id,
            metric=metric,
            quantity=quantity,
        )
```

---

## 7. Sécurité des Prompts

### Protections

1. **Input sanitization** : nettoyer les inputs utilisateur avant injection dans les prompts
2. **System prompt isolation** : le system prompt n'est jamais exposé à l'utilisateur
3. **Output validation** : parser le JSON attendu, rejeter les outputs malformés
4. **Injection detection** : classifier rapide pour détecter les tentatives d'injection

```python
class PromptSecurity:
    INJECTION_PATTERNS = [
        r"ignore (all |previous |above )?instructions",
        r"you are now",
        r"new instructions:",
        r"system prompt:",
        r"reveal your",
        r"act as",
    ]

    @classmethod
    def sanitize_user_input(cls, text: str) -> str:
        """Remove potential prompt injection patterns."""
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                raise PromptInjectionDetected(
                    f"Potential prompt injection detected"
                )
        # Escape special characters that could affect prompts
        text = text.replace("{", "{{").replace("}", "}}")
        return text

    @classmethod
    def validate_output(cls, output: str, expected_format: str) -> bool:
        """Validate that LLM output matches expected format."""
        if expected_format == "json":
            try:
                json.loads(output)
                return True
            except json.JSONDecodeError:
                return False
        return True
```

---

## 8. Protection contre les réponses dangereuses

```python
class SafetyGuard:
    """Vérifie que les réponses IA ne contiennent pas de contenu dangereux
    avant de les envoyer au client."""

    BLOCKED_PATTERNS = {
        "medical_advice": r"(prend(s|ez)|consomm(e|ez)) .* (médicament|comprimé|pilule)",
        "financial_advice": r"(invest|place(z|r)) .* (argent|épargne|FCFA)",
        "personal_data": r"\b\d{8,}\b",  # numéros de téléphone, etc.
        "competitor_mention": None,  # dynamique, basé sur brand config
    }

    async def check(self, content: str, brand_context: dict) -> SafetyResult:
        flags = []
        for check_name, pattern in self.BLOCKED_PATTERNS.items():
            if pattern and re.search(pattern, content, re.IGNORECASE):
                flags.append(check_name)

        # Check brand-specific blocked topics
        banned = brand_context.get("guidelines", {}).get("banned_topics", [])
        for topic in banned:
            if topic.lower() in content.lower():
                flags.append(f"banned_topic:{topic}")

        return SafetyResult(
            safe=len(flags) == 0,
            flags=flags,
            requires_human_review=len(flags) > 0,
        )
```

---

## 9. Validation Humaine (Human-in-the-Loop)

### Matrice de décision

| Action | Auto si confidence ≥ | Sinon |
|--------|----------------------|-------|
| Publier un post | 0.85 (si config auto_publish) | Review humaine obligatoire |
| Répondre à un commentaire | 0.70 | Draft pour review |
| Répondre à un DM/WhatsApp | 0.60 | Escalade humaine |
| Envoyer un template WhatsApp | N/A | Toujours review humaine (coût) |

### Configurable par tenant

```python
# Tenant settings
{
    "human_in_loop": {
        "require_approval_for_posts": true,       # Défaut: true
        "auto_reply_comments_threshold": 0.7,     # 0 = jamais auto
        "auto_reply_messages_threshold": 0.6,
        "auto_publish_threshold": null,            # null = toujours review
        "escalation_notification": "email+push",
    }
}
```

---

## 10. Audit Trail

Chaque action importante est loggée dans `audit_events` :

```python
class AuditService:
    async def log(
        self,
        action: str,
        resource_type: str,
        resource_id: UUID | None,
        actor_id: UUID | None,
        tenant_id: UUID,
        changes: dict | None = None,
        request: Request | None = None,
    ):
        event = AuditEvent(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None,
            changes=changes or {},
        )
        await self.repo.create(event)

# Usage
await audit.log(
    action="post.publish",
    resource_type="post",
    resource_id=post.id,
    actor_id=current_user.id,
    tenant_id=current_user.tenant_id,
    changes={"status": {"before": "approved", "after": "published"}},
    request=request,
)
```

### Actions auditées

```
user.register, user.login, user.login_failed, user.logout
tenant.update, tenant.member_invite, tenant.member_remove
brand.create, brand.update, brand.delete
social_account.connect, social_account.disconnect, social_account.token_refresh
post.create, post.update, post.publish, post.delete, post.schedule
knowledge.upload, knowledge.delete, knowledge.reindex
conversation.assign, conversation.escalate, conversation.close
approval.approve, approval.reject
billing.subscribe, billing.cancel, billing.plan_change
settings.update
```

---

## 11. Score de Confiance & Politique d'Escalade

```python
class ConfidencePolicy:
    """Politique centralisée pour décider si l'IA peut agir seule."""

    def __init__(self, tenant_settings: dict):
        self.settings = tenant_settings.get("human_in_loop", {})

    def should_auto_publish(self, score: float) -> bool:
        threshold = self.settings.get("auto_publish_threshold")
        if threshold is None:
            return False  # Toujours review humaine
        return score >= threshold

    def should_auto_reply_comment(self, score: float) -> bool:
        threshold = self.settings.get("auto_reply_comments_threshold", 0.7)
        return score >= threshold

    def should_auto_reply_message(self, score: float) -> bool:
        threshold = self.settings.get("auto_reply_messages_threshold", 0.6)
        return score >= threshold

    def should_escalate(self, context: dict) -> tuple[bool, str]:
        reasons = []

        if context.get("confidence_score", 1.0) < 0.4:
            reasons.append("confidence_too_low")

        if context.get("consecutive_negative_sentiment", 0) >= 2:
            reasons.append("customer_unhappy")

        if context.get("topic") in ("refund", "complaint", "legal"):
            reasons.append("sensitive_topic")

        if context.get("customer_requested_human"):
            reasons.append("customer_request")

        if context.get("no_kb_match"):
            reasons.append("no_knowledge_match")

        return len(reasons) > 0, ", ".join(reasons)
```
