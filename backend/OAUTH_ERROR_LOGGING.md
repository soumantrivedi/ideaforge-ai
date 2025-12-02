# OAuth Error Logging Implementation

## Overview

This document describes the comprehensive error logging implementation for McKinsey SSO OAuth/OIDC operations. The implementation satisfies Requirements 6.1, 6.2, 6.3, and 6.4 from the OAuth2/OIDC authentication specification.

## Requirements Coverage

### Requirement 6.1: OAuth Error Logging
**Requirement**: WHEN an OAuth error occurs THEN the Backend System SHALL log the error with context including user identifier, provider name, and error details

**Implementation**: 
- `OAuthErrorLogger.log_oauth_error()` method logs all OAuth errors with comprehensive context
- Includes user_id, user_email, provider name, error type, error message, and exception details
- Additional context can be provided for specific error scenarios
- All sensitive data is automatically sanitized before logging

### Requirement 6.2: State Validation Failure Logging
**Requirement**: WHEN State Parameter validation fails THEN the Backend System SHALL reject the request and log a security warning

**Implementation**:
- `OAuthErrorLogger.log_state_validation_failure()` method specifically handles state validation failures
- Logs as a security event with WARNING level for visibility
- Includes state parameter (truncated), failure reason, provider, and IP address
- Used in `/api/auth/mckinsey/callback` endpoint when state validation fails

### Requirement 6.3: Token Exchange Error Logging
**Requirement**: WHEN token exchange fails THEN the Backend System SHALL return a user-friendly error message and log the detailed error

**Implementation**:
- `OAuthErrorLogger.log_token_exchange_error()` method handles token exchange failures
- Logs detailed error information including status code, response body (truncated), and authorization code prefix
- User receives friendly error message while detailed error is logged for troubleshooting
- Used in `/api/auth/mckinsey/callback` endpoint during token exchange

### Requirement 6.4: Token Validation Error Logging
**Requirement**: WHEN ID Token validation fails THEN the Backend System SHALL reject the authentication and log the validation failure reason

**Implementation**:
- `OAuthErrorLogger.log_token_validation_error()` method handles ID token validation failures
- Logs specific validation failure reason (signature invalid, issuer mismatch, expired, etc.)
- Includes sanitized token claims for debugging (only non-sensitive claims)
- Used in `/api/auth/mckinsey/callback` endpoint during ID token validation

## Architecture

### Core Components

#### 1. OAuthErrorLogger Class
Location: `backend/services/oauth_error_logger.py`

Main class providing comprehensive error logging functionality:
- `log_oauth_error()` - General OAuth error logging
- `log_security_event()` - Security event logging for audit
- `log_performance_metric()` - Performance metrics logging
- `log_token_exchange_error()` - Specialized token exchange error logging
- `log_token_validation_error()` - Specialized token validation error logging
- `log_state_validation_failure()` - Specialized state validation failure logging
- `log_rate_limit_violation()` - Rate limit violation logging
- `log_authentication_success()` - Successful authentication logging
- `log_logout_success()` - Successful logout logging

#### 2. Error Type Enums

**OAuthErrorType**: Categorizes OAuth errors for filtering and analysis
- Authorization errors (AUTHORIZATION_FAILED, INVALID_STATE, etc.)
- Token exchange errors (TOKEN_EXCHANGE_FAILED, INVALID_AUTHORIZATION_CODE, etc.)
- Token validation errors (TOKEN_VALIDATION_FAILED, INVALID_SIGNATURE, etc.)
- Token refresh errors (TOKEN_REFRESH_FAILED, REFRESH_TOKEN_EXPIRED, etc.)
- User profile errors (PROFILE_CREATION_FAILED, MISSING_REQUIRED_CLAIMS, etc.)
- Session errors (SESSION_CREATION_FAILED, SESSION_INVALIDATION_FAILED)
- Network errors (PROVIDER_UNREACHABLE, NETWORK_TIMEOUT, JWKS_FETCH_FAILED)
- Configuration errors (INVALID_CONFIGURATION, MISSING_CONFIGURATION)
- Rate limiting (RATE_LIMIT_EXCEEDED)

