# McKinsey SSO Secrets Setup Guide

This guide provides step-by-step instructions for setting up McKinsey SSO secrets in Kubernetes for IdeaForge AI.

## Overview

McKinsey SSO requires secure storage of OAuth 2.0 credentials and encryption keys. This guide covers:
- Generating encryption keys
- Creating Kubernetes secrets
- Verifying secret configuration
- Security best practices

## Prerequisites

- Kubernetes cluster access with appropriate permissions
- `kubectl` configured for your cluster
- Python 3.7+ with `cryptography` package (for key generation)
- McKinsey OAuth credentials (obtain from McKinsey Identity Platform team)

## Step 1: Obtain McKinsey Credentials

### Contact McKinsey Identity Platform Team

1. **Email**: identity-platform@mckinsey.com (verify actual contact)
2. **Provide**:
   - Application name: "IdeaForge AI"
   - Environment: Development/Staging/Production
   - Redirect URIs for each environment

### Information to Receive

McKinsey Identity Platform team will provide:
- **Client ID**: OAuth 2.0 client identifier
- **Client Secret**: OAuth 2.0 client secret
- **Registered Redirect URIs**: Confirmed callback URLs

### Example Request Email

```
Subject: OAuth 2.0 Client Registration for IdeaForge AI

Hello McKinsey Identity Platform Team,

We would like to register an OAuth 2.0 client for IdeaForge AI.

Application Details:
- Name: IdeaForge AI
- Description: Multi-agent platform for product management
- Environment: Production

Redirect URIs:
- https://ideaforge-ai-prod.cf.platform.mckinsey.cloud/auth/mckinsey/callback

Required Scopes:
- openid
- profile
- email

Please provide the Client ID and Client Secret for this application.

Thank you,
[Your Name]
```

## Step 2: Generate Encryption Key

The `MCKINSEY_TOKEN_ENCRYPTION_KEY` must be a 32-byte Fernet key for encrypting refresh tokens.

### Method 1: Python (Recommended)

```bash
# Install cryptography if not already installed
pip install cryptography

# Generate Fernet key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Example output**:
```
xK8vN2pQ5rT9wB3cF6hJ8kL0mP2sU4vX7yA9bD1eG3i=
```

### Method 2: OpenSSL

```bash
openssl rand -base64 32
```

**Important**: 
- Generate a unique key for each environment (dev, staging, prod)
- Store the key securely (password manager, secrets vault)
- Never commit the key to git

## Step 3: Create Kubernetes Secret

### Option A: Create from Literal Values (Recommended)

```bash
# Set your namespace
NAMESPACE="your-namespace"

# Create secret with actual values
kubectl create secret generic mckinsey-sso-secrets \
  --from-literal=MCKINSEY_CLIENT_ID='your-actual-client-id' \
  --from-literal=MCKINSEY_CLIENT_SECRET='your-actual-client-secret' \
  --from-literal=MCKINSEY_REDIRECT_URI='https://your-domain.com/auth/mckinsey/callback' \
  --from-literal=MCKINSEY_TOKEN_ENCRYPTION_KEY='your-actual-encryption-key' \
  --namespace=$NAMESPACE
```

### Option B: Create from Environment File

1. **Create environment file** (temporary):
   ```bash
   cat > mckinsey-sso.env << EOF
   MCKINSEY_CLIENT_ID=your-actual-client-id
   MCKINSEY_CLIENT_SECRET=your-actual-client-secret
   MCKINSEY_REDIRECT_URI=https://your-domain.com/auth/mckinsey/callback
   MCKINSEY_TOKEN_ENCRYPTION_KEY=your-actual-encryption-key
   EOF
   ```

2. **Create secret**:
   ```bash
   kubectl create secret generic mckinsey-sso-secrets \
     --from-env-file=mckinsey-sso.env \
     --namespace=$NAMESPACE
   ```

3. **Delete environment file immediately**:
   ```bash
   rm mckinsey-sso.env
   ```

### Option C: Use Template (Not Recommended for Production)

```bash
# Copy template
cp k8s/base/mckinsey-sso-secrets.yaml mckinsey-sso-secrets-actual.yaml

# Edit with actual values
vim mckinsey-sso-secrets-actual.yaml

# Apply
kubectl apply -f mckinsey-sso-secrets-actual.yaml

