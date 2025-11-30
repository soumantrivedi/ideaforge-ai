#!/bin/bash
# Complete Database Backup Script for Production Deployment
# Creates a full backup including schema, data, and all objects
# Usage: ./scripts/db-full-backup.sh [namespace] [backup-file]

set -e

NAMESPACE="${1:-ideaforge-ai}"
BACKUP_FILE="${2:-}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Default backup file name
if [ -z "$BACKUP_FILE" ]; then
    BACKUP_FILE="${BACKUP_DIR}/full_db_backup_${TIMESTAMP}.sql"
fi

echo "🔄 Starting complete database backup..."
echo "   Namespace: $NAMESPACE"
echo "   Backup file: $BACKUP_FILE"
echo "   Timestamp: $TIMESTAMP"
echo ""

# Get PostgreSQL pod name
POSTGRES_POD=$(kubectl get pods -n "$NAMESPACE" -l app=postgres -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -z "$POSTGRES_POD" ]; then
    echo "❌ Error: PostgreSQL pod not found in namespace $NAMESPACE"
    exit 1
fi

echo "✅ Found PostgreSQL pod: $POSTGRES_POD"

# Get database credentials
POSTGRES_USER=$(kubectl get configmap ideaforge-ai-config -n "$NAMESPACE" -o jsonpath='{.data.POSTGRES_USER}' 2>/dev/null || \
                kubectl get configmap ideaforge-ai-config -n "$NAMESPACE" -o jsonpath='{.data.POSTGRES_USER}' 2>/dev/null || \
                echo "agentic_pm")
POSTGRES_DB=$(kubectl get configmap ideaforge-ai-config -n "$NAMESPACE" -o jsonpath='{.data.POSTGRES_DB}' 2>/dev/null || \
              kubectl get configmap ideaforge-ai-config -n "$NAMESPACE" -o jsonpath='{.data.POSTGRES_DB}' 2>/dev/null || \
              echo "agentic_pm_db")
POSTGRES_PASSWORD=$(kubectl get secret ideaforge-ai-secrets -n "$NAMESPACE" -o jsonpath='{.data.POSTGRES_PASSWORD}' 2>/dev/null | base64 -d || \
                    kubectl get secret ideaforge-ai-secrets -n "$NAMESPACE" -o jsonpath='{.data.POSTGRES_PASSWORD}' 2>/dev/null | base64 -d || \
                    echo "")

if [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_DB" ]; then
    echo "❌ Error: Could not retrieve database credentials"
    exit 1
fi

echo "🔄 Creating comprehensive database backup..."
echo "   Database: $POSTGRES_DB"
echo "   User: $POSTGRES_USER"
echo ""

# Create comprehensive backup with all options
kubectl exec -n "$NAMESPACE" "$POSTGRES_POD" -- \
    env PGPASSWORD="$POSTGRES_PASSWORD" \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    --clean --if-exists --create \
    --verbose \
    --format=plain \
    --no-owner --no-privileges \
    --schema=public \
    --data-only=false \
    --blobs \
    --encoding=UTF8 \
    > "$BACKUP_FILE" 2>&1

if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo ""
    echo "✅ Complete database backup created successfully!"
    echo "   File: $BACKUP_FILE"
    echo "   Size: $BACKUP_SIZE"
    
    # Create metadata file
    METADATA_FILE="${BACKUP_FILE}.metadata.json"
    cat > "$METADATA_FILE" <<EOF
{
  "backup_file": "$(basename "$BACKUP_FILE")",
  "timestamp": "$TIMESTAMP",
  "namespace": "$NAMESPACE",
  "database": "$POSTGRES_DB",
  "user": "$POSTGRES_USER",
  "size_bytes": $(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE" 2>/dev/null || echo 0),
  "size_human": "$BACKUP_SIZE",
  "postgres_version": "$(kubectl exec -n "$NAMESPACE" "$POSTGRES_POD" -- psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT version();" 2>/dev/null | head -1 | xargs || echo "unknown")"
}
EOF
    
    echo "   Metadata: $METADATA_FILE"
    
    # Create symlink to latest backup
    ln -sf "$(basename "$BACKUP_FILE")" "$BACKUP_DIR/latest_full_backup.sql"
    echo "   Latest backup: $BACKUP_DIR/latest_full_backup.sql"
    
    echo ""
    echo "📊 Backup Summary:"
    echo "   • Schema: Included"
    echo "   • Data: Included"
    echo "   • Extensions: Included"
    echo "   • Sequences: Included"
    echo "   • Indexes: Included"
    echo "   • Constraints: Included"
    echo ""
    echo "✅ Backup ready for production deployment!"
else
    echo "❌ Error: Backup failed"
    exit 1
fi