**SecurityEventType**: Categorizes security events for audit
- CSRF protection (STATE_VALIDATION_FAILED, STATE_REUSE_ATTEMPTED)
- Token security (TOKEN_SIGNATURE_INVALID, TOKEN_TAMPERING_DETECTED)
- Authentication (AUTHENTICATION_FAILED, AUTHENTICATION_SUCCESS, LOGOUT_SUCCESS)
- Session management (SESSION_HIJACKING_SUSPECTED, INVALID_SESSION_TOKEN)
- Rate limiting (RATE_LIMIT_VIOLATION, SUSPICIOUS_ACTIVITY)

### Integration Points

#### 1. McKinsey SSO Endpoints (`backend/api/auth.py`)

**GET /api/auth/mckinsey/authorize**
- Logs performance metrics for authorization URL generation
- Logs comprehensive errors if authorization fails

**GET /api/auth/mckinsey/callback**
- Logs state validation failures as security events (Requirement 6.2)
- Logs token exchange errors with detailed context (Requirement 6.3)
- Logs token validation errors with failure reasons (Requirement 6.4)
- Logs successful authentication as security event
- Logs comprehensive errors for unexpected failures (Requirement 6.1)

**POST /api/auth/mckinsey/refresh**
- Logs token refresh failures with user context
- Logs comprehensive errors for unexpected failures

**POST /api/auth/mckinsey/logout**
- Logs successful logout as security event
- Logs comprehensive errors if logout fails

#### 2. McKinsey OIDC Provider (`backend/services/mckinsey_oidc.py`)
- Already has comprehensive logging for token operations
- Logs token exchange success/failure with status codes
- Logs token refresh success/failure with status codes
- Logs JWKS fetch operations

#### 3. Token Validator (`backend/services/token_validator.py`)
- Already has comprehensive logging for validation operations
- Logs signature verification success/failure
- Logs claims validation failures with specific reasons
- Logs user info extraction

## Log Structure

### OAuth Error Log Format
```json
{
  "event": "oauth_error",
  "error_type": "token_exchange_failed",
  "error_message": "Failed to exchange authorization code for tokens",
  "provider": "mckinsey",
  "timestamp": "2025-12-02T10:30:00.000Z",
  "user_id": "user-123",
  "user_email": "user@example.com",
  "exception_type": "HTTPStatusError",
  "exception_message": "400 Bad Request",
  "status_code": 400,
  "code_prefix": "auth-code-..."
}
```

### Security Event Log Format
```json
{
  "event": "security_event",
  "event_type": "state_validation_failed",
  "description": "State validation failed: State not found in Redis",
  "provider": "mckinsey",
  "timestamp": "2025-12-02T10:30:00.000Z",
  "ip_address": "192.168.1.1",
  "state_prefix": "state-123...",
  "failure_reason": "State not found in Redis"
}
```

### Performance Metric Log Format
```json
{
  "event": "oauth_performance",
  "operation": "token_exchange",
  "duration_ms": 250.5,
  "provider": "mckinsey",
  "success": true,
  "timestamp": "2025-12-02T10:30:00.000Z"
}
```

## Security Features

### 1. Sensitive Data Sanitization
The `_sanitize_context()` method automatically removes or truncates sensitive data:

**Removed entirely**:
- password
- client_secret
- access_token
- refresh_token
- id_token
- authorization_code
- session_token

**Truncated** (if > 100 characters):
- Long strings are truncated to 100 characters + "..."

### 2. Token Truncation
Authorization codes, state parameters, and nonces are truncated to first 10 characters + "..." for security while maintaining debuggability.

### 3. Claim Sanitization
When logging token claims, only non-sensitive claims are included:
- iss (issuer)
- aud (audience)
- exp (expiration)
- iat (issued at)
- sub (subject - truncated)

## Usage Examples

