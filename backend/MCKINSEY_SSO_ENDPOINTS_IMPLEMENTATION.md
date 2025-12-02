# McKinsey SSO API Endpoints Implementation

## Overview

This document summarizes the implementation of McKinsey SSO (Single Sign-On) API endpoints in `backend/api/auth.py`. These endpoints enable OAuth 2.0 / OpenID Connect authentication with McKinsey's identity provider (auth.mckinsey.id).

## Implemented Endpoints

### 1. GET /api/auth/mckinsey/authorize

**Purpose**: Initiate McKinsey SSO login flow

**Functionality**:
- Generates cryptographically secure state parameter for CSRF protection
- Generates nonce for ID token replay protection
- Constructs authorization URL with all required OAuth 2.0 parameters
- Stores state and nonce in Redis with 10-minute TTL

**Response Model**: `McKinseyAuthorizeResponse`
```python
{
    "authorization_url": "https://auth.mckinsey.id/auth/realms/r/protocol/openid-connect/auth?...",
    "state": "secure_random_state_value"
}
```

**Requirements**: 1.1, 5.1

---

### 2. GET /api/auth/mckinsey/callback

**Purpose**: Handle McKinsey SSO callback after user authentication

**Functionality**:
1. **State Validation**: Validates state parameter to prevent CSRF attacks
2. **Token Exchange**: Exchanges authorization code for access token, ID token, and refresh token
3. **ID Token Validation**: Validates ID token signature, issuer, audience, and expiration
4. **User Profile Management**: Creates new user or updates existing user profile with McKinsey claims
5. **Session Creation**: Generates session token and stores in Redis
6. **Cookie Management**: Sets secure, httponly session cookie

**Request Parameters**:
- `code`: Authorization code from McKinsey
- `state`: State parameter for CSRF protection

**Response Model**: `LoginResponse`
```python
{
    "user_id": "uuid",
    "email": "user@mckinsey.com",
    "full_name": "User Name",
    "tenant_id": "uuid",
    "tenant_name": "Default Tenant",
    "token": "session_token",
    "expires_at": "2025-12-09T10:00:00"
}
```

**User Profile Fields Updated**:
- `mckinsey_subject`: Unique McKinsey user identifier (sub claim)
- `mckinsey_email`: Email from ID token
- `email`: Main email field
- `full_name`: Constructed from name, given_name, or family_name claims
- `mckinsey_fmno`: McKinsey firm member number (employee ID)
- `mckinsey_preferred_username`: Preferred username
- `mckinsey_session_state`: Keycloak session state
- `mckinsey_refresh_token_encrypted`: Encrypted refresh token
- `mckinsey_token_expires_at`: Token expiration timestamp

**Requirements**: 1.2, 1.3, 1.4, 3.2, 4.2, 4.3, 5.2

---

### 3. POST /api/auth/mckinsey/refresh

**Purpose**: Refresh McKinsey access token using stored refresh token

**Functionality**:
1. **Token Retrieval**: Retrieves encrypted refresh token from database
2. **Token Decryption**: Decrypts refresh token using Fernet encryption
3. **Token Exchange**: Exchanges refresh token for new access token
4. **Token Storage**: Updates database with new tokens (handles token rotation)
5. **Session Extension**: Extends session expiration time
6. **Error Handling**: Clears tokens and returns 401 if refresh fails

**Authentication**: Requires valid session token (via `get_current_user` dependency)

**Response Model**: `McKinseyRefreshResponse`
```python
{
    "access_token": "new_access_token",
    "expires_in": 3600,
    "message": "Token refreshed successfully"
}
```

**Requirements**: 3.5, 5.4, 10.1, 10.2, 10.3, 10.4, 10.5

---

### 4. POST /api/auth/mckinsey/logout

**Purpose**: Logout from McKinsey SSO and initiate RP-initiated logout

**Functionality**:
1. **Session Invalidation**: Deletes session token from Redis
2. **Token Cleanup**: Clears refresh token and session state from database
3. **Logout URL Construction**: Constructs RP-initiated logout URL for McKinsey
4. **Cookie Cleanup**: Clears session cookie

