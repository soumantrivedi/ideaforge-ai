# Quick Start Guide - Enterprise Agentic PM Platform

## 🚀 Get Started in 5 Minutes

### Step 1: Prerequisites Check

```bash
# Verify Docker is installed
docker --version
# Should show: Docker version 20.10+

# Verify Docker Compose is installed
docker-compose --version
# Should show: Docker Compose version 2.0+
```

### Step 2: Clone and Configure

```bash
# Navigate to project directory
cd /path/to/project

# Copy environment template
cp .env.example .env

# Edit .env file (use your favorite editor)
nano .env
```

### Step 3: Add Your API Keys

Edit `.env` and add **at least one** AI provider key:

```env
# Choose at least one:
OPENAI_API_KEY=sk-...                    # Get from: https://platform.openai.com/api-keys
ANTHROPIC_API_KEY=sk-ant-...             # Get from: https://console.anthropic.com/
GOOGLE_API_KEY=AIza...                   # Get from: https://ai.google.dev/

# Supabase (required for database)
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key
```

### Step 4: Start the Platform

```bash
# Start all services (frontend, backend, MCP servers, database)
docker-compose up -d

# Wait 30 seconds for services to initialize

# Check status
docker-compose ps
```

### Step 5: Verify Everything Works

```bash
# Test backend health
curl http://localhost:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "services": {
#     "api": true,
#     "openai": true,
#     ...
#   }
# }
```

### Step 6: Access the Application

Open your browser:
- **Frontend**: http://localhost:3000
- **Backend API Docs**: http://localhost:8000/docs
- **Backend Health**: http://localhost:8000/health

## 🎯 First Tasks

### Task 1: Configure AI Providers (Frontend)

1. Open http://localhost:3000
2. Click "Settings" tab
3. Enter your API keys
4. Click "Save Configuration"
5. Return to "Chat" tab

### Task 2: Test an Agent (API)

```bash
# Test the Ideation Agent
curl -X POST http://localhost:8000/api/agents/process \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "00000000-0000-0000-0000-000000000001",
    "agent_type": "ideation",
    "messages": [
      {
        "role": "user",
        "content": "Generate feature ideas for a task management application"
      }
    ]
  }'
```

### Task 3: Run a Multi-Agent Workflow

```bash
# Idea to Jira workflow
curl -X POST http://localhost:8000/api/workflows/idea_to_jira \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "00000000-0000-0000-0000-000000000001",
    "product_id": "00000000-0000-0000-0000-000000000002",
    "messages": [
      {
        "role": "user",
        "content": "Mobile app for team task management"
      }
    ]
  }'
```

## 📊 Available Agents

| Agent | Type | Purpose | Best For |
|-------|------|---------|----------|
| PRD Authoring | `prd_authoring` | Create PRDs following McKinsey CodeBeyond standards | Product documentation |
| Ideation | `ideation` | Generate feature ideas and brainstorm | Early product phases |
| Jira Integration | `jira_integration` | Create epics, stories, and Jira tickets | SDLC integration |

## 🔧 Common Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f mcp-github
```

### Restart Services
```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart backend
```

### Stop Services
```bash
# Stop all
docker-compose stop

# Stop and remove
docker-compose down
```

### Rebuild After Changes
```bash
# Rebuild specific service
docker-compose build backend

# Rebuild and restart
docker-compose up -d --build
```

## 🔌 MCP Server Tools

### GitHub MCP (Port 8001)
- `list_repositories` - List repos
- `create_issue` - Create GitHub issue
- `get_file_content` - Read file

### Jira MCP (Port 8002)
- `list_projects` - List projects
- `create_epic` - Create epic
- `create_story` - Create story
- `search_issues` - JQL search

### Confluence MCP (Port 8003)
- `list_spaces` - List spaces
- `create_page` - Create page
- `search_content` - Search content

## 🐛 Troubleshooting

### Services Won't Start
```bash
# Check what's wrong
docker-compose logs

# Rebuild from scratch
docker-compose down -v
docker-compose up -d --build
```

### Port Already in Use
```bash
# Find what's using the port
lsof -i :3000  # or :8000, :5432, etc.

# Kill the process or change port in docker-compose.yml
```

### Database Connection Issues
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Test database connection
docker-compose exec postgres psql -U postgres -c "SELECT 1;"

# Verify migrations
docker-compose exec postgres psql -U postgres -d agentic_pm_db -c "\dt"
```

### API Keys Not Working
```bash
# Verify .env is loaded
docker-compose config | grep API_KEY

# Restart backend after .env changes
docker-compose restart backend
```

## 📝 Useful API Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

### List Available Agents
```bash
curl http://localhost:8000/api/agents
```

### Process Agent Request
```bash
curl -X POST http://localhost:8000/api/agents/process \
  -H "Content-Type: application/json" \
  -d @request.json
```

### Execute Workflow
```bash
curl -X POST http://localhost:8000/api/workflows/idea_to_jira \
  -H "Content-Type: application/json" \
  -d @workflow.json
```

## 🎓 Next Steps

### Learn More
- Read `DEPLOYMENT_GUIDE.md` for production setup
- Check `IMPLEMENTATION_SUMMARY.md` for architecture details
- Review `README.md` for full documentation

### Add Integrations
1. Configure Jira credentials in `.env`
2. Configure Confluence credentials in `.env`
3. Add GitHub token in `.env`
4. Restart services: `docker-compose restart`

### Customize
1. Add custom agents in `backend/agents/`
2. Extend MCP servers in `mcp-servers/`
3. Modify frontend in `src/`
4. Update database schema via Supabase

## 💡 Pro Tips

1. **Use tmux/screen** for running logs in separate terminal
2. **Set up aliases** for common docker-compose commands
3. **Monitor resources** with `docker stats`
4. **Backup database** regularly with `pg_dump`
5. **Use .env.local** for local overrides (gitignored)

## 🆘 Get Help

### Check Logs First
```bash
docker-compose logs -f | grep ERROR
```

### Verify Configuration
```bash
docker-compose config
```

### Test Individual Services
```bash
# Test backend directly
curl http://localhost:8000/

# Test MCP servers
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

### Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Port conflict | Change ports in `docker-compose.yml` |
| Out of memory | Increase Docker memory limit |
| Slow responses | Check network, reduce context size |
| Database errors | Verify Supabase credentials |
| API key invalid | Check key format, expiration |

## 📚 Documentation Links

- **Full Deployment Guide**: `DEPLOYMENT_GUIDE.md`
- **Implementation Details**: `IMPLEMENTATION_SUMMARY.md`
- **API Documentation**: http://localhost:8000/docs (when running)
- **Feature Overview**: `README.md`

---

**Need Help?** Check logs, verify .env, and review documentation.

**Ready to Build?** Start with the Ideation Agent and work your way through PRD authoring to Jira integration!

**Platform Version**: 1.0.0
