"""Token storage service using Redis for distributed token management."""
import json
import structlog
from typing import Optional, Dict
from datetime import datetime, timedelta
import redis.asyncio as redis
from backend.config import settings

logger = structlog.get_logger()


class TokenStorage:
    """Token storage using Redis for distributed access across multiple backend pods."""
    
    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
        self._fallback_tokens: Dict[str, dict] = {}  # Fallback in-memory storage
    
    async def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get or create Redis client."""
        if self._redis_client is None:
            try:
                # Parse Redis URL
                redis_url = settings.redis_url
                self._redis_client = await redis.from_url(
                    redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                # Test connection
                await self._redis_client.ping()
                logger.info("redis_connected", url=redis_url)
            except Exception as e:
                logger.warning("redis_connection_failed", error=str(e), fallback="in-memory")
                self._redis_client = None
        return self._redis_client
    
    async def store_token(self, token: str, token_data: dict, expires_in_seconds: int = 604800) -> bool:
        """Store token in Redis with expiration."""
        try:
            redis_client = await self._get_redis_client()
            if redis_client:
                # Store in Redis with expiration
                key = f"token:{token}"
                await redis_client.setex(
                    key,
                    expires_in_seconds,
                    json.dumps(token_data)
                )
                logger.debug("token_stored_redis", token=token[:10] + "...")
                return True
            else:
                # Fallback to in-memory storage
                self._fallback_tokens[token] = token_data
                logger.debug("token_stored_memory", token=token[:10] + "...")
                return True
        except Exception as e:
            logger.error("token_storage_error", error=str(e))
            # Fallback to in-memory storage
            self._fallback_tokens[token] = token_data
            return True
    
    async def get_token(self, token: str) -> Optional[dict]:
        """Get token data from Redis or fallback storage."""
        try:
            redis_client = await self._get_redis_client()
            if redis_client:
                key = f"token:{token}"
                data = await redis_client.get(key)
                if data:
                    token_data = json.loads(data)
                    logger.debug("token_retrieved_redis", token=token[:10] + "...")
                    return token_data
            else:
                # Fallback to in-memory storage
                if token in self._fallback_tokens:
                    logger.debug("token_retrieved_memory", token=token[:10] + "...")
                    return self._fallback_tokens[token]
        except Exception as e:
            logger.warning("token_retrieval_error", error=str(e))
            # Fallback to in-memory storage
            if token in self._fallback_tokens:
                return self._fallback_tokens[token]
        return None
    
    async def delete_token(self, token: str) -> bool:
        """Delete token from Redis or fallback storage."""
        try:
            redis_client = await self._get_redis_client()
            if redis_client:
                key = f"token:{token}"
                await redis_client.delete(key)
                logger.debug("token_deleted_redis", token=token[:10] + "...")
            else:
                # Fallback to in-memory storage
                if token in self._fallback_tokens:
                    del self._fallback_tokens[token]
                    logger.debug("token_deleted_memory", token=token[:10] + "...")
            return True
        except Exception as e:
            logger.warning("token_deletion_error", error=str(e))
            # Fallback to in-memory storage
            if token in self._fallback_tokens:
                del self._fallback_tokens[token]
            return True
    
    async def close(self):
        """Close Redis connection."""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None


# Global token storage instance
_token_storage: Optional[TokenStorage] = None


async def get_token_storage() -> TokenStorage:
    """Get or create global token storage instance."""
    global _token_storage
    if _token_storage is None:
        _token_storage = TokenStorage()
    return _token_storage

