#!/bin/bash
# Script to update V0_API_KEY in EKS cluster
# Usage: ./scripts/update-eks-v0-key.sh [EKS_NAMESPACE] [EKS_CLUSTER_NAME] [AWS_REGION]

set -e

EKS_NAMESPACE=${1:-20890-ideaforge-ai-dev-58a50}
EKS_CLUSTER_NAME=${2:-ideaforge-ai}
AWS_REGION=${3:-us-east-1}

echo "🔐 Updating V0_API_KEY in EKS Cluster"
echo "======================================"
echo "Namespace: $EKS_NAMESPACE"
echo "Cluster: $EKS_CLUSTER_NAME"
echo "Region: $AWS_REGION"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    exit 1
fi

# Check if V0_API_KEY exists in .env
if ! grep -q "^V0_API_KEY=" .env; then
    echo "❌ Error: V0_API_KEY not found in .env file"
    exit 1
fi

V0_KEY=$(grep "^V0_API_KEY=" .env | cut -d= -f2- | tr -d '"' | tr -d "'")
echo "✅ Found V0_API_KEY in .env (length: ${#V0_KEY} chars)"
echo "   Key prefix: ${V0_KEY:0:15}..."
echo ""

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &>/dev/null; then
    echo "❌ AWS CLI not configured. Please run: aws configure"
    exit 1
fi

# Check if kubectl is configured for EKS
echo "🔍 Checking EKS cluster access..."
if ! kubectl cluster-info &>/dev/null; then
    echo "⚠️  kubectl not connected to EKS. Attempting to connect..."
    aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$AWS_REGION" || {
        echo "❌ Failed to connect to EKS cluster: $EKS_CLUSTER_NAME"
        echo "   Please verify cluster name and AWS credentials"
        exit 1
    }
    echo "✅ Connected to EKS cluster"
fi

# Verify namespace exists
if ! kubectl get namespace "$EKS_NAMESPACE" &>/dev/null; then
    echo "❌ Namespace $EKS_NAMESPACE does not exist in EKS cluster"
    exit 1
fi

echo "✅ Namespace $EKS_NAMESPACE found"
echo ""

# Update secret
echo "📦 Updating Kubernetes secret: ideaforge-ai-secrets"
bash k8s/push-env-secret.sh .env "$EKS_NAMESPACE"
echo ""

# Verify V0_API_KEY in secret
echo "🔍 Verifying V0_API_KEY in secret..."
SECRET_KEY=$(kubectl get secret ideaforge-ai-secrets -n "$EKS_NAMESPACE" -o jsonpath='{.data.V0_API_KEY}' 2>/dev/null | base64 -d || echo "")
if [ -n "$SECRET_KEY" ]; then
    if [ "$SECRET_KEY" = "$V0_KEY" ]; then
        echo "✅ V0_API_KEY matches .env file"
    else
        echo "⚠️  V0_API_KEY in secret differs from .env file"
        echo "   Secret length: ${#SECRET_KEY} chars"
        echo "   .env length: ${#V0_KEY} chars"
    fi
else
    echo "❌ V0_API_KEY not found in secret"
    exit 1
fi
echo ""

# Restart backend pods to pick up new key
echo "🔄 Restarting backend pods to pick up new V0_API_KEY..."
kubectl rollout restart deployment/backend -n "$EKS_NAMESPACE"
echo "⏳ Waiting for rollout to complete..."
kubectl rollout status deployment/backend -n "$EKS_NAMESPACE" --timeout=300s
echo ""

# Verify key in running pod
echo "🔍 Verifying V0_API_KEY in backend pod..."
BACKEND_POD=$(kubectl get pods -n "$EKS_NAMESPACE" -l app=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$BACKEND_POD" ]; then
    POD_KEY=$(kubectl exec "$BACKEND_POD" -n "$EKS_NAMESPACE" -- env 2>/dev/null | grep "^V0_API_KEY=" | cut -d= -f2 || echo "")
    if [ -n "$POD_KEY" ]; then
        if [ "$POD_KEY" = "$V0_KEY" ]; then
            echo "✅ V0_API_KEY verified in backend pod: $BACKEND_POD"
            echo "   Key matches .env file"
        else
            echo "⚠️  V0_API_KEY in pod differs from .env file"
        fi
    else
        echo "❌ V0_API_KEY not found in pod environment"
    fi
else
    echo "⚠️  Backend pod not found"
fi

echo ""
echo "✅ V0_API_KEY update complete for EKS cluster!"
echo "   Namespace: $EKS_NAMESPACE"
echo "   Cluster: $EKS_CLUSTER_NAME"

