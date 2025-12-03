#!/bin/bash
# Backup PostgreSQL database from Kind cluster

set -e

NAMESPACE=${K8S_NAMESPACE:-ideaforge-ai}
CONTEXT=${KUBECTL_CONTEXT:-kind-ideaforge-ai}
CLUSTER_NAME=${KIND_CLUSTER_NAME:-ideaforge-ai}
BACKUP_DIR=${BACKUP_DIR:-./backups}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/ideaforge-ai-backup-${TIMESTAMP}.sql"

echo "📦 Backing up database from Kind cluster..."
echo "   Cluster: ${CLUSTER_NAME}"
echo "   Namespace: ${NAMESPACE}"
echo ""

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Get PostgreSQL pod name
POSTGRES_POD=$(kubectl get pods -n ${NAMESPACE} --context ${CONTEXT} -l app=postgres -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POSTGRES_POD" ]; then
    echo "❌ PostgreSQL pod not found in namespace ${NAMESPACE}"
    exit 1
fi

echo "   Found PostgreSQL pod: ${POSTGRES_POD}"
echo "   Creating backup: ${BACKUP_FILE}"

# Get database credentials from secret
DB_NAME=$(kubectl get secret postgres-secret -n ${NAMESPACE} --context ${CONTEXT} -o jsonpath='{.data.POSTGRES_DB}' 2>/dev/null | base64 -d || echo "agentic_pm_db")
DB_USER=$(kubectl get secret postgres-secret -n ${NAMESPACE} --context ${CONTEXT} -o jsonpath='{.data.POSTGRES_USER}' 2>/dev/null | base64 -d || echo "agentic_pm")
DB_PASSWORD=$(kubectl get secret postgres-secret -n ${NAMESPACE} --context ${CONTEXT} -o jsonpath='{.data.POSTGRES_PASSWORD}' 2>/dev/null | base64 -d || echo "devpassword")

# Create database backup using pg_dump
kubectl exec -n ${NAMESPACE} ${POSTGRES_POD} --context ${CONTEXT} -- \
    env PGPASSWORD="${DB_PASSWORD}" \
    pg_dump -U "${DB_USER}" -d "${DB_NAME}" --clean --if-exists > "${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    echo "✅ Database backup created successfully!"
    echo "   File: ${BACKUP_FILE}"
    echo "   Size: ${BACKUP_SIZE}"
    echo ""
    echo "📝 To restore this backup, run:"
    echo "   make kind-restore-database BACKUP_FILE=${BACKUP_FILE}"
else
    echo "❌ Database backup failed"
    rm -f "${BACKUP_FILE}"
    exit 1
fi
