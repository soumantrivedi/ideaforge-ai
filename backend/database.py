"""Database connection and session management."""
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
import structlog

logger = structlog.get_logger()

# Database URL from environment
# Convert postgresql:// to postgresql+asyncpg:// if needed
raw_db_url = os.getenv(
    "DATABASE_URL",
    "postgresql://agentic_pm:devpassword@postgres:5432/agentic_pm_db"
)

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