**Authentication**: Requires valid session token (via `get_current_user` dependency)

**Response Model**: `McKinseyLogoutResponse`
```python
{
    "logout_url": "https://auth.mckinsey.id/auth/realms/r/protocol/openid-connect/logout?...",
    "message": "Logged out successfully"
}
```

**Logout URL Parameters**:
- `post_logout_redirect_uri`: Where to redirect after logout (frontend login page)
- `client_id`: McKinsey client ID

**Requirements**: 4.4, 5.5, 11.1, 11.2

---

## Dependencies

### Services Used

1. **McKinseyOIDCProvider** (`backend/services/mckinsey_oidc.py`)
   - Authorization URL generation
   - Token exchange
   - Token refresh
   - JWKS fetching

2. **OAuthStateManager** (`backend/services/oauth_state.py`)
   - State parameter generation and validation
   - Nonce generation and validation
   - Redis-based storage with TTL

3. **McKinseyTokenValidator** (`backend/services/token_validator.py`)
   - ID token signature verification
   - Claims validation (issuer, audience, expiration, nonce)
   - User info extraction

4. **TokenEncryptionService** (`backend/services/token_encryption.py`)
   - Refresh token encryption using Fernet
   - Refresh token decryption

5. **TokenStorage** (`backend/services/token_storage.py`)
   - Session token storage in Redis
   - Token retrieval and deletion

### Database Tables

- **user_profiles**: Stores user information and McKinsey SSO fields
- **tenants**: Stores tenant information (default tenant used for McKinsey users)

### Configuration

Required environment variables (from `backend/config.py`):
- `MCKINSEY_CLIENT_ID`: McKinsey OAuth client ID
- `MCKINSEY_CLIENT_SECRET`: McKinsey OAuth client secret
- `MCKINSEY_AUTHORIZATION_ENDPOINT`: McKinsey authorization endpoint URL
- `MCKINSEY_TOKEN_ENDPOINT`: McKinsey token endpoint URL
- `MCKINSEY_REDIRECT_URI`: Callback URL for OAuth flow
- `MCKINSEY_TOKEN_ENCRYPTION_KEY`: 32-byte Fernet encryption key

---

## Security Features

1. **CSRF Protection**: State parameter validation with single-use enforcement
2. **Token Replay Protection**: Nonce validation in ID tokens
3. **Secure Token Storage**: Refresh tokens encrypted with Fernet before storage
4. **Secure Cookies**: HttpOnly, Secure (in production), SameSite=Lax
5. **Session Management**: Redis-based distributed session storage with TTL
6. **Error Handling**: User-friendly error messages without exposing sensitive data
7. **Comprehensive Logging**: Structured logging with structlog for all operations

---

## Error Handling

All endpoints implement comprehensive error handling:

- **400 Bad Request**: Invalid state, expired state, token exchange failures
- **401 Unauthorized**: Missing/invalid session, expired refresh token
- **500 Internal Server Error**: Unexpected errors with user-friendly messages

Error responses include:
- User-friendly error messages for frontend display
- Detailed error logging for debugging (without sensitive data)
- Automatic cleanup of invalid sessions/tokens

---

## Testing

The implementation has been verified for:
- ✅ All four endpoints present and properly decorated
- ✅ All response models defined
- ✅ State validation logic
- ✅ Token exchange logic
- ✅ ID token validation
- ✅ User creation/update logic
- ✅ Session token generation
- ✅ Token refresh logic
- ✅ Logout URL construction
- ✅ Cookie management
- ✅ Python syntax validation

---

## Next Steps

1. **Property-Based Testing**: Implement property-based tests for each endpoint (tasks 8.2-8.20)
2. **Integration Testing**: Test complete OAuth flow with mock McKinsey provider
3. **Frontend Integration**: Implement frontend components to use these endpoints
4. **Environment Configuration**: Set up environment variables in deployment environments
5. **Documentation**: Update API documentation with endpoint details
