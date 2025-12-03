#!/bin/bash
# Deploy IdeaForge AI to EKS STG Environment
# This script deploys a complete clone of DEV environment to STG

set -e

# Configuration
STG_NAMESPACE="20890-ideaforge-ai-stg-60df9"
KUBECONFIG_FILE="/tmp/kubeconfig.wUHiei"
K8S_DIR="k8s"
EKS_DIR="${K8S_DIR}/eks"
BACKEND_IMAGE_TAG="${BACKEND_IMAGE_TAG:-latest}"
FRONTEND_IMAGE_TAG="${FRONTEND_IMAGE_TAG:-latest}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying IdeaForge AI to EKS STG Environment${NC}"
echo "=========================================="
echo "Namespace: ${STG_NAMESPACE}"
echo "Kubeconfig: ${KUBECONFIG_FILE}"
echo "Backend Image Tag: ${BACKEND_IMAGE_TAG}"
echo "Frontend Image Tag: ${FRONTEND_IMAGE_TAG}"
echo ""

# Check if kubeconfig exists
if [ ! -f "${KUBECONFIG_FILE}" ]; then
    echo -e "${RED}❌ Kubeconfig file not found: ${KUBECONFIG_FILE}${NC}"
    exit 1
fi

# Set KUBECONFIG
export KUBECONFIG="${KUBECONFIG_FILE}"

# Verify cluster access
echo -e "${YELLOW}🔍 Verifying cluster access...${NC}"
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}❌ Cannot access cluster. Please check kubeconfig.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Cluster access verified${NC}"

# Create namespace if it doesn't exist
echo -e "${YELLOW}📦 Creating namespace...${NC}"
kubectl create namespace "${STG_NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
echo -e "${GREEN}✅ Namespace ready${NC}"

# Setup GHCR secret
echo -e "${YELLOW}🔐 Setting up GitHub Container Registry secret...${NC}"
if [ -z "${GITHUB_TOKEN}" ]; then
    # Try to get from env.eks.stg or .env
    if [ -f "env.eks.stg" ]; then
        GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" env.eks.stg 2>/dev/null | cut -d'=' -f2- | tr -d '"' | tr -d "'" | xargs || echo "")
    elif [ -f ".env" ]; then
        GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" .env 2>/dev/null | cut -d'=' -f2- | tr -d '"' | tr -d "'" | xargs || echo "")
    fi
fi

if [ -z "${GITHUB_TOKEN}" ]; then
    echo -e "${RED}❌ GITHUB_TOKEN not found. Please set it or add to env.eks.stg${NC}"
    exit 1
fi

kubectl delete secret ghcr-secret -n "${STG_NAMESPACE}" --ignore-not-found=true
kubectl create secret docker-registry ghcr-secret \
    --docker-server=ghcr.io \
    --docker-username=soumantrivedi \
    --docker-password="${GITHUB_TOKEN}" \
    --namespace="${STG_NAMESPACE}"
echo -e "${GREEN}✅ GHCR secret created${NC}"

# Load secrets from env.eks.stg
echo -e "${YELLOW}📦 Loading secrets from env.eks.stg...${NC}"
if [ ! -f "env.eks.stg" ]; then
    echo -e "${RED}❌ env.eks.stg file not found${NC}"
    exit 1
fi

bash "${K8S_DIR}/push-env-secret.sh" env.eks.stg "${STG_NAMESPACE}"
echo -e "${GREEN}✅ Secrets loaded${NC}"

# Create database dump ConfigMap from latest DEV dump
echo -e "${YELLOW}📦 Creating database dump ConfigMap...${NC}"
LATEST_DUMP=$(find . -name "*.sql" -type f -mmin -30 2>/dev/null | head -1)
if [ -z "${LATEST_DUMP}" ]; then
    # Fallback to most recent dump
    LATEST_DUMP=$(find . -name "*.sql" -type f -o -name "*.dump" -type f 2>/dev/null | xargs ls -t | head -1)
fi

if [ -z "${LATEST_DUMP}" ] || [ ! -f "${LATEST_DUMP}" ]; then
    echo -e "${YELLOW}⚠️  No recent database dump found. Using db_backup_20251130_022436.sql${NC}"
    LATEST_DUMP="db_backup_20251130_022436.sql"
    if [ ! -f "${LATEST_DUMP}" ]; then
        echo -e "${RED}❌ Database dump file not found: ${LATEST_DUMP}${NC}"
        echo "   Please ensure a database dump is available"
        exit 1
    fi
fi

echo "   Using dump file: ${LATEST_DUMP}"
kubectl delete configmap db-dump-stg -n "${STG_NAMESPACE}" --ignore-not-found=true
kubectl create configmap db-dump-stg \
    --from-file=db_backup.sql="${LATEST_DUMP}" \
    --namespace="${STG_NAMESPACE}"
echo -e "${GREEN}✅ Database dump ConfigMap created${NC}"

# Create database ConfigMaps (migrations, seed, init scripts)
echo -e "${YELLOW}📦 Creating database ConfigMaps...${NC}"
EKS_NAMESPACE="${STG_NAMESPACE}" bash "${K8S_DIR}/create-db-configmaps.sh"
echo -e "${GREEN}✅ Database ConfigMaps created${NC}"

