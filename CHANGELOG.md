# Changelog

## [2.0.0] - 2025-11-30

### Removed
- **Lovable Prototype Generation Button**: Removed from Design panel - users now copy prompts manually
- **Playwright Integration**: Removed browser automation complexity
- **Lovable API Key Requirement**: No longer needed (Lovable uses link generator)

### Enhanced
- **Lovable Agent**: 
  - Comprehensive Lovable.dev platform knowledge (as of Nov 2025)
  - Industry best practices integration
  - All phase data context in prompt generation
  - Clean prompts ready for copy-paste
  
- **Agent Dashboard**:
  - New endpoint: `GET /api/agents/usage-stats`
  - Usage statistics from first login
  - Performance metrics (processing time, cache hits, token usage)
  - Usage trends and phase distribution

### Fixed
- Agent dashboard database query (product_lifecycle_phases table)
- Lovable prompt generation to include all phase data
- Frontend Lovable API key alerts removed

### Documentation
- Updated README.md with latest changes
- Created DEPLOYMENT_NOTES.md with complete deployment guide
