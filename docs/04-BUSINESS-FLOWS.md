# OptimusAI — Flux Métiers

## Flux 1 : Onboarding Entreprise

```
Inscription (email + mot de passe)
    │
    ▼
Création du Tenant
    │ → slug auto-généré
    │ → plan = trial (14 jours)
    │ → rôle = owner
    │
    ▼
Assistant de configuration
    │
    ├─ 1. Infos entreprise (nom, secteur, pays, langue)
    │
    ├─ 2. Création Brand (nom, logo, couleurs, ton)
    │
    ├─ 3. Connexion comptes sociaux (Facebook en premier)
    │     │ → OAuth2 flow → récupère access_token + pages
    │     │ → Détecte automatiquement les capabilities
    │     │ → Crée SocialAccount + Channels
    │
    ├─ 4. Import de documents (optionnel)
    │     │ → Upload FAQ, catalogue produits, PDF
    │     │ → Queue: document_ingestion worker
    │     │ → Chunking → Embedding → Indexation
    │
    └─ 5. Premier post test (optionnel)
          │ → Génération IA d'un post de bienvenue
          │ → Preview → Validation → Draft sauvegardé
```

**Durée cible** : < 10 minutes pour les étapes 1-3.

---

## Flux 2 : Connexion Comptes Sociaux

```
User clique "Connecter Facebook"
    │
    ▼
Redirection OAuth2 vers Facebook
    │ → Scopes demandés :
    │   pages_manage_posts, pages_read_engagement,
    │   pages_messaging, pages_read_user_content
    │
    ▼
Callback avec authorization code
    │
    ▼
Backend échange code → access_token + page tokens
    │
    ▼
Lister les Pages Facebook de l'utilisateur
    │ → L'user choisit quelle(s) page(s) connecter
    │
    ▼
Pour chaque page sélectionnée :
    │ → Créer SocialAccount (platform=facebook, token chiffré)
    │ → Détecter capabilities via API test
    │ → Créer Channels : feed, messenger
    │ → Enregistrer webhooks (page feed, messaging)
    │
    ▼
Vérification de santé (test post permissions)
    │ → Si OK → is_active = true
    │ → Si KO → notification + guide de résolution
```

### Pour WhatsApp Business

```
User fournit :
    │ → WhatsApp Business Account ID
    │ → Phone Number ID
    │ → Access Token (depuis Meta Business Suite)
    │
    ▼
Backend valide le token via API WhatsApp Cloud
    │
    ▼
Crée SocialAccount (platform=whatsapp)
    │ → Crée Channel (whatsapp)
    │ → Configure webhook URL dans Meta dashboard
    │   (ou utilise Evolution API si non-officiel)
    │
    ▼
Test : envoi d'un message template à un numéro test
    │ → Si OK → actif
    │ → Si KO → guide de résolution
```

---

## Flux 3 : Ingestion Documents / FAQ

```
User upload document (PDF, DOCX, CSV, TXT, URL)
    │
    ▼
API crée KnowledgeDoc (status=pending)
    │ → Fichier stocké dans S3/MinIO
    │
    ▼
Queue → document_ingestion worker
    │
    ├─ 1. Extraction texte
    │     │ → PDF : PyMuPDF ou pdfplumber
    │     │ → DOCX : python-docx
    │     │ → CSV : parsing structuré → Q/A pairs
    │     │ → URL : httpx + BeautifulSoup
    │
    ├─ 2. Nettoyage + normalisation
    │     │ → Suppression headers/footers inutiles
    │     │ → Détection de langue
    │
    ├─ 3. Chunking
    │     │ → Stratégie : RecursiveCharacterTextSplitter
    │     │ → Chunk size : 512 tokens
    │     │ → Overlap : 50 tokens
    │     │ → Respect des limites de section
    │
    ├─ 4. Embedding
    │     │ → Modèle : multilingual-e5-large ou BGE-M3
    │     │ → Batch processing pour efficacité
    │     │ → Stockage dans pgvector (table chunks)
    │
    └─ 5. Indexation
          │ → Mise à jour KnowledgeDoc (status=indexed, chunk_count=N)
          │ → Notification user "Document prêt"
          │ → AnalyticsEvent (document_ingested)

Erreur à n'importe quelle étape :
    → KnowledgeDoc.status = "failed"
    → Error log dans metadata
    → Notification user avec suggestion
```

