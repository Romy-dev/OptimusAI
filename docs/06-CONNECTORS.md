# OptimusAI — Connecteurs Sociaux

## Architecture des Connecteurs

Chaque plateforme a un **adapter** qui implémente une interface commune. Cela permet d'ajouter de nouvelles plateformes sans modifier le code métier.

```python
from abc import ABC, abstractmethod
from pydantic import BaseModel

class NormalizedEvent(BaseModel):
    """Événement normalisé, commun à toutes les plateformes."""
    event_type: str  # "message", "comment", "reaction", "status_update"
    platform: str
    account_id: str
    external_id: str
    author_id: str | None
    author_name: str | None
    content: str | None
    content_type: str  # "text", "image", "video", "audio", "document"
    media_url: str | None
    parent_id: str | None  # For replies/comments: the parent post/comment ID
    timestamp: datetime
    raw_data: dict  # Original webhook payload

class PublishResult(BaseModel):
    success: bool
    external_id: str | None
    external_url: str | None
    error: str | None
    platform: str

class BaseSocialConnector(ABC):
    """Interface commune pour tous les connecteurs sociaux."""

    platform: str

    @abstractmethod
    async def publish_post(
        self, content: str, media_urls: list[str] | None = None,
        **kwargs
    ) -> PublishResult:
        """Publier un post."""
        ...

    @abstractmethod
    async def reply_to_comment(
        self, comment_id: str, content: str
    ) -> PublishResult:
        """Répondre à un commentaire."""
        ...

    @abstractmethod
    async def send_message(
        self, recipient_id: str, content: str,
        content_type: str = "text", media_url: str | None = None
    ) -> PublishResult:
        """Envoyer un message privé."""
        ...

    @abstractmethod
    async def get_post_insights(self, external_post_id: str) -> dict:
        """Récupérer les métriques d'un post."""
        ...

    @abstractmethod
    async def verify_token(self) -> bool:
        """Vérifier que le token est valide."""
        ...

    @abstractmethod
    async def refresh_access_token(self) -> str | None:
        """Renouveler le token si possible."""
        ...

    @abstractmethod
    def parse_webhook(self, payload: dict) -> list[NormalizedEvent]:
        """Parser un webhook entrant en événements normalisés."""
        ...
```

---

## Facebook Pages

### Capabilities

| Fonctionnalité | Support | Détails |
|----------------|---------|---------|
| **Publier un post** | ✅ | Texte, image, vidéo, lien |
| **Publier un carousel** | ✅ | Multi-image |
| **Lire les commentaires** | ✅ | Via webhooks + API polling |
| **Répondre aux commentaires** | ✅ | En tant que la page |
| **Cacher/supprimer commentaires** | ✅ | En tant que la page |
| **Lire les messages (Messenger)** | ✅ | Via webhooks |
| **Répondre messages (Messenger)** | ✅ | Send API |
| **Scheduling** | ✅ | Via `scheduled_publish_time` |
| **Insights / analytics** | ✅ | Page insights + post insights |
| **Webhooks** | ✅ | feed, messaging, mentions |

### Limites

- **Rate limit** : 200 appels / heure / utilisateur (varie selon le type)
- **App Review** requis pour : `pages_manage_posts`, `pages_messaging`
- **Business Verification** requis pour les apps publiques
- **Token longue durée** : 60 jours, renouvelable
- **Messaging** : pas de restriction 24h pour les Pages (contrairement à Messenger bot)
- **Vidéo** : upload via Resumable Upload API pour > 1GB

### Webhooks Facebook

```
POST /webhooks/facebook
Signature: X-Hub-Signature-256

Events:
- feed: {field: "feed", value: {item: "comment", ...}}
- messaging: {sender: {id}, message: {text, attachments}}
- mention: {field: "mention", ...}
```

### Implémentation clé

