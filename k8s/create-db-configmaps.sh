#!/bin/bash
# Script to create ConfigMaps for database migrations and seed data
# This allows Kubernetes to run db-setup automatically

set -e

# Accept namespace as first argument, or use K8S_NAMESPACE env var, or default to ideaforge-ai
NAMESPACE=${1:-${K8S_NAMESPACE:-${EKS_NAMESPACE:-ideaforge-ai}}}
CONTEXT=${2:-}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "📦 Creating ConfigMaps for database setup in namespace: $NAMESPACE"

# Verify namespace exists (don't create it)
KUBECTL_CMD="kubectl"
if [ -n "$CONTEXT" ]; then
  KUBECTL_CMD="kubectl --context=$CONTEXT"
fi

if ! $KUBECTL_CMD get namespace "$NAMESPACE" &>/dev/null; then
  echo "❌ Namespace $NAMESPACE does not exist"
  echo "   Please create it first or ensure it exists in your cluster"
  exit 1
fi

# Create ConfigMap for migrations
# Include both init-db/migrations and supabase/migrations to ensure all migrations are captured
echo "🔄 Creating ConfigMap for database migrations..."
# Create a temporary directory with all migrations
TEMP_MIGRATIONS=$(mktemp -d)
trap "rm -rf $TEMP_MIGRATIONS" EXIT

# Copy all migrations from both directories
if [ -d "$PROJECT_ROOT/init-db/migrations" ]; then
  cp "$PROJECT_ROOT/init-db/migrations"/*.sql "$TEMP_MIGRATIONS/" 2>/dev/null || true
fi
if [ -d "$PROJECT_ROOT/supabase/migrations" ]; then
  cp "$PROJECT_ROOT/supabase/migrations"/*.sql "$TEMP_MIGRATIONS/" 2>/dev/null || true
fi

# Create ConfigMap from combined migrations
$KUBECTL_CMD create configmap db-migrations \
  --namespace="$NAMESPACE" \
  --from-file="$TEMP_MIGRATIONS/" \
  --dry-run=client -o yaml | $KUBECTL_CMD apply -f -

echo "   ✅ Created ConfigMap with $(ls -1 $TEMP_MIGRATIONS/*.sql 2>/dev/null | wc -l | xargs) migration files"

# Create ConfigMap for seed data
echo "🌱 Creating ConfigMap for seed data..."
$KUBECTL_CMD create configmap db-seed \
  --namespace="$NAMESPACE" \
  --from-file=seed_sample_data.sql="$PROJECT_ROOT/init-db/seed_sample_data.sql" \
  --dry-run=client -o yaml | $KUBECTL_CMD apply -f -

# Create ConfigMap for init scripts (for postgres init container)
echo "📝 Creating ConfigMap for postgres init scripts..."
$KUBECTL_CMD create configmap postgres-init-scripts \
  --namespace="$NAMESPACE" \
  --from-file="$PROJECT_ROOT/init-db/01-init-schema.sql" \
  --from-file="$PROJECT_ROOT/init-db/migrations/" \
  --from-file=seed_sample_data.sql="$PROJECT_ROOT/init-db/seed_sample_data.sql" \
  --dry-run=client -o yaml | $KUBECTL_CMD apply -f -

echo "✅ ConfigMaps created successfully!"
echo ""
echo "📋 Created ConfigMaps:"
echo "   - db-migrations (for db-setup job)"
echo "   - db-seed (for db-setup job)"
echo "   - postgres-init-scripts (for postgres init container)"