# Delete file immediately
rm mckinsey-sso-secrets-actual.yaml
```

## Step 4: Configure Backend to Use Secret

### Update Backend Deployment

Ensure your backend deployment references the secret:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: your-namespace
spec:
  template:
    spec:
      containers:
      - name: backend
        image: ghcr.io/your-org/ideaforge-ai-backend:latest
        envFrom:
        - secretRef:
            name: mckinsey-sso-secrets
        # ... other configuration
```

### Apply Deployment

```bash
kubectl apply -f k8s/your-environment/backend.yaml
```

## Step 5: Verify Configuration

### Check Secret Exists

```bash
kubectl get secret mckinsey-sso-secrets -n your-namespace
```

**Expected output**:
```
NAME                    TYPE     DATA   AGE
mckinsey-sso-secrets    Opaque   4      1m
```

### View Secret Keys (Not Values)

```bash
kubectl describe secret mckinsey-sso-secrets -n your-namespace
```

**Expected output**:
```
Name:         mckinsey-sso-secrets
Namespace:    your-namespace
Labels:       <none>
Annotations:  <none>

Type:  Opaque

Data
====
MCKINSEY_CLIENT_ID:                 16 bytes
MCKINSEY_CLIENT_SECRET:             36 bytes
MCKINSEY_REDIRECT_URI:              65 bytes
MCKINSEY_TOKEN_ENCRYPTION_KEY:      44 bytes
```

### Test Backend Can Access Secret

```bash
# Check environment variables in backend pod
kubectl exec -it deployment/backend -n your-namespace -- env | grep MCKINSEY
```

**Expected output**:
```
MCKINSEY_CLIENT_ID=your-client-id
MCKINSEY_CLIENT_SECRET=your-client-secret
MCKINSEY_REDIRECT_URI=https://your-domain.com/auth/mckinsey/callback
MCKINSEY_TOKEN_ENCRYPTION_KEY=your-encryption-key
```

### Test McKinsey Endpoints Reachable

```bash
# Test from backend pod
kubectl exec -it deployment/backend -n your-namespace -- \
  curl -I https://auth.mckinsey.id/auth/realms/r/protocol/openid-connect/auth
```

**Expected output**:
```
HTTP/2 200
...
```

## Step 6: Test SSO Flow

### Access Application

1. Navigate to your application URL
2. Click "Sign in with McKinsey SSO"
3. Should redirect to `auth.mckinsey.id`
4. Authenticate with McKinsey credentials
5. Should redirect back to application with active session

### Check Backend Logs

```bash
kubectl logs -f deployment/backend -n your-namespace | grep -i mckinsey
```

**Look for**:
- "McKinsey SSO authorization initiated"
- "McKinsey SSO callback received"
- "McKinsey SSO authentication successful"

## Environment-Specific Configuration

### Development (Kind)

```bash
# For local development, McKinsey SSO can be disabled
kubectl create secret generic mckinsey-sso-secrets \
  --from-literal=MCKINSEY_CLIENT_ID='' \
  --from-literal=MCKINSEY_CLIENT_SECRET='' \
  --from-literal=MCKINSEY_REDIRECT_URI='http://localhost:80/auth/mckinsey/callback' \
  --from-literal=MCKINSEY_TOKEN_ENCRYPTION_KEY='' \
  --namespace=ideaforge-ai
```

### Staging

```bash
kubectl create secret generic mckinsey-sso-secrets \
  --from-literal=MCKINSEY_CLIENT_ID='staging-client-id' \
  --from-literal=MCKINSEY_CLIENT_SECRET='staging-client-secret' \
  --from-literal=MCKINSEY_REDIRECT_URI='https://ideaforge-ai-staging.cf.platform.mckinsey.cloud/auth/mckinsey/callback' \
  --from-literal=MCKINSEY_TOKEN_ENCRYPTION_KEY='staging-encryption-key' \
  --namespace=ideaforge-ai-staging
```

### Production

```bash
kubectl create secret generic mckinsey-sso-secrets \
  --from-literal=MCKINSEY_CLIENT_ID='prod-client-id' \
  --from-literal=MCKINSEY_CLIENT_SECRET='prod-client-secret' \
  --from-literal=MCKINSEY_REDIRECT_URI='https://ideaforge-ai-prod.cf.platform.mckinsey.cloud/auth/mckinsey/callback' \
  --from-literal=MCKINSEY_TOKEN_ENCRYPTION_KEY='prod-encryption-key' \
  --namespace=ideaforge-ai-prod
```

## Advanced: External Secrets Operator

