"""Rate limiting middleware for FastAPI using slowapi and Redis."""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import structlog
from backend.config import settings
from backend.services.redis_cache import get_cache

logger = structlog.get_logger()

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/hour", "100/minute"],  # Default limits
    storage_uri=settings.redis_url,  # Use Redis for distributed rate limiting
    headers_enabled=True  # Include rate limit headers in response
)


def get_user_id(request: Request) -> str:
    """Get user ID from request for per-user rate limiting."""
    # Try to get user from auth token
    try:
        from backend.api.auth import get_current_user
        # This would need to be called in a dependency, but for now use IP
        return get_remote_address(request)
    except:
        return get_remote_address(request)


# Per-endpoint rate limits
RATE_LIMITS = {
    "/api/multi-agent/process": "10/minute",  # Multi-agent processing
    "/api/streaming/multi-agent/stream": "20/minute",  # Streaming
    "/api/design/generate-mockup": "5/minute",  # Design generation
    "/api/design/create-project": "10/minute",  # Project creation
    "/api/design/submit-chat": "20/minute",  # Chat submission
    "/api/auth/login": "5/minute",  # Login attempts
    "/api/auth/register": "3/minute",  # Registration
    "/api/products": "30/minute",  # Product operations
    "/api/conversations": "50/minute",  # Conversation operations
}


def get_rate_limit_for_path(path: str) -> str:
    """Get rate limit for a specific path."""
    for endpoint, limit in RATE_LIMITS.items():
        if endpoint in path:
            return limit
    return "100/minute"  # Default limit


@limiter.limit("100/minute")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware."""
    try:
        # Apply endpoint-specific limits
        path = request.url.path
        limit = get_rate_limit_for_path(path)
        
        # Check rate limit
        response = await call_next(request)
        return response
    except RateLimitExceeded as e:
        logger.warning("rate_limit_exceeded", path=request.url.path, ip=get_remote_address(request))
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Please wait a moment and try again.",
                    "details": {
                        "retry_after": getattr(e, "retry_after", 60)
                    }
                }
            }
        )


def setup_rate_limiting(app):
    """Setup rate limiting for FastAPI app."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info("rate_limiting_configured", redis_url=settings.redis_url)

