# Enterprise Agentic PM Platform - Deployment Guide

## Overview

This guide covers deploying the complete Enterprise Agentic PM Platform with Docker containers, backend FastAPI services, MCP servers, and full database integration.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)                  │
│                      Port: 3001                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────┐
│               Backend (FastAPI + Python)                     │
│                      Port: 8000                              │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ PRD Authoring│  │  Ideation    │  │  Jira Agent     │  │
│  │    Agent     │  │   Agent      │  │                 │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────┐
│                   MCP Servers (FastMCP)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │   GitHub     │  │     Jira     │  │   Confluence    │  │
│  │   :8001      │  │    :8002     │  │     :8003       │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┴──────────────────┐
        │                                      │
┌───────┴──────────┐              ┌───────────┴────────────┐
│  PostgreSQL      │              │      Redis             │
│  with pgvector   │              │   Cache/Session        │
│    Port: 5432    │              │     Port: 6379         │
└──────────────────┘              └────────────────────────┘
```

## Prerequisites

### Required
- Docker 20.10+
- Docker Compose 2.0+
- At least 4GB RAM available
- 10GB disk space

### API Keys & Credentials
1. **AI Provider Keys** (at least one required):
   - OpenAI API Key: https://platform.openai.com/api-keys
   - Anthropic API Key: https://console.anthropic.com/
   - Google AI API Key: https://ai.google.dev/

2. **Database**:
   - Default deployment uses the bundled PostgreSQL 15 + pgvector container (no external service required).
   - For managed Postgres, supply `DATABASE_URL` in `.env` and ensure the `pgvector` extension is enabled.

3. **Integration Keys** (optional but recommended):
   - **Okta**: Client ID, Client Secret, Issuer URL
   - **Jira**: URL, Email, API Token
   - **Confluence**: URL, Email, API Token
   - **GitHub**: Personal Access Token, Organization

## Quick Start (Development)

### 1. Clone and Configure

```bash
# Clone the repository
git clone <repository-url>
cd project

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### 2. Configure Environment Variables

Edit `.env` file with your credentials:

```env
# API Configuration
VITE_API_URL=http://localhost:8000
DATABASE_URL=postgresql://user:password@postgres:5432/agentic_pm_db

# Optional: Okta OAuth/SSO (for enterprise authentication)
VITE_OKTA_CLIENT_ID=your_okta_client_id
VITE_OKTA_ISSUER=your_okta_issuer
OKTA_CLIENT_ID=your_okta_client_id
OKTA_CLIENT_SECRET=your_okta_client_secret
OKTA_ISSUER=your_okta_issuer

# AI Provider API Keys (at least one required)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...

# Optional: Okta OAuth/SSO
OKTA_CLIENT_ID=your_okta_client_id
OKTA_CLIENT_SECRET=your_okta_client_secret
OKTA_ISSUER=https://your-domain.okta.com/oauth2/default

# Optional: Jira Integration
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your_jira_api_token

# Optional: Confluence Integration
CONFLUENCE_URL=https://your-domain.atlassian.net/wiki
CONFLUENCE_EMAIL=your-email@company.com
CONFLUENCE_API_TOKEN=your_confluence_api_token

# Optional: GitHub Integration
GITHUB_TOKEN=ghp_your_github_personal_access_token
GITHUB_ORG=your-organization
```

### 3. Start Services

