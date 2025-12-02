"""
Test script for McKinsey SSO migration.
Verifies that the migration runs successfully and creates all required columns and indexes.
"""
import asyncio
import os
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
import structlog

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from database.migrate import run_migrations

logger = structlog.get_logger()


async def verify_migration():
    """Verify that the McKinsey SSO migration was applied correctly."""
    
    # Get database URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        postgres_host = os.getenv("POSTGRES_HOST", "localhost")
        postgres_port = os.getenv("POSTGRES_PORT", "5432")
        postgres_user = os.getenv("POSTGRES_USER", "agentic_pm")
        postgres_password = os.getenv("POSTGRES_PASSWORD", "devpassword")
        postgres_db = os.getenv("POSTGRES_DB", "agentic_pm_db")
        database_url = f"postgresql+asyncpg://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"
    
    engine = create_async_engine(database_url, echo=False)
    
    try:
        async with engine.begin() as conn:
            session = AsyncSession(conn, expire_on_commit=False)
            
            # Check if migration was applied
            result = await session.execute(
                text("SELECT 1 FROM schema_migrations WHERE migration_name = '20251202000000_add_mckinsey_sso_fields.sql'")
            )
            migration_applied = result.fetchone() is not None
            
            if not migration_applied:
                logger.error("migration_not_applied", migration="20251202000000_add_mckinsey_sso_fields.sql")
                return False
            
            logger.info("migration_applied", migration="20251202000000_add_mckinsey_sso_fields.sql")
            
            # Verify all columns exist
            expected_columns = [
                'mckinsey_subject',
                'mckinsey_email',
                'mckinsey_refresh_token_encrypted',
                'mckinsey_token_expires_at',
                'mckinsey_fmno',
                'mckinsey_preferred_username',
                'mckinsey_session_state'
            ]
            
            for column in expected_columns:
                result = await session.execute(
                    text("""
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'user_profiles' AND column_name = :column_name
                    """),
                    {"column_name": column}
                )
                if result.fetchone() is None:
                    logger.error("column_missing", column=column)
                    return False
                logger.info("column_verified", column=column)
            
            # Verify indexes exist
            expected_indexes = [
                'idx_user_profiles_mckinsey_subject',
                'idx_user_profiles_mckinsey_email',
                'idx_user_profiles_mckinsey_fmno'
            ]
            
            for index in expected_indexes:
                result = await session.execute(
                    text("""
                        SELECT 1 FROM pg_indexes 
                        WHERE tablename = 'user_profiles' AND indexname = :index_name
                    """),
                    {"index_name": index}
                )
                if result.fetchone() is None:
                    logger.error("index_missing", index=index)
                    return False
                logger.info("index_verified", index=index)
            
            # Verify backward compatibility - check that existing user_profiles records still work
            result = await session.execute(
                text("SELECT COUNT(*) FROM user_profiles")
            )
            user_count = result.scalar()
            logger.info("existing_users_verified", count=user_count)
            
            # Test inserting a user with McKinsey SSO fields
            test_user_id = "00000000-0000-0000-0000-000000000001"
            await session.execute(
                text("""
                    INSERT INTO user_profiles (
                        id, email, full_name, 
                        mckinsey_subject, mckinsey_email, mckinsey_fmno,
                        mckinsey_preferred_username, mckinsey_session_state
                    ) VALUES (
                        :id, :email, :full_name,
                        :mckinsey_subject, :mckinsey_email, :mckinsey_fmno,
                        :mckinsey_preferred_username, :mckinsey_session_state
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        mckinsey_subject = EXCLUDED.mckinsey_subject,
                        mckinsey_email = EXCLUDED.mckinsey_email,
                        mckinsey_fmno = EXCLUDED.mckinsey_fmno,
                        mckinsey_preferred_username = EXCLUDED.mckinsey_preferred_username,
                        mckinsey_session_state = EXCLUDED.mckinsey_session_state
                """),
                {
                    "id": test_user_id,
                    "email": "test.user@mckinsey.com",
                    "full_name": "Test User",
                    "mckinsey_subject": "test-subject-123",
                    "mckinsey_email": "test.user@mckinsey.com",
                    "mckinsey_fmno": "12345",
                    "mckinsey_preferred_username": "testuser",
                    "mckinsey_session_state": "test-session-state"
                }
            )
            await session.commit()
            logger.info("test_user_inserted", user_id=test_user_id)
            
            # Verify the test user was inserted correctly
            result = await session.execute(
                text("""
                    SELECT mckinsey_subject, mckinsey_email, mckinsey_fmno 
                    FROM user_profiles 
                    WHERE id = :id
                """),
                {"id": test_user_id}
            )
            row = result.fetchone()
            if row is None:
                logger.error("test_user_not_found")
                return False
            
            if row[0] != "test-subject-123" or row[1] != "test.user@mckinsey.com" or row[2] != "12345":
                logger.error("test_user_data_mismatch", data=row)
                return False
            
            logger.info("test_user_verified", data=row)
            
            # Clean up test user
            await session.execute(
                text("DELETE FROM user_profiles WHERE id = :id"),
                {"id": test_user_id}
            )
            await session.commit()
            logger.info("test_user_cleaned_up")
            
            logger.info("migration_verification_complete", status="SUCCESS")
            return True
            
    except Exception as e:
        logger.error("migration_verification_failed", error=str(e), error_type=type(e).__name__)
        return False
    finally:
        await engine.dispose()


async def main():
    """Main entry point for testing the migration."""
    logger.info("starting_migration_test")
    
    # Run migrations
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        postgres_host = os.getenv("POSTGRES_HOST", "localhost")
        postgres_port = os.getenv("POSTGRES_PORT", "5432")
        postgres_user = os.getenv("POSTGRES_USER", "agentic_pm")
        postgres_password = os.getenv("POSTGRES_PASSWORD", "devpassword")
        postgres_db = os.getenv("POSTGRES_DB", "agentic_pm_db")
        database_url = f"postgresql+asyncpg://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"
    
    logger.info("running_migrations")
    success = await run_migrations(database_url)
    
    if not success:
        logger.error("migrations_failed")
        sys.exit(1)
    
    logger.info("migrations_completed", status="SUCCESS")
    
    # Verify migration
    logger.info("verifying_migration")
    verification_success = await verify_migration()
    
    if verification_success:
        logger.info("migration_test_complete", status="SUCCESS")
        sys.exit(0)
    else:
        logger.error("migration_test_failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
