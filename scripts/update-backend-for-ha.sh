#!/bin/bash
# Update backend configuration for PostgreSQL HA
# This script updates the backend ConfigMap to use the HA PostgreSQL setup

set -e

NAMESPACE=${EKS_NAMESPACE:-20890-ideaforge-ai-dev-58a50}
CONFIGMAP_NAME=${CONFIGMAP_NAME:-ideaforge-ai-config}

echo "🔄 Updating backend configuration for PostgreSQL HA..."

# Get current POSTGRES_HOST
CURRENT_HOST=$(kubectl get configmap "$CONFIGMAP_NAME" -n "$NAMESPACE" -o jsonpath='{.data.POSTGRES_HOST}')

echo "Current POSTGRES_HOST: $CURRENT_HOST"

# Update to use HA service
# For writes, use the primary pod directly: postgres-ha-0.postgres-ha
# For reads, can use the service: postgres-ha (which routes to primary)
# Or use specific replicas: postgres-ha-1.postgres-ha, postgres-ha-2.postgres-ha

NEW_HOST="postgres-ha-0.postgres-ha"

if [ "$CURRENT_HOST" != "$NEW_HOST" ]; then
  echo "Updating POSTGRES_HOST to: $NEW_HOST"
  kubectl patch configmap "$CONFIGMAP_NAME" -n "$NAMESPACE" \
    --type='json' \
    -p="[{\"op\": \"replace\", \"path\": \"/data/POSTGRES_HOST\", \"value\": \"$NEW_HOST\"}]"
  
  echo "✅ Configuration updated"
  echo "⚠️  Restart backend pods to pick up new configuration:"
  echo "   kubectl rollout restart deployment backend -n $NAMESPACE"
else
  echo "✅ POSTGRES_HOST already set to HA primary: $NEW_HOST"
fi

