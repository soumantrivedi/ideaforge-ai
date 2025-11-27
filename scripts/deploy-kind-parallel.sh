#!/bin/bash
# Kind Cluster Deployment (Parallel with EKS)
# Usage: ./scripts/deploy-kind-parallel.sh

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

IMAGE_TAG="28a283d"
K8S_NAMESPACE="ideaforge-ai"
KIND_CLUSTER_NAME="ideaforge-ai"

echo -e "${BLUE}🐳 Kind Cluster Deployment${NC}"
echo "=========================="
echo "Image Tag: $IMAGE_TAG"
echo "Namespace: $K8S_NAMESPACE"
echo ""

# Check if kind cluster exists
if ! kind get clusters | grep -q "^${KIND_CLUSTER_NAME}$"; then
    echo -e "${YELLOW}⚠️  Kind cluster not found, creating...${NC}"
    make kind-create kind-setup-ingress
fi

# Build images if not exist
echo -e "${YELLOW}🔨 Checking Docker images...${NC}"
if ! docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "ideaforge-ai-backend:${IMAGE_TAG}"; then
    echo "   Building backend image..."
    make build-apps
else
    echo -e "${GREEN}✅ Images already exist${NC}"
fi

# Load images into kind
echo -e "${YELLOW}📦 Loading images into kind...${NC}"
make kind-load-images

# Update image references
echo -e "${YELLOW}🔄 Updating image references...${NC}"
make kind-update-images

# Load secrets
echo -e "${YELLOW}🔐 Loading secrets...${NC}"
if [ -f .env ]; then
    make kind-load-secrets
else
    echo -e "${YELLOW}⚠️  .env not found, using default secrets${NC}"
fi

# Deploy
echo -e "${YELLOW}📦 Deploying to kind...${NC}"
make kind-deploy-internal

echo ""
echo -e "${GREEN}✅ Kind Deployment Complete!${NC}"
echo ""
echo -e "${BLUE}Access Information:${NC}"
make kind-show-access-info