```python
class FacebookConnector(BaseSocialConnector):
    platform = "facebook"
    BASE_URL = "https://graph.facebook.com/v21.0"

    async def publish_post(self, content, media_urls=None, **kwargs):
        if media_urls:
            # Upload photo/video first, then attach
            photo_ids = []
            for url in media_urls:
                resp = await self._upload_photo(url)
                photo_ids.append(resp["id"])
            # Publish with attached photos
            payload = {"message": content, "attached_media": [
                {"media_fbid": pid} for pid in photo_ids
            ]}
        else:
            payload = {"message": content}

        if scheduled_at := kwargs.get("scheduled_at"):
            payload["scheduled_publish_time"] = int(scheduled_at.timestamp())
            payload["published"] = False

        resp = await self.client.post(
            f"{self.BASE_URL}/{self.page_id}/feed",
            params={"access_token": self.access_token},
            json=payload,
        )
        data = resp.json()
        return PublishResult(
            success="id" in data,
            external_id=data.get("id"),
            external_url=f"https://facebook.com/{data.get('id')}",
            error=data.get("error", {}).get("message"),
            platform="facebook",
        )
```

---

## Instagram (Graph API)

### Capabilities

| Fonctionnalité | Support | Détails |
|----------------|---------|---------|
| **Publier image** | ✅ | Single image post |
| **Publier carousel** | ✅ | Multi-image (2-10 images) |
| **Publier Reel** | ✅ | Vidéo courte |
| **Publier Story** | ❌ | Pas supporté par l'API |
| **Lire commentaires** | ✅ | Via API |
| **Répondre commentaires** | ✅ | Via API |
| **Lire DMs** | ✅ | Via Instagram Messaging API |
| **Répondre DMs** | ⚠️ | Règle des 24h (Human Agent) |
| **Scheduling** | ✅ | Via Content Publishing API |
| **Insights** | ✅ | Media insights, account insights |
| **Webhooks** | ✅ | comments, messaging (via Facebook) |

### Limites

- **Requiert** un compte Instagram Business/Creator lié à une Page Facebook
- **Rate limit** : 200 appels / heure / utilisateur
- **Publication** : process en 2 étapes (create container → publish)
- **Images** : JPEG uniquement, ratio 4:5 à 1.91:1
- **DM 24h rule** : après 24h sans message du client, doit utiliser un "Human Agent" tag ou attendre un nouveau message
- **Pas de texte-only** : chaque post DOIT avoir une image ou vidéo

### Publication en 2 étapes

```python
# Étape 1 : Créer le container
POST /{ig_user_id}/media
  image_url=..., caption=..., hashtags...
→ {id: "container_id"}

# Étape 2 : Publier
POST /{ig_user_id}/media_publish
  creation_id=container_id
→ {id: "media_id"}
```

---

## WhatsApp Business (Cloud API)

### Capabilities

| Fonctionnalité | Support | Détails |
|----------------|---------|---------|
| **Envoyer messages texte** | ✅ | Session + template |
| **Envoyer images** | ✅ | JPEG, PNG |
| **Envoyer documents** | ✅ | PDF, DOCX, etc. |
| **Envoyer audio** | ✅ | MP3, OGG |
| **Envoyer vidéo** | ✅ | MP4 |
| **Envoyer boutons** | ✅ | Quick replies, URL buttons |
| **Envoyer listes** | ✅ | List messages |
| **Recevoir messages** | ✅ | Via webhooks |
| **Recevoir média** | ✅ | Images, audio, docs |
| **Statuts de livraison** | ✅ | sent, delivered, read |
| **Templates** | ✅ | Obligatoires hors session 24h |
| **Webhooks** | ✅ | Messages, statuts |

### Limites CRITIQUES

- **Session messaging** : gratuit dans les 24h après le dernier message du client
- **Hors session** : DOIT utiliser un Message Template pré-approuvé par Meta
- **Coût templates** : 0.03-0.15 USD par message (varie par pays et catégorie)
- **Catégories de templates** : utility, marketing, authentication
- **Rate limit** : 80 messages/seconde (Business tier)
- **Rate limit** : 1000 messages/24h (nouveau numéro, augmente progressivement)
- **Business verification** : OBLIGATOIRE pour plus de 50 conversations/jour
- **Un seul numéro** par WhatsApp Business Account peut être connecté à l'API à la fois

### Pricing WhatsApp (Afrique)

