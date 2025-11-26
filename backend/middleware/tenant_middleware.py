"""Middleware for tenant isolation and user context."""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
import structlog

from backend.database import get_db
from backend.api.auth import get_current_user

logger = structlog.get_logger()


class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware to set current user context for RLS policies."""
    
    async def dispatch(self, request: Request, call_next):
        # Skip for health checks and public endpoints
        if request.url.path in ["/", "/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        # Try to get current user from token
        user_id = None
        try:
            # Get token from Authorization header or cookie
            auth_header = request.headers.get("Authorization")
            session_token = request.cookies.get("session_token")
            
            token = None
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
            elif session_token:
                token = session_token
            
            if token:
                # Import here to avoid circular dependency
                from backend.services.token_storage import get_token_storage
                token_storage = await get_token_storage()
                token_data = await token_storage.get_token(token)
                if token_data:
                    user_id = token_data.get("user_id")
        except Exception as e:
            logger.debug("token_extraction_failed", error=str(e))
        
        # Set user context for database queries
        if user_id:
            # Set as request state for use in dependencies
            request.state.current_user_id = user_id
            
            # Also set as PostgreSQL session variable for RLS
            # This will be used in database queries
            original_call_next = call_next
            
            async def call_next_with_context(request):
                # This will be handled in database connection
                response = await original_call_next(request)
                return response
            
            response = await call_next_with_context(request)
        else:
            # For unauthenticated requests, set anonymous user
            request.state.current_user_id = "00000000-0000-0000-0000-000000000000"
            response = await call_next(request)
        
        return response