---

## Flux 4 : Génération de Post

```
User : brief + canal cible + (campagne optionnelle)
    │
    ▼
API → ContentService.generate_post()
    │
    ▼
Queue → content_generation worker
    │
    ├─ 1. Orchestrator détecte : GENERATE_POST
    │
    ├─ 2. KnowledgeRetriever : cherche contexte brand
    │     │ → Brand guidelines, tone, past posts
    │     │ → Documents pertinents si applicable
    │
    ├─ 3. CopywriterAgent : génère le contenu
    │     │ → Prompt : system + brand context + brief
    │     │ → Output : texte + hashtags + media_prompt
    │     │ → Variantes si demandé
    │
    ├─ 4. ModeratorAgent : vérifie le contenu
    │     │ → Score de modération
    │     │ → Flags éventuels
    │
    ├─ 5. (Optionnel) ImageGenAgent : génère visuel
    │     │ → Si media_prompt fourni par copywriter
    │     │ → Génération via Stable Diffusion
    │     │ → Moderation de l'image
    │
    └─ 6. Création Post (status=draft ou pending_review)
          │ → PostAssets attachés si image générée
          │ → AgentRun logged
          │ → Notification user "Post prêt à reviewer"

User review :
    │
    ├─ Approuve → status=approved (ou scheduled si date)
    ├─ Édite → modifications sauvegardées
    └─ Rejette → status=rejected + feedback pour amélioration
```

---

## Flux 5 : Validation Humaine (Approval)

```
Post passe en status=pending_review
    │
    ▼
Notification aux reviewers (rôle manager+ )
    │ → Push notification / email
    │ → Visible dans dashboard "À valider"
    │
    ▼
Reviewer ouvre le post
    │ → Voit : contenu, image, canal cible, score IA
    │ → Voit : suggestions de l'agent moderator
    │
    ├─ "Approuver"
    │     │ → Approval.status = approved
    │     │ → Post.status = approved
    │     │ → Si scheduled_at défini → status = scheduled
    │     │ → Sinon → prêt à publier manuellement
    │     │ → AuditEvent logged
    │
    ├─ "Modifier et approuver"
    │     │ → Edit inline → save → approve
    │
    └─ "Rejeter"
          │ → Approval.status = rejected
          │ → Post.status = rejected
          │ → Reviewer ajoute note (obligatoire)
          │ → Notification au créateur
          │ → AuditEvent logged

Timeout : si pas de review en 48h → notification rappel.
Si config auto_approve et confidence > 0.85 → skip review.
```

---

## Flux 6 : Publication

```
Post.status = approved ou scheduled_at atteint
    │
    ▼
Queue → publishing worker
    │
    ├─ 1. PublisherAgent vérifie :
    │     │ → Post a approval? ✅
    │     │ → Social account actif? ✅
    │     │ → Token valide? ✅ (sinon refresh)
    │     │ → Rate limit OK? ✅
    │     │ → Média uploadé et valide? ✅
    │
    ├─ 2. Pour chaque canal cible :
    │     │ → Adapter le contenu (variants si définis)
    │     │ → Adapter le format média (resize si besoin)
    │     │ → Appeler le connector approprié
    │     │
    │     ├─ FacebookConnector.publish(post, media)
    │     │   → POST /v21.0/{page_id}/feed
    │     │   → Récupère external_id
    │     │
    │     ├─ InstagramConnector.publish(post, media)
    │     │   → POST /v21.0/{ig_user_id}/media (container)
    │     │   → POST /v21.0/{ig_user_id}/media_publish
    │     │
    │     └─ Etc.
    │
    ├─ 3. Mise à jour Post :
    │     │ → status = published
    │     │ → published_at = now()
    │     │ → external_ids = {...}
    │
    └─ 4. Events :
          │ → AnalyticsEvent (post_published)
          │ → AuditEvent (post.publish)
          │ → Notification user "Post publié ✓"

Erreur :
    → Retry 3x avec exponential backoff
    → Si échec persistant → status = failed
    → error dans metadata
    → Notification user + suggestion (re-auth, etc.)
```

