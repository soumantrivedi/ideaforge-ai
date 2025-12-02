"""Tests for OAuth error logging service.

This module tests the comprehensive error logging functionality
for OAuth/OIDC operations.

Requirements: 6.1, 6.2, 6.3, 6.4
"""

import pytest
from backend.services.oauth_error_logger import (
    OAuthErrorLogger,
    OAuthErrorType,
    SecurityEventType,
    get_oauth_error_logger,
)


def test_oauth_error_logger_singleton():
    """Test that get_oauth_error_logger returns singleton instance."""
    logger1 = get_oauth_error_logger()
    logger2 = get_oauth_error_logger()
    assert logger1 is logger2


def test_log_oauth_error_basic():
    """Test basic OAuth error logging."""
    logger = get_oauth_error_logger()

    # Should not raise exception
    logger.log_oauth_error(
        error_type=OAuthErrorType.TOKEN_EXCHANGE_FAILED,
        error_message="Test error message",
        provider="mckinsey",
    )


def test_log_oauth_error_with_user_context():
    """Test OAuth error logging with user context."""
    logger = get_oauth_error_logger()

    logger.log_oauth_error(
        error_type=OAuthErrorType.TOKEN_VALIDATION_FAILED,
        error_message="Token validation failed",
        provider="mckinsey",
        user_id="test-user-123",
        user_email="test@example.com",
    )


def test_log_oauth_error_with_additional_context():
    """Test OAuth error logging with additional context."""
    logger = get_oauth_error_logger()

    additional_context = {
        "status_code": 400,
        "response_body": "Invalid request",
        "endpoint": "/token",
    }

    logger.log_oauth_error(
        error_type=OAuthErrorType.TOKEN_EXCHANGE_FAILED,
        error_message="Token exchange failed",
        provider="mckinsey",
        additional_context=additional_context,
    )


def test_log_oauth_error_with_exception():
    """Test OAuth error logging with exception."""
    logger = get_oauth_error_logger()

    try:
        raise ValueError("Test exception")
    except ValueError as e:
        logger.log_oauth_error(
            error_type=OAuthErrorType.UNKNOWN_ERROR,
            error_message="Unexpected error occurred",
            provider="mckinsey",
            exception=e,
        )


def test_log_security_event_basic():
    """Test basic security event logging."""
    logger = get_oauth_error_logger()

    logger.log_security_event(
        event_type=SecurityEventType.STATE_VALIDATION_FAILED,
        description="State parameter validation failed",
        provider="mckinsey",
    )


def test_log_security_event_with_context():
    """Test security event logging with full context."""
    logger = get_oauth_error_logger()

    logger.log_security_event(
        event_type=SecurityEventType.AUTHENTICATION_SUCCESS,
        description="User authenticated successfully",
        provider="mckinsey",
        user_id="test-user-123",
        user_email="test@example.com",
        ip_address="192.168.1.1",
        additional_context={"auth_method": "sso"},
    )


def test_log_performance_metric():
    """Test performance metric logging."""
    logger = get_oauth_error_logger()

    logger.log_performance_metric(
        operation="token_exchange",
        duration_ms=250.5,
        provider="mckinsey",
        success=True,
    )


def test_log_performance_metric_failure():
    """Test performance metric logging for failures."""
    logger = get_oauth_error_logger()

    logger.log_performance_metric(
        operation="token_validation",
        duration_ms=150.0,
        provider="mckinsey",
        success=False,
        additional_context={"error": "signature_invalid"},
    )


def test_log_token_exchange_error():
    """Test token exchange error logging."""
    logger = get_oauth_error_logger()

    logger.log_token_exchange_error(
        error_message="Token exchange failed",
        status_code=400,
        response_body='{"error": "invalid_grant"}',
        code="test-auth-code-123",
        provider="mckinsey",
    )


