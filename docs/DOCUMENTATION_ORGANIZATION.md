# Documentation Organization

**Last Updated:** November 30, 2025

## Overview

All documentation has been organized into logical subdirectories within the `docs/` folder. This document provides a guide to the new structure.

## Directory Structure

```
docs/
├── README.md                          # Documentation index and quick links
├── architecture/                      # System architecture documentation
│   ├── 01-high-level-architecture.md
│   ├── 02-detailed-design-architecture.md
│   ├── 03-complete-application-guide.md
│   ├── 04-multi-agent-orchestration.md
│   ├── 05-scalability-and-performance.md
│   └── COMPLETE_FEATURE_INVENTORY.md
│
├── configuration/                     # Configuration guides
│   ├── AGNO_INITIALIZATION.md
│   ├── AGNO_INITIALIZATION_FIX.md
│   ├── AI_MODEL_UPGRADE.md
│   ├── API_KEYS_SETUP.md
│   ├── ASYNC_JOB_CONFIGURATION.md
│   ├── ENVIRONMENT_URL_CONFIG.md
│   ├── PLATFORM_ENV_GUIDE.md
│   ├── RUNTIME_API_URL_CONFIG.md
│   └── environment-variables.md
│
├── deployment/                        # Deployment documentation
│   ├── DEPLOYMENT_GUIDE.md
│   ├── DEPLOYMENT_INSTRUCTIONS.md
│   ├── DEPLOYMENT_NOTES.md
│   ├── DEPLOYMENT_PRODUCTION.md
│   ├── DEPLOYMENT_SUMMARY.md
│   ├── DEPLOYMENT_VALIDATION.md
│   ├── PRODUCTION_DEPLOYMENT_GUIDE.md
│   ├── PRODUCTION_READINESS.md
│   ├── backups.md
│   ├── eks-deployment-guide.md
│   ├── eks-image-tags.md
│   ├── eks-ingress-quickstart.md
│   ├── eks-ingress.md
│   ├── eks.md
│   └── kind-access.md
│
├── guides/                            # User and developer guides
│   ├── STREAMING_IMPLEMENTATION.md
│   ├── V0_AGENT_IMPLEMENTATION_COMPLETE.md
│   ├── V0_PROTOTYPE_TRACKING.md
│   ├── agent-development-guide.md
│   ├── agno-migration.md
│   ├── async-job-processing.md
│   ├── database-migration.md
│   ├── deployment-guide.md
│   ├── eks-production-guide.md
│   ├── flexible-lifecycle-and-export.md
│   ├── implementation-guide.md
│   ├── local-development-guide.md
│   ├── make-targets.md
│   ├── multi-agent-backend.md
│   ├── multi-agent-memory.md
│   ├── multi-agent-system.md
│   ├── product-lifecycle.md
│   ├── quick-deploy.md
│   └── quick-start.md
│
├── improvements/                      # Improvement plans and analysis
│   ├── AGNO_FRAMEWORK_OPTIMIZATION_BACKLOG.md
│   ├── COMPREHENSIVE_IMPROVEMENTS_ANALYSIS.md
│   ├── COMPREHENSIVE_IMPROVEMENTS_COMPLETE.md
│   ├── IMPROVEMENTS_IMPLEMENTATION_STATUS.md
│   ├── IMPROVEMENTS_PLAN.md
│   ├── IMPROVEMENTS_SUMMARY.md
│   ├── PROMPT_OPTIMIZATION.md
│   └── UI_UX_IMPROVEMENTS_ANALYSIS.md
│
├── troubleshooting/                   # Troubleshooting guides
│   ├── AGENT_TIMEOUT_REMOVAL.md
│   ├── CLOUD_NATIVE_API_FIX.md
│   ├── CORS_ERROR_ANALYSIS.md
│   ├── FRONTEND_API_URL_FIX.md
│   ├── FRONTEND_ERROR_DEBUGGING.md
│   ├── V0_API_CREDITS_ISSUE.md
│   └── common-issues.md
│
└── verification/                      # Verification and testing
    ├── ATLASSIAN_AGENT_INTEGRATION.md
    ├── DEPLOYMENT_VERIFICATION.md
    ├── DEPLOYMENT_VERIFICATION_REPORT.md
    ├── REQUIREMENTS_VERIFICATION.md
    ├── TIMEOUT_AND_ERROR_HANDLING.md
    ├── V0_WORKFLOW_TEST_RESULTS.md
    └── VALIDATION_RESULTS.md
```

