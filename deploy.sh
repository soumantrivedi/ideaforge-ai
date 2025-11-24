#!/bin/bash

# IdeaForge AI Deployment Script
# This script helps deploy the frontend and backend services

set -e

echo "🚀 IdeaForge AI Deployment Script"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found${NC}"
    echo "Creating .env from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}✅ Created .env file${NC}"
        echo -e "${YELLOW}⚠️  Please edit .env file with your credentials before continuing${NC}"
        exit 1
    else
        echo -e "${RED}❌ .env.example not found. Please create .env file manually${NC}"
        exit 1
    fi
fi

# Check for required environment variables
echo ""
echo "Checking required environment variables..."

REQUIRED_VARS=(
)

MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^${var}=" .env || grep -q "^${var}=$" .env || grep -q "^${var}=your_" .env; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo -e "${RED}❌ Missing or incomplete required environment variables:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo -e "   - ${var}"
    done
    echo ""
    echo "Please update your .env file with the required values."
    exit 1
fi

# Check for at least one AI provider
AI_PROVIDERS=("OPENAI_API_KEY" "ANTHROPIC_API_KEY" "GOOGLE_API_KEY")
HAS_AI_PROVIDER=false

for provider in "${AI_PROVIDERS[@]}"; do
    if grep -q "^${provider}=" .env && ! grep -q "^${provider}=$" .env && ! grep -q "^${provider}=\.\.\." .env; then
        HAS_AI_PROVIDER=true
        break
    fi
done

if [ "$HAS_AI_PROVIDER" = false ]; then
    echo -e "${YELLOW}⚠️  No AI provider API keys configured${NC}"
    echo "At least one AI provider (OpenAI, Anthropic, or Google) is required."
    echo "The application may not work without AI provider keys."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}✅ Environment variables check passed${NC}"

# Check Docker
echo ""
echo "Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✅ Docker is installed${NC}"

# Build and start services
echo ""
echo "Building Docker images..."
docker-compose build

echo ""
echo "Starting services..."
docker-compose up -d

echo ""
echo "Waiting for services to be ready..."
sleep 5

# Health check
echo ""
echo "Checking service health..."

MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend is healthy${NC}"
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        echo "Waiting for backend... ($RETRY_COUNT/$MAX_RETRIES)"
        sleep 2
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ Backend health check failed${NC}"
    echo "Check logs with: docker-compose logs backend"
    exit 1
fi

# Check frontend
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend is accessible${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend may not be ready yet${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Deployment complete!${NC}"
echo ""
echo "Services are running:"
echo "  📱 Frontend:  http://localhost:3000"
echo "  🔧 Backend:   http://localhost:8000"
echo "  📚 API Docs:  http://localhost:8000/docs"
echo "  ❤️  Health:    http://localhost:8000/health"
echo ""
echo "Useful commands:"
echo "  View logs:     docker-compose logs -f"
echo "  Stop services: docker-compose down"
echo "  Restart:       docker-compose restart"
echo "  Status:        docker-compose ps"
echo ""