```bash
# Start all services with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 4. Apply Database Migrations

The Postgres container automatically runs `init-db/01-init-schema.sql` on first start.  
If you connect to an external Postgres instance, run that script manually to create the product-lifecycle tables and pgvector indexes.

### 5. Access the Application

- **Frontend**: http://localhost:3001
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Service Details

### Frontend (React + Vite)
- **Port**: 3001
- **Technology**: React 18, TypeScript, Tailwind CSS
- **Features**:
  - Multi-agent chat interface
  - Knowledge base management
  - Provider configuration
  - Real-time streaming responses

### Backend (FastAPI)
- **Port**: 8000
- **Technology**: Python 3.11, FastAPI, asyncio
- **Endpoints**:
  - `GET /` - Service info
  - `GET /health` - Health check with provider status
  - `GET /api/agents` - List available agents
  - `POST /api/agents/process` - Process agent request
  - `POST /api/workflows/{workflow_type}` - Execute multi-agent workflow

### MCP Servers

#### GitHub MCP Server
- **Port**: 8001
- **Tools**:
  - `list_repositories` - List org/user repositories
  - `get_repository` - Get repository details
  - `create_issue` - Create GitHub issue
  - `list_pull_requests` - List PRs
  - `get_file_content` - Read file content

#### Jira MCP Server
- **Port**: 8002
- **Tools**:
  - `list_projects` - List Jira projects
  - `create_epic` - Create new epic
  - `create_story` - Create user story
  - `get_issue` - Get issue details
  - `search_issues` - JQL search
  - `add_comment` - Add comment to issue

#### Confluence MCP Server
- **Port**: 8003
- **Tools**:
  - `list_spaces` - List Confluence spaces
  - `create_page` - Create new page
  - `get_page` - Get page content
  - `update_page` - Update existing page
  - `search_content` - Search content
  - `get_page_children` - List child pages

## Database Schema

### Tables Created
- `user_profiles` - User accounts and personas
- `products` - Product definitions and lifecycle
- `prd_documents` - PRD versioning and content
- `conversation_sessions` - Chat sessions
- `agent_messages` - Message history
- `knowledge_articles` - RAG knowledge base with embeddings
- `agent_activity_log` - Agent actions and metrics
- `feedback_entries` - User feedback for learning

### Row Level Security
All tables have RLS enabled with policies ensuring:
- Users can only access their own data
- Product owners control their product data
- No cross-user data leakage

## Using the Platform

### 1. First Login

Since Okta integration is optional, the initial setup uses API keys:

1. Open http://localhost:3001
2. Navigate to "Settings" tab
3. Enter your AI provider API keys
4. Click "Save Configuration"
5. Return to "Chat" tab

### 2. Create a Product

```bash
# Using the backend API
curl -X POST http://localhost:8000/api/products \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your-uuid",
    "name": "New Product",
    "description": "Product description",
    "status": "ideation"
  }'
```

### 3. Interact with Agents

#### Ideation Phase
```bash
curl -X POST http://localhost:8000/api/agents/process \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your-uuid",
    "product_id": "product-uuid",
    "agent_type": "ideation",
    "messages": [
      {
        "role": "user",
        "content": "Generate feature ideas for a task management app"
      }
    ]
  }'
```

#### PRD Authoring
```bash
curl -X POST http://localhost:8000/api/agents/process \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your-uuid",
    "product_id": "product-uuid",
    "agent_type": "prd_authoring",
    "messages": [
      {
        "role": "user",
        "content": "Create a PRD for our task management features"
      }
    ]
  }'
```

#### Jira Integration
```bash
curl -X POST http://localhost:8000/api/agents/process \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your-uuid",
    "product_id": "product-uuid",
    "agent_type": "jira_integration",
    "messages": [
      {
        "role": "user",
        "content": "Convert this PRD to Jira epics and stories"
      }
    ],
    "context": {
      "project_key": "PROJ"
    }
  }'
```

### 4. Multi-Agent Workflows

Execute complex workflows that chain multiple agents:

```bash
# Idea to Jira workflow
curl -X POST http://localhost:8000/api/workflows/idea_to_jira \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your-uuid",
    "product_id": "product-uuid",
    "messages": [
      {
        "role": "user",
        "content": "Mobile app for team collaboration"
      }
    ]
  }'
```

## Production Deployment

### 1. Environment Preparation

```bash
# Set production environment
export NODE_ENV=production
export ENVIRONMENT=production

# Update .env with production values
# - Use strong secrets
# - Enable all security features
# - Configure production databases
# - Set up monitoring
```

### 2. Security Hardening

```bash
# Generate strong session secret
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Update in .env
SESSION_SECRET=<generated-secret>

