# Quick Start Guide

Everything you need to get IdeaForge AI running locally in under 10 minutes.

## 1. Prerequisites

- Docker 20.10+ and Docker Compose v2
- GNU Make (macOS/Linux include it; Windows users can run via WSL or use the raw `docker-compose` commands)
- At least one API key (OpenAI, Anthropic Claude, or Google Gemini)

```bash
docker --version
docker-compose --version
```

## 2. Clone & Configure

```bash
git clone <repo> ideaforge-ai
cd ideaforge-ai

# copy defaults and edit if needed
cp .env.example .env
```

Environment variables:
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY` are optional but you must supply at least one to use the agents.
- Database credentials already match the in-container Postgres service (`postgresql+asyncpg://agentic_pm:devpassword@postgres:5432/agentic_pm_db`).

## 3. Launch the stack

```bash
make build     # builds backend/frontend/postgres images
make up        # starts backend, frontend, Postgres, Redis
make health    # shows health info + docker-compose ps
```

Services:
- Frontend: http://localhost:3001
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

## 4. Configure & Verify API Keys

1. Open the UI at **http://localhost:3001** → **Settings**.
2. Enter one or more provider keys.
3. Use the **Verify Key** button. The UI calls `/api/providers/verify` and shows success/failure inline.
4. Click **Save Configuration** to push keys to the backend registry.

👉 Keys are stored in the browser for client-side SDK calls and registered with the backend so every agent immediately uses the correct provider.

## 5. First interactions

### Test an agent
```bash
curl -X POST http://localhost:8000/api/agents/process \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "00000000-0000-0000-0000-000000000001",
    "agent_type": "ideation",
    "messages": [{ "role": "user", "content": "Generate feature ideas for a team productivity app" }]
  }'
```

### Run the multi-agent workflow
```bash
curl -X POST http://localhost:8000/api/multi-agent/process \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "00000000-0000-0000-0000-000000000001",
    "query": "Create a PRD outline for an AI onboarding copilot",
    "coordination_mode": "collaborative",
    "primary_agent": "ideation",
    "supporting_agents": ["research", "analysis"]
  }'
```

Then switch back to the UI and iterate via the Product Lifecycle wizard.

## 6. Helpful commands

```bash
make logs SERVICE=backend   # follow backend logs
make restart                # bounce all services
make down                   # stop everything
make rebuild                # rebuild images without cache and restart
```

Common docker-compose equivalents are still available if you prefer to run commands manually.

## 7. Troubleshooting

| Symptom | Try This |
|---------|----------|
| `/api/multi-agent/process` hangs | `docker-compose logs backend` – look for provider connection errors |
| “Connection error” from agents   | Ensure the backend container has outbound HTTPS access (corporate proxies often block it) |
| Database errors                  | `docker-compose ps postgres` should show “healthy”; volume `postgres-data` stores all state |
| Keys show “invalid” in UI        | Use the **Verify Key** button; the backend endpoint returns the exact provider error |
| Ports already in use             | Edit `docker-compose.yml` or stop conflicting processes (`lsof -i :3001`) |

## 8. Next steps

1. Review `docs/01-high-level-architecture.md` for system diagrams.
2. Deploy using `docs/guides/deployment-guide.md`.
3. Explore RAG/document workflows via `docs/guides/product-lifecycle.md`.
4. Customize or extend agents in `backend/agents/`.

Happy building! 🎉
