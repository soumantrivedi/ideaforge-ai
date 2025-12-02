# Database Migration Job Setup

## Overview

Database migrations are now configured to run as Kubernetes Jobs instead of init containers. This provides better control, visibility, and error handling for migrations.

## Architecture

### Migration Job (`db-migrations-job.yaml`)

- **Type**: Kubernetes Job
- **Purpose**: Run database migrations before backend deployment
- **Image**: Uses the same backend image tag as the deployment
- **Cleanup**: Automatically deleted after 1 hour (`ttlSecondsAfterFinished: 3600`)
- **Retry**: Up to 3 retries on failure (`backoffLimit: 3`)
- **Timeout**: 10 minutes maximum (`activeDeadlineSeconds: 600`)

### Deployment Flow

1. **Wait for Database Services**: PostgreSQL and Redis must be ready
2. **Run Migration Job**: Execute `db-migrations` job with backend image
3. **Verify Success**: Wait for job completion (fail deployment if migrations fail)
4. **Deploy Backend**: Only proceed if migrations completed successfully
5. **Deploy Frontend**: Deploy frontend after backend is ready

## Usage

### EKS Deployment

```bash
# Full deployment (includes migrations)
make eks-deploy-full \
  EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50 \
  BACKEND_IMAGE_TAG=672425b \
  FRONTEND_IMAGE_TAG=672425b
```

The Makefile will:
1. Prepare manifests with correct namespace and image tags
2. Wait for PostgreSQL and Redis to be ready
3. Update migration job with backend image tag
4. Delete any existing migration job
5. Create and run migration job
6. Wait for migrations to complete (fails deployment if migrations fail)
7. Deploy backend and frontend

### Manual Migration Execution

```bash
# Update migration job image tag
sed -i "s|ghcr.io/soumantrivedi/ideaforge-ai/backend:.*|ghcr.io/soumantrivedi/ideaforge-ai/backend:YOUR_TAG|g" k8s/eks/db-migrations-job.yaml

# Delete existing job (if any)
kubectl delete job db-migrations -n YOUR_NAMESPACE --ignore-not-found=true

# Apply migration job
kubectl apply -f k8s/eks/db-migrations-job.yaml

# Wait for completion
kubectl wait --for=condition=complete job/db-migrations -n YOUR_NAMESPACE --timeout=600s

# Check logs
kubectl logs -n YOUR_NAMESPACE job/db-migrations
```

## Error Handling

### Migration Failure

If migrations fail:
1. Deployment is **stopped** (backend will not deploy)
2. Migration job logs are displayed
3. Job status is shown
4. User must fix migration issues before continuing

### Checking Migration Status

```bash
# Check job status
kubectl get job db-migrations -n YOUR_NAMESPACE

# View logs
kubectl logs -n YOUR_NAMESPACE job/db-migrations

# Describe job for detailed status
kubectl describe job db-migrations -n YOUR_NAMESPACE
```

## Benefits

1. **Better Visibility**: Migration logs are separate and easier to debug
2. **Failure Isolation**: Migration failures don't block backend pods from starting
3. **Retry Logic**: Automatic retries on transient failures
4. **Resource Control**: Dedicated resources for migrations
5. **Cleanup**: Automatic cleanup of completed jobs
6. **Pre-deployment Validation**: Ensures database is ready before backend starts

## Migration Job Configuration

### Environment Variables

The migration job uses the same environment variables as the backend:
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `REDIS_URL` (optional)

### Volumes

- `/migrations`: ConfigMap `db-migrations` (if exists)
- `/app/migrations`: ConfigMap `db-migrations` (if exists)

The migration runner checks multiple paths:
1. `/migrations` (Kubernetes ConfigMap mount)
2. `/app/migrations` (Docker volume mount)
3. `supabase/migrations` (Local development)
4. `init-db/migrations` (Alternative local path)

## Troubleshooting

### Migration Job Stuck

```bash
# Check job status
kubectl describe job db-migrations -n YOUR_NAMESPACE

# Check pod logs
kubectl logs -n YOUR_NAMESPACE -l app=db-migration

# Delete and recreate
kubectl delete job db-migrations -n YOUR_NAMESPACE
kubectl apply -f k8s/eks/db-migrations-job.yaml
```

### Migration Already Applied

The migration runner tracks applied migrations in the `schema_migrations` table. If a migration is already applied, it will be skipped.

### Multiple SQL Statements

The migration runner now properly splits SQL files into individual statements, allowing migrations with multiple SQL commands (e.g., `ALTER TABLE`, `COMMENT ON COLUMN`).

## Backend Deployment Changes

### Removed

- `run-migrations` init container from `backend.yaml`
- `migrations` volume mount from backend pods

### Kept

- `wait-for-postgres` init container (still needed for pod startup)
- `wait-for-redis` init container (still needed for pod startup)

Backend pods now start faster since they don't wait for migrations to complete.

