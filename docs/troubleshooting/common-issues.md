# Common Issues and Troubleshooting

This guide covers common issues and their solutions for IdeaForge AI deployments.

## Table of Contents

- [Multi-Agent Issues](#multi-agent-issues)
- [Database Issues](#database-issues)
- [Provider Configuration](#provider-configuration)
- [Deployment Issues](#deployment-issues)
- [Network and Connectivity](#network-and-connectivity)

## Multi-Agent Issues

### Agent Calls Hang or Timeout

**Symptoms:**
- Multi-agent API calls hang indefinitely
- Frontend shows loading state for extended periods
- Backend logs show no activity

**Solutions:**
1. Check backend logs for provider connection errors:
   ```bash
   make logs SERVICE=backend
   # or for kind
   make kind-logs
   ```

2. Verify API keys are configured and valid:
   - Go to Settings in the UI
   - Click "Verify Key" for each provider
   - Ensure keys have proper permissions

3. Check network connectivity from backend container:
   ```bash
   make shell-backend
   curl https://api.openai.com/v1/models
   ```

4. Verify Agno framework is initialized:
   ```bash
   make agno-init  # for docker-compose
   make kind-agno-init  # for kind
   ```

### Provider Still Marked Invalid After Configuration

**Solutions:**
1. Use Settings → **Verify Key** again
2. Confirm outbound network access from backend container
3. Check API key format (no extra spaces, correct prefix)
4. Verify API key has sufficient credits/permissions
5. Check backend logs for specific error messages

## Database Issues

### Database Connection Errors

**Symptoms:**
- Backend logs show "connection refused" or "authentication failed"
- Health check shows database as unhealthy

**Solutions:**
1. Ensure Postgres container is running:
   ```bash
   make ps
   # or for kind
   make kind-status
   ```

2. Verify database credentials in `.env` or ConfigMap:
   ```bash
   # Check docker-compose
   docker-compose exec postgres psql -U agentic_pm -d agentic_pm_db
   
   # Check kind
   kubectl exec -n ideaforge-ai -it deployment/postgres -- psql -U agentic_pm -d agentic_pm_db
   ```

3. Check database volume is mounted correctly:
   ```bash
   docker volume ls | grep postgres
   ```

4. Restart database service:
   ```bash
   make restart SERVICE=postgres
   ```

### Migration Errors

**Symptoms:**
- Database migrations fail
- Schema errors in logs

**Solutions:**
1. Check migration files are up to date
2. Verify database is accessible
3. Run migrations manually:
   ```bash
   make db-migrate
   ```

4. For kind/eks, check db-setup job:
   ```bash
   kubectl logs -n ideaforge-ai job/db-setup
   ```

## Provider Configuration

### API Keys Not Saving

**Solutions:**
1. Verify frontend can reach backend API
2. Check browser console for errors
3. Verify CORS configuration allows frontend origin
4. Check backend logs for API errors

### Provider Verification Fails

**Solutions:**
1. Verify API key format:
   - OpenAI: `sk-...`
   - Anthropic: `sk-ant-...`
   - Google: `AIza...`

2. Check API key has proper permissions/scopes
3. Verify network connectivity from backend
4. Check rate limits haven't been exceeded

## Deployment Issues

### Kind Cluster Deployment Fails

**Symptoms:**
- `make kind-deploy` fails
- Pods stuck in pending/crashloopbackoff

**Solutions:**
1. Check cluster exists:
   ```bash
   kind get clusters
   ```

2. Verify images are loaded:
   ```bash
   make kind-load-images
   ```

3. Check pod status:
   ```bash
   make kind-status
   ```

4. View pod logs:
   ```bash
   make kind-logs
   ```

5. Check ingress controller:
   ```bash
   kubectl get pods -n ingress-nginx
   ```

### EKS Deployment Fails

**Symptoms:**
- Deployment hangs or fails
- Image pull errors

**Solutions:**
1. Verify namespace exists:
   ```bash
   kubectl get namespace <namespace>
   ```

2. Check GHCR secret is configured:
   ```bash
   make eks-setup-ghcr-secret EKS_NAMESPACE=<namespace>
   ```

3. Verify image tags exist in registry
4. Check kubectl context:
   ```bash
   kubectl config current-context
   ```

5. View deployment status:
   ```bash
   make eks-status EKS_NAMESPACE=<namespace>
   ```

### Port Conflicts

**Symptoms:**
- Services fail to start
- "Port already in use" errors

**Solutions:**
1. Find process using port:
   ```bash
   lsof -i :8000  # backend
   lsof -i :3001  # frontend
   ```

2. Stop conflicting service or update port in `docker-compose.yml`
3. For kind, check ingress port mapping

## Network and Connectivity

### Frontend Can't Reach Backend API

**Symptoms:**
- `ERR_CONNECTION_REFUSED` errors
- API calls fail

**Solutions:**

**For Docker Compose:**
- Verify `VITE_API_URL=http://localhost:8000` in `.env`
- Check backend is running: `make ps`
- Verify backend health: `curl http://localhost:8000/health`

**For Kind/EKS:**
- Use relative paths (`VITE_API_URL=""`) for cloud-native proxying
- Verify nginx proxy configuration
- Check ingress is configured correctly
- See [Cloud-Native API Fix](CLOUD_NATIVE_API_FIX.md) for details

### CORS Errors

**Symptoms:**
- Browser console shows CORS errors
- API calls blocked by browser

**Solutions:**
1. Verify `FRONTEND_URL` matches actual frontend URL
2. Check `CORS_ORIGINS` includes frontend origin
3. Restart backend after ConfigMap changes
4. For kind/eks, ensure ingress URL is in CORS_ORIGINS

## Getting Help

If you encounter issues not covered here:

1. Check logs: `make logs SERVICE=<service>` or `make kind-logs`
2. Review relevant documentation in `docs/`
3. Check GitHub issues
4. Verify environment configuration matches platform requirements

