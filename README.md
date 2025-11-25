# IdeaForge AI

Multi-agent platform for full-stack product management. Specialized agents collaborate across ideation, research, analysis, validation, PRD authoring, and Jira execution while sharing a unified context, structured workflows, and a modern React/Vite interface.  

![Version](https://img.shields.io/badge/version-1.0.0-blue) ![Status](https://img.shields.io/badge/status-active-green)

---

## Core Capabilities

- **Multi-agent collaboration** with collaborative/parallel/sequential/debate modes
- **Agent consultation graph** orchestrated by FastAPI + CoordinatorAgent
- **Local, persistent Postgres + pgvector** (Supabase dependency removed)
- **Provider Registry** service for OpenAI, Anthropic Claude, and Google Gemini credentials
- **In-app key verification** (frontend + `/api/providers/verify`) before saving
- **RAG knowledge base** (vector search, knowledge articles, lifecycle submissions)
- **Product-lifecycle workspace** (phases, submissions, conversation history, Jira export)
- **Model Context Protocol (MCP)** servers for GitHub/Jira/Confluence integrations

For deeper diagrams, see:
- `docs/01-high-level-architecture.md`
- `docs/02-detailed-design-architecture.md`

---

## Quick Start

### Local Development (Docker Compose)

```bash
git clone <repo> ideaforge-ai
cd ideaforge-ai

# 1. Prepare env and images
cp .env.example .env
make build

# 2. Launch stack (frontend+backend+DB)
make up

# 3. Watch health
make health

# 4. Open UI
open http://localhost:3001
```

### Kubernetes Deployment (EKS)

```bash
# 1. Create namespace (REQUIRED - deployment will NOT create it)
kubectl create namespace 20890-ideaforge-ai-dev-58a50

# 2. Configure kubectl for EKS
aws eks update-kubeconfig --name ideaforge-ai --region us-east-1

# 3. Deploy with specific image tags
make eks-deploy-full \
  EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50 \
  BACKEND_IMAGE_TAG=fab20a2 \
  FRONTEND_IMAGE_TAG=e1dc1da
```

Full walkthrough: `docs/guides/quick-start.md`  
EKS Deployment Guide: `k8s/EKS_DEPLOYMENT_GUIDE.md`  
Image Tag Configuration: `k8s/EKS_IMAGE_TAGS.md`

---

## Provider Configuration & Verification

1. Navigate to **Settings** in the UI.
2. Enter one or more API keys (OpenAI, Claude, Gemini).
3. Click **Verify Key** per provider — the frontend calls `/api/providers/verify`.
4. When verified, click **Save Configuration**.  
   - The frontend stores keys locally for the browser SDKs.  
   - The backend’s Provider Registry is updated via `/api/providers/configure`, so orchestrator agents pick up the new clients immediately.

The backend health endpoint now reports which providers are active:

```bash
curl http://localhost:8000/health | jq '.services'
# { "api": true, "database": true, "openai": true, "anthropic": false, "google": false, ... }
```

---

## Project Layout

```
docs/
├── 01-high-level-architecture.md
├── 02-detailed-design-architecture.md
└── guides/
    ├── quick-start.md
    ├── quick-deploy.md
    ├── deployment-guide.md
    ├── database-migration.md
    ├── multi-agent-system.md
    ├── multi-agent-backend.md
    ├── implementation-guide.md
    └── product-lifecycle.md
backend/
├── main.py                 # FastAPI app + provider endpoints
├── services/provider_registry.py
├── agents/*                # Research, Analysis, Validation, Strategy, Ideation, PRD, Jira
└── api/database.py         # Postgres access layer (async SQLAlchemy)
frontend/src/
├── App.tsx                 # Main SPA
├── components/ProviderConfig.tsx
├── components/EnhancedChatInterface.tsx
├── lib/ai-providers.ts     # Browser-side manager for OpenAI/Claude/Gemini
└── lib/rag-system.ts
```

---

## Make Targets

| Command           | Description                                |
|-------------------|--------------------------------------------|
| `make build`      | Build all Docker images                    |
| `make up`         | Start stack in the background              |
| `make down`       | Stop and remove containers                 |
| `make restart`    | Restart every service                      |
| `make logs SERVICE=backend` | Stream logs for a service         |
| `make health`     | Hit backend health + show `docker-compose ps` |
| `make start`      | Start stopped services                     |
| `make stop`       | Stop running services                      |
| `make rebuild`    | Rebuild images without cache & restart     |

*(Updated port info: frontend runs on **3001**, backend on **8000**, Postgres on **5433**, Redis on **6379**.)*

---

## Documentation Highlights

- **Quick Start:** `docs/guides/quick-start.md`
- **Production Deployment:** `docs/guides/deployment-guide.md`
- **Database Migration (Supabase → Postgres):** `docs/guides/database-migration.md`
- **Multi-Agent Internals:** `docs/guides/multi-agent-system.md`
- **Product Lifecycle Workflows:** `docs/guides/product-lifecycle.md`

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Multi-agent call hangs | `docker-compose logs backend` (look for provider connection errors) |
| Provider still marked invalid | Use Settings → **Verify Key** again; confirm outbound network access from backend container |
| Database errors | Ensure Postgres container is up (`docker-compose ps postgres`); volume `postgres-data` is mounted |
| Port conflict | Update `docker-compose.yml` or stop conflicting local service |

---

## Contributing

1. Fork & clone.
2. Create a feature branch.
3. Run `make build && make up` locally.
4. Submit a PR with updated docs/tests where applicable.

---

Built with ❤️ using React, FastAPI, Docker, and a swarm of cooperative AI agents.
