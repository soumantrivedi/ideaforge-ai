#!/bin/bash
# Restore PostgreSQL database to Kind cluster

set -e

NAMESPACE=${K8S_NAMESPACE:-ideaforge-ai}
CONTEXT=${KUBECTL_CONTEXT:-kind-ideaforge-ai}
CLUSTER_NAME=${KIND_CLUSTER_NAME:-ideaforge-ai}
BACKUP_FILE=${BACKUP_FILE:-}

if [ -z "$BACKUP_FILE" ]; then
    echo "❌ BACKUP_FILE not specified"
    echo "   Usage: BACKUP_FILE=/path/to/backup.sql make kind-restore-database"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

echo "📥 Restoring database to Kind cluster..."
echo "   Cluster: ${CLUSTER_NAME}"
echo "   Namespace: ${NAMESPACE}"
echo "   Backup file: ${BACKUP_FILE}"
echo ""

# Get PostgreSQL pod name
POSTGRES_POD=$(kubectl get pods -n ${NAMESPACE} --context ${CONTEXT} -l app=postgres -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POSTGRES_POD" ]; then
    echo "❌ PostgreSQL pod not found in namespace ${NAMESPACE}"
    echo "   Make sure the cluster is running and database is deployed"
    exit 1
fi

echo "   Found PostgreSQL pod: ${POSTGRES_POD}"

# Get database credentials from secret
DB_NAME=$(kubectl get secret postgres-secret -n ${NAMESPACE} --context ${CONTEXT} -o jsonpath='{.data.POSTGRES_DB}' 2>/dev/null | base64 -d || echo "agentic_pm_db")
DB_USER=$(kubectl get secret postgres-secret -n ${NAMESPACE} --context ${CONTEXT} -o jsonpath='{.data.POSTGRES_USER}' 2>/dev/null | base64 -d || echo "agentic_pm")
DB_PASSWORD=$(kubectl get secret postgres-secret -n ${NAMESPACE} --context ${CONTEXT} -o jsonpath='{.data.POSTGRES_PASSWORD}' 2>/dev/null | base64 -d || echo "devpassword")

echo "   Restoring database: ${DB_NAME}"

# Restore database backup using psql
cat "${BACKUP_FILE}" | kubectl exec -i -n ${NAMESPACE} ${POSTGRES_POD} --context ${CONTEXT} -- \
    env PGPASSWORD="${DB_PASSWORD}" \
    psql -U "${DB_USER}" -d "${DB_NAME}"

if [ $? -eq 0 ]; then
    echo "✅ Database restored successfully!"
    echo ""
    echo "📝 Next steps:"
    echo "   1. Restart backend pods: make kind-restart-backend"
    echo "   2. Verify application: make kind-status"
else
    echo "❌ Database restore failed"
    exit 1
fi
