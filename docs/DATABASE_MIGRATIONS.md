# Database Migrations

This document describes the automated database migration system for IdeaForge AI.

## Overview

All database schema changes are automatically applied during deployment. The system ensures:
- **No manual SQL execution required** - All migrations run automatically
- **Idempotent migrations** - Safe to run multiple times
- **Migration tracking** - Prevents duplicate application
- **Multiple deployment paths** - Works in Kubernetes, Docker, and local development

## Migration Files

Migrations are stored in two locations (synced automatically):
- `supabase/migrations/` - Primary location for all migrations
- `init-db/migrations/` - Synced from supabase/migrations for Kubernetes ConfigMaps

### Migration Naming Convention

Migrations must follow the pattern: `YYYYMMDDHHMMSS_description.sql`

Example: `20251128000001_add_review_reports.sql`

## Automatic Migration Application

### 1. Backend Startup (Primary Method)

The backend application automatically runs migrations on startup via `backend/main.py`:

```python
# In lifespan() function
from backend.database.migrate import run_migrations
migration_success = await run_migrations(DATABASE_URL)
```

**Benefits:**
- Runs on every pod startup
- Ensures migrations are always applied
- No separate job required

### 2. Init Container (EKS Production)

For EKS production, an init container runs migrations before the backend starts:

```yaml
initContainers:
- name: run-migrations
  image: ghcr.io/soumantrivedi/ideaforge-ai/backend:latest
  command: ["python3", "-m", "backend.database.migrate"]
```

**Benefits:**
- Runs before backend starts
- Fails fast if migrations fail
- Prevents backend from starting with outdated schema

### 3. DB Setup Job (Alternative)

A Kubernetes Job can be used for one-time setup:

```bash
kubectl apply -f k8s/eks/db-setup-job.yaml
```

## Migration Tracking

The system uses a `schema_migrations` table to track applied migrations:

```sql
CREATE TABLE schema_migrations (
  id SERIAL PRIMARY KEY,
  migration_name VARCHAR(255) UNIQUE NOT NULL,
  applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

This prevents:
- Duplicate application of migrations
- Out-of-order execution
- Missing migrations

## Creating New Migrations

1. Create a new SQL file in `supabase/migrations/`:
   ```bash
   touch supabase/migrations/$(date +%Y%m%d%H%M%S)_your_description.sql
   ```

2. Write idempotent SQL:
   ```sql
   -- Use IF NOT EXISTS, IF EXISTS, etc.
   CREATE TABLE IF NOT EXISTS new_table (...);
   ALTER TABLE existing_table ADD COLUMN IF NOT EXISTS new_column TEXT;
   ```

3. Sync to init-db (automatic via script):
   ```bash
   # The create-db-configmaps.sh script handles this
   ```

4. Commit and push - migrations will be applied automatically on next deployment

## Migration Best Practices

1. **Always use IF NOT EXISTS / IF EXISTS**
   ```sql
   CREATE TABLE IF NOT EXISTS ...
   ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...
   DROP TABLE IF EXISTS ...
   ```

2. **Include rollback considerations**
   - Document what the migration does
   - Consider data migration needs
   - Test on staging first

3. **Test migrations**
   - Test on local database
   - Test on staging environment
   - Verify idempotency (run twice)

4. **Order matters**
   - Migrations run in filename order
   - Ensure dependencies are created first

## Kubernetes

### ConfigMap Creation

The `k8s/create-db-configmaps.sh` script creates ConfigMaps with all migrations:

```bash
./k8s/create-db-configmaps.sh <namespace>
```

This script:
- Combines migrations from `supabase/migrations/` and `init-db/migrations/`
- Creates `db-migrations` ConfigMap
- Updates existing ConfigMap if it exists

### ConfigMap Mount

Migrations are mounted in:
- Init containers: `/migrations`
- Backend containers: `/migrations` (for startup migrations)

## Troubleshooting

### Migrations Not Running

1. Check if ConfigMap exists:
   ```bash
   kubectl get configmap db-migrations -n <namespace>
   ```

2. Check init container logs:
   ```bash
   kubectl logs <pod-name> -c run-migrations -n <namespace>
   ```

3. Check backend startup logs:
   ```bash
   kubectl logs <pod-name> -c backend -n <namespace> | grep migration
   ```

### Migration Failed

1. Check migration tracking:
   ```sql
   SELECT * FROM schema_migrations ORDER BY applied_at DESC;
   ```

2. Review migration file for syntax errors

3. Check database permissions

4. Fix migration and redeploy

## Current Migrations

All migrations are automatically synced and applied. Recent additions:
- `20251128000000_add_v0_project_tracking.sql` - V0 prototype tracking
- `20251128000001_add_review_reports.sql` - Review reports table

## Production Deployment

For EKS production:
1. Ensure ConfigMap is created: `./k8s/create-db-configmaps.sh <namespace>`
2. Deploy backend - migrations run automatically via init container
3. Verify: Check pod logs for migration success

No manual SQL execution is ever required.

