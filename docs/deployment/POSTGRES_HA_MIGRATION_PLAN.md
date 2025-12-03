# PostgreSQL HA Migration Plan

## Overview

This document outlines the plan to migrate from a single-replica PostgreSQL Deployment to a High Availability (HA) setup with 3 replicas using PostgreSQL streaming replication.

## Pre-Migration Checklist

### ✅ Completed
- [x] Created complete database dump (custom format + SQL)
  - Location: `/tmp/postgres-full-backup-20251202-224805.dump`
  - SQL dump: `/tmp/postgres-schema-and-data-20251202-224809.sql`
  - Size: 1.0MB (custom), 4.0MB (SQL)
  - Tables: 25 tables with all data

- [x] Reviewed migration scripts
  - All migrations are idempotent
  - Migration system handles HA scenarios
  - Migration tracking table exists

### ⚠️ Required Before Migration

1. **Add Replication Password to Secrets**
   ```bash
   kubectl patch secret ideaforge-ai-secrets -n 20890-ideaforge-ai-dev-58a50 \
     --type='json' \
     -p='[{"op": "add", "path": "/data/POSTGRES_REPLICATION_PASSWORD", "value": "'$(echo -n 'REPLICATION_PASSWORD_HERE' | base64)'"}]'
   ```

2. **Verify Database Backup**
   ```bash
   # Verify backup integrity
   pg_restore --list /tmp/postgres-full-backup-20251202-224805.dump | head -20
   ```

3. **Test Backup Restoration** (in a test environment)
   ```bash
   # Create test database
   createdb test_restore
   
   # Restore backup
   pg_restore -d test_restore /tmp/postgres-full-backup-20251202-224805.dump
   
   # Verify data
   psql -d test_restore -c "SELECT COUNT(*) FROM user_profiles;"
   ```

## Migration Steps

### Step 1: Backup Current Database
```bash
# Already completed - backups are in /tmp/
# Verify backups are accessible and complete
ls -lh /tmp/postgres-*-backup-*.dump
ls -lh /tmp/postgres-schema-and-data-*.sql
```

### Step 2: Add Replication Password
```bash
export KUBECONFIG=/tmp/kubeconfig.JYmAbF
export EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50

# Generate secure password
REPLICATION_PASSWORD=$(openssl rand -base64 32)

# Add to secret
kubectl patch secret ideaforge-ai-secrets -n $EKS_NAMESPACE \
  --type='json' \
  -p="[{\"op\": \"add\", \"path\": \"/data/POSTGRES_REPLICATION_PASSWORD\", \"value\": \"$(echo -n "$REPLICATION_PASSWORD" | base64)\"}]"
```

### Step 3: Deploy HA StatefulSet
```bash
# Apply HA configuration
kubectl apply -f k8s/eks/postgres-ha-simple.yaml

# Wait for StatefulSet to be ready
kubectl wait --for=condition=ready pod -l app=postgres-ha -n $EKS_NAMESPACE --timeout=600s
```

### Step 4: Verify Primary Node
```bash
# Check primary node status
kubectl exec -n $EKS_NAMESPACE postgres-ha-0 -- psql -U agentic_pm -d agentic_pm_db -c "SELECT pg_is_in_recovery();"
# Should return: f (false - not in recovery, so it's the primary)

# Check replication slots
kubectl exec -n $EKS_NAMESPACE postgres-ha-0 -- psql -U agentic_pm -d agentic_pm_db -c "SELECT * FROM pg_replication_slots;"
```

### Step 5: Verify Replica Nodes
```bash
# Check replica nodes
kubectl exec -n $EKS_NAMESPACE postgres-ha-1 -- psql -U agentic_pm -d agentic_pm_db -c "SELECT pg_is_in_recovery();"
# Should return: t (true - in recovery, so it's a replica)

# Check replication lag
kubectl exec -n $EKS_NAMESPACE postgres-ha-1 -- psql -U agentic_pm -d agentic_pm_db -c "SELECT pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn();"
```

