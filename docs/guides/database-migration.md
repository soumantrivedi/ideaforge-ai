# Database Migration: Supabase to In-Container PostgreSQL

## Overview

The application has been migrated from Supabase (cloud database) to an in-container PostgreSQL database with persistent storage.

## Changes Made

### 1. Database Setup
- **PostgreSQL Container**: Using `pgvector/pgvector:pg15` image for vector similarity search
- **Port**: Changed from 5432 to 5433 to avoid conflicts with local PostgreSQL
- **Persistent Storage**: Data stored in Docker volume `postgres-data`
- **Initialization**: Automatic schema creation via `init-db/01-init-schema.sql`

### 2. Database Schema
All tables from Supabase migrations have been recreated:
- `user_profiles`
- `products`
- `prd_documents`
- `conversation_sessions`
- `agent_messages`
- `knowledge_articles` (with pgvector support)
- `agent_activity_log`
- `feedback_entries`
- `product_lifecycle_phases`
- `phase_submissions`
- `conversation_history`
- `exported_documents`

### 3. Backend Changes
- **Database Connection**: Using SQLAlchemy with asyncpg
- **New API Endpoints**: `/api/db/*` endpoints for database operations
- **Removed Supabase SDK**: Replaced with direct PostgreSQL queries
- **Health Check**: Database health included in `/health` endpoint

### 4. Frontend Changes
- **Removed Supabase Client**: All database operations now go through backend API
- **Updated Services**:
  - `product-lifecycle-service.ts`: Uses `/api/db/phases` and `/api/db/conversation-history`
  - `rag-system.ts`: Uses `/api/db/knowledge-articles`
- **No More Direct Database Access**: Frontend only communicates with backend API

## Configuration

### Environment Variables
```env
DATABASE_URL=postgresql://agentic_pm:devpassword@postgres:5432/agentic_pm_db
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=agentic_pm
POSTGRES_PASSWORD=devpassword
POSTGRES_DB=agentic_pm_db
```

### Docker Compose
- PostgreSQL service with health checks
- Automatic schema initialization
- Persistent volume for data
- Backend depends on PostgreSQL being healthy

## Data Persistence

Data is stored in Docker volume `postgres-data`:
- **Location**: Managed by Docker
- **Persistence**: Data survives container restarts
- **Backup**: Use `docker volume inspect ideaforge-ai_postgres-data` to find location

## Migration Steps

1. ✅ Database schema created
2. ✅ Backend API endpoints added
3. ✅ Frontend updated to use backend API
4. ✅ Supabase dependencies removed
5. ✅ Health checks configured

## Testing

```bash
# Check database tables
docker-compose exec postgres psql -U agentic_pm -d agentic_pm_db -c "\dt"

# Test API endpoints
curl http://localhost:8000/api/db/phases
curl http://localhost:8000/api/db/knowledge-articles
curl http://localhost:8000/health
```

## Benefits

1. **Self-Contained**: No external dependencies
2. **Persistent**: Data stored in Docker volumes
3. **Vector Search**: Full pgvector support for RAG
4. **Performance**: Direct database access, no API overhead
5. **Privacy**: All data stays in your infrastructure

## Notes

- Port 5433 is used externally to avoid conflicts
- Internal port 5432 is used within Docker network
- Database initialization runs automatically on first start
- All Supabase-specific features (RLS, auth) removed - handled by backend

