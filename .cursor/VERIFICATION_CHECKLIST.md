# IdeaForge AI - Complete Verification Checklist

**Purpose:** This checklist serves as a system prompt for Cursor AI agents to automatically verify all requirements after any code changes or deployments.

**Usage:** 
- Read this file before making changes
- Verify all items after changes
- Update status as items are verified
- Use this as a reference for comprehensive testing

---

## Core Requirements (1-16)

### ✅ Requirement 1: ChatGPT 5.1 as Default AI Provider
**Verification Steps:**
1. Check ConfigMap: `kubectl get configmap ideaforge-ai-config -n ideaforge-ai --context kind-ideaforge-ai -o jsonpath='{.data.AGENT_MODEL_PRIMARY}'`
2. Should return: `gpt-5.1`
3. Verify code uses: `settings.agent_model_primary` from ConfigMap
4. Check priority order in `backend/agents/agno_base_agent.py`: ChatGPT 5.1 → Gemini 3.0 Pro → Claude 4 Sonnet

**Files to Check:**
- `k8s/kind/configmap.yaml` (line 23)
- `backend/agents/agno_base_agent.py` (line 121)
- `backend/config.py` (agent_model_primary)

---

### ✅ Requirement 2: AI Providers Supported (ChatGPT, Gemini-3, Claude)
**Verification Steps:**
1. Check provider registry: `kubectl exec -n ideaforge-ai --context kind-ideaforge-ai deployment/backend -- python -c "from backend.services.provider_registry import provider_registry; print(provider_registry.get_configured_providers())"`
2. Should return: `['openai', 'claude', 'gemini']`
3. Verify all three models configured: `gpt-5.1`, `gemini-3.0-pro`, `claude-sonnet-4-20250522`

**Files to Check:**
- `backend/services/provider_registry.py`
- `backend/agents/agno_base_agent.py`
- `k8s/kind/configmap.yaml` (AGENT_MODEL_*)

---

### ✅ Requirement 3: Agno Framework Initialized by Default
**Verification Steps:**
1. Check startup logs: `kubectl logs -n ideaforge-ai --context kind-ideaforge-ai deployment/backend --tail=30 | grep "agno.*initialized"`
2. Should show: `"agno_orchestrator_initialized"`, `"agno_enabled": true`
3. Verify all agents initialized: Summary, Scoring, GitHub MCP, Atlassian MCP, V0, Lovable, RAG, Export, Research, Analysis, Ideation, PRD Authoring, Validation
4. Check initialization in `backend/main.py:198`

**Files to Check:**
- `backend/main.py` (lifespan function)
- `backend/agents/agno_orchestrator.py`
- Startup logs

---

### ✅ Requirement 4: User API Keys in Settings Page
**Verification Steps:**
1. Access Settings page in frontend
2. Verify `ProviderConfig` component exists
3. Test saving API keys via `/api/users/api-keys` endpoint
4. Verify user keys override environment keys

**Files to Check:**
- `src/components/EnhancedSettings.tsx`
- `src/components/ProviderConfig.tsx`
- `backend/api/api_keys.py`

---

### ✅ Requirement 5: Service Names (Not localhost)
**Verification Steps:**
1. Check backend.yaml: `grep -E "postgres|redis|backend" k8s/kind/backend.yaml`
2. Should use: `postgres:5432`, `redis:6379`, `backend:8000`
3. Verify no hardcoded `localhost` in k8s manifests
4. Check ConfigMap: `DATABASE_URL`, `REDIS_URL` use service names

**Files to Check:**
- `k8s/kind/backend.yaml`
- `k8s/kind/frontend.yaml`
- `k8s/kind/configmap.yaml`

---

### ✅ Requirement 6: External URLs Accessible
**Verification Steps:**
1. Test frontend: `curl http://localhost:80/`
2. Test backend API: `curl http://localhost:80/api/health`
3. Test Swagger docs: `curl http://localhost:80/api/docs`
4. All should return 200 OK

**Commands:**
```bash
curl http://localhost:80/health
curl http://localhost:80/api/docs
curl http://localhost:80/
```

