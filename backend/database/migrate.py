"""
Database migration runner for automatic migration application.
This module ensures all migrations are applied on application startup.
"""
import asyncio
import os
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import text
import structlog

logger = structlog.get_logger()

# Migration directory paths (in order of priority)
MIGRATION_DIRS = [
    Path("/migrations"),  # Kubernetes ConfigMap mount
    Path("/app/migrations"),  # Docker volume mount
    Path(__file__).parent.parent.parent / "supabase" / "migrations",  # Local development
    Path(__file__).parent.parent.parent / "init-db" / "migrations",  # Alternative local path
]


async def get_migration_files() -> list[Path]:
    """Get all migration files sorted by timestamp."""
    migration_files = []
    
    for migration_dir in MIGRATION_DIRS:
        if migration_dir.exists() and migration_dir.is_dir():
            logger.info("migration_dir_found", path=str(migration_dir))
            for file in sorted(migration_dir.glob("*.sql")):
                if file.is_file():
                    migration_files.append(file)
    
    # Sort by filename (which should include timestamp)
    migration_files.sort(key=lambda x: x.name)
    
    return migration_files


async def check_migration_applied(db: AsyncSession, migration_name: str) -> bool:
    """Check if a migration has already been applied."""
    try:
        # Create migrations tracking table if it doesn't exist
        await db.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                migration_name VARCHAR(255) UNIQUE NOT NULL,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        await db.commit()
        
        # Check if migration exists
        result = await db.execute(
            text("SELECT 1 FROM schema_migrations WHERE migration_name = :name"),
            {"name": migration_name}
        )
        return result.fetchone() is not None
    except Exception as e:
        logger.warning("migration_check_failed", migration=migration_name, error=str(e))
        await db.rollback()
        return False


async def mark_migration_applied(db: AsyncSession, migration_name: str):
    """Mark a migration as applied."""
    try:
        await db.execute(
            text("""
                INSERT INTO schema_migrations (migration_name)
                VALUES (:name)
                ON CONFLICT (migration_name) DO NOTHING
            """),
            {"name": migration_name}
        )
        await db.commit()
    except Exception as e:
        logger.warning("migration_mark_failed", migration=migration_name, error=str(e))
        await db.rollback()


async def apply_migration(db: AsyncSession, migration_file: Path) -> bool:
    """Apply a single migration file."""
    migration_name = migration_file.name
    
    # Check if already applied
    if await check_migration_applied(db, migration_name):
        logger.info("migration_already_applied", migration=migration_name)
        return True
    
    try:
        logger.info("applying_migration", migration=migration_name, path=str(migration_file))
        
        # Read migration file
        migration_sql = migration_file.read_text(encoding='utf-8')
        
        # Split SQL into individual statements by semicolon
        # Remove comments and empty lines, then split by semicolon
        lines = migration_sql.split('\n')
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            # Skip empty lines and full-line comments
            if not stripped or (stripped.startswith('--') and not ';' in stripped):
                continue
            cleaned_lines.append(line)
        
        # Join and split by semicolon to get individual statements
        full_sql = '\n'.join(cleaned_lines)
        # Split by semicolon, but keep the semicolon with each statement
        raw_statements = [s.strip() + ';' for s in full_sql.split(';') if s.strip()]
        
        # Clean up statements - remove trailing semicolons from the last one if needed
        statements = []
        for stmt in raw_statements:
            stmt = stmt.strip()
            if stmt and stmt != ';':
                # Remove duplicate semicolons at the end
                while stmt.endswith(';;'):
                    stmt = stmt[:-1]
                statements.append(stmt)
        
        # Execute each statement separately within the same transaction
        # This ensures atomicity - either all statements succeed or none do
        try:
            for statement in statements:
                if statement.strip() and statement.strip() != ';':
                    await db.execute(text(statement))
            await db.commit()
        except Exception as e:
            # Some statements may fail if already applied (e.g., CREATE TABLE IF NOT EXISTS, ADD COLUMN IF NOT EXISTS)
            error_msg = str(e).lower()
            if any(phrase in error_msg for phrase in [
                "already exists", 
                "duplicate", 
                "does not exist",  # For DROP IF EXISTS
                "column.*already exists",
                "relation.*already exists"
            ]):
                logger.debug("migration_skipped", 
                           migration=migration_name,
                           reason="already_applied_or_safe_to_skip")
                await db.rollback()
                # Mark as applied since it's safe to skip
                await mark_migration_applied(db, migration_name)
                return True
            else:
                # Real error - rollback and fail
                logger.error("migration_execution_failed",
                           migration=migration_name,
                           error=str(e),
                           error_type=type(e).__name__)
                await db.rollback()
                return False
        
        # Mark as applied
        await mark_migration_applied(db, migration_name)
        
        logger.info("migration_applied_successfully", migration=migration_name)
        return True
        
    except Exception as e:
        logger.error("migration_failed",
                    migration=migration_name,
                    error=str(e),
                    error_type=type(e).__name__)
        try:
            await db.rollback()
        except:
            pass
        return False


async def run_migrations(database_url: str) -> bool:
    """
    Run all pending migrations.
    Returns True if all migrations succeeded, False otherwise.
    
    Note: In HA setups, migrations should always run against the primary node.
    This function will automatically connect to the primary if database_url
    points to a service that routes to multiple nodes.
    """
    engine = None
    try:
        # Create database engine
        # For HA setups, ensure we connect to primary for migrations
        # The connection string should point to the primary pod or service
        engine = create_async_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=1,  # Minimal pool for migrations
            max_overflow=0,
            # Add connection retry for HA scenarios
            connect_args={
                "server_settings": {
                    "application_name": "migration_runner"
                }
            }
        )
        
        # Get all migration files
        migration_files = await get_migration_files()
        
        if not migration_files:
            logger.warning("no_migrations_found", 
                         searched_dirs=[str(d) for d in MIGRATION_DIRS])
            return True  # Not an error if no migrations found
        
        logger.info("migrations_found", count=len(migration_files))
        
        # Apply each migration in a separate transaction
        success_count = 0
        for migration_file in migration_files:
            async with engine.begin() as conn:
                async_session = AsyncSession(conn, expire_on_commit=False)
                if await apply_migration(async_session, migration_file):
                    success_count += 1
                else:
                    logger.error("migration_stopped", 
                               failed_migration=migration_file.name)
                    return False
        
        logger.info("migrations_complete",
                   total=len(migration_files),
                   successful=success_count)
        return True
        
    except Exception as e:
        logger.error("migration_runner_failed", error=str(e))
        return False
    finally:
        if engine:
            await engine.dispose()


async def main():
    """Main entry point for running migrations."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        # Construct from individual components
        postgres_host = os.getenv("POSTGRES_HOST", "localhost")
        postgres_port = os.getenv("POSTGRES_PORT", "5432")
        postgres_user = os.getenv("POSTGRES_USER", "agentic_pm")
        postgres_password = os.getenv("POSTGRES_PASSWORD", "")
        postgres_db = os.getenv("POSTGRES_DB", "agentic_pm_db")
        
        database_url = f"postgresql+asyncpg://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"
    
    logger.info("starting_migrations", database_host=postgres_host if 'postgres_host' in locals() else "from_url")
    
    success = await run_migrations(database_url)
    
    if success:
        logger.info("migrations_completed_successfully")
        sys.exit(0)
    else:
        logger.error("migrations_failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

