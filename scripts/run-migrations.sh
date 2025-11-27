#!/bin/bash
# Standalone script to run database migrations
# Can be used in init containers or as a separate job

set -e

echo "🔄 Running database migrations..."

# Get database connection details
POSTGRES_HOST=${POSTGRES_HOST:-postgres}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_USER=${POSTGRES_USER:-agentic_pm}
POSTGRES_DB=${POSTGRES_DB:-agentic_pm_db}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-}

export PGPASSWORD=$POSTGRES_PASSWORD

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
until pg_isready -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -p "$POSTGRES_PORT"; do
  echo "   PostgreSQL not ready, waiting..."
  sleep 2
done
echo "✅ PostgreSQL is ready"

# Find migration directories
MIGRATION_DIRS=(
  "/migrations"
  "/app/migrations"
  "/app/migrations-local"
)

MIGRATION_FILES=()

for dir in "${MIGRATION_DIRS[@]}"; do
  if [ -d "$dir" ]; then
    echo "📁 Found migration directory: $dir"
    while IFS= read -r -d '' file; do
      MIGRATION_FILES+=("$file")
    done < <(find "$dir" -name "*.sql" -type f -print0 | sort -z)
  fi
done

if [ ${#MIGRATION_FILES[@]} -eq 0 ]; then
  echo "⚠️  No migration files found in: ${MIGRATION_DIRS[*]}"
  exit 0
fi

echo "📋 Found ${#MIGRATION_FILES[@]} migration files"

# Create migration tracking table
echo "🔧 Creating migration tracking table..."
psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -p "$POSTGRES_PORT" <<EOF
CREATE TABLE IF NOT EXISTS schema_migrations (
  id SERIAL PRIMARY KEY,
  migration_name VARCHAR(255) UNIQUE NOT NULL,
  applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
EOF

# Run each migration
for migration_file in "${MIGRATION_FILES[@]}"; do
  migration_name=$(basename "$migration_file")
  
  # Check if already applied
  already_applied=$(psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -p "$POSTGRES_PORT" -t -c \
    "SELECT 1 FROM schema_migrations WHERE migration_name = '$migration_name';" 2>/dev/null | xargs || echo "")
  
  if [ -n "$already_applied" ]; then
    echo "   ⏭️  Skipping $migration_name (already applied)"
    continue
  fi
  
  echo "   🔄 Applying $migration_name..."
  
  # Run migration
  if psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -p "$POSTGRES_PORT" -f "$migration_file" 2>&1 | \
    grep -v "NOTICE" | \
    grep -v "^$" | \
    grep -v "already exists" | \
    grep -v "does not exist" | \
    grep -v "duplicate key" | \
    tee /tmp/migration_output.log; then
    
    # Mark as applied
    psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -p "$POSTGRES_PORT" -c \
      "INSERT INTO schema_migrations (migration_name) VALUES ('$migration_name') ON CONFLICT (migration_name) DO NOTHING;" >/dev/null 2>&1
    
    echo "   ✅ $migration_name applied successfully"
  else
    # Check if it's a safe-to-skip error
    if grep -qi "already exists\|does not exist\|duplicate" /tmp/migration_output.log 2>/dev/null; then
      echo "   ⚠️  $migration_name had safe-to-skip errors, marking as applied"
      psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -p "$POSTGRES_PORT" -c \
        "INSERT INTO schema_migrations (migration_name) VALUES ('$migration_name') ON CONFLICT (migration_name) DO NOTHING;" >/dev/null 2>&1
    else
      echo "   ❌ $migration_name failed"
      cat /tmp/migration_output.log
      exit 1
    fi
  fi
done

echo "✅ All migrations completed successfully"

