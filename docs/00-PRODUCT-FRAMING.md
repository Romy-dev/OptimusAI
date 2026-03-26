# OptimusAI — Cadrage Produit

## Le produit en 30 secondes

OptimusAI est un assistant digital pour les entreprises africaines. Il génère vos posts marketing, répond à vos clients sur WhatsApp et Facebook, apprend de vos documents, et escalade aux humains quand il doute. Tout ça depuis un seul dashboard.

---

## Modules du produit

| # | Module | Description | MVP |
|---|--------|-------------|-----|
| 1 | **Auth & Tenants** | Inscription, connexion, équipes, isolation | ✅ |
| 2 | **Brands** | Profil de marque, ton, couleurs, guidelines | ✅ |
| 3 | **Knowledge Base** | Upload docs, FAQ, catalogue → RAG | ✅ |
| 4 | **Content Generation** | Posts IA personnalisés par marque et canal | ✅ |
| 5 | **Image Generation** | Visuels de marque via Stable Diffusion | ❌ V1 |
| 6 | **Publishing** | Publication planifiée avec validation humaine | ✅ |
| 7 | **Social Connectors** | Facebook, WhatsApp (MVP), Instagram, TikTok (plus tard) | ✅ partiel |
| 8 | **Inbox Unifiée** | Tous les messages dans un seul flux | ✅ |
| 9 | **Support Client IA** | Réponses auto WhatsApp/Messenger via RAG | ✅ |
| 10 | **Comment Reply** | Réponse aux commentaires Facebook/Instagram | ✅ basique |
| 11 | **Approval Workflow** | Validation humaine obligatoire avant publication | ✅ |
| 12 | **Escalation** | Handoff IA → humain avec contexte | ✅ |
| 13 | **Analytics** | Engagement, temps de réponse, performance agents | ❌ V1 |
| 14 | **Billing** | Plans, quotas, add-ons, Mobile Money | ❌ V1 |
| 15 | **Moderation** | Filtre contenu, prompt injection, sujets sensibles | ✅ |
| 16 | **Audit** | Journal de toutes les actions | ✅ |
| 17 | **Workflows** | Automations personnalisées | ❌ V2 |
| 18 | **Video Generation** | Clips courts Reels/TikTok | ❌ V3 |
| 19 | **Voice Notes** | Transcription + réponse vocale | ❌ V3 |

---

## Matrice des plateformes

| Capacité | Facebook Pages | Instagram | WhatsApp | Messenger | TikTok |
|----------|:---:|:---:|:---:|:---:|:---:|
| **Publier texte** | ✅ | ❌ (image req.) | N/A | N/A | ❌ (vidéo req.) |
| **Publier image** | ✅ | ✅ | N/A | N/A | ⚠️ limité |
| **Publier vidéo** | ✅ | ✅ (Reel) | N/A | N/A | ✅ |
| **Scheduling** | ✅ natif API | ❌ (côté serveur) | N/A | N/A | ❌ |
| **Lire commentaires** | ✅ | ✅ | N/A | N/A | ✅ read-only |
| **Répondre commentaires** | ✅ auto | ✅ auto | N/A | N/A | ❌ impossible |
| **Recevoir messages** | via Messenger | ✅ (24h rule) | ✅ webhook | ✅ webhook | ❌ |
| **Envoyer messages** | via Messenger | ⚠️ (24h rule) | ✅ (template hors 24h) | ✅ (24h + tags) | ❌ |
| **Webhooks** | ✅ riche | ✅ basique | ✅ riche | ✅ riche | ⚠️ minimal |
| **Analytics API** | ✅ | ✅ | ⚠️ delivery only | ⚠️ | ✅ |
| **App Review requis** | ✅ | ✅ | ✅ + Business Verif | ✅ | ✅ (très strict) |
| **Coût API** | Gratuit | Gratuit | Payant/conversation | Gratuit | Gratuit |
| **Priorité MVP** | 🥇 | 🥉 read-only | 🥇 | 🥈 | ❌ post-MVP |

