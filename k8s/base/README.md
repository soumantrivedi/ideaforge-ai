# Kubernetes Base Manifests

This directory contains base Kubernetes manifests for IdeaForge AI that are shared across all environments.

## Files

### Application Deployments
- `backend.yaml` - Backend FastAPI application deployment and service
- `frontend.yaml` - Frontend React application deployment and service
- `postgres.yaml` - PostgreSQL database deployment and service
- `redis.yaml` - Redis cache deployment and service

### Configuration
- `configmap.yaml` - Application configuration (non-sensitive)
- `secrets.yaml` - Application secrets (sensitive data)
- `mckinsey-sso-secrets.yaml` - McKinsey SSO OAuth credentials (template)
- `namespace.yaml` - Namespace definition

### Jobs
- `db-setup-job.yaml` - Database initialization job

### Kustomize
- `kustomization.yaml` - Kustomize configuration for base resources

## Secrets Management

### General Secrets (`secrets.yaml`)

Contains common application secrets:
- Database passwords
- AI provider API keys (OpenAI, Anthropic, Google)
- Integration tokens (GitHub, Jira, Confluence)
- Session secrets and encryption keys

**Usage**:
```bash
# Edit with actual values
vim k8s/base/secrets.yaml

# Apply
kubectl apply -f k8s/base/secrets.yaml
```

### McKinsey SSO Secrets (`mckinsey-sso-secrets.yaml`)

Template for McKinsey SSO OAuth 2.0 credentials. **Do not apply this template directly!**

**Required values**:
- `MCKINSEY_CLIENT_ID` - OAuth client ID from McKinsey Identity Platform
- `MCKINSEY_CLIENT_SECRET` - OAuth client secret (keep secure!)
- `MCKINSEY_REDIRECT_URI` - OAuth callback URL
- `MCKINSEY_TOKEN_ENCRYPTION_KEY` - 32-byte Fernet key for token encryption

**Setup**:

1. **Generate encryption key**:
   ```bash
   python scripts/generate-mckinsey-encryption-key.py
   ```

2. **Create secret from literal values** (recommended):
   ```bash
   kubectl create secret generic mckinsey-sso-secrets \
     --from-literal=MCKINSEY_CLIENT_ID='your-client-id' \
     --from-literal=MCKINSEY_CLIENT_SECRET='your-client-secret' \
     --from-literal=MCKINSEY_REDIRECT_URI='https://your-domain.com/auth/mckinsey/callback' \
     --from-literal=MCKINSEY_TOKEN_ENCRYPTION_KEY='your-encryption-key' \
     --namespace=your-namespace
   ```

3. **Or create from environment file**:
   ```bash
   # Create temporary env file
   cat > mckinsey-sso.env << EOF
   MCKINSEY_CLIENT_ID=your-client-id
   MCKINSEY_CLIENT_SECRET=your-client-secret
   MCKINSEY_REDIRECT_URI=https://your-domain.com/auth/mckinsey/callback
   MCKINSEY_TOKEN_ENCRYPTION_KEY=your-encryption-key
   EOF
   
   # Create secret
   kubectl create secret generic mckinsey-sso-secrets \
     --from-env-file=mckinsey-sso.env \
     --namespace=your-namespace
   
   # Delete env file immediately
   rm mckinsey-sso.env
   ```

**Documentation**:
- Configuration guide: [docs/configuration/MCKINSEY_SSO_CONFIGURATION.md](../../docs/configuration/MCKINSEY_SSO_CONFIGURATION.md)
- Setup guide: [docs/deployment/MCKINSEY_SSO_SECRETS_SETUP.md](../../docs/deployment/MCKINSEY_SSO_SECRETS_SETUP.md)

## Environment-Specific Overlays

Base manifests are customized for each environment using Kustomize overlays:

- `k8s/overlays/kind/` - Local development (Kind cluster)
- `k8s/overlays/eks/` - Production (AWS EKS)

Each overlay can:
- Override image tags
- Adjust resource limits
- Configure environment-specific settings
- Add environment-specific secrets

## Usage with Kustomize

### Apply base manifests directly
```bash
kubectl apply -k k8s/base/
```

### Apply with environment overlay
```bash
# Kind (local development)
kubectl apply -k k8s/overlays/kind/

# EKS (production)
kubectl apply -k k8s/overlays/eks/
```

### Preview changes
```bash
# See what will be applied
kubectl kustomize k8s/overlays/kind/
```

## Security Best Practices

1. **Never commit secrets to git**
   - Use `.gitignore` for files containing actual secrets
   - Template files (like `mckinsey-sso-secrets.yaml`) should only contain placeholders

2. **Use Kubernetes RBAC**
   - Restrict who can read secrets
   - Use service accounts with minimal permissions

3. **Rotate secrets regularly**
   - Update passwords and encryption keys periodically
   - Use External Secrets Operator for automated rotation

4. **Use External Secrets in production**
   - Store secrets in AWS Secrets Manager
   - Use External Secrets Operator to sync to Kubernetes
   - See `mckinsey-sso-secrets.yaml` for example configuration

5. **Audit secret access**
   - Enable Kubernetes audit logging
   - Monitor for unauthorized secret access
   - Set up alerts for suspicious activity

## Troubleshooting

### Secret not found
```bash
# List secrets in namespace
kubectl get secrets -n your-namespace

# Check if secret exists
kubectl get secret mckinsey-sso-secrets -n your-namespace
```

### View secret keys (not values)
```bash
kubectl describe secret mckinsey-sso-secrets -n your-namespace
```

### Decode secret value (use with caution)
```bash
kubectl get secret mckinsey-sso-secrets -n your-namespace \
  -o jsonpath='{.data.MCKINSEY_CLIENT_ID}' | base64 -d
```

### Test if pod can access secret
```bash
kubectl exec -it deployment/backend -n your-namespace -- \
  env | grep MCKINSEY
```

## Additional Resources

- [Kubernetes Secrets Documentation](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Kustomize Documentation](https://kustomize.io/)
- [External Secrets Operator](https://external-secrets.io/)
- [IdeaForge AI Deployment Guide](../../docs/deployment/DEPLOYMENT_GUIDE.md)
