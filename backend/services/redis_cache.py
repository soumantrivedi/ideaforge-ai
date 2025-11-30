"""Redis-based response cache service for distributed caching across multiple backend pods."""
import json
import structlog
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import redis.asyncio as redis
from backend.config import settings

logger = structlog.get_logger()


class RedisCache:
    """Redis-based cache for agent responses with TTL support."""
    
    def __init__(self, ttl: int = 3600):
        """Initialize Redis cache.
        
        Args:
            ttl: Time-to-live in seconds (default: 1 hour)
        """
        self._redis_client: Optional[redis.Redis] = None
        self._fallback_cache: Dict[str, tuple] = {}  # Fallback in-memory storage: {key: (timestamp, value)}
        self.ttl = ttl
        self._cache_prefix = "agent_cache:"
    
    async def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get or create Redis client."""
        if self._redis_client is None:
            try:
                redis_url = settings.redis_url
                self._redis_client = await redis.from_url(
                    redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                # Test connection
                await self._redis_client.ping()
                logger.info("redis_cache_connected", url=redis_url)
            except Exception as e:
                logger.warning("redis_cache_connection_failed", error=str(e), fallback="in-memory")
                self._redis_client = None
        return self._redis_client
    
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache."""
        try:
            redis_client = await self._get_redis_client()
            if redis_client:
                cache_key = f"{self._cache_prefix}{key}"
                data = await redis_client.get(cache_key)
                if data:
                    value = json.loads(data)
                    logger.debug("cache_hit_redis", key=key[:20])
                    return value
            else:
                # Fallback to in-memory storage
                if key in self._fallback_cache:
                    timestamp, value = self._fallback_cache[key]
                    # Check if expired
                    if (datetime.utcnow() - timestamp).total_seconds() < self.ttl:
                        logger.debug("cache_hit_memory", key=key[:20])
                        return value
                    else:
                        # Expired, remove it
                        del self._fallback_cache[key]
        except Exception as e:
            logger.warning("cache_retrieval_error", error=str(e), key=key[:20])
            # Fallback to in-memory storage
            if key in self._fallback_cache:
                timestamp, value = self._fallback_cache[key]
                if (datetime.utcnow() - timestamp).total_seconds() < self.ttl:
                    return value
                else:
                    del self._fallback_cache[key]
        return None
    
    async def set(self, key: str, value: Any) -> bool:
        """Store value in cache."""
        try:
            redis_client = await self._get_redis_client()
            if redis_client:
                cache_key = f"{self._cache_prefix}{key}"
                data = json.dumps(value, default=str)
                await redis_client.setex(cache_key, self.ttl, data)
                logger.debug("cache_set_redis", key=key[:20])
                return True
            else:
                # Fallback to in-memory storage
                self._fallback_cache[key] = (datetime.utcnow(), value)
                logger.debug("cache_set_memory", key=key[:20])
                return True
        except Exception as e:
            logger.error("cache_storage_error", error=str(e), key=key[:20])
            # Fallback to in-memory storage
            self._fallback_cache[key] = (datetime.utcnow(), value)
            return True
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            redis_client = await self._get_redis_client()
            if redis_client:
                cache_key = f"{self._cache_prefix}{key}"
                await redis_client.delete(cache_key)
                logger.debug("cache_delete_redis", key=key[:20])
            else:
                # Fallback to in-memory storage
                if key in self._fallback_cache:
                    del self._fallback_cache[key]
                    logger.debug("cache_delete_memory", key=key[:20])
            return True
        except Exception as e:
            logger.warning("cache_deletion_error", error=str(e), key=key[:20])
            if key in self._fallback_cache:
                del self._fallback_cache[key]
            return True
    
    async def clear(self) -> bool:
        """Clear all cache entries."""
        try:
            redis_client = await self._get_redis_client()
            if redis_client:
                # Delete all keys with prefix
                keys = await redis_client.keys(f"{self._cache_prefix}*")
                if keys:
                    await redis_client.delete(*keys)
                logger.info("cache_cleared_redis", count=len(keys))
            else:
                # Fallback to in-memory storage
                count = len(self._fallback_cache)
                self._fallback_cache.clear()
                logger.info("cache_cleared_memory", count=count)
            return True
        except Exception as e:
            logger.error("cache_clear_error", error=str(e))
            self._fallback_cache.clear()
            return True
    
    async def close(self):
        """Close Redis connection."""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None


# Global cache instance
_cache_instance: Optional[RedisCache] = None


async def get_cache() -> RedisCache:
    """Get or create global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache(ttl=3600)  # 1 hour default
    return _cache_instance

