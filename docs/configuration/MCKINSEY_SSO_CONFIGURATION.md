# McKinsey SSO Configuration Guide

This document provides comprehensive instructions for configuring McKinsey Single Sign-On (SSO) authentication for IdeaForge AI.

## Overview

IdeaForge AI supports McKinsey SSO authentication using OpenID Connect (OIDC) with OAuth 2.0 Authorization Code Flow. The implementation integrates with McKinsey's Keycloak-based identity provider at `auth.mckinsey.id`.

## Prerequisites

1. **McKinsey Client Credentials**: Obtain from McKinsey Identity Platform team
   - Client ID
   - Client Secret
   - Approved redirect URI(s)

2. **Python Environment**: For generating encryption keys
   ```bash
   pip install cryptography
   ```

## Environment Variables

### Required Variables

#### MCKINSEY_CLIENT_ID
- **Description**: OAuth 2.0 client identifier issued by McKinsey Identity Platform
- **Format**: String (typically alphanumeric)
- **Example**: `ui-v2` or `ideaforge-ai-prod`
- **How to obtain**: Request from McKinsey Identity Platform team
- **Security**: Not sensitive, but should not be publicly exposed

#### MCKINSEY_CLIENT_SECRET
- **Description**: OAuth 2.0 client secret for authenticating with McKinsey Identity Platform
- **Format**: String (secure random value)
- **Example**: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`
- **How to obtain**: Provided by McKinsey Identity Platform team with Client ID
- **Security**: **CRITICAL** - Must be kept secret, stored in Kubernetes secrets, never committed to git

#### MCKINSEY_REDIRECT_URI
- **Description**: OAuth callback URL where McKinsey Identity Platform redirects after authentication
- **Format**: Full HTTPS URL (HTTP allowed for local development)
- **Examples**:
  - Production: `https://ideaforge-ai-prod.cf.platform.mckinsey.cloud/auth/mckinsey/callback`
  - Development: `http://localhost:80/auth/mckinsey/callback`
- **Requirements**:
  - Must be registered with McKinsey Identity Platform
  - Must match exactly (including protocol, domain, path)
  - Path must be `/auth/mckinsey/callback`

#### MCKINSEY_TOKEN_ENCRYPTION_KEY
- **Description**: 32-byte Fernet encryption key for encrypting refresh tokens at rest
- **Format**: Base64-encoded 32-byte key
- **Example**: `xK8vN2pQ5rT9wB3cF6hJ8kL0mP2sU4vX7yA9bD1eG3i=`
- **How to generate**:
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
- **Security**: **CRITICAL** - Must be kept secret, stored in Kubernetes secrets, rotate regularly

### Optional Variables (with defaults)

#### MCKINSEY_AUTHORIZATION_ENDPOINT
- **Description**: McKinsey OIDC authorization endpoint
- **Default**: `https://auth.mckinsey.id/auth/realms/r/protocol/openid-connect/auth`
- **When to override**: Only if McKinsey changes their identity provider URL

#### MCKINSEY_TOKEN_ENDPOINT
- **Description**: McKinsey OIDC token endpoint
- **Default**: `https://auth.mckinsey.id/auth/realms/r/protocol/openid-connect/token`
- **When to override**: Only if McKinsey changes their identity provider URL

#### MCKINSEY_JWKS_URI
- **Description**: McKinsey JWKS (JSON Web Key Set) endpoint for token signature verification
- **Default**: `https://auth.mckinsey.id/auth/realms/r/protocol/openid-connect/certs`
- **When to override**: Only if McKinsey changes their identity provider URL

## Configuration by Environment

### Local Development (Kind)

For local development, McKinsey SSO can be disabled by leaving credentials empty:

```bash
# env.kind
MCKINSEY_CLIENT_ID=
MCKINSEY_CLIENT_SECRET=
MCKINSEY_REDIRECT_URI=http://localhost:80/auth/mckinsey/callback
MCKINSEY_TOKEN_ENCRYPTION_KEY=
```

If testing McKinsey SSO locally:
1. Request test credentials from McKinsey Identity Platform team
2. Register `http://localhost:80/auth/mckinsey/callback` as redirect URI
3. Generate encryption key:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

### Production (EKS)

Production deployments **require** valid McKinsey SSO credentials:

```bash
# env.eks
MCKINSEY_CLIENT_ID=your-production-client-id
MCKINSEY_CLIENT_SECRET=your-production-client-secret
MCKINSEY_REDIRECT_URI=https://your-domain.cf.platform.mckinsey.cloud/auth/mckinsey/callback
MCKINSEY_TOKEN_ENCRYPTION_KEY=your-production-encryption-key
```

**Important**: Store sensitive values in Kubernetes secrets (see below).

## Kubernetes Secrets Configuration

### Creating Secrets

For production deployments, store sensitive McKinsey SSO credentials in Kubernetes secrets:

```bash
# Create secret from literal values
kubectl create secret generic mckinsey-sso-secrets \
  --from-literal=MCKINSEY_CLIENT_ID='your-client-id' \
  --from-literal=MCKINSEY_CLIENT_SECRET='your-client-secret' \
  --from-literal=MCKINSEY_TOKEN_ENCRYPTION_KEY='your-encryption-key' \
  --namespace=your-namespace

# Or create from file
kubectl create secret generic mckinsey-sso-secrets \
  --from-env-file=mckinsey-sso.env \
  --namespace=your-namespace
```

### Using Secrets in Deployments

Reference secrets in your backend deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  template:
    spec:
      containers:
      - name: backend
        envFrom:
        - secretRef:
            name: mckinsey-sso-secrets
```

See `k8s/base/mckinsey-sso-secrets.yaml` for a complete template.

## Generating Encryption Keys

The `MCKINSEY_TOKEN_ENCRYPTION_KEY` must be a valid Fernet key (32-byte base64-encoded):

### Method 1: Python Script
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Method 2: OpenSSL
```bash
openssl rand -base64 32
```

**Important**: 
- Generate a unique key for each environment
- Store securely in password manager or secrets management system
- Rotate keys periodically (requires re-encryption of stored tokens)

## Obtaining McKinsey Credentials

### Step 1: Request Access
Contact McKinsey Identity Platform team:
- Email: identity-platform@mckinsey.com (example - verify actual contact)
- Provide: Application name, environment (dev/prod), redirect URIs

### Step 2: Register Application
McKinsey Identity Platform team will:
1. Create OAuth 2.0 client in Keycloak
2. Provide Client ID and Client Secret
3. Register your redirect URI(s)
4. Configure appropriate scopes (openid, profile, email)

### Step 3: Configure Application
Add credentials to your environment configuration:
- For Kubernetes: Create secrets (see above)
- For local development: Add to `.env` file (never commit)

## Verification

### Test Configuration
```bash
# Check if variables are loaded
kubectl exec -it deployment/backend -n your-namespace -- env | grep MCKINSEY

# Test backend can reach McKinsey endpoints
kubectl exec -it deployment/backend -n your-namespace -- \
  curl -I https://auth.mckinsey.id/auth/realms/r/protocol/openid-connect/auth
```

### Test SSO Flow
1. Navigate to login page
2. Click "Sign in with McKinsey SSO"
3. Should redirect to `auth.mckinsey.id`
4. After authentication, should redirect back to application

## Troubleshooting

### Common Issues

#### "Invalid redirect_uri"
- **Cause**: Redirect URI doesn't match registered value
- **Solution**: Verify `MCKINSEY_REDIRECT_URI` exactly matches registered URI (including protocol, domain, path)

#### "Invalid client credentials"
- **Cause**: Client ID or Client Secret is incorrect
- **Solution**: Verify credentials with McKinsey Identity Platform team

#### "Token decryption failed"
- **Cause**: Invalid or changed encryption key
- **Solution**: Verify `MCKINSEY_TOKEN_ENCRYPTION_KEY` is valid Fernet key, regenerate if needed

#### "JWKS fetch failed"
- **Cause**: Cannot reach McKinsey JWKS endpoint
- **Solution**: Check network connectivity, verify `MCKINSEY_JWKS_URI` is correct

### Debug Logging

Enable debug logging for OAuth flow:

```bash
# Set in environment
LOG_LEVEL=debug

# Check logs
kubectl logs -f deployment/backend -n your-namespace | grep -i mckinsey
```

## Security Best Practices

1. **Never commit secrets**: Use `.gitignore` for `.env` files
2. **Use Kubernetes secrets**: Store sensitive values in secrets, not ConfigMaps
3. **Rotate keys regularly**: Update `MCKINSEY_TOKEN_ENCRYPTION_KEY` periodically
4. **Use HTTPS in production**: Never use HTTP for redirect URIs in production
5. **Limit secret access**: Use RBAC to restrict who can read secrets
6. **Monitor authentication**: Set up alerts for failed authentication attempts
7. **Audit access**: Review who has access to McKinsey SSO credentials

## Migration from Password Authentication

McKinsey SSO runs alongside existing password authentication:

1. **Dual authentication**: Users can use either method
2. **Gradual rollout**: Enable McKinsey SSO without disabling passwords
3. **User migration**: Users automatically linked by email address
4. **Fallback**: Password authentication remains available if SSO fails

## Additional Resources

- [McKinsey Identity Platform Documentation](https://identity.mckinsey.com/docs) (internal)
- [OpenID Connect Specification](https://openid.net/specs/openid-connect-core-1_0.html)
- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
- [Fernet Encryption](https://cryptography.io/en/latest/fernet/)

## Support

For issues with:
- **McKinsey credentials**: Contact McKinsey Identity Platform team
- **Application configuration**: Check this documentation and backend logs
- **Technical issues**: Review troubleshooting section above