---

## Cas d'usage prioritaires Afrique

### Tier 1 — MVP (valeur immédiate)
1. **Boutique textile Ouaga** : génère 3 posts/semaine pour Facebook, répond aux clients WhatsApp sur les prix et la dispo
2. **Restaurant Abidjan** : publie le menu du jour automatiquement, répond aux réservations WhatsApp
3. **E-commerce Dakar** : support client IA 24/7 sur WhatsApp avec FAQ produits, escalade pour les retours

### Tier 2 — V1 (valeur étendue)
4. **Agence marketing Ouaga** : gère 15 clients depuis un dashboard, génère posts + images, planifie les campagnes
5. **ONG Burkina** : publie sur Facebook + Instagram, répond aux questions sur ses programmes
6. **Banque** : support client IA sur WhatsApp pour les FAQ (solde, agences, taux), escalade pour les réclamations

### Tier 3 — V2+ (valeur avancée)
7. **Franchise restaurants** : contenu local par point de vente, même marque
8. **Marketplace** : gestion des vendeurs, support acheteurs, analytics
9. **Influenceur** : scheduling multi-plateforme, analytics engagement

---

## Niveaux d'automatisation

| Action | Automatique | Semi-auto (IA propose, humain valide) | Manuel |
|--------|:-----------:|:-------------------------------------:|:------:|
| Génération de post | | ✅ (défaut MVP) | ✅ option |
| Publication | | ✅ (approval obligatoire MVP) | ✅ option |
| Réponse WhatsApp client | ✅ si confidence ≥ 0.6 | ✅ si confidence < 0.6 | ✅ fallback |
| Réponse commentaire FB | | ✅ (défaut : suggestion) | ✅ option |
| Réponse commentaire IG | | ✅ (défaut : suggestion) | ✅ option |
| Réponse commentaire TikTok | | | ✅ seul mode (pas d'API) |
| Génération image | | ✅ toujours review | |
| Envoi template WhatsApp | | | ✅ toujours (coût réel) |
| Escalade support | ✅ auto si règle matchée | | |
| Analytics/rapports | ✅ batch cron | | |

---

## Politique d'escalade humaine

### Escalade automatique si :
| Condition | Priorité | Action |
|-----------|----------|--------|
| `confidence_score < 0.4` | Haute | Stoppe l'IA, notifie humain |
| `confidence_score < 0.6` | Moyenne | IA propose en draft, humain décide |
| Sentiment négatif 2x consécutif | Haute | Escalade + résumé auto |
| Client dit "je veux parler à quelqu'un" | Urgente | Escalade immédiate |
| Sujet = remboursement, plainte, juridique | Urgente | Escalade obligatoire |
| Question hors knowledge base (score RAG < 0.3) | Moyenne | "Je vérifie avec mon équipe" + escalade |
| Langue non supportée | Basse | Notification humain |
| 3+ messages sans résolution | Haute | Escalade auto |

### L'humain reçoit toujours :
- Résumé de la conversation
- Ce que l'IA a tenté et pourquoi elle a échoué
- Sources KB consultées
- Score de confiance
- Historique du client (si existant)

### Le client voit :
- "Un de nos conseillers va prendre le relais, merci de votre patience"
- Temps de réponse estimé (si configuré)
- Jamais un message qui révèle que c'était une IA (sauf si le tenant le configure)

---

## Politique de publication sûre

### Règles absolues (non configurables)
1. **JAMAIS** de publication sans au moins un contrôle (IA modération OU humain)
2. **JAMAIS** de contenu NSFW, haineux, discriminatoire
3. **JAMAIS** de prix inventés ou de faux faits sur l'entreprise
4. **JAMAIS** de données personnelles de clients dans un post public
5. **JAMAIS** d'envoi de template WhatsApp sans validation humaine (coût réel)

### Règles par défaut (configurables par tenant)
| Règle | Défaut MVP | Configurable |
|-------|-----------|:------------:|
| Approval humain avant publication | **Obligatoire** | ✅ (peut être auto si confidence ≥ 0.85) |
| Modération IA avant publication | **Obligatoire** | ❌ (toujours actif) |
| Réponse auto commentaires | **Désactivé** (suggestion only) | ✅ |
| Réponse auto WhatsApp | **Activé** (confidence ≥ 0.6) | ✅ (seuil ajustable) |
| Réponse auto Messenger | **Activé** (confidence ≥ 0.6) | ✅ |
| Sujets interdits | Aucun (à configurer par tenant) | ✅ |
| Mots interdits | Liste de base (insultes FR) | ✅ (extensible) |
| Heures de publication | Pas de restriction | ✅ |
| Publication le weekend | Autorisée | ✅ |

### Pipeline de sécurité avant toute sortie

```
Contenu généré (IA ou humain)
    │
    ├─ 1. Toxicity classifier (< 50ms)
    │     ├─ BLOQUÉ si score > 0.8
    │     └─ FLAG si score > 0.5
    │
    ├─ 2. Brand compliance check (< 100ms)
    │     ├─ Mots interdits → BLOQUÉ
    │     ├─ Sujets interdits → BLOQUÉ
    │     └─ Ton incohérent → FLAG
    │
    ├─ 3. Fact check minimal
    │     ├─ Prix mentionné → vérifie dans KB → si absent → FLAG
    │     └─ Nom de produit → vérifie dans KB → si inconnu → FLAG
    │
    ├─ 4. Prompt injection check (< 10ms)
    │     └─ Pattern détecté → BLOQUÉ + log sécurité
    │
    └─ Résultat
        ├─ APPROVED → prêt pour approval humain ou publication
        ├─ FLAGGED → draft + notification review
        └─ BLOCKED → rejeté + notification admin + audit log
```

---

## Définition du MVP

### Le MVP permet de faire exactement ceci :

```
1. Une entreprise BF s'inscrit (email + mot de passe)
2. Elle crée sa marque (nom, secteur, ton, langue)
3. Elle connecte sa Page Facebook (OAuth)
4. Elle connecte son WhatsApp Business (token Cloud API)
5. Elle uploade sa FAQ (PDF ou texte)
   → Le système indexe et prépare le RAG
6. Elle demande "Crée un post pour promouvoir nos tissus wax"
   → L'agent copywriter génère un post adapté à sa marque
   → Elle voit un draft avec score de confiance
7. Elle valide (ou édite) le post
8. Elle publie sur Facebook
   → Le publisher agent envoie via l'API
   → Le post apparaît sur sa page Facebook
9. Un client WhatsApp écrit "Combien coûte le wax n°5?"
   → Le support agent cherche dans la FAQ
   → Il répond "Le wax n°5 est à 3500 FCFA le mètre"
10. Un client demande "Vous livrez à Bobo?"
    → Le support agent ne trouve pas l'info
    → Il escalade : "Je vérifie avec mon équipe"
    → L'humain est notifié avec le contexte complet
11. Le dashboard montre : posts publiés, messages traités, escalations
```

### Ce que le MVP NE fait PAS :
- ❌ Génération d'images IA (templates avec overlay en attendant)
- ❌ Publication Instagram (read-only, pas de publish)
- ❌ TikTok
- ❌ Analytics avancé (juste des compteurs basiques)
- ❌ Billing réel (trial gratuit, facturation manuelle)
- ❌ Workflows/automations personnalisées
- ❌ A/B testing
- ❌ Voice notes
- ❌ Vidéo
- ❌ White-label
- ❌ App mobile native
- ❌ Multi-langue (français uniquement)

### Métriques de succès MVP :
| Métrique | Cible |
|----------|-------|
| Temps d'onboarding | < 10 min |
| Temps de génération post | < 30 sec |
| Temps de réponse WhatsApp | < 10 sec |
| Taux de résolution IA (support) | > 60% |
| Taux d'escalade | < 40% |
| Confidence score moyen | > 0.65 |
| Uptime | > 99% |