### Step 6: Restore Data to Primary (if needed)
```bash
# Only if starting fresh - otherwise data will be preserved from PVC
# This step is only needed if we're creating new volumes

# Copy backup to primary pod
kubectl cp /tmp/postgres-full-backup-20251202-224805.dump \
  $EKS_NAMESPACE/postgres-ha-0:/tmp/backup.dump

# Restore backup
kubectl exec -n $EKS_NAMESPACE postgres-ha-0 -- \
  pg_restore -U agentic_pm -d agentic_pm_db -v /tmp/backup.dump
```

### Step 7: Update Application Connection String
```bash
# Update backend to use postgres-ha service
# The service will route to postgres-ha-0 (primary) for writes
# For reads, can use postgres-ha-1 and postgres-ha-2 (replicas)

# Update ConfigMap if needed
kubectl get configmap ideaforge-ai-config -n $EKS_NAMESPACE -o yaml
# POSTGRES_HOST should be: postgres-ha-0.postgres-ha (for writes)
# Or: postgres-ha (service, routes to primary)
```

### Step 8: Scale Down Old Deployment
```bash
# Scale down old single-replica deployment
kubectl scale deployment postgres -n $EKS_NAMESPACE --replicas=0

# Wait for pods to terminate
kubectl wait --for=delete pod -l app=postgres -n $EKS_NAMESPACE --timeout=300s
```

### Step 9: Verify Application Connectivity
```bash
# Check backend pods can connect to new HA setup
kubectl exec -n $EKS_NAMESPACE $(kubectl get pod -l app=backend -n $EKS_NAMESPACE -o jsonpath='{.items[0].metadata.name}') -- \
  python3 -c "import asyncio; from sqlalchemy.ext.asyncio import create_async_engine; engine = create_async_engine('postgresql+asyncpg://agentic_pm:devpassword@postgres-ha:5432/agentic_pm_db'); print('Connection successful')"
```

### Step 10: Monitor and Validate
```bash
# Monitor replication status
watch -n 5 'kubectl exec -n 20890-ideaforge-ai-dev-58a50 postgres-ha-0 -- psql -U agentic_pm -d agentic_pm_db -c "SELECT client_addr, state, sync_state FROM pg_stat_replication;"'

# Check application logs
kubectl logs -n $EKS_NAMESPACE -l app=backend --tail=50
```

## Rollback Plan

If migration fails:

1. **Scale up old deployment**
   ```bash
   kubectl scale deployment postgres -n $EKS_NAMESPACE --replicas=1
   ```

2. **Update application to use old service**
   ```bash
   # Update POSTGRES_HOST back to 'postgres'
   kubectl patch configmap ideaforge-ai-config -n $EKS_NAMESPACE \
     --type='json' \
     -p='[{"op": "replace", "path": "/data/POSTGRES_HOST", "value": "postgres"}]'
   ```

3. **Delete HA StatefulSet**
   ```bash
   kubectl delete statefulset postgres-ha -n $EKS_NAMESPACE
   ```

4. **Restore from backup if data was lost**
   ```bash
   kubectl cp /tmp/postgres-full-backup-20251202-224805.dump \
     $EKS_NAMESPACE/postgres-xxx:/tmp/backup.dump
   
   kubectl exec -n $EKS_NAMESPACE postgres-xxx -- \
     pg_restore -U agentic_pm -d agentic_pm_db -v /tmp/backup.dump
   ```

## Post-Migration Tasks

1. **Update Documentation**
   - Update connection strings in documentation
   - Document failover procedures
   - Document backup/restore procedures

2. **Set Up Monitoring**
   - Monitor replication lag
   - Monitor primary/replica health
   - Set up alerts for failover scenarios

3. **Test Failover**
   - Test manual failover procedures
   - Test automatic failover (if using Patroni or operator)
   - Document failover procedures

4. **Backup Strategy**
   - Set up automated backups from primary
   - Test backup restoration regularly
   - Document backup procedures

## Notes

- **Data Preservation**: The existing PVC will be preserved, but we're creating new PVCs for HA setup
- **Migration Scripts**: All migration scripts are idempotent and will work with HA setup
- **Connection Pooling**: Application connection pool should be configured to handle primary/replica routing
- **Read Replicas**: Can use replicas for read-only queries to distribute load

## References

- PostgreSQL Streaming Replication: https://www.postgresql.org/docs/15/warm-standby.html
- Kubernetes StatefulSets: https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/
- pgvector: https://github.com/pgvector/pgvector

