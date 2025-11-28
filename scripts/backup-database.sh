#!/bin/bash
# Database backup script for EKS production
# Usage: ./scripts/backup-database.sh [namespace] [backup-file]

set -e

NAMESPACE="${1:-20890-ideaforge-ai-dev-58a50}"
BACKUP_FILE="${2:-backup-$(date +%Y%m%d-%H%M%S).sql}"

echo "🔄 Starting database backup..."
echo "   Namespace: $NAMESPACE"
echo "   Backup file: $BACKUP_FILE"

# Get PostgreSQL pod name
POSTGRES_POD=$(kubectl get pods -n "$NAMESPACE" -l app=postgres -o jsonpath='{.items[0].metadata.name}')

if [ -z "$POSTGRES_POD" ]; then
    echo "❌ Error: PostgreSQL pod not found in namespace $NAMESPACE"
    exit 1
fi

echo "✅ Found PostgreSQL pod: $POSTGRES_POD"

# Get database credentials from ConfigMap and Secrets
POSTGRES_USER=$(kubectl get configmap ideaforge-ai-config -n "$NAMESPACE" -o jsonpath='{.data.POSTGRES_USER}')
POSTGRES_DB=$(kubectl get configmap ideaforge-ai-config -n "$NAMESPACE" -o jsonpath='{.data.POSTGRES_DB}')
POSTGRES_PASSWORD=$(kubectl get secret ideaforge-ai-secrets -n "$NAMESPACE" -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 -d)

if [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_DB" ]; then
    echo "❌ Error: Could not retrieve database credentials"
    exit 1
fi

echo "🔄 Creating database backup..."

# Create backup using pg_dump
kubectl exec -n "$NAMESPACE" "$POSTGRES_POD" -- \
    env PGPASSWORD="$POSTGRES_PASSWORD" \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    --clean --if-exists --create \
    > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✅ Backup completed successfully!"
    echo "   File: $BACKUP_FILE"
    echo "   Size: $BACKUP_SIZE"
else
    echo "❌ Error: Backup failed"
    exit 1
fi

