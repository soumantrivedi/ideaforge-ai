"""Database connection and session management."""
import os
from typing import Optional
from fastapi import Request
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
import structlog

logger = structlog.get_logger()

# Database URL from environment
# If DATABASE_URL is not set or contains $(POSTGRES_PASSWORD), construct it from individual components
raw_db_url = os.getenv("DATABASE_URL", "")
if not raw_db_url or "$(POSTGRES_PASSWORD)" in raw_db_url:
    # Construct DATABASE_URL from individual POSTGRES_* environment variables
    postgres_user = os.getenv("POSTGRES_USER", "agentic_pm")
    postgres_password = os.getenv("POSTGRES_PASSWORD", "devpassword")
    postgres_host = os.getenv("POSTGRES_HOST", "postgres")
    postgres_port = os.getenv("POSTGRES_PORT", "5432")
    postgres_db = os.getenv("POSTGRES_DB", "agentic_pm_db")
    raw_db_url = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"

# Ensure we use asyncpg driver
if raw_db_url.startswith("postgresql://"):
    DATABASE_URL = raw_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif not raw_db_url.startswith("postgresql+asyncpg://"):
    DATABASE_URL = f"postgresql+asyncpg://{raw_db_url}"
else:
    DATABASE_URL = raw_db_url

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


async def get_db() -> AsyncSession:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_db_with_user(user_id: Optional[str] = None) -> AsyncSession:
    """Get database session with user context for RLS."""
    async with AsyncSessionLocal() as session:
        try:
            # Set user context for RLS policies
            if user_id:
                await session.execute(text(f"SET LOCAL app.current_user_id = '{user_id}'"))
            else:
                await session.execute(text("SET LOCAL app.current_user_id = '00000000-0000-0000-0000-000000000000'"))
            
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database connection and verify."""
    try:
        async with engine.begin() as conn:
            # Test connection
            result = await conn.execute(text("SELECT 1"))
            result.scalar()
            logger.info("database_connected", status="success")
            return True
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))
        return False


async def check_db_health() -> bool:
    """Check if database is healthy."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            result.scalar()
            return True
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        return False