---

### ✅ Requirement 7: No CORS Errors
**Verification Steps:**
1. Check ConfigMap: `FRONTEND_URL`, `CORS_ORIGINS` configured
2. Test CORS preflight: `curl -X OPTIONS http://localhost:80/api/auth/login -H "Origin: http://localhost:80" -H "Access-Control-Request-Method: POST" -v`
3. Should return `access-control-allow-origin` header
4. Verify runtime API URL injection working (no build-time dependencies)

**Files to Check:**
- `backend/main.py` (CORS middleware)
- `k8s/kind/configmap.yaml` (CORS_ORIGINS)
- `scripts/docker-entrypoint.sh` (runtime injection)

---

### ✅ Requirement 8: Internal Service Communication
**Verification Steps:**
1. Check all services use Kubernetes DNS names
2. Verify backend connects to `postgres:5432`, `redis:6379`
3. Verify frontend proxies to `backend:8000`
4. No external URLs for service-to-service communication

**Files to Check:**
- `k8s/kind/backend.yaml`
- `k8s/kind/frontend.yaml`
- `k8s/kind/configmap.yaml`

---

### ✅ Requirement 9: ConfigMap-Driven Configuration
**Verification Steps:**
1. Verify `VITE_API_URL` injected at runtime via `docker-entrypoint.sh`
2. Check all config in ConfigMap: `VITE_API_URL`, `FRONTEND_URL`, `CORS_ORIGINS`, model configs
3. Test: Change ConfigMap value, restart pod, verify change applied (no image rebuild)

**Files to Check:**
- `scripts/docker-entrypoint.sh`
- `k8s/kind/configmap.yaml`
- `k8s/kind/frontend.yaml` (env from ConfigMap)

---

### ✅ Requirement 10: Phases Not Locked/Opinionated
**Verification Steps:**
1. Check phases loaded from database: `SELECT * FROM product_lifecycle_phases`
2. Verify no hardcoded phase list in code
3. Test: Add new phase via database, verify it appears in UI

**Files to Check:**
- `backend/api/database.py` (get_lifecycle_phases endpoint)
- Database schema

---

### ✅ Requirement 11: Agno Multi-Agent PRD with ICAgile
**Verification Steps:**
1. Verify PRD Authoring Agent follows ICAgile standards
2. Check Export Agent generates ICAgile-compliant PRDs
3. Verify templates include: BCS, ICAgile, AIPMM, Pragmatic Institute

**Files to Check:**
- `backend/agents/agno_prd_authoring_agent.py`
- `backend/agents/agno_export_agent.py`

---

### ✅ Requirement 12: RAG Agent with Vector DB
**Verification Steps:**
1. Verify RAG agent uses pgvector for semantic search
2. Test Confluence, GitHub, local uploads
3. Verify product-scoped storage: `knowledge_articles.product_id`
4. Check vector DB: pgvector container (PostgreSQL extension)

**Files to Check:**
- `backend/agents/rag_agent.py`
- `backend/api/documents.py`
- `backend/agents/agno_base_agent.py` (RAG setup)

---

### ✅ Requirement 13: PRD Export with Validation & Confluence Publish
**Verification Steps:**
1. Test export agent validates missing phases
2. Test export as Markdown and PDF
3. Test Confluence publish: `/api/export/publish-to-confluence`
4. Verify phase validation prompts user if phases missing

**Files to Check:**
- `backend/agents/agno_export_agent.py`
- `backend/api/export.py`

---

### ✅ Requirement 14: v0/Lovable Prompts in Design Section
**Verification Steps:**
1. Check design phase has `v0_lovable_prompts` field
2. Verify Agno agents: `AgnoV0Agent`, `AgnoLovableAgent`
3. Test prompts can be refined with multi-agent help
4. Verify prompts stored in chatbot/form data

**Files to Check:**
- `src/components/PhaseFormModal.tsx`
- `backend/agents/agno_v0_agent.py`
- `backend/agents/agno_lovable_agent.py`

---

