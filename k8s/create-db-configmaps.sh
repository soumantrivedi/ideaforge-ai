#!/bin/bash
# Script to create ConfigMaps for database migrations and seed data
# This allows Kubernetes to run db-setup automatically

set -e

NAMESPACE=${K8S_NAMESPACE:-ideaforge-ai}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "📦 Creating ConfigMaps for database setup in namespace: $NAMESPACE"

# Create namespace if it doesn't exist
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

# Create ConfigMap for migrations
echo "🔄 Creating ConfigMap for database migrations..."
kubectl create configmap db-migrations \
  --namespace="$NAMESPACE" \
  --from-file="$PROJECT_ROOT/init-db/migrations/" \
  --dry-run=client -o yaml | kubectl apply -f -

# Create ConfigMap for seed data
echo "🌱 Creating ConfigMap for seed data..."
kubectl create configmap db-seed \
  --namespace="$NAMESPACE" \
  --from-file=seed_sample_data.sql="$PROJECT_ROOT/init-db/seed_sample_data.sql" \
  --dry-run=client -o yaml | kubectl apply -f -

# Create ConfigMap for init scripts (for postgres init container)
echo "📝 Creating ConfigMap for postgres init scripts..."
kubectl create configmap postgres-init-scripts \
  --namespace="$NAMESPACE" \
  --from-file="$PROJECT_ROOT/init-db/01-init-schema.sql" \
  --from-file="$PROJECT_ROOT/init-db/migrations/" \
  --from-file=seed_sample_data.sql="$PROJECT_ROOT/init-db/seed_sample_data.sql" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "✅ ConfigMaps created successfully!"
echo ""
echo "📋 Created ConfigMaps:"
echo "   - db-migrations (for db-setup job)"
echo "   - db-seed (for db-setup job)"
echo "   - postgres-init-scripts (for postgres init container)"

