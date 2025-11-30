# Production Deployment Guide

**Last Updated:** November 30, 2025  
**Status:** ✅ Ready for Production

---

## Quick Start

### For EKS Production Deployment:

```bash
# 1. Ensure .env file has all required secrets
cp env.eks.example .env
# Edit .env with production values

# 2. Configure kubectl
aws eks update-kubeconfig --name ideaforge-ai --region us-east-1

# 3. Deploy (single command)
make eks-deploy-full \
  EKS_NAMESPACE=your-namespace \
  BACKEND_IMAGE_TAG=$(git rev-parse --short HEAD) \
  FRONTEND_IMAGE_TAG=$(git rev-parse --short HEAD)
```

### For Kind Local Development:

```bash
# 1. Ensure .env file has all required secrets
cp env.kind.example .env
# Edit .env with your API keys

# 2. Deploy (single command)
make kind-deploy-full
```

---

## Secrets Management

### ✅ All Secrets Load from .env File

**Primary Method (Recommended):**
```bash
# For Kind
make kind-load-secrets

# For EKS
make eks-load-secrets EKS_NAMESPACE=your-namespace
```

**Required Secrets in .env:**
- `OPENAI_API_KEY` (or `ANTHROPIC_API_KEY` or `GOOGLE_API_KEY` - at least one)
- `POSTGRES_PASSWORD`
- `SESSION_SECRET`
- `API_KEY_ENCRYPTION_KEY`
- `V0_API_KEY` (optional)
- `LOVABLE_API_KEY` (optional)
- `GITHUB_TOKEN` (optional)
- `ATLASSIAN_EMAIL` (optional)
- `ATLASSIAN_API_TOKEN` (optional)

**Note:** The make targets automatically:
- Check for `.env` or `env.kind`/`env.eks` files
- Load all secrets to Kubernetes secret: `ideaforge-ai-secrets`
- Handle context and namespace automatically

---

## Make Targets Reference

### Build & Development
- `make build-apps` - Build backend and frontend images
- `make build-backend-base` - Build base image (if needed)

### Kind (Local Development)
- `make kind-deploy-full` - Complete setup (cluster, ingress, build, secrets, deploy)
- `make kind-load-secrets` - Load secrets from .env
- `make kind-status` - Check deployment status
- `make kind-logs` - View logs

### EKS (Production)
- `make eks-deploy-full` - Complete deployment (GHCR, namespace, secrets, deploy)
- `make eks-load-secrets EKS_NAMESPACE=ns` - Load secrets from .env
- `make eks-status EKS_NAMESPACE=ns` - Check deployment status

### Verification
- `./scripts/verify-deployment.sh` - Comprehensive verification

---

## Deprecated Scripts

The following scripts are **deprecated** and should not be used:

- ❌ `deploy.sh` - Use `make kind-deploy-full` or docker-compose
- ❌ `deploy-v2.sh` - Use `make kind-deploy-full`
- ❌ `k8s/load-secrets-to-k8s.sh` - Use `make kind-load-secrets` or `make eks-load-secrets`
- ❌ `k8s/load-secrets-from-env.sh` - Not used, can be removed
- ❌ `scripts/deploy-eks-production.sh` - Use `make eks-deploy-full`
- ❌ `scripts/deploy-to-eks.sh` - Use `make eks-deploy-full`

**Always use make targets for deployment and secret management.**

---

## Production Checklist

### Pre-Deployment

- [ ] `.env` file configured with all required secrets
- [ ] kubectl configured for target cluster
- [ ] Docker images built and tagged
- [ ] Namespace exists or will be created
- [ ] Database backup completed (if upgrading)

### Deployment

- [ ] Run `make eks-deploy-full` with correct parameters
- [ ] Verify secrets loaded: `kubectl get secret ideaforge-ai-secrets -n <namespace>`
- [ ] Check pod status: `make eks-status EKS_NAMESPACE=<namespace>`

### Post-Deployment

- [ ] Run verification: `./scripts/verify-deployment.sh`
- [ ] Check backend health endpoint
- [ ] Verify AI provider initialization
- [ ] Verify Agno agents initialization
- [ ] Test knowledge base preview

---

## Troubleshooting

### Secrets Not Loading

**Issue:** API keys not available in pods

**Solution:**
```bash
# Reload secrets
make eks-load-secrets EKS_NAMESPACE=your-namespace

# Restart backend pods
kubectl rollout restart deployment/backend -n your-namespace
```

### Agno Agents Not Initialized

**Issue:** Agno agents deferred, no providers configured

**Solution:**
1. Ensure API keys are in `.env` file
2. Load secrets: `make eks-load-secrets EKS_NAMESPACE=your-namespace`
3. Restart backend: `kubectl rollout restart deployment/backend -n your-namespace`
4. Check logs: `kubectl logs -n your-namespace -l app=backend | grep agno`

### Image Pull Errors

**Issue:** Pods can't pull images

**Solution:**
```bash
# For Kind: Load images
make kind-load-images

# For EKS: Ensure images are pushed to registry
# Images should be in GHCR: ghcr.io/soumantrivedi/ideaforge-ai/*
```

---

## Documentation

All documentation has been updated to use make targets:

- `docs/DEPLOYMENT_PRODUCTION.md` - Production deployment guide
- `docs/AGNO_INITIALIZATION_FIX.md` - Agno initialization guide
- `docs/configuration/API_KEYS_SETUP.md` - API keys setup
- `PRODUCTION_READINESS.md` - Production readiness checklist

---

## Summary

✅ **Production Ready:**
- All secrets load from `.env` via make targets
- Redundant scripts removed or deprecated
- Documentation updated to use make targets
- Verification scripts available
- Code cleanup complete

**Primary Deployment Method:** `make eks-deploy-full`  
**Primary Secret Loading:** `make eks-load-secrets`  
**All Configuration:** `.env` file

---

## Next Steps

1. ✅ Code is production-ready
2. ✅ All secrets load from .env via make targets
3. ✅ Redundant code removed
4. ✅ Documentation updated
5. 🚀 **Ready for production deployment**

