"""Common error handling framework for consistent error messages across the application."""
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from enum import Enum
import structlog

logger = structlog.get_logger()


class ErrorCode(str, Enum):
    """Standard error codes for consistent error handling."""
    # Authentication & Authorization
    AUTH_REQUIRED = "AUTH_REQUIRED"
    AUTH_INVALID = "AUTH_INVALID"
    AUTH_EXPIRED = "AUTH_EXPIRED"
    AUTH_INSUFFICIENT_PERMISSIONS = "AUTH_INSUFFICIENT_PERMISSIONS"
    
    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"
    
    # Resource Management
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    
    # AI Provider
    AI_PROVIDER_NOT_CONFIGURED = "AI_PROVIDER_NOT_CONFIGURED"
    AI_PROVIDER_ERROR = "AI_PROVIDER_ERROR"
    AI_RATE_LIMIT_EXCEEDED = "AI_RATE_LIMIT_EXCEEDED"
    AI_TIMEOUT = "AI_TIMEOUT"
    AI_QUOTA_EXCEEDED = "AI_QUOTA_EXCEEDED"
    
    # Agent & Processing
    AGENT_ERROR = "AGENT_ERROR"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"
    AGENT_NOT_AVAILABLE = "AGENT_NOT_AVAILABLE"
    PROCESSING_ERROR = "PROCESSING_ERROR"
    
    # Database
    DATABASE_ERROR = "DATABASE_ERROR"
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"
    DATABASE_QUERY_ERROR = "DATABASE_QUERY_ERROR"
    
    # External Services
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    EXTERNAL_SERVICE_TIMEOUT = "EXTERNAL_SERVICE_TIMEOUT"
    EXTERNAL_SERVICE_UNAVAILABLE = "EXTERNAL_SERVICE_UNAVAILABLE"
    
    # Rate Limiting
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    TOO_MANY_REQUESTS = "TOO_MANY_REQUESTS"
    
    # General
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class AppError(Exception):
    """Base application error with structured error information."""
    
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ):
        """
        Initialize application error.
        
        Args:
            error_code: Standard error code
            message: Technical error message (for logging)
            user_message: User-friendly error message (for API response)
            details: Additional error details
            status_code: HTTP status code
        """
        self.error_code = error_code
        self.message = message
        self.user_message = user_message or message
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)


def create_http_exception(
    error_code: ErrorCode,
    message: str,
    user_message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    status_code: Optional[int] = None
) -> HTTPException:
    """
    Create a standardized HTTP exception.
    
    Args:
        error_code: Standard error code
        message: Technical error message
        user_message: User-friendly error message
        details: Additional error details
        status_code: HTTP status code (defaults based on error_code)
    
    Returns:
        HTTPException with structured error response
    """
    # Default status codes by error category
    if status_code is None:
        if error_code.value.startswith("AUTH_"):
            status_code = status.HTTP_401_UNAUTHORIZED
        elif error_code.value.startswith("VALIDATION_"):
            status_code = status.HTTP_400_BAD_REQUEST
        elif error_code.value.startswith("RESOURCE_NOT_FOUND"):
            status_code = status.HTTP_404_NOT_FOUND
        elif error_code.value.startswith("RESOURCE_ALREADY_EXISTS") or error_code.value.startswith("RESOURCE_CONFLICT"):
            status_code = status.HTTP_409_CONFLICT
        elif error_code.value.startswith("RATE_LIMIT") or error_code.value.startswith("TOO_MANY"):
            status_code = status.HTTP_429_TOO_MANY_REQUESTS
        elif error_code.value.startswith("AI_PROVIDER") or error_code.value.startswith("AGENT_"):
            status_code = status.HTTP_502_BAD_GATEWAY
        elif error_code.value.startswith("SERVICE_UNAVAILABLE") or error_code.value.startswith("EXTERNAL_SERVICE_UNAVAILABLE"):
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    error_response = {
        "error": {
            "code": error_code.value,
            "message": user_message or message,
            "details": details or {}
        }
    }
    
    # Log error for debugging
    logger.error(
        "http_error",
        error_code=error_code.value,
        message=message,
        user_message=user_message,
        status_code=status_code,
        details=details
    )
    
    return HTTPException(status_code=status_code, detail=error_response)


def handle_exception(e: Exception, context: Optional[str] = None) -> HTTPException:
    """
    Handle exceptions and convert to standardized HTTP exceptions.
    
    Args:
        e: Exception to handle
        context: Additional context about where the error occurred
    
    Returns:
        HTTPException with appropriate error code and message
    """
    if isinstance(e, AppError):
        return create_http_exception(
            error_code=e.error_code,
            message=e.message,
            user_message=e.user_message,
            details=e.details,
            status_code=e.status_code
        )
    
    if isinstance(e, HTTPException):
        return e
    
    # Handle common exception types
    error_message = str(e)
    error_type = type(e).__name__
    
    if "timeout" in error_message.lower() or "timed out" in error_message.lower():
        return create_http_exception(
            error_code=ErrorCode.AI_TIMEOUT,
            message=f"Request timed out: {error_message}",
            user_message="The request took too long to process. Please try again with a simpler query.",
            details={"error_type": error_type, "context": context}
        )
    
    if "rate limit" in error_message.lower() or "quota" in error_message.lower():
        return create_http_exception(
            error_code=ErrorCode.AI_RATE_LIMIT_EXCEEDED,
            message=f"Rate limit exceeded: {error_message}",
            user_message="API rate limit exceeded. Please wait a moment and try again.",
            details={"error_type": error_type, "context": context}
        )
    
    if "not found" in error_message.lower():
        return create_http_exception(
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            message=error_message,
            user_message="The requested resource was not found.",
            details={"error_type": error_type, "context": context}
        )
    
    # Generic error
    return create_http_exception(
        error_code=ErrorCode.INTERNAL_ERROR,
        message=f"Internal error: {error_message}",
        user_message="An unexpected error occurred. Please try again later.",
        details={"error_type": error_type, "context": context}
    )


# User-friendly error messages
USER_ERROR_MESSAGES = {
    ErrorCode.AI_PROVIDER_NOT_CONFIGURED: "AI provider is not configured. Please configure an AI provider in Settings.",
    ErrorCode.AI_TIMEOUT: "The AI request took too long. Please try a simpler query or try again later.",
    ErrorCode.AI_RATE_LIMIT_EXCEEDED: "AI service rate limit exceeded. Please wait a moment and try again.",
    ErrorCode.AI_QUOTA_EXCEEDED: "AI service quota exceeded. Please check your subscription or contact support.",
    ErrorCode.AGENT_ERROR: "An error occurred while processing your request. Please try again.",
    ErrorCode.AGENT_TIMEOUT: "The agent took too long to respond. Please try a simpler query.",
    ErrorCode.RESOURCE_NOT_FOUND: "The requested resource was not found.",
    ErrorCode.VALIDATION_ERROR: "Invalid input. Please check your request and try again.",
    ErrorCode.RATE_LIMIT_EXCEEDED: "Too many requests. Please wait a moment and try again.",
    ErrorCode.DATABASE_ERROR: "Database error occurred. Please try again later.",
    ErrorCode.EXTERNAL_SERVICE_ERROR: "External service error. Please try again later.",
}