### ✅ Requirement 15: Chatbot Memory Retention
**Verification Steps:**
1. Verify conversation history table: `conversation_history`
2. Check product-scoped: `conversation_history.product_id`
3. Test API endpoints: `/api/conversations/history`, `/api/db/conversation-history`
4. Verify history loaded automatically in multi-agent context

**Files to Check:**
- `backend/api/conversations.py`
- `backend/agents/agno_orchestrator.py`
- Database schema

---

### ✅ Requirement 16: Git Commit, Push, Rebuild, Deploy
**Verification Steps:**
1. Verify all changes committed
2. Check pushed to all remotes: `git remote -v` and verify both `origin` and `mck-internal`
3. Verify images built: Check Makefile output or Docker images
4. Verify images loaded into cluster and deployments updated

**Commands:**
```bash
git status
git log --oneline -5
git remote -v
docker images | grep ideaforge-ai
kubectl get deployments -n ideaforge-ai --context kind-ideaforge-ai
```

---

## Agent Integration Requirements (17-19)

### ✅ Requirement 17: Atlassian Agent Multi-Agent Integration
**Verification Steps:**
1. Check `AgnoAtlassianAgent` in `AgnoCoordinatorAgent`: `grep "atlassian_mcp" backend/agents/agno_coordinator_agent.py`
2. Check `AgnoAtlassianAgent` in `AgnoEnhancedCoordinator`: `grep "atlassian_mcp" backend/agents/agno_enhanced_coordinator.py`
3. Verify automatic selection when Confluence/Jira keywords detected
4. Test coordination with Export and RAG agents
5. Verify all coordination modes work: collaborative, sequential, parallel, enhanced_collaborative

**Files to Check:**
- `backend/agents/agno_coordinator_agent.py`
- `backend/agents/agno_enhanced_coordinator.py`
- `backend/agents/agno_atlassian_agent.py`
- `docs/verification/ATLASSIAN_AGENT_INTEGRATION.md`

**Test Command:**
```bash
# Verify integration
grep -r "atlassian_mcp" backend/agents/agno_coordinator_agent.py backend/agents/agno_enhanced_coordinator.py
```

---

### ✅ Requirement 18: Complete Documentation and Mermaid Diagrams
**Verification Steps:**
1. Check architecture diagrams exist: `ls docs/architecture/*.md`
2. Verify agent hierarchy diagram shows all agents including Atlassian
3. Check multi-agent coordination modes diagram exists
4. Verify agent workflow sequence diagrams
5. Check product lifecycle phase diagrams
6. Verify documentation structure file exists

**Files to Check:**
- `docs/architecture/03-complete-application-guide.md` (mermaid diagrams)
- `docs/architecture/02-detailed-design-architecture.md` (architecture diagrams)
- `docs/DOCUMENTATION_STRUCTURE.md`

**Required Diagrams:**
- Agent hierarchy (all agents including Atlassian)
- Multi-agent coordination modes (collaborative, sequential, parallel, enhanced)
- Agent workflow sequence
- Product lifecycle phases
- Data flow diagrams

---

### ✅ Requirement 19: Agent List and Multi-Agent Orchestration Documentation
**Verification Steps:**
1. Verify complete agent list documented with capabilities
2. Check multi-agent orchestration flow documented with mermaid diagrams
3. Verify coordination modes explained (collaborative, sequential, parallel, enhanced_collaborative)
4. Check agent-to-agent communication patterns documented
5. Verify integration examples provided
6. Check Atlassian agent integration documented

**Files to Check:**
- `docs/architecture/03-complete-application-guide.md`
- `docs/guides/multi-agent-system.md`
- `docs/verification/ATLASSIAN_AGENT_INTEGRATION.md`

**Required Documentation:**
- Complete list of all agents with roles and capabilities
- Multi-agent orchestration flow diagram
- Coordination mode explanations
- Agent-to-agent communication patterns
- Integration examples (Atlassian + Export + RAG)
- Workflow examples

---

## Complete Agent List (Must Be Documented)

