# Testing and Deployment Checklist

**Date:** December 1, 2025  
**Status:** 🔄 In Progress

---

## Pre-Deployment Testing

### 1. Agent Testing ✅
- [ ] Research Agent
- [ ] Analysis Agent
- [ ] PRD Authoring Agent
- [ ] Ideation Agent
- [ ] Summary Agent
- [ ] Scoring Agent
- [ ] Strategy Agent
- [ ] Validation Agent
- [ ] Export Agent
- [ ] GitHub MCP Agent
- [ ] Atlassian MCP Agent
- [ ] V0 Agent
- [ ] Lovable Agent
- [ ] RAG Agent

### 2. API Endpoint Testing ✅
- [ ] `/api/health` - Health check
- [ ] `/api/auth/login` - Authentication
- [ ] `/api/auth/me` - User info
- [ ] `/api/products` - Product management
- [ ] `/api/multi-agent/chat` - Multi-agent chat
- [ ] `/api/agent-stats` - Agent statistics
- [ ] `/api/metrics` - Metrics
- [ ] `/api/db/*` - Database endpoints
- [ ] `/api/documents/*` - Document upload
- [ ] `/api/phase-form-help` - Phase form help
- [ ] `/api/agno/*` - Agno framework endpoints
- [ ] `/api/integrations/*` - Integration endpoints
- [ ] `/api/export/*` - Export endpoints
- [ ] `/api/design/*` - Design endpoints

### 3. Frontend Feature Testing ✅
- [ ] Login/Logout
- [ ] Product Dashboard
- [ ] Product Lifecycle Wizard
- [ ] Chat Interface
- [ ] Agent Dashboard
- [ ] Knowledge Base Manager
- [ ] Document Uploader
- [ ] Settings/Integrations
- [ ] API Key Configuration
- [ ] Export PRD
- [ ] Design Mockup Gallery

### 4. Workflow Testing ✅
- [ ] Single Agent Workflow
- [ ] Multi-Agent Collaborative Workflow
- [ ] Multi-Agent Sequential Workflow
- [ ] Multi-Agent Parallel Workflow
- [ ] Product Lifecycle Workflow
- [ ] Document Upload Workflow
- [ ] Confluence Integration Workflow
- [ ] GitHub Integration Workflow
- [ ] V0 Design Workflow
- [ ] Lovable Design Workflow

### 5. Integration Testing ✅
- [ ] Atlassian/Confluence Integration
- [ ] GitHub Integration
- [ ] V0 Integration
- [ ] Lovable Integration
- [ ] AI Provider Integration (OpenAI, Claude, Gemini)

---

## Pre-Deployment Verification

### Code Quality ✅
- [ ] No linter errors
- [ ] No build errors
- [ ] All tests pass
- [ ] Code review complete

### Configuration ✅
- [ ] Environment variables configured
- [ ] Secrets properly loaded
- [ ] Database migrations applied
- [ ] CORS configured correctly
- [ ] API keys configured

### Documentation ✅
- [ ] README updated
- [ ] Deployment guide updated
- [ ] API documentation updated
- [ ] Configuration guide updated

---

## Deployment Steps

### 1. Git Push to All Remotes
```bash
# Verify all changes are committed
git status

# Push to all remotes
git push --all
```

### 2. EKS Deployment Preparation
```bash
# 1. Configure kubectl for EKS
aws eks update-kubeconfig --name ideaforge-ai --region us-east-1

# 2. Verify namespace exists
kubectl get namespace <EKS_NAMESPACE>

# 3. Load secrets
make eks-load-secrets EKS_NAMESPACE=<namespace>

# 4. Build and push images
make eks-build-images \
  BACKEND_IMAGE_TAG=$(git rev-parse --short HEAD) \
  FRONTEND_IMAGE_TAG=$(git rev-parse --short HEAD)

# 5. Deploy
make eks-deploy-full \
  EKS_NAMESPACE=<namespace> \
  BACKEND_IMAGE_TAG=$(git rev-parse --short HEAD) \
  FRONTEND_IMAGE_TAG=$(git rev-parse --short HEAD)
```

### 3. Post-Deployment Verification
- [ ] All pods running
- [ ] Services accessible
- [ ] Ingress configured
- [ ] Database connected
- [ ] Secrets loaded
- [ ] Health checks passing
- [ ] Frontend accessible
- [ ] API endpoints working

---

## Rollback Plan

If deployment fails:
1. Rollback to previous image version
2. Check pod logs for errors
3. Verify secrets and configuration
4. Check database connectivity
5. Verify ingress configuration

---

## Notes

- All tests should pass before deployment
- Verify all agents are accessible
- Check all API endpoints
- Test all frontend features
- Verify all workflows work correctly
- Ensure no v2 features are missing