| Type | Coût estimé (USD) |
|------|-------------------|
| Marketing template | ~$0.08 |
| Utility template | ~$0.03 |
| Authentication template | ~$0.03 |
| Service (session 24h) | Gratuit (first 1000/mois) |

### Webhooks WhatsApp

```json
{
  "object": "whatsapp_business_account",
  "entry": [{
    "changes": [{
      "field": "messages",
      "value": {
        "messages": [{
          "from": "22670123456",
          "type": "text",
          "text": {"body": "Bonjour, combien coûte..."},
          "timestamp": "1234567890"
        }],
        "contacts": [{"profile": {"name": "Amadou"}}]
      }
    }]
  }]
}
```

### Alternative : Evolution API (non-officiel)

| Aspect | Cloud API | Evolution API |
|--------|-----------|---------------|
| **Coût** | Payant (templates) | Gratuit (open source) |
| **Légalité** | Officiel Meta | Zone grise (ToS WhatsApp) |
| **Stabilité** | Haute | Risque de ban |
| **Features** | Templates, buttons | Tout WhatsApp |
| **Recommandation** | ✅ Production | ⚠️ Dev/test uniquement |

**Décision** : Utiliser Cloud API en production. Evolution API en dev/test.

---

## Messenger

### Capabilities

| Fonctionnalité | Support | Détails |
|----------------|---------|---------|
| **Envoyer messages** | ✅ | Send API |
| **Recevoir messages** | ✅ | Webhooks |
| **Quick replies** | ✅ | Boutons rapides |
| **Templates** | ✅ | Generic, button, receipt |
| **Persistent menu** | ✅ | Menu fixe |
| **Handover protocol** | ✅ | IA → humain |
| **Webhooks** | ✅ | messaging, messaging_postbacks |

### Limites

- **24h + 1 rule** : après 24h sans message du client, 1 seul message autorisé
- **Message tags** : pour envoyer hors 24h (CONFIRMED_EVENT_UPDATE, POST_PURCHASE_UPDATE, ACCOUNT_UPDATE)
- **Rate limit** : 200 appels / heure
- **Requiert** une Page Facebook avec l'app configurée
- **Même tokens** que Facebook Pages

### Handover Protocol

```
IA répond au client → Page "primary receiver"
    │
    ▼
Client demande un humain ou confidence < seuil
    │
    ▼
Pass thread control → "secondary receiver" (human inbox)
    │ POST /me/pass_thread_control
    │   recipient_id, target_app_id, metadata
    │
    ▼
Agent humain répond via Page Inbox ou dashboard
    │
    ▼
Conversation terminée → Take thread control → retour à l'IA
```

---

## TikTok

### Capabilities

| Fonctionnalité | Support | Détails |
|----------------|---------|---------|
| **Publier vidéo** | ✅ | Content Posting API |
| **Publier image** | ⚠️ | Photo mode (limité) |
| **Lire commentaires** | ✅ | Via API |
| **Répondre commentaires** | ❌ | PAS D'API WRITE |
| **Lire DMs** | ❌ | Pas d'API DM |
| **Insights** | ✅ | Video insights |
| **Webhooks** | ⚠️ | Limité (comment, video publish) |

### Limites majeures

- **PAS de réponse aux commentaires** via API → notification only
- **PAS d'accès aux DMs** via API
- **Publication** : vidéo uniquement (min 3s, max 10min)
- **OAuth2** : PKCE flow obligatoire
- **App Review** : très strict, long processus
- **Rate limit** : 100 requêtes/minute

**Stratégie TikTok** : publication de vidéos + lecture commentaires + analytics. Aucune interaction automatisée.

---

## Normalisation des événements

