# AI Model Upgrade: ChatGPT 5.1 and Gemini 3.0 Pro

## Summary

Upgraded AI providers to use **ChatGPT 5.1** as the default primary model (instead of GPT-4o) and added support for **Gemini 3.0 Pro**. Updated agno agent initialization to prefer ChatGPT 5.1 for best reasoning, with Gemini 3.0 Pro as fallback.

## Changes Made

### 1. Backend Configuration (`backend/config.py`)
- Updated comments to clarify ChatGPT 5.1 is the default for best reasoning
- Model priority: ChatGPT 5.1 (primary) > Gemini 3.0 Pro (tertiary) > Claude 4 Sonnet (secondary)

### 2. Agno Agent Initialization
Updated all agno agent classes to prefer ChatGPT 5.1, then Gemini 3.0 Pro:
- `backend/agents/agno_base_agent.py`
- `backend/agents/agno_coordinator_agent.py`
- `backend/agents/agno_enhanced_coordinator.py`

**Priority Order:**
1. **ChatGPT 5.1** (`gpt-5.1`) - Best for reasoning, ideation, discovery
2. **Gemini 3.0 Pro** (`gemini-3.0-pro`) - Enhanced multimodal reasoning
3. **Claude 4 Sonnet** (`claude-sonnet-4-20250522`) - Advanced reasoning

### 3. ConfigMaps Updated
All Kubernetes ConfigMaps updated with consistent model configuration:
- `k8s/base/configmap.yaml`
- `k8s/kind/configmap.yaml`
- `k8s/eks/configmap.yaml`
- `k8s/configmap.yaml`

**Model Configuration:**
```yaml
AGENT_MODEL_PRIMARY: "gpt-5.1"  # ChatGPT 5.1: Best for reasoning
AGENT_MODEL_SECONDARY: "claude-sonnet-4-20250522"  # Claude 4 Sonnet
AGENT_MODEL_TERTIARY: "gemini-3.0-pro"  # Gemini 3.0 Pro
```

### 4. Environment Example (`env.example`)
Already configured with correct defaults:
```bash
AGENT_MODEL_PRIMARY=gpt-5.1
AGENT_MODEL_SECONDARY=claude-sonnet-4-20250522
AGENT_MODEL_TERTIARY=gemini-3.0-pro
```

## Testing

### Prerequisites
- Docker Desktop running
- Kind cluster created
- API keys configured (OpenAI and/or Google Gemini)

### Deploy to Kind Cluster

1. **Create/Verify Kind Cluster:**
   ```bash
   make kind-create kind-setup-ingress
   ```

2. **Build and Load Images:**
   ```bash
   make build-apps kind-load-images
   ```

3. **Deploy to Kind:**
   ```bash
   make kind-deploy
   ```

4. **Initialize Agno Agents:**
   ```bash
   make kind-agno-init
   ```

5. **Verify Agent Initialization:**
   - Check backend logs to confirm agents are using ChatGPT 5.1 or Gemini 3.0 Pro
   - Test agent functionality through API endpoints
   - Verify model selection priority (OpenAI > Gemini > Claude)

### Verification Steps

1. **Check Agent Model Selection:**
   ```bash
   kubectl logs -n ideaforge-ai -l app=backend --tail=50 | grep -i "model\|agent"
   ```

2. **Test Agent Initialization:**
   ```bash
   curl -X POST http://localhost:8000/api/agno/initialize \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json"
   ```

3. **Verify Model Priority:**
   - With OpenAI key: Should use `gpt-5.1`
   - Without OpenAI, with Gemini key: Should use `gemini-3.0-pro`
   - Without both, with Claude key: Should use `claude-sonnet-4-20250522`

## Deployment to EKS

After successful testing in kind cluster:

1. **Commit and Push:**
   ```bash
   git add .
   git commit -m "feat: Upgrade AI models to ChatGPT 5.1 and Gemini 3.0 Pro"
   git push origin <branch>
   ```

2. **Deploy to EKS:**
   ```bash
   make eks-deploy EKS_NAMESPACE=<namespace> BACKEND_IMAGE_TAG=<tag> FRONTEND_IMAGE_TAG=<tag>
   ```

3. **Initialize Agno Agents in EKS:**
   ```bash
   make eks-agno-init EKS_NAMESPACE=<namespace>
   ```

## Model Availability Notes

- **ChatGPT 5.1**: Ensure OpenAI API key has access to GPT-5.1 model
- **Gemini 3.0 Pro**: Ensure Google API key has access to Gemini 3.0 Pro model
- If models are not available, agents will fall back to next available provider

## Files Changed

- `backend/config.py`
- `backend/agents/agno_base_agent.py`
- `backend/agents/agno_coordinator_agent.py`
- `backend/agents/agno_enhanced_coordinator.py`
- `k8s/base/configmap.yaml`
- `k8s/kind/configmap.yaml`
- `k8s/eks/configmap.yaml`
- `k8s/configmap.yaml`

## Next Steps

1. ✅ Code changes complete
2. ⏳ Test in kind cluster (requires Docker)
3. ⏳ Commit and push to GitHub
4. ⏳ Deploy to EKS cluster

