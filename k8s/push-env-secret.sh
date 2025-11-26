#!/bin/bash
# Script to push .env file as Kubernetes Secret
# Usage: ./push-env-secret.sh [.env-file] [namespace] [context]
# Example: ./push-env-secret.sh .env ideaforge-ai kind-ideaforge-ai

set -e

ENV_FILE=${1:-.env}
NAMESPACE=${2:-ideaforge-ai}
CONTEXT=${3:-}

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: .env file not found: $ENV_FILE"
    echo "   Create it from .env.example: cp .env.example .env"
    exit 1
fi

echo "📦 Pushing .env file as Kubernetes Secret to namespace: $NAMESPACE"
if [ -n "$CONTEXT" ]; then
    echo "   Using kubectl context: $CONTEXT"
    KUBECTL_CMD="kubectl --context $CONTEXT"
else
    KUBECTL_CMD="kubectl"
fi

# Verify namespace exists (don't create it - namespace must pre-exist)
if ! $KUBECTL_CMD get namespace "$NAMESPACE" &>/dev/null; then
    echo "❌ Namespace $NAMESPACE does not exist"
    echo "   Please create it first or ensure it exists in your cluster"
    exit 1
fi

# Create secret from .env file
# Strip quotes from values to avoid issues with API keys
echo "🔐 Creating/updating Kubernetes secret: ideaforge-ai-secrets from $ENV_FILE"
# Create a temporary file with cleaned values (strip surrounding quotes)
TEMP_ENV=$(mktemp)
grep -v '^#' "$ENV_FILE" | grep -v '^$' | while IFS='=' read -r key value; do
    # Remove surrounding quotes if present
    cleaned_value=$(echo "$value" | sed 's/^"\(.*\)"$/\1/')
    echo "${key}=${cleaned_value}"
done > "$TEMP_ENV"

$KUBECTL_CMD create secret generic ideaforge-ai-secrets \
    --from-env-file="$TEMP_ENV" \
    --namespace="$NAMESPACE" \
    --dry-run=client -o yaml | $KUBECTL_CMD apply -f -

rm -f "$TEMP_ENV"

echo "✅ Secret created/updated successfully!"
echo ""
echo "📋 To verify:"
echo "   $KUBECTL_CMD get secret ideaforge-ai-secrets -n $NAMESPACE -o yaml"
echo ""
echo "💡 Note: This secret contains all environment variables from $ENV_FILE"
echo "   For production, consider using external secret management (AWS Secrets Manager, etc.)"

