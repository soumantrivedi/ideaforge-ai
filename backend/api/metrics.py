"""Metrics and monitoring endpoints for connection pool and performance monitoring."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, Any
import structlog
from datetime import datetime

from backend.database import get_db, engine
from backend.api.auth import get_current_user

logger = structlog.get_logger()
router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/connection-pool")
async def get_connection_pool_metrics(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get database connection pool metrics.
    Returns current pool status, size, and usage statistics.
    """
    try:
        pool = engine.pool
        
        # Get pool statistics
        metrics = {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid(),
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Calculate utilization
        total_connections = metrics["pool_size"] + metrics["overflow"]
        active_connections = metrics["checked_out"]
        utilization = (active_connections / total_connections * 100) if total_connections > 0 else 0
        
        metrics["utilization_percent"] = round(utilization, 2)
        metrics["available_connections"] = total_connections - active_connections
        
        # Health status
        if utilization > 90:
            metrics["status"] = "critical"
            metrics["message"] = "Connection pool nearly exhausted"
        elif utilization > 70:
            metrics["status"] = "warning"
            metrics["message"] = "High connection pool usage"
        else:
            metrics["status"] = "healthy"
            metrics["message"] = "Connection pool operating normally"
        
        logger.info("connection_pool_metrics", **metrics)
        return metrics
        
    except Exception as e:
        logger.error("connection_pool_metrics_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get connection pool metrics: {str(e)}")


@router.get("/database-health")
async def get_database_health(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get database health metrics including connection status and query performance.
    """
    try:
        start_time = datetime.utcnow()
        
        # Test query performance
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        
        query_time = (datetime.utcnow() - start_time).total_seconds() * 1000  # milliseconds
        
        # Get database version
        version_result = await db.execute(text("SELECT version()"))
        db_version = version_result.scalar()
        
        health = {
            "status": "healthy",
            "query_time_ms": round(query_time, 2),
            "database_version": db_version.split(',')[0] if db_version else "unknown",
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Determine health status based on query time
        if query_time > 1000:
            health["status"] = "degraded"
            health["message"] = "Slow database response"
        elif query_time > 500:
            health["status"] = "warning"
            health["message"] = "Elevated database response time"
        else:
            health["message"] = "Database responding normally"
        
        logger.info("database_health_check", **health)
        return health
        
    except Exception as e:
        logger.error("database_health_check_error", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.get("/cache-stats")
async def get_cache_stats(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get Redis cache statistics.
    """
    try:
        from backend.services.redis_cache import get_cache
        
        cache = await get_cache()
        
        # Try to get Redis info if available
        stats = {
            "cache_enabled": True,
            "cache_type": "redis",
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # If we have access to Redis client, get more stats
        if hasattr(cache, '_redis_client') and cache._redis_client:
            try:
                info = await cache._redis_client.info('stats')
                stats.update({
                    "keyspace_hits": info.get('keyspace_hits', 0),
                    "keyspace_misses": info.get('keyspace_misses', 0),
                    "total_commands_processed": info.get('total_commands_processed', 0),
                })
                
                # Calculate hit rate
                hits = stats.get("keyspace_hits", 0)
                misses = stats.get("keyspace_misses", 0)
                total = hits + misses
                hit_rate = (hits / total * 100) if total > 0 else 0
                stats["hit_rate_percent"] = round(hit_rate, 2)
            except:
                stats["message"] = "Redis stats not available"
        else:
            stats["cache_type"] = "in-memory (fallback)"
            stats["message"] = "Using in-memory cache fallback"
        
        return stats
        
    except Exception as e:
        logger.error("cache_stats_error", error=str(e))
        return {
            "cache_enabled": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.get("/agent-metrics")
async def get_agent_metrics(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get aggregated agent performance metrics.
    """
    try:
        from backend.agents.agno_orchestrator import AgnoAgenticOrchestrator
        
        # Get orchestrator instance
        # This is a simplified version - in production, you'd want to track metrics across all agent instances
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "agents": {},
            "summary": {
                "total_calls": 0,
                "total_time": 0.0,
                "avg_time": 0.0,
                "cache_hits": 0,
                "cache_misses": 0,
            }
        }
        
        # Note: In a production system, you'd want to collect metrics from all agent instances
        # This is a placeholder that shows the structure
        
        return metrics
        
    except Exception as e:
        logger.error("agent_metrics_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get agent metrics: {str(e)}")