# Enable HTTPS (recommended: use reverse proxy like nginx)
# Configure SSL certificates
# Enable HSTS headers
```

### 3. Build Production Images

```bash
# Build all services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Tag for registry
docker tag project-frontend:latest registry.example.com/project-frontend:latest
docker tag project-backend:latest registry.example.com/project-backend:latest

# Push to registry
docker push registry.example.com/project-frontend:latest
docker push registry.example.com/project-backend:latest
```

### 4. Deploy to Production

```bash
# Pull latest images on production server
docker-compose pull

# Start services
docker-compose up -d

# Run health checks
curl http://localhost:8000/health

# Monitor logs
docker-compose logs -f
```

## Monitoring & Maintenance

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00Z",
  "version": "1.0.0",
  "services": {
    "api": true,
    "openai": true,
    "anthropic": true,
    "google": true,
    "database": true
  }
}
```

### Logs

```bash
# View all logs
docker-compose logs -f

# Specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f mcp-github

# Search logs
docker-compose logs | grep ERROR
```

### Database Maintenance

```bash
# Backup database
docker-compose exec postgres pg_dump -U postgres agentic_pm_db > backup.sql

# Restore database
docker-compose exec -T postgres psql -U postgres agentic_pm_db < backup.sql

# Vacuum and analyze
docker-compose exec postgres psql -U postgres -d agentic_pm_db -c "VACUUM ANALYZE;"
```

### Performance Monitoring

```bash
# Container resource usage
docker stats

# Database connections
docker-compose exec postgres psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# Redis statistics
docker-compose exec redis redis-cli INFO stats
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs <service-name>

# Verify environment variables
docker-compose config

# Rebuild service
docker-compose build --no-cache <service-name>
```

### Database Connection Issues

```bash
# Test connection
docker-compose exec postgres psql -U postgres -c "SELECT 1;"

# Check migrations
docker-compose exec postgres psql -U postgres -d agentic_pm_db -c "\dt"

# Verify pgvector extension
docker-compose exec postgres psql -U postgres -d agentic_pm_db -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

### API Key Issues

```bash
# Test OpenAI
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Test Anthropic
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-3-sonnet-20240229","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}'
```

### MCP Server Not Responding

```bash
# Check MCP server logs
docker-compose logs mcp-github
docker-compose logs mcp-jira
docker-compose logs mcp-confluence

# Test MCP server directly
curl http://localhost:8001/health

# Restart MCP service
docker-compose restart mcp-github
```

## Scaling

### Horizontal Scaling

```bash
# Scale backend workers
docker-compose up -d --scale backend=3

# Configure load balancer (nginx example)
upstream backend {
    server backend:8000;
    server backend:8001;
    server backend:8002;
}
```

### Database Scaling

- Enable connection pooling (PgBouncer)
- Use managed Postgres replicas or high-availability clusters when running outside Docker
- Configure Redis for session management
- Implement caching layers

### Resource Optimization

```yaml
# docker-compose.yml resource limits
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## Security Considerations

### API Keys
- Store in environment variables only
- Never commit to version control
- Rotate keys regularly
- Use separate keys per environment

### Database
- Enable RLS on all tables
- Use strong passwords
- Limit connection access by IP
- Regular backups

### Network
- Use HTTPS in production
- Configure CORS properly
- Implement rate limiting
- Use API gateways

## Support & Resources

### Documentation
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Docker Documentation](https://docs.docker.com/)

### Getting Help
- Check logs first: `docker-compose logs -f`
- Review configuration: `docker-compose config`
- Test services individually
- Verify API keys and credentials

## Next Steps

1. **Configure Okta** for enterprise SSO
2. **Set up monitoring** with Prometheus/Grafana
3. **Implement CI/CD** pipeline
4. **Add custom agents** for your use case
5. **Extend MCP servers** with additional tools
6. **Configure backup** automation
7. **Set up alerting** for critical issues

---

**Platform Version**: 1.0.0
**Last Updated**: 2025-01-15
**Maintained by**: Enterprise Platform Team
