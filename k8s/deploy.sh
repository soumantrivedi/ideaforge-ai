#!/bin/bash
# Deployment script for IdeaForge AI on EKS

set -e

NAMESPACE="ideaforge-ai"
K8S_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Deploying IdeaForge AI to EKS cluster..."
echo ""

# Check if kubectl is configured
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ kubectl is not configured or cluster is not accessible"
    exit 1
fi

echo "✅ kubectl is configured"
echo ""

# Verify namespace exists (do NOT create it - namespace must pre-exist)
echo "📦 Verifying namespace exists..."
if ! kubectl get namespace "${NAMESPACE}" &> /dev/null; then
    echo "❌ Namespace ${NAMESPACE} does not exist"
    echo "   Please create it first: kubectl create namespace ${NAMESPACE}"
    exit 1
fi
echo "✅ Namespace ${NAMESPACE} exists"

# Apply ConfigMap
echo "⚙️  Applying ConfigMap..."
kubectl apply -f "${K8S_DIR}/configmap.yaml"

# Check if secrets exist
if ! kubectl get secret ideaforge-ai-secrets -n "${NAMESPACE}" &> /dev/null; then
    echo "⚠️  Secrets not found. Please create secrets first:"
    echo "   kubectl apply -f ${K8S_DIR}/secrets.yaml"
    echo "   Or update secrets.yaml and apply it"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ Secrets found"
fi

# Apply secrets (if file exists and not empty)
if [ -s "${K8S_DIR}/secrets.yaml" ]; then
    echo "🔐 Applying secrets..."
    kubectl apply -f "${K8S_DIR}/secrets.yaml"
fi

# Deploy PostgreSQL
echo "🐘 Deploying PostgreSQL..."
kubectl apply -f "${K8S_DIR}/postgres.yaml"

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
kubectl wait --for=condition=ready pod -l app=postgres -n "${NAMESPACE}" --timeout=300s || true

# Deploy Redis
echo "📦 Deploying Redis..."
kubectl apply -f "${K8S_DIR}/redis.yaml"

# Wait for Redis to be ready
echo "⏳ Waiting for Redis to be ready..."
kubectl wait --for=condition=ready pod -l app=redis -n "${NAMESPACE}" --timeout=120s || true

# Deploy Backend
echo "🔧 Deploying Backend..."
kubectl apply -f "${K8S_DIR}/backend.yaml"

# Deploy Frontend
echo "🌐 Deploying Frontend..."
kubectl apply -f "${K8S_DIR}/frontend.yaml"

# Deploy Ingress
echo "🌍 Deploying Ingress..."
kubectl apply -f "${K8S_DIR}/ingress.yaml"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Checking deployment status..."
kubectl get all -n "${NAMESPACE}"

echo ""
echo "🔍 To check logs:"
echo "   kubectl logs -f deployment/backend -n ${NAMESPACE}"
echo "   kubectl logs -f deployment/frontend -n ${NAMESPACE}"
echo ""
echo "🌐 To get ingress URL:"
echo "   kubectl get ingress -n ${NAMESPACE}"
echo ""

