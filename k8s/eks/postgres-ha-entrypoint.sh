#!/bin/bash
# PostgreSQL HA Entrypoint Script
# This script handles initialization for both primary and replica nodes

set -e

# Determine if this is the primary (first pod) or replica
POD_INDEX=${POD_NAME##*-}

if [ "$POD_INDEX" = "0" ]; then
  # Primary node
  echo "Initializing primary PostgreSQL node..."
  
  # If data directory is empty, let docker-entrypoint.sh initialize it
  # Otherwise, configure replication settings
  if [ ! -f "$PGDATA/PG_VERSION" ]; then
    echo "Data directory empty, will be initialized by docker-entrypoint.sh"
    # docker-entrypoint.sh will handle initialization as postgres user
    # We just need to configure replication after init
    exec /usr/local/bin/docker-entrypoint.sh postgres \
      -c wal_level=replica \
      -c max_wal_senders=10 \
      -c max_replication_slots=10 \
      -c hot_standby=on \
      -c hot_standby_feedback=on \
      -c max_connections=500 \
      -c shared_buffers=1GB \
      -c effective_cache_size=3GB \
      -c maintenance_work_mem=256MB \
      -c checkpoint_completion_target=0.9 \
      -c wal_buffers=16MB \
      -c default_statistics_target=100 \
      -c random_page_cost=1.1 \
      -c effective_io_concurrency=200 \
      -c work_mem=8MB \
      -c min_wal_size=1GB \
      -c max_wal_size=4GB \
      -c max_worker_processes=4 \
      -c max_parallel_workers_per_gather=2 \
      -c max_parallel_workers=4
  else
    # Data exists - configure replication and start
    echo "Data directory exists, configuring replication..."
    
    # Update postgresql.conf for replication if not already configured
    if ! grep -q "wal_level = replica" "$PGDATA/postgresql.conf" 2>/dev/null; then
      cat >> "$PGDATA/postgresql.conf" <<EOF

# Replication settings (added by HA setup)
wal_level = replica
max_wal_senders = 10
max_replication_slots = 10
hot_standby = on
hot_standby_feedback = on
EOF
    fi
    
    # Update pg_hba.conf for replication if not already configured
    if ! grep -q "replication.*replicator" "$PGDATA/pg_hba.conf" 2>/dev/null; then
      echo "host replication $POSTGRES_REPLICATION_USER 0.0.0.0/0 md5" >> "$PGDATA/pg_hba.conf"
    fi
    
    # Start PostgreSQL with performance settings
    exec /usr/local/bin/docker-entrypoint.sh postgres \
      -c max_connections=500 \
      -c shared_buffers=1GB \
      -c effective_cache_size=3GB \
      -c maintenance_work_mem=256MB \
      -c checkpoint_completion_target=0.9 \
      -c wal_buffers=16MB \
      -c default_statistics_target=100 \
      -c random_page_cost=1.1 \
      -c effective_io_concurrency=200 \
      -c work_mem=8MB \
      -c min_wal_size=1GB \
      -c max_wal_size=4GB \
      -c max_worker_processes=4 \
      -c max_parallel_workers_per_gather=2 \
      -c max_parallel_workers=4
  fi
else
  # Replica node
  echo "Initializing replica PostgreSQL node (index: $POD_INDEX)..."
  
  # Wait for primary to be ready
  PRIMARY_POD="postgres-ha-0.postgres-ha-headless"
  echo "Waiting for primary at $PRIMARY_POD..."
  
  # Wait up to 5 minutes for primary
  for i in {1..150}; do
    if pg_isready -h "$PRIMARY_POD" -U "$POSTGRES_USER" -d "$POSTGRES_DB" 2>/dev/null; then
      echo "Primary is ready!"
      break
    fi
    if [ $i -eq 150 ]; then
      echo "ERROR: Primary did not become ready within 5 minutes"
      exit 1
    fi
    echo "Waiting for primary PostgreSQL to be ready... ($i/150)"
    sleep 2
  done
  
  # Initialize replica if not already done
  if [ ! -f "$PGDATA/PG_VERSION" ]; then
    echo "Performing base backup from primary..."
    REPLICA_SLOT="replica_${POD_INDEX}"
    
    # Perform base backup from primary
    PGPASSWORD="$POSTGRES_REPLICATION_PASSWORD" pg_basebackup \
      -h "$PRIMARY_POD" \
      -U "$POSTGRES_REPLICATION_USER" \
      -D "$PGDATA" \
      -Fp \
      -Xs \
      -P \
      -R \
      -S "$REPLICA_SLOT" || {
        echo "Base backup failed, waiting 10s and retrying..."
        sleep 10
        PGPASSWORD="$POSTGRES_REPLICATION_PASSWORD" pg_basebackup \
          -h "$PRIMARY_POD" \
          -U "$POSTGRES_REPLICATION_USER" \
          -D "$PGDATA" \
          -Fp \
          -Xs \
          -P \
          -R \
          -S "$REPLICA_SLOT"
      }
    
    echo "Base backup completed successfully"
  else
    echo "Replica data directory already exists"
  fi
  
  # Start PostgreSQL in recovery mode
  exec /usr/local/bin/docker-entrypoint.sh postgres \
    -c hot_standby=on \
    -c hot_standby_feedback=on \
    -c max_connections=500 \
    -c shared_buffers=1GB \
    -c effective_cache_size=3GB \
    -c maintenance_work_mem=256MB \
    -c checkpoint_completion_target=0.9 \
    -c wal_buffers=16MB \
    -c default_statistics_target=100 \
    -c random_page_cost=1.1 \
    -c effective_io_concurrency=200 \
    -c work_mem=8MB \
    -c min_wal_size=1GB \
    -c max_wal_size=4GB \
    -c max_worker_processes=4 \
    -c max_parallel_workers_per_gather=2 \
    -c max_parallel_workers=4
fi

