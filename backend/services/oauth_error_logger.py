"""Comprehensive error logging service for OAuth/OIDC operations.

This module provides structured logging for OAuth errors, security events,
and performance metrics to support troubleshooting and security monitoring.

Requirements: 6.1, 6.2, 6.3, 6.4
"""

import structlog
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

logger = structlog.get_logger()


class OAuthErrorType(Enum):
    """OAuth error types for categorization."""

    # Authorization errors
    AUTHORIZATION_FAILED = "authorization_failed"
    INVALID_STATE = "invalid_state"
    STATE_EXPIRED = "state_expired"
    STATE_MISSING = "state_missing"

    # Token exchange errors
    TOKEN_EXCHANGE_FAILED = "token_exchange_failed"
    INVALID_AUTHORIZATION_CODE = "invalid_authorization_code"
    TOKEN_ENDPOINT_ERROR = "token_endpoint_error"

    # Token validation errors
    TOKEN_VALIDATION_FAILED = "token_validation_failed"
    INVALID_SIGNATURE = "invalid_signature"
    INVALID_ISSUER = "invalid_issuer"
    INVALID_AUDIENCE = "invalid_audience"
    TOKEN_EXPIRED = "token_expired"
    INVALID_NONCE = "invalid_nonce"

    # Token refresh errors
    TOKEN_REFRESH_FAILED = "token_refresh_failed"
    REFRESH_TOKEN_EXPIRED = "refresh_token_expired"
    REFRESH_TOKEN_INVALID = "refresh_token_invalid"

    # User profile errors
    PROFILE_CREATION_FAILED = "profile_creation_failed"
    PROFILE_UPDATE_FAILED = "profile_update_failed"
    MISSING_REQUIRED_CLAIMS = "missing_required_claims"

    # Session errors
    SESSION_CREATION_FAILED = "session_creation_failed"
    SESSION_INVALIDATION_FAILED = "session_invalidation_failed"

    # Network errors
    PROVIDER_UNREACHABLE = "provider_unreachable"
    NETWORK_TIMEOUT = "network_timeout"
    JWKS_FETCH_FAILED = "jwks_fetch_failed"

    # Configuration errors
    INVALID_CONFIGURATION = "invalid_configuration"
    MISSING_CONFIGURATION = "missing_configuration"

    # Rate limiting
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

    # Generic
    UNKNOWN_ERROR = "unknown_error"


class SecurityEventType(Enum):
    """Security event types for audit logging."""

    # CSRF protection
    STATE_VALIDATION_FAILED = "state_validation_failed"
    STATE_REUSE_ATTEMPTED = "state_reuse_attempted"

    # Token security
    TOKEN_SIGNATURE_INVALID = "token_signature_invalid"
    TOKEN_TAMPERING_DETECTED = "token_tampering_detected"

    # Authentication
    AUTHENTICATION_FAILED = "authentication_failed"
    AUTHENTICATION_SUCCESS = "authentication_success"
    LOGOUT_SUCCESS = "logout_success"

    # Session management
    SESSION_HIJACKING_SUSPECTED = "session_hijacking_suspected"
    INVALID_SESSION_TOKEN = "invalid_session_token"

    # Rate limiting
    RATE_LIMIT_VIOLATION = "rate_limit_violation"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


