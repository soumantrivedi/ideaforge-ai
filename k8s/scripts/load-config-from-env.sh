#!/bin/bash
# Load environment variables from platform-specific .env files into Kubernetes ConfigMap
# Usage:
#   ./load-config-from-env.sh kind    # Load from env.kind
#   ./load-config-from-env.sh eks     # Load from env.eks
#   ./load-config-from-env.sh docker  # Load from env.docker-compose (for reference only)

set -e

PLATFORM=${1:-kind}
NAMESPACE=${2:-ideaforge-ai}

case $PLATFORM in
  kind)
    ENV_FILE="env.kind"
    NAMESPACE="ideaforge-ai"
    ;;
  eks)
    ENV_FILE="env.eks"
    NAMESPACE=${2:-20890-ideaforge-ai-dev-58a50}
    ;;
  docker|docker-compose)
    echo "⚠️  Docker Compose uses .env file directly, not ConfigMap"
    echo "   Copy env.docker-compose.example to .env and configure"
    exit 0
    ;;
  *)
    echo "❌ Unknown platform: $PLATFORM"
    echo "   Usage: $0 [kind|eks|docker] [namespace]"
    exit 1
    ;;
esac

# Check if env file exists
if [ ! -f "$ENV_FILE" ]; then
  echo "❌ Environment file not found: $ENV_FILE"
  echo "   Copy $ENV_FILE.example to $ENV_FILE and configure"
  exit 1
fi

echo "📦 Loading ConfigMap from $ENV_FILE for platform: $PLATFORM"
echo "   Namespace: $NAMESPACE"

# Extract only ConfigMap-relevant variables (non-secret)
# Filter out secrets, API keys, and other sensitive data
CONFIG_VARS=$(grep -E "^(VITE_API_URL|FRONTEND_URL|CORS_ORIGINS|POSTGRES_HOST|POSTGRES_PORT|POSTGRES_USER|POSTGRES_DB|REDIS_URL|BACKEND_PORT|LOG_LEVEL|SESSION_EXPIRES_IN|AGENT_MODEL_PRIMARY|AGENT_MODEL_SECONDARY|AGENT_MODEL_TERTIARY|K8S_NAMESPACE)=" "$ENV_FILE" | grep -v "^#" | sed 's/^/  /')

if [ -z "$CONFIG_VARS" ]; then
  echo "⚠️  No ConfigMap variables found in $ENV_FILE"
  exit 0
fi

# Create ConfigMap YAML
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: ideaforge-ai-config
  namespace: $NAMESPACE
data:
$(echo "$CONFIG_VARS" | sed 's/^/  /')
EOF

echo "✅ ConfigMap updated successfully"
echo "   View with: kubectl get configmap ideaforge-ai-config -n $NAMESPACE -o yaml"

