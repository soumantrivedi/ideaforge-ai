#!/bin/bash
# Deployment Preparation Script
# Verifies all requirements before deployment

set -e

echo "=== Deployment Preparation ==="
echo ""

# 1. Check git status
echo "1. Checking git status..."
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  Uncommitted changes detected:"
    git status --short
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ No uncommitted changes"
fi
echo ""

# 2. Check remotes
echo "2. Checking git remotes..."
REMOTES=$(git remote | wc -l | tr -d ' ')
if [ "$REMOTES" -lt 1 ]; then
    echo "❌ No git remotes configured"
    exit 1
else
    echo "✅ Found $REMOTES remote(s):"
    git remote -v
fi
echo ""

# 3. Check EKS configuration
echo "3. Checking EKS configuration..."
if [ -f "env.eks" ]; then
    echo "✅ env.eks file exists"
    if grep -q "CHANGE_ME\|PLACEHOLDER\|example" env.eks 2>/dev/null; then
        echo "⚠️  env.eks contains placeholder values - please update"
    else
        echo "✅ env.eks appears configured"
    fi
else
    echo "⚠️  env.eks not found - will use .env or env.eks.example"
fi
echo ""

# 4. Check Makefile targets
echo "4. Checking Makefile targets..."
if grep -q "eks-deploy-full:" Makefile; then
    echo "✅ eks-deploy-full target exists"
else
    echo "❌ eks-deploy-full target not found"
    exit 1
fi
if grep -q "eks-load-secrets:" Makefile; then
    echo "✅ eks-load-secrets target exists"
else
    echo "❌ eks-load-secrets target not found"
    exit 1
fi
echo ""

# 5. Check kubectl
echo "5. Checking kubectl..."
if command -v kubectl &> /dev/null; then
    echo "✅ kubectl installed"
    if kubectl cluster-info &>/dev/null; then
        echo "✅ kubectl connected to cluster"
    else
        echo "⚠️  kubectl not connected to cluster (may need: aws eks update-kubeconfig)"
    fi
else
    echo "❌ kubectl not installed"
    exit 1
fi
echo ""

# 6. Check AWS CLI
echo "6. Checking AWS CLI..."
if command -v aws &> /dev/null; then
    echo "✅ AWS CLI installed"
    if aws sts get-caller-identity &>/dev/null; then
        echo "✅ AWS credentials configured"
    else
        echo "⚠️  AWS credentials not configured"
    fi
else
    echo "⚠️  AWS CLI not installed (needed for EKS)"
fi
echo ""

echo "=== Preparation Complete ==="
echo ""
echo "Next steps:"
echo "1. git push --all"
echo "2. make eks-deploy-full EKS_NAMESPACE=<namespace> BACKEND_IMAGE_TAG=<tag> FRONTEND_IMAGE_TAG=<tag>"
