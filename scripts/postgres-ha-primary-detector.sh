#!/bin/bash
# PostgreSQL HA Primary Detector
# This script detects the current primary node in a PostgreSQL HA cluster
# and updates the service endpoint accordingly

set -e

NAMESPACE=${EKS_NAMESPACE:-20890-ideaforge-ai-dev-58a50}
SERVICE_NAME=${POSTGRES_SERVICE:-postgres-ha}
STATEFULSET_NAME=${POSTGRES_STATEFULSET:-postgres-ha}

echo "🔍 Detecting PostgreSQL HA primary node..."

# Check each pod to find the primary
for i in 0 1 2; do
  POD_NAME="${STATEFULSET_NAME}-${i}"
  
  # Check if pod exists
  if ! kubectl get pod "$POD_NAME" -n "$NAMESPACE" &>/dev/null; then
    continue
  fi
  
  # Check if pod is ready
  if [ "$(kubectl get pod "$POD_NAME" -n "$NAMESPACE" -o jsonpath='{.status.phase}')" != "Running" ]; then
    continue
  fi
  
  # Check if this is the primary (not in recovery mode)
  if kubectl exec "$POD_NAME" -n "$NAMESPACE" -- \
    psql -U agentic_pm -d agentic_pm_db -t -c "SELECT pg_is_in_recovery();" 2>/dev/null | grep -q "f"; then
    echo "✅ Primary node detected: $POD_NAME"
    echo "$POD_NAME"
    exit 0
  fi
done

echo "❌ No primary node found"
exit 1

