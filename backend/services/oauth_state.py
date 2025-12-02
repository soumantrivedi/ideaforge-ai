"""OAuth state and nonce management for CSRF protection."""

import secrets
import structlog
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import redis.asyncio as redis
from backend.config import settings

logger = structlog.get_logger()


class OAuthStateManager:
    """Manages OAuth state and nonce for CSRF protection.

    This class provides cryptographically secure state and nonce generation,
    storage in Redis with TTL, and validation with single-use enforcement.
    """

    def __init__(self, ttl: int = 600):
        """Initialize OAuth state manager.

        Args:
            ttl: Time-to-live in seconds (default: 600 seconds / 10 minutes)
        """
        self._redis_client: Optional[redis.Redis] = None
        self._fallback_storage: Dict[str, tuple] = (
            {}
        )  # Fallback: {key: (timestamp, value)}
        self.ttl = ttl
        self._state_prefix = "oauth:state:"
        self._nonce_prefix = "oauth:nonce:"

    async def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get or create Redis client."""
        if self._redis_client is None:
            try:
                redis_url = settings.redis_url
                self._redis_client = await redis.from_url(
                    redis_url, encoding="utf-8", decode_responses=True
                )
                # Test connection
                await self._redis_client.ping()
                logger.info("oauth_state_redis_connected", url=redis_url)
            except Exception as e:
                logger.warning(
                    "oauth_state_redis_connection_failed",
                    error=str(e),
                    fallback="in-memory",
                )
                self._redis_client = None
        return self._redis_client

    def _generate_secure_token(self, nbytes: int = 32) -> str:
        """Generate a cryptographically secure random token.

        Args:
            nbytes: Number of random bytes to generate (default: 32)

        Returns:
            URL-safe base64-encoded token string
        """
        return secrets.token_urlsafe(nbytes)

    async def create_state(self, user_data: Optional[Dict[str, Any]] = None) -> str:
        """Create a new OAuth state parameter with optional user data.

        Generates a cryptographically secure state parameter and stores it
        in Redis with a TTL of 600 seconds (10 minutes).

        Args:
            user_data: Optional dictionary of data to associate with the state

        Returns:
            The generated state parameter string
        """
        state = self._generate_secure_token()

        # Prepare data to store
        data = {
            "created_at": datetime.utcnow().isoformat(),
            "user_data": user_data or {},
        }

        try:
            redis_client = await self._get_redis_client()
            if redis_client:
                state_key = f"{self._state_prefix}{state}"
                # Store as JSON string
                import json

                await redis_client.setex(
                    state_key, self.ttl, json.dumps(data, default=str)
                )
                logger.debug("oauth_state_created_redis", state=state[:10])
            else:
                # Fallback to in-memory storage
                self._fallback_storage[state] = (datetime.utcnow(), data)
                logger.debug("oauth_state_created_memory", state=state[:10])
        except Exception as e:
            logger.error("oauth_state_creation_error", error=str(e), state=state[:10])
            # Fallback to in-memory storage
            self._fallback_storage[state] = (datetime.utcnow(), data)

        return state

    async def validate_state(self, state: str) -> Optional[Dict[str, Any]]:
        """Validate OAuth state parameter and return associated data.

        Validates that the state exists and has not expired. Implements
        single-use enforcement by deleting the state after validation.

        Args:
            state: The state parameter to validate

        Returns:
            Dictionary containing user_data if valid, None if invalid or expired
        """
        if not state:
            logger.warning("oauth_state_validation_failed", reason="empty_state")
            return None

        try:
            redis_client = await self._get_redis_client()
            if redis_client:
                state_key = f"{self._state_prefix}{state}"
                # Get and delete in one operation (single-use enforcement)
                data_str = await redis_client.getdel(state_key)

                if data_str:
                    import json

                    data = json.loads(data_str)
                    logger.info(
                        "oauth_state_validated_redis",
                        state=state[:10],
                        created_at=data.get("created_at"),
                    )
                    return data.get("user_data", {})
                else:
                    logger.warning(
                        "oauth_state_validation_failed",
                        reason="not_found_or_expired",
                        state=state[:10],
                    )
                    return None
            else:
                # Fallback to in-memory storage
                if state in self._fallback_storage:
                    timestamp, data = self._fallback_storage[state]
                    # Check if expired
                    if (datetime.utcnow() - timestamp).total_seconds() < self.ttl:
                        # Single-use: delete after validation
                        del self._fallback_storage[state]
                        logger.info(
                            "oauth_state_validated_memory",
                            state=state[:10],
                            created_at=data.get("created_at"),
                        )
                        return data.get("user_data", {})
                    else:
                        # Expired, remove it
                        del self._fallback_storage[state]
                        logger.warning(
                            "oauth_state_validation_failed",
                            reason="expired",
                            state=state[:10],
                        )
                        return None
                else:
                    logger.warning(
                        "oauth_state_validation_failed",
                        reason="not_found",
                        state=state[:10],
                    )
                    return None
        except Exception as e:
            logger.error("oauth_state_validation_error", error=str(e), state=state[:10])
            return None

    async def create_nonce(self) -> str:
        """Create a new nonce for ID token validation.

        Generates a cryptographically secure nonce and stores it in Redis
        with a TTL of 600 seconds (10 minutes).

        Returns:
            The generated nonce string
        """
        nonce = self._generate_secure_token()

        # Store nonce with timestamp
        data = {"created_at": datetime.utcnow().isoformat()}

        try:
            redis_client = await self._get_redis_client()
            if redis_client:
                nonce_key = f"{self._nonce_prefix}{nonce}"
                import json

                await redis_client.setex(
                    nonce_key, self.ttl, json.dumps(data, default=str)
                )
                logger.debug("oauth_nonce_created_redis", nonce=nonce[:10])
            else:
                # Fallback to in-memory storage
                self._fallback_storage[f"nonce:{nonce}"] = (datetime.utcnow(), data)
                logger.debug("oauth_nonce_created_memory", nonce=nonce[:10])
        except Exception as e:
            logger.error("oauth_nonce_creation_error", error=str(e), nonce=nonce[:10])
            # Fallback to in-memory storage
            self._fallback_storage[f"nonce:{nonce}"] = (datetime.utcnow(), data)

        return nonce

    async def validate_nonce(self, nonce: str) -> bool:
        """Validate nonce and enforce single-use.

        Validates that the nonce exists and has not expired. Implements
        single-use enforcement by deleting the nonce after validation.

        Args:
            nonce: The nonce to validate

        Returns:
            True if valid, False if invalid or expired
        """
        if not nonce:
            logger.warning("oauth_nonce_validation_failed", reason="empty_nonce")
            return False

        try:
            redis_client = await self._get_redis_client()
            if redis_client:
                nonce_key = f"{self._nonce_prefix}{nonce}"
                # Get and delete in one operation (single-use enforcement)
                data_str = await redis_client.getdel(nonce_key)

                if data_str:
                    logger.info("oauth_nonce_validated_redis", nonce=nonce[:10])
                    return True
                else:
                    logger.warning(
                        "oauth_nonce_validation_failed",
                        reason="not_found_or_expired",
                        nonce=nonce[:10],
                    )
                    return False
            else:
                # Fallback to in-memory storage
                fallback_key = f"nonce:{nonce}"
                if fallback_key in self._fallback_storage:
                    timestamp, data = self._fallback_storage[fallback_key]
                    # Check if expired
                    if (datetime.utcnow() - timestamp).total_seconds() < self.ttl:
                        # Single-use: delete after validation
                        del self._fallback_storage[fallback_key]
                        logger.info("oauth_nonce_validated_memory", nonce=nonce[:10])
                        return True
                    else:
                        # Expired, remove it
                        del self._fallback_storage[fallback_key]
                        logger.warning(
                            "oauth_nonce_validation_failed",
                            reason="expired",
                            nonce=nonce[:10],
                        )
                        return False
                else:
                    logger.warning(
                        "oauth_nonce_validation_failed",
                        reason="not_found",
                        nonce=nonce[:10],
                    )
                    return False
        except Exception as e:
            logger.error("oauth_nonce_validation_error", error=str(e), nonce=nonce[:10])
            return False

    async def close(self):
        """Close Redis connection."""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None


# Global state manager instance
_state_manager_instance: Optional[OAuthStateManager] = None


async def get_state_manager() -> OAuthStateManager:
    """Get or create global state manager instance."""
    global _state_manager_instance
    if _state_manager_instance is None:
        _state_manager_instance = OAuthStateManager(ttl=600)  # 10 minutes
    return _state_manager_instance
