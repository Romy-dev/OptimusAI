# OptimusAI — Project Context

## What is this?
OptimusAI is a multi-tenant SaaS platform for African businesses (Burkina Faso first). It combines:
- AI-powered social media marketing (post generation, image creation, scheduling, publishing)
- AI customer support (WhatsApp, Messenger, unified inbox)
- Multi-agent orchestration (specialized agents for each task)
- Knowledge base / RAG for contextual responses

## Stack
- **Backend**: Python 3.12 + FastAPI (monolith modulaire)
- **DB**: PostgreSQL 16 + pgvector
- **ORM**: SQLAlchemy 2.0 (async) + Alembic
- **Cache/Queue**: Redis + ARQ
- **Storage**: MinIO (S3-compatible)
- **AI**: Ollama/vLLM (self-hosted) + Claude/OpenAI fallback
- **Embeddings**: sentence-transformers (BGE-M3)

## Project structure
```
app/
├── main.py          # FastAPI app factory
├── config.py        # Pydantic settings
├── core/            # Auth, DB, middleware, security, permissions
├── models/          # SQLAlchemy models
├── schemas/         # Pydantic request/response schemas
├── repositories/    # Data access (tenant-isolated)
├── services/        # Business logic
├── api/v1/          # FastAPI routes
├── agents/          # AI agents (orchestrator, copywriter, support, etc.)
├── connectors/      # Social platform adapters (Facebook, WhatsApp, etc.)
├── workers/         # Background tasks (ARQ)
├── prompts/         # Prompt templates
└── integrations/    # External service clients (LLM, embeddings, image gen)
```

## Key patterns
- **Multi-tenant isolation**: Every table has `tenant_id`, every query filters by it
- **Repository pattern**: `BaseRepository[Model]` with automatic tenant filtering
- **RBAC**: Roles (owner/admin/manager/editor/viewer/support_agent) with permission matrix
- **Agent pattern**: `BaseAgent` with retry, validation, confidence scoring, escalation
- **Connector pattern**: `BaseSocialConnector` with normalized events across platforms

## Commands
- `make dev` — start dev server
- `make up` — start Docker services
- `make test` — run tests
- `make lint` — run ruff
- `make migrate` — run Alembic migrations

## Architecture docs
See `docs/` folder:
- 01-ARCHITECTURE.md — global architecture, stack, module layout
- 02-AGENTS.md — all 10 agents with roles, inputs, outputs, escalation rules
- 03-DATA-MODEL.md — full SQLAlchemy schema (30+ tables)
- 04-BUSINESS-FLOWS.md — all user flows (onboarding → support → analytics)
- 05-API-DESIGN.md — REST API endpoints with permissions
- 06-CONNECTORS.md — social platform capabilities and limits
- 07-AI-STRATEGY.md — LLM/embedding/image model selection and routing
- 08-SECURITY.md — auth, RBAC, tenant isolation, audit, prompt security
- 09-MONETIZATION.md — plans, pricing, billing strategy
- 10-ROADMAP.md — phased roadmap and implementation plan
