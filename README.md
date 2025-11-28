# IdeaForge AI

Multi-agent platform for full-stack product management. Specialized agents collaborate across ideation, research, analysis, validation, PRD authoring, and Jira execution while sharing a unified context, structured workflows, and a modern React/Vite interface.

![Version](https://img.shields.io/badge/version-1.0.0-blue) ![Status](https://img.shields.io/badge/status-active-green)

---

## 🚀 Quick Start

### Local Development (Kind Cluster)

For complete step-by-step instructions, see [Local Development Guide](docs/guides/local-development-guide.md).

```bash
# 1. Setup environment
cp env.kind.example env.kind
# Edit env.kind with your API keys

# 2. Build and deploy (single command)
make build-apps
make kind-deploy-full

# 3. Access application
# Frontend: http://localhost:8080/
# Backend API: http://localhost:8080/api/
```

### Production (EKS)

For complete step-by-step instructions, see [EKS Production Deployment Guide](docs/guides/eks-production-guide.md).

```bash
# 1. Setup environment
cp env.eks.example env.eks
# Edit env.eks with production configuration

# 2. Configure kubectl
aws eks update-kubeconfig --name ideaforge-ai --region us-east-1

# 3. Deploy
make eks-deploy-full \
  EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50 \
  BACKEND_IMAGE_TAG=$(git rev-parse --short HEAD) \
  FRONTEND_IMAGE_TAG=$(git rev-parse --short HEAD)
```

---

## 📚 Documentation

### Architecture
- [High-Level Architecture](docs/architecture/01-high-level-architecture.md)
- [Detailed Design Architecture](docs/architecture/02-detailed-design-architecture.md)
- [Complete Application Guide](docs/architecture/03-complete-application-guide.md)

### Deployment
- [Kind Cluster Deployment](docs/deployment/kind-access.md) - Local development
- [EKS Production Deployment](docs/deployment/eks.md) - Production deployment
- [EKS Ingress Setup](docs/deployment/eks-ingress.md) - Ingress configuration
- [Database Backups](docs/deployment/backups.md) - Backup and restore

### Configuration
- [Environment Variables](docs/configuration/environment-variables.md)
- [Platform-Specific Configuration](docs/configuration/PLATFORM_ENV_GUIDE.md)
- [API Keys Setup](docs/configuration/API_KEYS_SETUP.md)
- [Agno Framework Initialization](docs/configuration/AGNO_INITIALIZATION.md)
- [AI Model Configuration](docs/AI_MODEL_UPGRADE.md)

### Guides
- [Local Development Guide](docs/guides/local-development-guide.md) - Complete setup for local development
- [EKS Production Deployment Guide](docs/guides/eks-production-guide.md) - Step-by-step EKS deployment
- [Quick Start Guide](docs/guides/quick-start.md) - Get started in 10 minutes
- [Make Targets Reference](docs/guides/make-targets.md) - All available make commands
- [Multi-Agent System](docs/guides/multi-agent-system.md) - Understanding agent collaboration
- [Multi-Agent Memory](docs/guides/multi-agent-memory.md) - Agent memory and context
- [Product Lifecycle](docs/guides/product-lifecycle.md) - Product lifecycle management
- [Flexible Lifecycle and Export](docs/guides/flexible-lifecycle-and-export.md) - Lifecycle customization
- [Database Migration Guide](docs/guides/database-migration.md) - Database migrations
- [Agno Framework Migration](docs/guides/agno-migration.md) - Agno framework integration

### Troubleshooting
- [Common Issues](docs/troubleshooting/common-issues.md)
- [Cloud-Native API Fix](docs/troubleshooting/CLOUD_NATIVE_API_FIX.md)
- [Frontend API URL Fix](docs/troubleshooting/FRONTEND_API_URL_FIX.md)

---

## 🛠️ Make Targets

### Build & Development

| Target | Description |
|--------|-------------|
| `make build-apps` | Build only backend and frontend images |
| `make build-no-cache` | Build Docker images without cache |

### Database

| Target | Description |
|--------|-------------|
| `make db-backup` | Backup database from Kind cluster |
| `make db-restore BACKUP=file.sql` | Restore database to Kind cluster |
| `make db-list-backups` | List available database backups |

### Kind Cluster (Local Development)

| Target | Description |
|--------|-------------|
| `make kind-create` | Create a local kind cluster |
| `make kind-delete` | Delete the kind cluster |
| `make kind-setup-ingress` | Install NGINX ingress controller |
| `make kind-load-images` | Load Docker images into kind |
| `make kind-update-images` | Update image references in manifests |
| `make kind-deploy` | Full deployment to kind (creates cluster, installs ingress, loads images, deploys) |
| `make kind-status` | Show status of kind cluster deployment |
| `make kind-test` | Test service-to-service interactions |
| `make kind-logs` | Show logs from kind cluster |
| `make kind-port-forward` | Port forward services for local access |
| `make kind-cleanup` | Clean up deployment (keeps cluster) |
| `make kind-agno-init` | Initialize Agno framework in kind |
| `make kind-load-secrets` | Load secrets from .env file |

### EKS Cluster (Production)

| Target | Description |
|--------|-------------|
| `make eks-deploy-full` | Full EKS deployment with GHCR setup |
| `make eks-deploy` | Deploy to EKS cluster |
| `make eks-status` | Show status of EKS deployment |
| `make eks-test` | Test service-to-service interactions |
| `make eks-port-forward` | Port-forward to EKS services |
| `make eks-setup-ghcr-secret` | Setup GitHub Container Registry secret |
| `make eks-load-secrets` | Load secrets from .env file |
| `make eks-agno-init` | Initialize Agno framework in EKS |
| `make eks-update-db-configmaps` | Update database ConfigMaps |
| `make eks-add-demo-accounts` | Add demo accounts to database |

### Utilities

| Target | Description |
|--------|-------------|
| `make help` | Show all available make targets |
| `make version` | Show current version information |
| `make kind-logs` | Show logs from Kind cluster |
| `make kind-status` | Show status of Kind cluster |

---

## 🏗️ Project Structure

```
.
├── backend/              # FastAPI backend application
│   ├── agents/          # AI agent implementations
│   ├── api/             # API endpoints
│   ├── services/        # Business logic services
│   └── main.py          # FastAPI app entry point
├── src/                 # React frontend application
│   ├── components/      # React components
│   ├── lib/             # Utility libraries
│   └── App.tsx          # Main SPA component
├── k8s/                 # Kubernetes manifests
│   ├── base/            # Base Kustomize resources
│   ├── overlays/        # Platform-specific overlays
│   │   ├── kind/        # Kind cluster overlay
│   │   └── eks/         # EKS cluster overlay
│   └── scripts/         # Deployment scripts
├── docs/                # Documentation
│   ├── architecture/    # Architecture documentation
│   ├── deployment/      # Deployment guides
│   ├── configuration/   # Configuration guides
│   ├── guides/          # User guides
│   └── troubleshooting/ # Troubleshooting guides
├── env.kind.example     # Kind-specific variables (local development)
└── env.eks.example      # EKS-specific variables (production)
```

---

## 🔑 Provider Configuration

1. Navigate to **Settings** in the UI
2. Enter one or more API keys (OpenAI, Claude, Gemini)
3. Click **Verify Key** per provider
4. When verified, click **Save Configuration**

The backend health endpoint reports which providers are active:

```bash
curl http://localhost:8000/health | jq '.services'
```

---

## 🎯 Core Capabilities

- **Multi-agent collaboration** with collaborative/parallel/sequential/debate modes
- **Agent consultation graph** orchestrated by FastAPI + CoordinatorAgent
- **Local, persistent Postgres + pgvector** for vector search
- **Provider Registry** service for OpenAI, Anthropic Claude, and Google Gemini
- **In-app key verification** before saving
- **RAG knowledge base** with vector search
- **Product-lifecycle workspace** with phases, submissions, and Jira export
- **Model Context Protocol (MCP)** servers for GitHub/Jira/Confluence integrations

---

## 🐛 Troubleshooting

| Symptom | Solution |
|---------|----------|
| Multi-agent call hangs | Check backend logs: `make kind-logs` |
| Provider marked invalid | Use Settings → **Verify Key** again; check network access |
| Database errors | Check PostgreSQL pod: `kubectl get pods -n ideaforge-ai -l app=postgres` |
| Kind cluster issues | Check cluster status: `make kind-status` |
| EKS deployment fails | Verify namespace exists and kubectl is configured |

See [Troubleshooting Guide](docs/troubleshooting/common-issues.md) for more details.

---

## 🤝 Contributing

1. Fork & clone the repository
2. Create a feature branch
3. Run `make build-apps && make kind-deploy-full` locally
4. Submit a PR with updated docs/tests where applicable

---

## 📝 License

Built with ❤️ using React, FastAPI, Docker, Kubernetes, and a swarm of cooperative AI agents.