---

## Flux 7 : Réponse aux Commentaires

```
Webhook Facebook : nouveau commentaire sur un post
    │
    ▼
API webhook handler → vérifie signature → 200 OK immédiat
    │
    ▼
Queue → webhook_processing worker
    │
    ├─ 1. Normaliser l'événement
    │     │ → NormalizedEvent(type=comment, platform=facebook, ...)
    │
    ├─ 2. Trouver le Post interne via external_id
    │
    ├─ 3. Créer Comment en DB
    │     │ → Sentiment analysis (positif/négatif/neutre)
    │
    ├─ 4. Vérifier reply_policy du brand :
    │     │ → auto_reply_all : répond à tout
    │     │ → auto_reply_questions : répond seulement aux questions
    │     │ → manual_only : notifie seulement
    │     │ → disabled : ignore
    │
    ├─ 5. Si auto-reply activé :
    │     │ → Orchestrator → SocialReplyAgent
    │     │ → Agent récupère contexte : post, brand, KB
    │     │ → Génère réponse
    │     │ → ModeratorAgent vérifie
    │     │
    │     ├─ Confidence ≥ 0.7 et approved :
    │     │   → Publie la réponse via connector
    │     │   → Reply.status = published
    │     │
    │     └─ Confidence < 0.7 ou flagged :
    │         → Reply.status = draft
    │         → Notification human "Réponse à valider"
    │
    └─ 6. Log : AgentRun, AnalyticsEvent

Note : TikTok ne supporte PAS les réponses aux commentaires via API.
       → Notification only pour TikTok.
```

---

## Flux 8 : Support Client (WhatsApp / Messenger)

```
Message entrant (webhook WhatsApp ou Messenger)
    │
    ▼
Webhook handler → 200 OK → Queue
    │
    ▼
webhook_processing worker
    │
    ├─ 1. Normaliser le message
    │     │ → NormalizedMessage(from, content, channel, media, ...)
    │
    ├─ 2. Trouver ou créer Conversation
    │     │ → Lookup par (channel_id, customer_external_id)
    │     │ → Si nouvelle → Conversation(status=open)
    │     │ → Si existante → update last_message_at
    │
    ├─ 3. Créer Message (direction=inbound)
    │
    ├─ 4. Vérifier le status de la conversation :
    │     │
    │     ├─ status = human_handling :
    │     │   → Ne pas interférer avec l'agent humain
    │     │   → Notification à l'agent assigné
    │     │   → FIN
    │     │
    │     ├─ status = open ou ai_handling :
    │     │   → Continuer vers l'IA
    │     │
    │     └─ status = closed/resolved :
    │         → Réouvrir la conversation
    │
    ├─ 5. Orchestrator → SupportAgent
    │     │
    │     ├─ 5a. Récupérer contexte :
    │     │   → Historique conversation (derniers N messages)
    │     │   → Customer metadata
    │     │   → Brand context + KB search
    │     │
    │     ├─ 5b. Générer réponse :
    │     │   → LLM avec context + historique + KB results
    │     │   → Sources citées
    │     │
    │     └─ 5c. Modération :
    │         → ModeratorAgent vérifie la réponse
    │
    ├─ 6. Évaluation :
    │     │
    │     ├─ Confidence ≥ 0.6 et pas de flag :
    │     │   → Créer Message (direction=outbound, is_ai=true)
    │     │   → Envoyer via connector (WhatsApp/Messenger)
    │     │   → Conversation.status = ai_handling
    │     │
    │     └─ Confidence < 0.6 OU flag OU client mécontent :
    │         → EscalationAgent
    │         → Créer Escalation
    │         → Message auto : "Un conseiller va prendre le relais"
    │         → Conversation.status = escalated
    │         → Notification équipe support
    │
    └─ 7. Log : AgentRun, AnalyticsEvent

IMPORTANT WhatsApp :
    → Session messaging : gratuit dans les 24h après dernier message client
    → Après 24h : doit utiliser un Message Template (pré-approuvé par Meta)
    → Coût par template message : ~0.05-0.15 USD selon le pays
```

