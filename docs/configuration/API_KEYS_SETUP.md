# API Keys Configuration Guide

This guide explains how to configure API keys for IdeaForge AI across different deployment methods.

## Required API Keys

The following API keys are **REQUIRED** for the application to function:

1. **OpenAI API Key** - For GPT models
2. **Anthropic API Key** - For Claude models  
3. **Google API Key** - For Gemini models
4. **Vercel V0 API Key** - For V0 design generation
5. **GitHub PAT Token** - For GitHub integration
6. **Atlassian API Token** - For Jira & Confluence integration

## Configuration Methods

### 1. Docker Compose Deployment

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file** with your actual API keys:
   ```bash
   # Required API Keys
   OPENAI_API_KEY=sk-your-actual-key-here
   ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
   GOOGLE_API_KEY=your-actual-key-here
   V0_API_KEY=your-actual-v0-key-here
   GITHUB_TOKEN=ghp_your-actual-token-here
   GITHUB_ORG=your-github-org
   ATLASSIAN_EMAIL=your-email@example.com
   ATLASSIAN_API_TOKEN=your-actual-token-here
   ```

3. **Deploy:**
   ```bash
   make deploy-full
   ```

   The `.env` file will be automatically loaded by docker-compose.

### 2. Kind Cluster Deployment

#### Option A: Using .env file (Recommended)

1. **Create `.env` file** (same as docker-compose):
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Load secrets to Kubernetes:**
   ```bash
   # For kind cluster
   ./k8s/load-secrets-to-k8s.sh .env ideaforge-ai kind-ideaforge-ai
   ```

3. **Or use the Makefile target:**
   ```bash
   make kind-load-secrets
   ```

4. **Deploy:**
   ```bash
   make kind-deploy
   ```

#### Option B: Using Kustomize overlay

1. **Copy the example secrets file:**
   ```bash
   cp k8s/overlays/kind/secrets.yaml.example k8s/overlays/kind/secrets.yaml
   ```

2. **Edit `k8s/overlays/kind/secrets.yaml`** with your API keys:
   ```yaml
   POSTGRES_PASSWORD: "devpassword"
   OPENAI_API_KEY: "sk-your-actual-key-here"
   ANTHROPIC_API_KEY: "sk-ant-your-actual-key-here"
   GOOGLE_API_KEY: "your-actual-key-here"
   V0_API_KEY: "your-actual-v0-key-here"
   GITHUB_TOKEN: "ghp_your-actual-token-here"
   GITHUB_ORG: "your-github-org"
   ATLASSIAN_EMAIL: "your-email@example.com"
   ATLASSIAN_API_TOKEN: "your-actual-token-here"
   SESSION_SECRET: "your-secure-secret"
   API_KEY_ENCRYPTION_KEY: "your-encryption-key"
   ```

3. **Deploy:**
   ```bash
   make kind-deploy
   ```

   Kustomize will automatically merge your secrets.

### 3. EKS Cluster Deployment

#### Option A: Using .env file (Recommended)

1. **Create `.env` file:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Load secrets to Kubernetes:**
   ```bash
   # For EKS cluster (replace with your namespace)
   ./k8s/load-secrets-to-k8s.sh .env your-namespace
   ```

3. **Deploy:**
   ```bash
   make eks-deploy EKS_NAMESPACE=your-namespace
   ```

#### Option B: Using Kustomize overlay

1. **Copy the example secrets file:**
   ```bash
   cp k8s/overlays/eks/secrets.yaml.example k8s/overlays/eks/secrets.yaml
   ```

2. **Edit `k8s/overlays/eks/secrets.yaml`** with your API keys

3. **Deploy:**
   ```bash
   make eks-deploy EKS_NAMESPACE=your-namespace
   ```

## Database Setup

Database setup (migrations + seeding) runs **automatically** for all deployment methods:

- **Docker Compose**: Runs via `make db-setup` in `deploy-full` target
- **Kind Cluster**: Runs via `db-setup-job.yaml` Kubernetes Job
- **EKS Cluster**: Runs via `db-setup-job.yaml` Kubernetes Job

The database setup job:
1. Waits for PostgreSQL to be ready
2. Runs all migrations from `init-db/migrations/`
3. Seeds the database with sample data (9 products) if empty
4. Verifies the setup

## Security Best Practices

1. **Never commit `.env` files** - They are in `.gitignore`
2. **Never commit `secrets.yaml` files** - Only commit `.example` files
3. **Use external secret management** in production:
   - AWS Secrets Manager
   - HashiCorp Vault
   - External Secrets Operator
   - Sealed Secrets
4. **Rotate API keys regularly**
5. **Use different keys for different environments**

## Verifying API Keys

After deployment, verify API keys are loaded:

### Docker Compose
```bash
docker-compose exec backend env | grep -E "OPENAI_API_KEY|ANTHROPIC_API_KEY|V0_API_KEY"
```

### Kubernetes
```bash
# For kind
kubectl get secret ideaforge-ai-secrets -n ideaforge-ai --context kind-ideaforge-ai -o jsonpath='{.data}' | jq

# For EKS
kubectl get secret ideaforge-ai-secrets -n your-namespace -o jsonpath='{.data}' | jq
```

## Troubleshooting

### API keys not working

1. **Check if keys are loaded:**
   - Docker Compose: Check `.env` file exists and has correct values
   - Kubernetes: Check secret exists and has correct keys

2. **Check backend logs:**
   ```bash
   # Docker Compose
   make logs-backend
   
   # Kubernetes
   kubectl logs -n ideaforge-ai -l app=backend --tail=100
   ```

3. **Verify key format:**
   - OpenAI: Should start with `sk-`
   - Anthropic: Should start with `sk-ant-`
   - V0: Check format at https://v0.app/chat/settings/billing
   - GitHub: Should start with `ghp_` or `github_pat_`
   - Atlassian: Should be a base64-encoded token

### Database not seeded

1. **Check db-setup job status:**
   ```bash
   kubectl get job db-setup -n ideaforge-ai
   kubectl logs job/db-setup -n ideaforge-ai
   ```

2. **Manually run database setup:**
   ```bash
   # Docker Compose
   make db-setup
   
   # Kubernetes
   kubectl delete job db-setup -n ideaforge-ai --ignore-not-found=true
   kubectl apply -f k8s/db-setup-job.yaml
   ```

## Getting API Keys

- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/settings/keys
- **Google**: https://makersuite.google.com/app/apikey
- **Vercel V0**: https://v0.app/chat/settings/billing
- **GitHub**: https://github.com/settings/tokens (create PAT with `repo`, `read:org`, `read:user` scopes)
- **Atlassian**: https://id.atlassian.com/manage-profile/security/api-tokens

