#!/bin/bash
# Database restore script for EKS production
# Usage: ./scripts/restore-database.sh [namespace] [backup-file]

set -e

NAMESPACE="${1:-20890-ideaforge-ai-dev-58a50}"
BACKUP_FILE="${2}"

if [ -z "$BACKUP_FILE" ]; then
    echo "❌ Error: Backup file is required"
    echo "Usage: $0 [namespace] <backup-file>"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "⚠️  WARNING: This will restore the database from backup!"
echo "   Namespace: $NAMESPACE"
echo "   Backup file: $BACKUP_FILE"
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Restore cancelled"
    exit 1
fi

echo "🔄 Starting database restore..."

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

echo "🔄 Restoring database from backup..."

# Restore backup using psql
cat "$BACKUP_FILE" | kubectl exec -i -n "$NAMESPACE" "$POSTGRES_POD" -- \
    env PGPASSWORD="$POSTGRES_PASSWORD" \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"

if [ $? -eq 0 ]; then
    echo "✅ Restore completed successfully!"
else
    echo "❌ Error: Restore failed"
    exit 1
fi