## File Moves Summary

### Root → docs/deployment/
- `DEPLOYMENT_INSTRUCTIONS.md`
- `DEPLOYMENT_NOTES.md`
- `DEPLOYMENT_SUMMARY.md`
- `DEPLOYMENT_VALIDATION.md`
- `PRODUCTION_DEPLOYMENT_GUIDE.md`
- `PRODUCTION_READINESS.md`

### Root → docs/improvements/
- `COMPREHENSIVE_IMPROVEMENTS_ANALYSIS.md`
- `COMPREHENSIVE_IMPROVEMENTS_COMPLETE.md`
- `IMPROVEMENTS_IMPLEMENTATION_STATUS.md`
- `IMPROVEMENTS_PLAN.md`

### Root → docs/verification/
- `DEPLOYMENT_VERIFICATION_REPORT.md`
- `VALIDATION_RESULTS.md`

### Root → docs/guides/
- `STREAMING_IMPLEMENTATION.md`

### docs/ → docs/configuration/
- `AGNO_INITIALIZATION_FIX.md`
- `AI_MODEL_UPGRADE.md`
- `ASYNC_JOB_CONFIGURATION.md`

### docs/ → docs/improvements/
- `AGNO_FRAMEWORK_OPTIMIZATION_BACKLOG.md`
- `IMPROVEMENTS_SUMMARY.md`
- `PROMPT_OPTIMIZATION.md`
- `UI_UX_IMPROVEMENTS_ANALYSIS.md`

### docs/ → docs/architecture/
- `COMPLETE_FEATURE_INVENTORY.md`

### docs/ → docs/deployment/
- `DEPLOYMENT_PRODUCTION.md`

### docs/ → docs/troubleshooting/
- `AGENT_TIMEOUT_REMOVAL.md`
- `V0_API_CREDITS_ISSUE.md` (from backend/)

### docs/ → docs/guides/
- `V0_AGENT_IMPLEMENTATION_COMPLETE.md`
- `V0_PROTOTYPE_TRACKING.md`

### docs/ → docs/verification/
- `V0_WORKFLOW_TEST_RESULTS.md`

## Files Remaining in Root

The following files remain in the root directory (standard locations):
- `README.md` - Main project README
- `CHANGELOG.md` - Project changelog (standard location)

## Quick Reference

### For Deployment
- Production: `docs/deployment/PRODUCTION_DEPLOYMENT_GUIDE.md`
- Local Dev: `docs/deployment/kind-access.md`
- Readiness: `docs/deployment/PRODUCTION_READINESS.md`

### For Configuration
- API Keys: `docs/configuration/API_KEYS_SETUP.md`
- Environment: `docs/configuration/environment-variables.md`
- Agno Init: `docs/configuration/AGNO_INITIALIZATION.md`

### For Troubleshooting
- Common Issues: `docs/troubleshooting/common-issues.md`
- Agno Fix: `docs/configuration/AGNO_INITIALIZATION_FIX.md`

### For Improvements
- Analysis: `docs/improvements/COMPREHENSIVE_IMPROVEMENTS_ANALYSIS.md`
- Status: `docs/improvements/IMPROVEMENTS_IMPLEMENTATION_STATUS.md`

## Updating References

If you find references to old file paths, update them to the new locations:
- `DEPLOYMENT_INSTRUCTIONS.md` → `docs/deployment/DEPLOYMENT_INSTRUCTIONS.md`
- `PRODUCTION_READINESS.md` → `docs/deployment/PRODUCTION_READINESS.md`
- etc.

## Notes

- All documentation is now centralized in `docs/`
- Root directory is clean (only README.md and CHANGELOG.md)
- Documentation is organized by purpose/category
- Easy to find and maintain

