#!/bin/bash
# Script to load secrets from .env file into Kubernetes secrets
# Usage: ./load-secrets-to-k8s.sh [.env-file] [namespace] [context]
# Example: ./load-secrets-to-k8s.sh .env ideaforge-ai kind-ideaforge-ai

set -e

ENV_FILE=${1:-.env}
NAMESPACE=${2:-ideaforge-ai}
CONTEXT=${3:-}

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: .env file not found: $ENV_FILE"
    echo "   Create it from .env.example: cp .env.example .env"
    exit 1
fi

echo "📦 Loading secrets from $ENV_FILE to Kubernetes namespace: $NAMESPACE"
if [ -n "$CONTEXT" ]; then
    echo "   Using kubectl context: $CONTEXT"
    KUBECTL_CMD="kubectl --context $CONTEXT"
else
    KUBECTL_CMD="kubectl"
fi

# Create namespace if it doesn't exist
$KUBECTL_CMD create namespace "$NAMESPACE" --dry-run=client -o yaml | $KUBECTL_CMD apply -f -

# Build secret data from .env file
SECRET_DATA=""
while IFS='=' read -r key value || [ -n "$key" ]; do
    # Skip empty lines and comments
    [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
    
    # Remove leading/trailing whitespace
    key=$(echo "$key" | xargs)
    value=$(echo "$value" | xargs)
    
    # Remove quotes if present
    value=$(echo "$value" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
    
    # Only include secret keys
    case "$key" in
        POSTGRES_PASSWORD|SESSION_SECRET|API_KEY_ENCRYPTION_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY|GOOGLE_API_KEY|V0_API_KEY|LOVABLE_API_KEY|GITHUB_TOKEN|GITHUB_ORG|ATLASSIAN_EMAIL|ATLASSIAN_API_TOKEN|JIRA_URL|JIRA_EMAIL|JIRA_API_TOKEN|CONFLUENCE_URL|CONFLUENCE_EMAIL|CONFLUENCE_API_TOKEN|OKTA_CLIENT_ID|OKTA_CLIENT_SECRET|OKTA_ISSUER)
            if [ -n "$SECRET_DATA" ]; then
                SECRET_DATA="$SECRET_DATA --from-literal=$key=$value"
            else
                SECRET_DATA="--from-literal=$key=$value"
            fi
            ;;
    esac
done < "$ENV_FILE"

if [ -z "$SECRET_DATA" ]; then
    echo "⚠️  No secret keys found in $ENV_FILE"
    echo "   Make sure your .env file contains API keys"
    exit 1
fi

# Create or update secret
echo "🔐 Creating/updating Kubernetes secret: ideaforge-ai-secrets"
$KUBECTL_CMD create secret generic ideaforge-ai-secrets \
    $SECRET_DATA \
    --namespace="$NAMESPACE" \
    --dry-run=client -o yaml | $KUBECTL_CMD apply -f -

echo "✅ Secrets loaded successfully!"
echo ""
echo "📋 Loaded secrets:"
echo "$SECRET_DATA" | tr ' ' '\n' | grep -E "^--from-literal" | sed 's/--from-literal=//' | cut -d= -f1 | sed 's/^/   - /'
echo ""
echo "💡 To verify:"
echo "   $KUBECTL_CMD get secret ideaforge-ai-secrets -n $NAMESPACE -o yaml"