### Core Product Management Agents
1. **AgnoResearchAgent** - Market Research & Competitive Analysis
2. **AgnoAnalysisAgent** - Strategic Analysis & SWOT
3. **AgnoIdeationAgent** - Creative Brainstorming
4. **AgnoValidationAgent** - Idea Validation
5. **AgnoPRDAuthoringAgent** - PRD Generation (ICAgile standards)
6. **AgnoSummaryAgent** - Multi-Session Summarization
7. **AgnoScoringAgent** - Product Idea Scoring
8. **AgnoExportAgent** - PRD Export & Document Generation

### Design Agents
9. **AgnoV0Agent** - V0 Design Generation
10. **AgnoLovableAgent** - Lovable AI Integration

### Integration Agents
11. **AgnoGitHubAgent** - GitHub Integration (MCP)
12. **AgnoAtlassianAgent** - Jira & Confluence Integration (MCP)

### Knowledge Agent
13. **RAGAgent** - Knowledge Retrieval & Synthesis (Vector DB)

---

## Multi-Agent Orchestration Modes (Must Be Documented)

### 1. Collaborative Mode
- Primary agent consults supporting agents
- Supporting agents provide insights
- Primary agent synthesizes all inputs

### 2. Sequential Mode
- Agents work one after another
- Each agent builds on previous output
- Chain of agent processing

### 3. Parallel Mode
- All agents process simultaneously
- Independent responses combined
- Multiple perspectives at once

### 4. Enhanced Collaborative Mode
- Heavy context sharing
- RAG agent always included
- Full conversation history context
- Product-scoped knowledge retrieval

---

## Verification Workflow

### After Code Changes:
1. ✅ Run all verification commands
2. ✅ Check all files listed for each requirement
3. ✅ Test functionality manually if needed
4. ✅ Update status in this checklist
5. ✅ Update `docs/verification/REQUIREMENTS_VERIFICATION.md`

### After Deployment:
1. ✅ Verify all services running
2. ✅ Check logs for errors
3. ✅ Test external URLs
4. ✅ Verify ConfigMap values
5. ✅ Test multi-agent coordination
6. ✅ Verify documentation updated

### Before Committing:
1. ✅ All requirements verified
2. ✅ Documentation updated
3. ✅ Mermaid diagrams updated
4. ✅ Agent list documented
5. ✅ Integration examples provided

---

## Quick Verification Script

```bash
#!/bin/bash
# Quick verification script

echo "=== Requirement 1: Default Model ==="
kubectl get configmap ideaforge-ai-config -n ideaforge-ai --context kind-ideaforge-ai -o jsonpath='{.data.AGENT_MODEL_PRIMARY}' && echo ""

echo "=== Requirement 2: Providers ==="
kubectl exec -n ideaforge-ai --context kind-ideaforge-ai deployment/backend -- python -c "from backend.services.provider_registry import provider_registry; print(provider_registry.get_configured_providers())" 2>&1

echo "=== Requirement 3: Agno Initialization ==="
kubectl logs -n ideaforge-ai --context kind-ideaforge-ai deployment/backend --tail=10 | grep -E "agno.*initialized|startup_orchestrator_status" | tail -3

echo "=== Requirement 6: External URLs ==="
curl -s http://localhost:80/health | jq -r '.status' 2>/dev/null || echo "Check manually"

echo "=== Requirement 17: Atlassian Agent ==="
grep -c "atlassian_mcp" backend/agents/agno_coordinator_agent.py backend/agents/agno_enhanced_coordinator.py 2>/dev/null | head -2

echo "=== Requirement 18: Documentation ==="
ls -1 docs/architecture/*.md docs/verification/*.md 2>/dev/null | wc -l

echo "=== Requirement 19: Agent Documentation ==="
grep -c "AgnoAtlassianAgent\|atlassian_mcp" docs/architecture/*.md docs/guides/*.md 2>/dev/null | grep -v ":0" | wc -l
```

---

## Notes

- This checklist should be read before any major changes
- All items should be verified after deployments
- Status should be updated as items are verified
- Documentation should be kept in sync with code changes
- Mermaid diagrams should reflect current architecture

---

**Last Updated:** 2025-11-26  
**Maintained By:** Development Team  
**Review Frequency:** After every major change or deployment

