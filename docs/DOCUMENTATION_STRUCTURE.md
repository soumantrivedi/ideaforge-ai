# Documentation Structure

This document describes the organization of all documentation in the IdeaForge AI repository.

## Overview

All documentation is organized in the `docs/` folder with a clear hierarchical structure:

```
docs/
├── architecture/          # System architecture documentation
├── deployment/            # Deployment guides for different platforms
├── configuration/         # Configuration and environment setup
├── guides/                # User and developer guides
└── troubleshooting/      # Troubleshooting and issue resolution
```

## Directory Structure

### Architecture (`docs/architecture/`)

High-level and detailed architecture documentation:

- `01-high-level-architecture.md` - System overview, components, and high-level design
- `02-detailed-design-architecture.md` - Detailed technical design and implementation
- `03-complete-application-guide.md` - Complete application guide and features

### Deployment (`docs/deployment/`)

Platform-specific deployment guides:

- `DEPLOYMENT_GUIDE.md` - General deployment guide (docker-compose)
- `kind-access.md` - Kind cluster deployment and access
- `eks.md` - EKS production deployment guide
- `eks-ingress.md` - EKS ingress configuration
- `eks-ingress-quickstart.md` - Quick start for EKS ingress
- `eks-image-tags.md` - EKS image tag management
- `backups.md` - Database backup and restore procedures

### Configuration (`docs/configuration/`)

Configuration and environment setup:

- `environment-variables.md` - Environment variable reference
- `PLATFORM_ENV_GUIDE.md` - Platform-specific environment configuration
- `ENVIRONMENT_URL_CONFIG.md` - URL configuration across environments
- `API_KEYS_SETUP.md` - API keys setup and verification

### Guides (`docs/guides/`)

User and developer guides:

- `quick-start.md` - Quick start guide
- `quick-deploy.md` - Quick deployment guide
- `deployment-guide.md` - Comprehensive deployment guide
- `multi-agent-system.md` - Multi-agent system documentation
- `multi-agent-backend.md` - Backend multi-agent implementation
- `product-lifecycle.md` - Product lifecycle workflows
- `database-migration.md` - Database migration procedures
- `implementation-guide.md` - Implementation guide
- `agno-migration.md` - Agno framework migration guide

### Troubleshooting (`docs/troubleshooting/`)

Issue resolution and troubleshooting:

- `common-issues.md` - Common issues and solutions
- `CLOUD_NATIVE_API_FIX.md` - Cloud-native API communication fixes
- `FRONTEND_API_URL_FIX.md` - Frontend API URL configuration fixes

### Root Level

- `AI_MODEL_UPGRADE.md` - AI model upgrade documentation (ChatGPT 5.1, Gemini 3.0 Pro)

## Documentation Principles

1. **Single Source of Truth**: Each topic has one authoritative document
2. **Platform-Specific**: Separate guides for different deployment platforms
3. **Hierarchical Organization**: Clear folder structure by topic
4. **Cross-References**: Documents reference each other appropriately
5. **Up-to-Date**: Documentation reflects current codebase state

## Finding Documentation

### By Topic

- **Getting Started**: `docs/guides/quick-start.md`
- **Deployment**: `docs/deployment/`
- **Configuration**: `docs/configuration/`
- **Architecture**: `docs/architecture/`
- **Troubleshooting**: `docs/troubleshooting/common-issues.md`

### By Platform

- **Docker Compose**: `docs/deployment/DEPLOYMENT_GUIDE.md`
- **Kind (Local Dev)**: `docs/deployment/kind-access.md`
- **EKS (Production)**: `docs/deployment/eks.md`

### By Task

- **Setup Environment**: `docs/configuration/PLATFORM_ENV_GUIDE.md`
- **Configure API Keys**: `docs/configuration/API_KEYS_SETUP.md`
- **Deploy to Kind**: `docs/deployment/kind-access.md`
- **Deploy to EKS**: `docs/deployment/eks.md`
- **Troubleshoot Issues**: `docs/troubleshooting/common-issues.md`

## Maintenance

When adding new documentation:

1. Place in appropriate subdirectory
2. Update this structure document
3. Add cross-references from related docs
4. Update README.md if it's a major guide

## Migration Notes

Documentation was reorganized from scattered locations:
- Root level markdown files → `docs/`
- `k8s/*.md` → `docs/deployment/` or `docs/configuration/`
- `backend/agents/*.md` → `docs/guides/`
- Redundant/stale docs removed