```python
# app/connectors/normalizer.py

class EventNormalizer:
    """Normalise les événements de toutes les plateformes
    vers un format unique."""

    @staticmethod
    def from_facebook_feed(payload: dict) -> list[NormalizedEvent]:
        events = []
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                if change["field"] == "feed" and change["value"]["item"] == "comment":
                    events.append(NormalizedEvent(
                        event_type="comment",
                        platform="facebook",
                        account_id=entry["id"],
                        external_id=change["value"]["comment_id"],
                        author_id=change["value"].get("from", {}).get("id"),
                        author_name=change["value"].get("from", {}).get("name"),
                        content=change["value"].get("message"),
                        content_type="text",
                        parent_id=change["value"].get("post_id"),
                        timestamp=datetime.fromtimestamp(
                            change["value"]["created_time"]
                        ),
                        raw_data=change["value"],
                    ))
        return events

    @staticmethod
    def from_whatsapp(payload: dict) -> list[NormalizedEvent]:
        events = []
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                if change["field"] == "messages":
                    for msg in change["value"].get("messages", []):
                        content = None
                        content_type = msg["type"]
                        media_url = None

                        if msg["type"] == "text":
                            content = msg["text"]["body"]
                        elif msg["type"] in ("image", "video", "audio", "document"):
                            media_url = msg[msg["type"]].get("id")  # media_id to download
                            content = msg[msg["type"]].get("caption")

                        contact = change["value"].get("contacts", [{}])[0]
                        events.append(NormalizedEvent(
                            event_type="message",
                            platform="whatsapp",
                            account_id=change["value"]["metadata"]["phone_number_id"],
                            external_id=msg["id"],
                            author_id=msg["from"],
                            author_name=contact.get("profile", {}).get("name"),
                            content=content,
                            content_type=content_type,
                            media_url=media_url,
                            parent_id=msg.get("context", {}).get("id"),  # reply to
                            timestamp=datetime.fromtimestamp(int(msg["timestamp"])),
                            raw_data=msg,
                        ))
        return events
```

---

## Alertes spécifiques Afrique

### Business Verification Meta (Facebook/Instagram/WhatsApp)
- Les documents d'enregistrement d'entreprises africaines ne sont **pas toujours acceptés** au premier essai
- Prévoir des documents supplémentaires : RCCM, IFU, facture d'électricité, site web vérifié
- Le process peut prendre 2-4 semaines pour les entreprises BF/CI/SN
- **Action** : créer un guide d'onboarding spécifique pour la vérification Meta en Afrique de l'Ouest

### WhatsApp Pricing Afrique (par conversation, estimé)
| Pays | Marketing | Utility | Authentication | Service (1000 free/mois) |
|------|-----------|---------|----------------|--------------------------|
| Nigeria | ~$0.034 | ~$0.008 | ~$0.023 | Gratuit |
| South Africa | ~$0.040 | ~$0.010 | ~$0.023 | Gratuit |
| Burkina Faso | ~$0.030-0.040 | ~$0.008 | ~$0.020 | Gratuit |
| Côte d'Ivoire | ~$0.030-0.040 | ~$0.008 | ~$0.020 | Gratuit |

### Instagram scheduling
- L'API Instagram **n'a pas** de paramètre `scheduled_publish_time` natif
- Le scheduling doit être géré côté serveur (worker cron qui publie à l'heure prévue)
- Notre architecture le prévoit via le worker `scheduled_posts`

### Paiement API WhatsApp
- Requiert une **carte bancaire internationale** dans Meta Business Manager
- Barrière pour certaines PME africaines → proposer un pack prépayé via notre billing

---

## Matrice de capacités résumée

| Capacité | Facebook | Instagram | WhatsApp | Messenger | TikTok |
|----------|----------|-----------|----------|-----------|--------|
| Publier texte | ✅ | ❌ (image req) | N/A | N/A | ❌ (vidéo req) |
| Publier image | ✅ | ✅ | N/A | N/A | ⚠️ |
| Publier vidéo | ✅ | ✅ (Reel) | N/A | N/A | ✅ |
| Lire commentaires | ✅ | ✅ | N/A | N/A | ✅ |
| Répondre commentaires | ✅ | ✅ | N/A | N/A | ❌ |
| Recevoir messages | N/A | ✅ (24h) | ✅ | ✅ | ❌ |
| Envoyer messages | N/A | ⚠️ (24h) | ✅ | ✅ (24h) | ❌ |
| Scheduling | ✅ | ✅ | N/A | N/A | ❌ |
| Webhooks | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| Analytics | ✅ | ✅ | ⚠️ | ⚠️ | ✅ |
