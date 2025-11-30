#!/bin/bash
# Comprehensive Database Backup and Restore Script
# Supports both Kind and EKS clusters
# Usage: 
#   Backup: ./scripts/db-backup-restore.sh backup [namespace] [backup-file]
#   Restore: ./scripts/db-backup-restore.sh restore [namespace] [backup-file]

set -e

ACTION="${1:-backup}"
NAMESPACE="${2:-ideaforge-ai}"
BACKUP_FILE="${3:-}"

# Detect cluster type
if kubectl config current-context | grep -q "kind"; then
    CLUSTER_TYPE="kind"
    DEFAULT_NAMESPACE="ideaforge-ai"
else
    CLUSTER_TYPE="eks"
    DEFAULT_NAMESPACE="${NAMESPACE:-20890-ideaforge-ai-dev-58a50}"
fi

NAMESPACE="${NAMESPACE:-$DEFAULT_NAMESPACE}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

backup_database() {
    local backup_file="${BACKUP_FILE:-${BACKUP_DIR}/db_backup_$(date +%Y%m%d_%H%M%S).sql}"
    
    echo "🔄 Starting database backup..."
    echo "   Cluster: $CLUSTER_TYPE"
    echo "   Namespace: $NAMESPACE"
    echo "   Backup file: $backup_file"
    
    # Get PostgreSQL pod name
    POSTGRES_POD=$(kubectl get pods -n "$NAMESPACE" -l app=postgres -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    
    if [ -z "$POSTGRES_POD" ]; then
        echo "❌ Error: PostgreSQL pod not found in namespace $NAMESPACE"
        exit 1
    fi
    
    echo "✅ Found PostgreSQL pod: $POSTGRES_POD"
    
    # Get database credentials from ConfigMap and Secrets
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
    
    echo "🔄 Creating database backup..."
    echo "   Database: $POSTGRES_DB"
    echo "   User: $POSTGRES_USER"
    
    # Create backup using pg_dump with comprehensive options
    kubectl exec -n "$NAMESPACE" "$POSTGRES_POD" -- \
        env PGPASSWORD="$POSTGRES_PASSWORD" \
        pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        --clean --if-exists --create \
        --verbose \
        --format=plain \
        --no-owner --no-privileges \
        > "$backup_file" 2>&1
    
    if [ $? -eq 0 ]; then
        BACKUP_SIZE=$(du -h "$backup_file" | cut -f1)
        echo "✅ Backup completed successfully!"
        echo "   File: $backup_file"
        echo "   Size: $BACKUP_SIZE"
        
        # Create a symlink to latest backup
        ln -sf "$(basename "$backup_file")" "$BACKUP_DIR/latest_backup.sql"
        echo "   Latest backup: $BACKUP_DIR/latest_backup.sql"
    else
        echo "❌ Error: Backup failed"
        exit 1
    fi
}

restore_database() {
    local backup_file="${BACKUP_FILE:-${BACKUP_DIR}/latest_backup.sql}"
    
    if [ ! -f "$backup_file" ]; then
        echo "❌ Error: Backup file not found: $backup_file"
        exit 1
    fi
    
    echo "🔄 Starting database restore..."
    echo "   Cluster: $CLUSTER_TYPE"
    echo "   Namespace: $NAMESPACE"
    echo "   Backup file: $backup_file"
    echo ""
    echo "⚠️  WARNING: This will replace all existing data in the database!"
    read -p "Are you sure you want to continue? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        echo "❌ Restore cancelled"
        exit 1
    fi
    
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
    
    echo "🔄 Restoring database from backup..."
    
    # Copy backup file to pod
    kubectl cp "$backup_file" "$NAMESPACE/$POSTGRES_POD:/tmp/restore.sql"
    
    # Restore database
    kubectl exec -n "$NAMESPACE" "$POSTGRES_POD" -- \
        env PGPASSWORD="$POSTGRES_PASSWORD" \
        psql -U "$POSTGRES_USER" -f /tmp/restore.sql
    
    # Clean up
    kubectl exec -n "$NAMESPACE" "$POSTGRES_POD" -- rm -f /tmp/restore.sql
    
    if [ $? -eq 0 ]; then
        echo "✅ Database restore completed successfully!"
    else
        echo "❌ Error: Restore failed"
        exit 1
    fi
}

case "$ACTION" in
    backup)
        backup_database
        ;;
    restore)
        restore_database
        ;;
    *)
        echo "Usage: $0 {backup|restore} [namespace] [backup-file]"
        exit 1
        ;;
esac