For production environments, use External Secrets Operator with AWS Secrets Manager:

### 1. Store Secrets in AWS Secrets Manager

```bash
# Store each secret
aws secretsmanager create-secret \
  --name ideaforge-ai/mckinsey-sso/client-id \
  --secret-string 'your-client-id'

aws secretsmanager create-secret \
  --name ideaforge-ai/mckinsey-sso/client-secret \
  --secret-string 'your-client-secret'

aws secretsmanager create-secret \
  --name ideaforge-ai/mckinsey-sso/redirect-uri \
  --secret-string 'https://your-domain.com/auth/mckinsey/callback'

aws secretsmanager create-secret \
  --name ideaforge-ai/mckinsey-sso/encryption-key \
  --secret-string 'your-encryption-key'
```

### 2. Create ExternalSecret Resource

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: mckinsey-sso-secrets
  namespace: ideaforge-ai
spec:
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: mckinsey-sso-secrets
    creationPolicy: Owner
  refreshInterval: 1h
  data:
    - secretKey: MCKINSEY_CLIENT_ID
      remoteRef:
        key: ideaforge-ai/mckinsey-sso/client-id
    - secretKey: MCKINSEY_CLIENT_SECRET
      remoteRef:
        key: ideaforge-ai/mckinsey-sso/client-secret
    - secretKey: MCKINSEY_REDIRECT_URI
      remoteRef:
        key: ideaforge-ai/mckinsey-sso/redirect-uri
    - secretKey: MCKINSEY_TOKEN_ENCRYPTION_KEY
      remoteRef:
        key: ideaforge-ai/mckinsey-sso/encryption-key
```

### 3. Apply ExternalSecret

```bash
kubectl apply -f external-secret.yaml
```

## Security Best Practices

### 1. Access Control

```bash
# Create role for secret access
kubectl create role mckinsey-sso-secret-reader \
  --verb=get,list \
  --resource=secrets \
  --resource-name=mckinsey-sso-secrets \
  --namespace=your-namespace

# Bind role to service account
kubectl create rolebinding backend-mckinsey-sso-access \
  --role=mckinsey-sso-secret-reader \
  --serviceaccount=your-namespace:backend \
  --namespace=your-namespace
```

### 2. Audit Logging

Enable audit logging for secret access:

```yaml
# audit-policy.yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
- level: RequestResponse
  resources:
  - group: ""
    resources: ["secrets"]
  namespaces: ["your-namespace"]
```

### 3. Secret Rotation

Rotate encryption key regularly:

```bash
# Generate new key
NEW_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Update secret
kubectl patch secret mckinsey-sso-secrets \
  -n your-namespace \
  --type='json' \
  -p="[{'op': 'replace', 'path': '/data/MCKINSEY_TOKEN_ENCRYPTION_KEY', 'value': '$(echo -n $NEW_KEY | base64)'}]"

# Restart backend to pick up new key
kubectl rollout restart deployment/backend -n your-namespace
```

**Note**: Rotating the encryption key will invalidate all existing encrypted tokens.

### 4. Monitoring

Set up alerts for:
- Failed authentication attempts
- Secret access by unauthorized users
- Unusual authentication patterns

## Troubleshooting

### Secret Not Found

```bash
# Check if secret exists
kubectl get secrets -n your-namespace | grep mckinsey

# If not found, create it
kubectl create secret generic mckinsey-sso-secrets ...
```

### Backend Can't Access Secret

```bash
# Check if secret is mounted
kubectl describe pod <backend-pod-name> -n your-namespace | grep -A 10 "Environment"

# Check service account permissions
kubectl auth can-i get secrets --as=system:serviceaccount:your-namespace:backend -n your-namespace
```

### Invalid Encryption Key

```bash
# Verify key is valid Fernet key
python -c "from cryptography.fernet import Fernet; Fernet(b'your-key-here')"

# If invalid, generate new key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Additional Resources

- [Kubernetes Secrets Documentation](https://kubernetes.io/docs/concepts/configuration/secret/)
- [External Secrets Operator](https://external-secrets.io/)
- [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/)
- [McKinsey SSO Configuration Guide](../configuration/MCKINSEY_SSO_CONFIGURATION.md)

## Support

For issues with:
- **McKinsey credentials**: Contact McKinsey Identity Platform team
- **Kubernetes secrets**: Check cluster permissions and RBAC
- **Application configuration**: Review backend logs and configuration