class OAuthErrorLogger:
    """Comprehensive error logger for OAuth/OIDC operations."""

    @staticmethod
    def log_oauth_error(
        error_type: OAuthErrorType,
        error_message: str,
        provider: str = "mckinsey",
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None,
    ) -> None:
        """Log an OAuth error with comprehensive context.

        Args:
            error_type: Type of OAuth error
            error_message: Human-readable error message
            provider: OAuth provider name (default: mckinsey)
            user_id: User identifier if available
            user_email: User email if available
            additional_context: Additional context data
            exception: Original exception if available

        Requirements: 6.1, 6.3
        """
        log_data = {
            "event": "oauth_error",
            "error_type": error_type.value,
            "error_message": error_message,
            "provider": provider,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Add user context if available
        if user_id:
            log_data["user_id"] = user_id
        if user_email:
            log_data["user_email"] = user_email

        # Add additional context
        if additional_context:
            # Sanitize sensitive data
            sanitized_context = OAuthErrorLogger._sanitize_context(additional_context)
            log_data.update(sanitized_context)

        # Add exception details if available
        if exception:
            log_data["exception_type"] = type(exception).__name__
            log_data["exception_message"] = str(exception)

        logger.error(**log_data)

    @staticmethod
    def log_security_event(
        event_type: SecurityEventType,
        description: str,
        provider: str = "mckinsey",
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        ip_address: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a security event for audit purposes.

        Args:
            event_type: Type of security event
            description: Description of the security event
            provider: OAuth provider name (default: mckinsey)
            user_id: User identifier if available
            user_email: User email if available
            ip_address: Client IP address if available
            additional_context: Additional context data

        Requirements: 6.2, 6.4
        """
        log_data = {
            "event": "security_event",
            "event_type": event_type.value,
            "description": description,
            "provider": provider,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Add user context if available
        if user_id:
            log_data["user_id"] = user_id
        if user_email:
            log_data["user_email"] = user_email
        if ip_address:
            log_data["ip_address"] = ip_address

        # Add additional context
        if additional_context:
            # Sanitize sensitive data
            sanitized_context = OAuthErrorLogger._sanitize_context(additional_context)
            log_data.update(sanitized_context)

        # Use warning level for security events to ensure visibility
        logger.warning(**log_data)

    @staticmethod
    def log_performance_metric(
        operation: str,
        duration_ms: float,
        provider: str = "mckinsey",
        success: bool = True,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log performance metrics for OAuth operations.

        Args:
            operation: Name of the operation (e.g., "token_exchange", "token_validation")
            duration_ms: Duration of the operation in milliseconds
            provider: OAuth provider name (default: mckinsey)
            success: Whether the operation succeeded
            additional_context: Additional context data

        Requirements: 6.1
        """
        log_data = {
            "event": "oauth_performance",
            "operation": operation,
            "duration_ms": round(duration_ms, 2),
            "provider": provider,
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Add additional context
        if additional_context:
            sanitized_context = OAuthErrorLogger._sanitize_context(additional_context)
            log_data.update(sanitized_context)

        logger.info(**log_data)

    @staticmethod
    def log_token_exchange_error(
        error_message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        code: Optional[str] = None,
        provider: str = "mckinsey",
        exception: Optional[Exception] = None,
    ) -> None:
        """Log token exchange errors with detailed context.

        Args:
            error_message: Error message
            status_code: HTTP status code from provider
            response_body: Response body from provider (sanitized)
            code: Authorization code (truncated for security)
            provider: OAuth provider name
            exception: Original exception if available

        Requirements: 6.3
        """
        additional_context = {}

        if status_code:
            additional_context["status_code"] = status_code
        if response_body:
            # Truncate response body to avoid logging sensitive data
            additional_context["response_body"] = response_body[:200]
        if code:
            # Only log first 10 characters of code for debugging
            additional_context["code_prefix"] = code[:10] + "..."

        OAuthErrorLogger.log_oauth_error(
            error_type=OAuthErrorType.TOKEN_EXCHANGE_FAILED,
            error_message=error_message,
            provider=provider,
            additional_context=additional_context,
            exception=exception,
        )

    @staticmethod
    def log_token_validation_error(
        validation_failure_reason: str,
        token_claims: Optional[Dict[str, Any]] = None,
        provider: str = "mckinsey",
        user_id: Optional[str] = None,
        exception: Optional[Exception] = None,
    ) -> None:
        """Log ID token validation errors with failure reason.

        Args:
            validation_failure_reason: Specific reason for validation failure
            token_claims: Token claims (sanitized)
            provider: OAuth provider name
            user_id: User identifier if available
            exception: Original exception if available

        Requirements: 6.4
        """
        additional_context = {
            "validation_failure_reason": validation_failure_reason,
        }

        # Add sanitized token claims for debugging
        if token_claims:
            # Only include non-sensitive claims
            safe_claims = {
                "iss": token_claims.get("iss"),
                "aud": token_claims.get("aud"),
                "exp": token_claims.get("exp"),
                "iat": token_claims.get("iat"),
                "sub": token_claims.get("sub", "")[:10] + "...",  # Truncate
            }
            additional_context["token_claims"] = safe_claims

        OAuthErrorLogger.log_oauth_error(
            error_type=OAuthErrorType.TOKEN_VALIDATION_FAILED,
            error_message=f"ID token validation failed: {validation_failure_reason}",
            provider=provider,
            user_id=user_id,
            additional_context=additional_context,
            exception=exception,
        )

    @staticmethod
    def log_state_validation_failure(
        state: str,
        reason: str,
        provider: str = "mckinsey",
        ip_address: Optional[str] = None,
    ) -> None:
        """Log state validation failures as security events.

        Args:
            state: State parameter (truncated for security)
            reason: Reason for validation failure
            provider: OAuth provider name
            ip_address: Client IP address if available

        Requirements: 6.2
        """
        additional_context = {
            "state_prefix": state[:10] + "..." if state else "missing",
            "failure_reason": reason,
        }

        OAuthErrorLogger.log_security_event(
            event_type=SecurityEventType.STATE_VALIDATION_FAILED,
            description=f"State validation failed: {reason}",
            provider=provider,
            ip_address=ip_address,
            additional_context=additional_context,
        )

    @staticmethod
    def log_rate_limit_violation(
        endpoint: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        limit: Optional[int] = None,
        window_seconds: Optional[int] = None,
    ) -> None:
        """Log rate limit violations.

        Args:
            endpoint: API endpoint that was rate limited
            user_id: User identifier if available
            ip_address: Client IP address if available
            limit: Rate limit threshold
            window_seconds: Rate limit window in seconds

        Requirements: 6.1
        """
        additional_context = {
            "endpoint": endpoint,
        }

        if limit:
            additional_context["limit"] = limit
        if window_seconds:
            additional_context["window_seconds"] = window_seconds

        OAuthErrorLogger.log_security_event(
            event_type=SecurityEventType.RATE_LIMIT_VIOLATION,
            description=f"Rate limit exceeded for endpoint: {endpoint}",
            user_id=user_id,
            ip_address=ip_address,
            additional_context=additional_context,
        )

    @staticmethod
    def log_authentication_success(
        user_id: str,
        user_email: str,
        provider: str = "mckinsey",
        auth_method: str = "sso",
        ip_address: Optional[str] = None,
    ) -> None:
        """Log successful authentication events.

        Args:
            user_id: User identifier
            user_email: User email
            provider: OAuth provider name
            auth_method: Authentication method (sso, password, etc.)
            ip_address: Client IP address if available
        """
        additional_context = {
            "auth_method": auth_method,
        }

        OAuthErrorLogger.log_security_event(
            event_type=SecurityEventType.AUTHENTICATION_SUCCESS,
            description=f"User authenticated successfully via {auth_method}",
            provider=provider,
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            additional_context=additional_context,
        )

    @staticmethod
    def log_logout_success(
        user_id: str,
        provider: str = "mckinsey",
        ip_address: Optional[str] = None,
    ) -> None:
        """Log successful logout events.

        Args:
            user_id: User identifier
            provider: OAuth provider name
            ip_address: Client IP address if available
        """
        OAuthErrorLogger.log_security_event(
            event_type=SecurityEventType.LOGOUT_SUCCESS,
            description="User logged out successfully",
            provider=provider,
            user_id=user_id,
            ip_address=ip_address,
        )

    @staticmethod
    def _sanitize_context(context: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize context data to remove sensitive information.

        Args:
            context: Context dictionary to sanitize

        Returns:
            Sanitized context dictionary
        """
        # List of sensitive keys that should be excluded or truncated
        sensitive_keys = {
            "password",
            "client_secret",
            "access_token",
            "refresh_token",
            "id_token",
            "authorization_code",
            "session_token",
        }

        sanitized = {}
        for key, value in context.items():
            # Skip sensitive keys entirely
            if key.lower() in sensitive_keys:
                continue

            # Truncate long strings
            if isinstance(value, str) and len(value) > 100:
                sanitized[key] = value[:100] + "..."
            else:
                sanitized[key] = value

        return sanitized


# Singleton instance
_oauth_error_logger = OAuthErrorLogger()


def get_oauth_error_logger() -> OAuthErrorLogger:
    """Get the OAuth error logger instance.

    Returns:
        OAuthErrorLogger instance
    """
    return _oauth_error_logger