def test_log_token_validation_error():
    """Test token validation error logging."""
    logger = get_oauth_error_logger()

    token_claims = {
        "iss": "https://auth.mckinsey.id/auth/realms/r",
        "aud": "test-client-id",
        "exp": 1234567890,
        "iat": 1234567800,
        "sub": "test-subject-123",
    }

    logger.log_token_validation_error(
        validation_failure_reason="Token signature invalid",
        token_claims=token_claims,
        provider="mckinsey",
        user_id="test-user-123",
    )


def test_log_state_validation_failure():
    """Test state validation failure logging.

    Requirements: 6.2
    """
    logger = get_oauth_error_logger()

    logger.log_state_validation_failure(
        state="test-state-parameter-123",
        reason="State not found in Redis",
        provider="mckinsey",
        ip_address="192.168.1.1",
    )


def test_log_rate_limit_violation():
    """Test rate limit violation logging.

    Requirements: 6.1
    """
    logger = get_oauth_error_logger()

    logger.log_rate_limit_violation(
        endpoint="/api/auth/mckinsey/authorize",
        user_id="test-user-123",
        ip_address="192.168.1.1",
        limit=10,
        window_seconds=60,
    )


def test_log_authentication_success():
    """Test authentication success logging."""
    logger = get_oauth_error_logger()

    logger.log_authentication_success(
        user_id="test-user-123",
        user_email="test@example.com",
        provider="mckinsey",
        auth_method="sso",
        ip_address="192.168.1.1",
    )


def test_log_logout_success():
    """Test logout success logging."""
    logger = get_oauth_error_logger()

    logger.log_logout_success(
        user_id="test-user-123",
        provider="mckinsey",
        ip_address="192.168.1.1",
    )


def test_sanitize_context_removes_sensitive_keys():
    """Test that sensitive keys are removed from context."""
    logger = OAuthErrorLogger()

    context = {
        "user_id": "test-123",
        "password": "secret-password",
        "client_secret": "secret-client-secret",
        "access_token": "secret-token",
        "refresh_token": "secret-refresh",
        "normal_field": "normal-value",
    }

    sanitized = logger._sanitize_context(context)

    # Sensitive keys should be removed
    assert "password" not in sanitized
    assert "client_secret" not in sanitized
    assert "access_token" not in sanitized
    assert "refresh_token" not in sanitized

    # Normal keys should be preserved
    assert "user_id" in sanitized
    assert "normal_field" in sanitized
    assert sanitized["user_id"] == "test-123"
    assert sanitized["normal_field"] == "normal-value"


def test_sanitize_context_truncates_long_strings():
    """Test that long strings are truncated."""
    logger = OAuthErrorLogger()

    long_string = "a" * 200
    context = {
        "long_field": long_string,
        "short_field": "short",
    }

    sanitized = logger._sanitize_context(context)

    # Long string should be truncated
    assert len(sanitized["long_field"]) == 103  # 100 chars + "..."
    assert sanitized["long_field"].endswith("...")

    # Short string should be preserved
    assert sanitized["short_field"] == "short"


def test_all_error_types_defined():
    """Test that all OAuth error types are defined."""
    # Verify enum has expected error types
    assert OAuthErrorType.AUTHORIZATION_FAILED
    assert OAuthErrorType.INVALID_STATE
    assert OAuthErrorType.TOKEN_EXCHANGE_FAILED
    assert OAuthErrorType.TOKEN_VALIDATION_FAILED
    assert OAuthErrorType.TOKEN_REFRESH_FAILED
    assert OAuthErrorType.RATE_LIMIT_EXCEEDED


def test_all_security_event_types_defined():
    """Test that all security event types are defined."""
    # Verify enum has expected event types
    assert SecurityEventType.STATE_VALIDATION_FAILED
    assert SecurityEventType.AUTHENTICATION_FAILED
    assert SecurityEventType.AUTHENTICATION_SUCCESS
    assert SecurityEventType.LOGOUT_SUCCESS
    assert SecurityEventType.RATE_LIMIT_VIOLATION


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