### Example 1: Log State Validation Failure
```python
from backend.services.oauth_error_logger import get_oauth_error_logger

error_logger = get_oauth_error_logger()
error_logger.log_state_validation_failure(
    state=state,
    reason="State not found or expired in Redis",
    provider="mckinsey",
    ip_address=request.client.host,
)
```

### Example 2: Log Token Exchange Error
```python
from backend.services.oauth_error_logger import get_oauth_error_logger

error_logger = get_oauth_error_logger()
try:
    tokens = await provider.exchange_code_for_tokens(code)
except Exception as e:
    error_logger.log_token_exchange_error(
        error_message="Failed to exchange authorization code for tokens",
        code=code,
        provider="mckinsey",
        exception=e,
    )
    raise
```

### Example 3: Log Token Validation Error
```python
from backend.services.oauth_error_logger import get_oauth_error_logger

error_logger = get_oauth_error_logger()
try:
    id_token_claims = await validator.validate_id_token(id_token)
except Exception as e:
    error_logger.log_token_validation_error(
        validation_failure_reason=str(e),
        provider="mckinsey",
        exception=e,
    )
    raise
```

### Example 4: Log Successful Authentication
```python
from backend.services.oauth_error_logger import get_oauth_error_logger

error_logger = get_oauth_error_logger()
error_logger.log_authentication_success(
    user_id=user_id,
    user_email=email,
    provider="mckinsey",
    auth_method="sso",
    ip_address=request.client.host,
)
```

## Testing

### Unit Tests
Location: `backend/test_oauth_error_logging.py`

Tests cover:
- Singleton pattern for logger instance
- Basic OAuth error logging
- OAuth error logging with user context
- OAuth error logging with additional context
- OAuth error logging with exceptions
- Security event logging
- Performance metric logging
- Token exchange error logging
- Token validation error logging
- State validation failure logging
- Rate limit violation logging
- Authentication success logging
- Logout success logging
- Sensitive data sanitization
- Long string truncation

### Running Tests
```bash
cd backend
python -m pytest test_oauth_error_logging.py -v
```

## Monitoring and Alerting

### Key Metrics to Monitor

1. **OAuth Error Rate**
   - Filter: `event="oauth_error"`
   - Alert if error rate > 10% of total OAuth attempts

2. **State Validation Failures**
   - Filter: `event_type="state_validation_failed"`
   - Alert on any occurrence (potential CSRF attack)

3. **Token Exchange Failures**
   - Filter: `error_type="token_exchange_failed"`
   - Alert if failure rate > 5%

4. **Token Validation Failures**
   - Filter: `error_type="token_validation_failed"`
   - Alert if failure rate > 5%

5. **Performance Degradation**
   - Filter: `event="oauth_performance"`
   - Alert if average duration_ms > 1000ms

### Log Aggregation

Logs are structured using structlog and can be aggregated using:
- CloudWatch Logs (AWS)
- Elasticsearch + Kibana
- Splunk
- Datadog
- New Relic

Example CloudWatch Insights query:
```
fields @timestamp, error_type, error_message, user_id, provider
| filter event = "oauth_error"
| stats count() by error_type
| sort count desc
```

## Compliance and Audit

### Audit Trail
All security events are logged with:
- Timestamp (ISO 8601 format)
- User identifier (if available)
- IP address (if available)
- Event type
- Description
- Provider name

### Data Retention
- Production logs: Retain for 90 days minimum
- Security event logs: Retain for 1 year minimum
- Compliance with GDPR, SOC 2, and other regulations

### Privacy Considerations
- No passwords or secrets are logged
- Tokens are never logged in full
- Personal data is minimized (only user_id and email when necessary)
- IP addresses are logged for security events only

## Future Enhancements

1. **Structured Error Codes**
   - Add numeric error codes for easier filtering and alerting

2. **Correlation IDs**
   - Add request correlation IDs to trace errors across services

3. **Metrics Export**
   - Export metrics to Prometheus/StatsD for real-time monitoring

4. **Anomaly Detection**
   - Implement ML-based anomaly detection for security events

5. **Automated Remediation**
   - Trigger automated responses for certain error patterns