---

## Flux 9 : Handoff Humain (Escalade)

```
Agent IA décide d'escalader
    │
    ├─ Raison : confidence trop basse
    ├─ Raison : client mécontent (2x sentiment négatif)
    ├─ Raison : sujet hors KB
    ├─ Raison : client demande un humain
    ├─ Raison : sujet sensible (remboursement, plainte)
    │
    ▼
EscalationAgent :
    │
    ├─ 1. Résumer la conversation pour l'humain
    │     │ → Qui est le client
    │     │ → Qu'est-ce qu'il demande
    │     │ → Ce que l'IA a tenté
    │     │ → Pourquoi l'escalade
    │
    ├─ 2. Créer Escalation en DB
    │     │ → priority basée sur le contexte
    │     │ → ai_summary + ai_context
    │
    ├─ 3. Assigner un agent humain
    │     │ → Round-robin ou least-busy
    │     │ → Ou skill-based si tags configurés
    │     │ → Si aucun agent disponible → queue
    │
    ├─ 4. Notifier :
    │     │ → Agent humain : push/email/WhatsApp interne
    │     │ → Client : "Un membre de notre équipe va prendre le relais"
    │
    └─ 5. Conversation.status = human_handling
          │ → assigned_to = human_agent_user_id
          │ → L'IA n'intervient plus sur cette conversation
          │ → L'agent humain répond via le dashboard/inbox

Agent humain résout :
    │
    ├─ Répond au client via inbox unifiée
    ├─ Peut utiliser les suggestions IA (assistant mode)
    ├─ Marque comme résolu → Conversation.status = resolved
    ├─ Escalation.status = resolved + resolution_note
    │
    └─ Feedback loop :
        → Si l'info manquait dans la KB → suggestion d'ajout
        → Si l'IA aurait pu répondre → amélioration prompt
```

---

## Flux 10 : Analytics

```
Cron quotidien (ou déclenché manuellement)
    │
    ▼
analytics_aggregation worker
    │
    ├─ 1. Pour chaque tenant actif :
    │     │
    │     ├─ Récupérer métriques depuis les plateformes :
    │     │   → Facebook : GET /{post_id}/insights
    │     │   → Instagram : GET /{media_id}/insights
    │     │   → WhatsApp : delivery/read receipts
    │     │
    │     ├─ Stocker dans analytics_events :
    │     │   → post_engagement (likes, comments, shares, reach)
    │     │   → message_metrics (sent, delivered, read, response_time)
    │     │   → support_metrics (conversations, escalations, resolution_time)
    │     │
    │     └─ Détecter anomalies :
    │         → Chute engagement > 30% → alerte
    │         → Pic de messages → alerte
    │         → Temps de réponse dégradé → alerte
    │
    └─ 2. AnalyticsAgent (optionnel, V2) :
          → Analyse les tendances
          → Propose des optimisations
          → "Vos posts du mardi à 10h performent 40% mieux"
          → "Le ton amical génère 2x plus d'engagement"

Dashboard user :
    → KPIs : posts publiés, engagement, messages traités, escalations
    → Graphiques temporels
    → Comparaison par canal
    → Top posts / pires posts
    → Métriques support : temps de réponse, satisfaction, taux résolution IA
```
