# Environment Variables Configuration

This document explains environment variable configuration for IdeaForge AI.

## Overview

IdeaForge AI uses platform-specific environment configuration:

- **Common variables**: `env.example` (shared across all platforms)
- **Platform-specific**: `env.<platform>.example` files
  - `env.eks.example` → Production (EKS)
  - `env.kind.example` → Local Development (Kind)
  - `env.docker-compose.example` → Fallback (Docker Compose)

## Quick Reference

See [Platform-Specific Configuration Guide](PLATFORM_ENV_GUIDE.md) for detailed setup instructions.

## Common Variables (env.example)

These variables are shared across all platforms:

### Database
- `POSTGRES_HOST` - Database hostname
- `POSTGRES_PORT` - Database port
- `POSTGRES_USER` - Database user
- `POSTGRES_DB` - Database name
- `POSTGRES_PASSWORD` - **Platform-specific** (not in common)

### Redis
- `REDIS_URL` - Redis connection URL

### AI Providers
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `GOOGLE_API_KEY` - Google Gemini API key

### Agent Configuration
- `AGENT_MODEL_PRIMARY` - Primary model (default: gpt-5.1)
- `AGENT_MODEL_SECONDARY` - Secondary model (default: claude-sonnet-4-20250522)
- `AGENT_MODEL_TERTIARY` - Tertiary model (default: gemini-3.0-pro)

### Application
- `BACKEND_PORT` - Backend port (default: 8000)
- `LOG_LEVEL` - Logging level (default: info)
- `SESSION_EXPIRES_IN` - Session expiration in seconds

## Platform-Specific Variables

### EKS (Production)
- `POSTGRES_PASSWORD` - Strong production password
- `VITE_API_URL` - Empty (relative paths)
- `FRONTEND_URL` - External domain URL
- `CORS_ORIGINS` - Production domains
- `K8S_NAMESPACE` - EKS namespace

### Kind (Local Development)
- `POSTGRES_PASSWORD` - Dev password
- `VITE_API_URL` - Empty (relative paths)
- `FRONTEND_URL` - Ingress URL (http://localhost:80)
- `CORS_ORIGINS` - Local development origins
- `K8S_NAMESPACE` - Kind namespace

### Docker Compose (Fallback)
- `POSTGRES_PASSWORD` - Dev password
- `DATABASE_URL` - Full database connection string
- `VITE_API_URL` - Direct backend URL (http://localhost:8000)
- `FRONTEND_URL` - Frontend URL (http://localhost:3001)
- `CORS_ORIGINS` - Local development origins

## Setup Instructions

1. Copy example files:
   ```bash
   cp env.example .env
   cp env.kind.example env.kind  # for kind
   cp env.eks.example env.eks    # for eks
   ```

2. Configure platform-specific values in respective files

3. For Kubernetes, use Kustomize to load ConfigMaps:
   ```bash
   kubectl apply -k k8s/overlays/kind
   kubectl apply -k k8s/overlays/eks
   ```

See [Platform-Specific Configuration Guide](PLATFORM_ENV_GUIDE.md) for complete setup instructions.