# Update namespace in EKS manifests
echo -e "${YELLOW}📝 Updating namespace in EKS manifests...${NC}"
python3 "${K8S_DIR}/update-eks-namespace.py" "${EKS_DIR}" "${STG_NAMESPACE}" "${BACKEND_IMAGE_TAG}" "${FRONTEND_IMAGE_TAG}" "default-storage-class" || {
    echo -e "${YELLOW}⚠️  Python script failed, using sed fallback...${NC}"
    for file in $(find "${EKS_DIR}" -name "*.yaml" -type f ! -name "*stg*" ! -name "*dev*"); do
        if [[ "$(uname)" == "Darwin" ]]; then
            sed -i '' "s|namespace: 20890-ideaforge-ai-dev-58a50|namespace: ${STG_NAMESPACE}|g" "${file}"
            sed -i '' "s|namespace: ideaforge-ai|namespace: ${STG_NAMESPACE}|g" "${file}"
        else
            sed -i "s|namespace: 20890-ideaforge-ai-dev-58a50|namespace: ${STG_NAMESPACE}|g" "${file}"
            sed -i "s|namespace: ideaforge-ai|namespace: ${STG_NAMESPACE}|g" "${file}"
        fi
    done
}
echo -e "${GREEN}✅ Manifests updated${NC}"

# Deploy PostgreSQL HA
echo -e "${YELLOW}🗄️  Deploying PostgreSQL HA...${NC}"
kubectl apply -f "${EKS_DIR}/postgres-ha-etcd-stg.yaml"
kubectl apply -f "${EKS_DIR}/postgres-ha-statefulset-stg.yaml"
echo -e "${GREEN}✅ PostgreSQL HA deployed${NC}"

# Wait for PostgreSQL to be ready
echo -e "${YELLOW}⏳ Waiting for PostgreSQL to be ready...${NC}"
kubectl wait --for=condition=ready pod -l app=postgres-ha -n "${STG_NAMESPACE}" --timeout=600s || {
    echo -e "${YELLOW}⚠️  PostgreSQL may still be starting...${NC}"
}

# Deploy Redis
echo -e "${YELLOW}📦 Deploying Redis...${NC}"
kubectl apply -f "${EKS_DIR}/redis.yaml"
kubectl wait --for=condition=ready pod -l app=redis -n "${STG_NAMESPACE}" --timeout=120s || true
echo -e "${GREEN}✅ Redis deployed${NC}"

# Restore database from dump
echo -e "${YELLOW}📥 Restoring database from DEV dump...${NC}"
kubectl delete job db-restore-stg -n "${STG_NAMESPACE}" --ignore-not-found=true
kubectl apply -f "${EKS_DIR}/db-restore-stg-job.yaml"
echo -e "${YELLOW}⏳ Waiting for database restore to complete...${NC}"
if kubectl wait --for=condition=complete job/db-restore-stg -n "${STG_NAMESPACE}" --timeout=1800s; then
    echo -e "${GREEN}✅ Database restore completed${NC}"
    kubectl logs -n "${STG_NAMESPACE}" job/db-restore-stg --tail=20 || true
else
    echo -e "${RED}❌ Database restore failed!${NC}"
    echo "   Checking logs..."
    kubectl logs -n "${STG_NAMESPACE}" job/db-restore-stg --tail=50 || true
    exit 1
fi

# Deploy backend and frontend
echo -e "${YELLOW}🚀 Deploying backend and frontend...${NC}"
kubectl apply -f "${EKS_DIR}/backend.yaml"
kubectl apply -f "${EKS_DIR}/frontend.yaml"
echo -e "${GREEN}✅ Backend and frontend deployed${NC}"

# Deploy HPA for 150 users
echo -e "${YELLOW}📈 Deploying HPA for 150 users...${NC}"
kubectl apply -f "${EKS_DIR}/hpa-backend-stg.yaml"
kubectl apply -f "${EKS_DIR}/hpa-frontend-stg.yaml"
echo -e "${GREEN}✅ HPA deployed${NC}"

# Deploy ingress
echo -e "${YELLOW}🌐 Deploying ingress...${NC}"
kubectl apply -f "${EKS_DIR}/ingress-alb-stg.yaml"
echo -e "${GREEN}✅ Ingress deployed${NC}"

# Wait for pods to be ready
echo -e "${YELLOW}⏳ Waiting for application pods to be ready...${NC}"
kubectl wait --for=condition=ready pod -l app=backend -n "${STG_NAMESPACE}" --timeout=300s || true
kubectl wait --for=condition=ready pod -l app=frontend -n "${STG_NAMESPACE}" --timeout=300s || true

# Show status
echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo "📊 Deployment Status:"
kubectl get all -n "${STG_NAMESPACE}"
echo ""
echo "🌐 Ingress:"
kubectl get ingress -n "${STG_NAMESPACE}"
echo ""
echo "📈 HPA:"
kubectl get hpa -n "${STG_NAMESPACE}"
echo ""
INGRESS_HOST=$(kubectl get ingress -n "${STG_NAMESPACE}" -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "pending...")
echo -e "${GREEN}🌐 Frontend URL: https://ideaforge-ai-stg-60df9.cf.platform.mckinsey.cloud${NC}"
echo -e "${GREEN}🌐 Backend URL: https://api-ideaforge-ai-stg-60df9.cf.platform.mckinsey.cloud${NC}"
echo ""
echo "⚠️  Next steps:"
echo "   1. Update McKinsey SSO redirect URI to: https://ideaforge-ai-stg-60df9.cf.platform.mckinsey.cloud/api/auth/mckinsey/callback"
echo "   2. Verify ingress is accessible"
echo "   3. Test application functionality"

