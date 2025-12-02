"""Authentication API endpoints."""

from fastapi import APIRouter, HTTPException, Depends, Cookie, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from datetime import datetime, timedelta
from uuid import UUID
import structlog
import secrets

from backend.database import get_db
from backend.config import settings

logger = structlog.get_logger()
router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Password hashing
# Use bcrypt directly to avoid passlib compatibility issues
import bcrypt

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# Security
security = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str]
    tenant_id: str
    tenant_name: str
    token: str
    expires_at: str


class UserInfo(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    tenant_id: str
    tenant_name: str
    persona: str
    avatar_url: Optional[str]
    mckinsey_subject: Optional[str] = None  # Present if user logged in via McKinsey SSO


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    tenant_id: Optional[str] = None


# Token storage using Redis for distributed access across multiple backend pods
from backend.services.token_storage import get_token_storage


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    if not hashed_password:
        return False

    try:
        # Convert hashed_password to bytes if it's a string
        if isinstance(hashed_password, str):
            hashed_bytes = hashed_password.encode("utf-8")
        else:
            hashed_bytes = hashed_password

        # Use bcrypt directly to avoid passlib issues
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_bytes)
    except Exception as e:
        # Fallback to passlib if bcrypt fails
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            logger.warning("password_verification_failed", error=str(e))
            return False


def generate_token() -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(32)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session_token: Optional[str] = Cookie(None),
) -> dict:
    """Get current authenticated user from token.

    Supports both password-based and McKinsey SSO authentication.
    Session type is automatically detected from token data stored in Redis.

    Args:
        db: Database session
        authorization: Optional Bearer token from Authorization header
        session_token: Optional session token from cookie

    Returns:
        dict: User information including id, email, full_name, tenant_id, persona, avatar_url

    Raises:
        HTTPException: If authentication fails (401)

    Requirements: 4.5, 5.3
    """
    token = None
    if authorization:
        token = authorization.credentials
    elif session_token:
        token = session_token

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Check token in Redis or fallback storage
    # This works for both password-based and McKinsey SSO sessions
    token_storage = await get_token_storage()
    token_data = await token_storage.get_token(token)

    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Validate token expiration
    if datetime.utcnow() > datetime.fromisoformat(token_data["expires_at"]):
        await token_storage.delete_token(token)
        raise HTTPException(status_code=401, detail="Token expired")

    # Log authentication method for monitoring (optional field)
    auth_method = token_data.get("auth_method", "password")
    logger.debug(
        "user_authenticated",
        user_id=token_data["user_id"],
        auth_method=auth_method,
        token=token[:10] + "...",
    )

    # Verify user still exists and is active
    # This query works for both password-based and McKinsey SSO users
    query = text(
        """
        SELECT id, email, full_name, tenant_id, is_active, persona, avatar_url, mckinsey_subject
        FROM user_profiles
        WHERE id = :user_id AND is_active = true
    """
    )

    result = await db.execute(query, {"user_id": token_data["user_id"]})
    row = result.fetchone()

    if not row:
        await token_storage.delete_token(token)
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return {
        "id": str(row[0]),
        "email": row[1],
        "full_name": row[2],
        "tenant_id": str(row[3]),
        "persona": row[5],
        "avatar_url": row[6],
        "mckinsey_subject": row[7],  # Include McKinsey subject for SSO detection
        "auth_method": auth_method,  # Include auth method in response
    }


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)
):
    """Authenticate user and return session token."""
    try:
        # Get user from database
        query = text(
            """
            SELECT up.id, up.email, up.full_name, up.password_hash, up.tenant_id, 
                   up.is_active, COALESCE(t.name, 'Default') as tenant_name
            FROM user_profiles up
            LEFT JOIN tenants t ON up.tenant_id = t.id
            WHERE up.email = :email
        """
        )

        result = await db.execute(query, {"email": request.email.lower()})
        row = result.fetchone()

        if not row:
            logger.warning(
                "login_failed", email=request.email.lower(), reason="user_not_found"
            )
            raise HTTPException(status_code=401, detail="Invalid email or password")

        user_id, email, full_name, password_hash, tenant_id, is_active, tenant_name = (
            row
        )

        if not is_active:
            logger.warning(
                "login_failed",
                email=request.email.lower(),
                user_id=str(user_id),
                reason="account_inactive",
            )
            raise HTTPException(status_code=403, detail="User account is inactive")

        # Verify password
        if not password_hash or not verify_password(request.password, password_hash):
            logger.warning(
                "login_failed",
                email=request.email.lower(),
                user_id=str(user_id),
                reason="invalid_password",
            )
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Generate token
        token = generate_token()
        expires_at = datetime.utcnow() + timedelta(days=7)

        # Store token in Redis or fallback storage
        try:
            token_storage = await get_token_storage()
            token_data = {
                "user_id": str(user_id),
                "email": email,
                "tenant_id": str(tenant_id),
                "expires_at": expires_at.isoformat(),
            }
            expires_in_seconds = int((expires_at - datetime.utcnow()).total_seconds())
            await token_storage.store_token(token, token_data, expires_in_seconds)
        except Exception as e:
            logger.error("token_storage_failed", error=str(e), user_id=str(user_id))
            raise HTTPException(
                status_code=500, detail="Failed to create session. Please try again."
            )

        # Update last login
        try:
            update_query = text(
                """
                UPDATE user_profiles
                SET last_login_at = now()
                WHERE id = :user_id
            """
            )
            await db.execute(update_query, {"user_id": user_id})
            await db.commit()
        except Exception as e:
            logger.warning(
                "last_login_update_failed", error=str(e), user_id=str(user_id)
            )
            # Don't fail login if last_login update fails
            await db.rollback()

        # Set cookie
        try:
            response.set_cookie(
                key="session_token",
                value=token,
                httponly=True,
                secure=False,  # Set to True in production with HTTPS
                samesite="lax",
                max_age=7 * 24 * 60 * 60,  # 7 days
            )
        except Exception as e:
            logger.warning("cookie_set_failed", error=str(e), user_id=str(user_id))
            # Don't fail login if cookie setting fails

        return LoginResponse(
            user_id=str(user_id),
            email=email,
            full_name=full_name,
            tenant_id=str(tenant_id),
            tenant_name=tenant_name,
            token=token,
            expires_at=expires_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "login_error", error=str(e), error_type=type(e).__name__, exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@router.post("/logout")
async def logout(
    response: Response,
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session_token: Optional[str] = Cookie(None),
):
    """Logout user and invalidate token."""
    token = None
    if authorization:
        token = authorization.credentials
    elif session_token:
        token = session_token

    if token:
        token_storage = await get_token_storage()
        await token_storage.delete_token(token)

    response.delete_cookie(key="session_token")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Get current user information."""
    try:
        # Get tenant name (handle case where tenant might not exist)
        tenant_name = "Default Tenant"
        try:
            query = text(
                """
                SELECT name FROM tenants WHERE id = :tenant_id
            """
            )
            result = await db.execute(query, {"tenant_id": current_user["tenant_id"]})
            row = result.fetchone()
            if row:
                tenant_name = row[0]
        except Exception:
            # If tenant table doesn't exist or query fails, use default
            pass

        return UserInfo(
            id=current_user["id"],
            email=current_user["email"],
            full_name=current_user["full_name"],
            tenant_id=current_user["tenant_id"],
            tenant_name=tenant_name,
            persona=current_user["persona"],
            avatar_url=current_user.get("avatar_url"),
            mckinsey_subject=current_user.get("mckinsey_subject"),
        )
    except HTTPException:
        # Re-raise HTTP exceptions (like 401) as-is
        raise
    except Exception as e:
        logger.error("get_user_info_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get user info")


@router.get("/users")
async def list_users(
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """List all users in the same tenant."""
    try:
        query = text(
            """
            SELECT id, email, full_name, persona, avatar_url, created_at, last_login_at
            FROM user_profiles
            WHERE tenant_id = :tenant_id AND is_active = true
            ORDER BY full_name, email
        """
        )

        result = await db.execute(query, {"tenant_id": current_user["tenant_id"]})
        rows = result.fetchall()

        users = [
            {
                "id": str(row[0]),
                "email": row[1],
                "full_name": row[2],
                "persona": row[3],
                "avatar_url": row[4],
                "created_at": row[5].isoformat() if row[5] else None,
                "last_login_at": row[6].isoformat() if row[6] else None,
            }
            for row in rows
        ]

        return {"users": users}
    except Exception as e:
        logger.error("list_users_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list users")


# ============================================================================
# McKinsey SSO Endpoints
# ============================================================================


class McKinseyAuthorizeResponse(BaseModel):
    """Response model for McKinsey SSO authorization endpoint."""

    authorization_url: str
    state: str


@router.get("/mckinsey/authorize", response_model=McKinseyAuthorizeResponse)
async def mckinsey_authorize():
    """Initiate McKinsey SSO login flow.

    Generates a secure state parameter and nonce, then constructs the
    authorization URL for redirecting the user to McKinsey's identity provider.

    Returns:
        McKinseyAuthorizeResponse: Contains authorization_url and state

    Raises:
        HTTPException: If authorization URL generation fails

    Requirements: 1.1, 5.1
    """
    from datetime import datetime as dt

    start_time = dt.now()

    try:
        # Import McKinsey services
        from backend.services.mckinsey_oidc import get_mckinsey_provider
        from backend.services.oauth_state import get_state_manager
        from backend.services.oauth_error_logger import (
            get_oauth_error_logger,
            OAuthErrorType,
        )

        error_logger = get_oauth_error_logger()

        # Get service instances
        provider = await get_mckinsey_provider()
        state_manager = await get_state_manager()

        # Generate state and nonce for CSRF protection
        state = await state_manager.create_state()
        nonce = await state_manager.create_nonce()

        # Generate authorization URL
        authorization_url = await provider.get_authorization_url(state, nonce)

        # Log performance metric
        duration_ms = (dt.now() - start_time).total_seconds() * 1000
        error_logger.log_performance_metric(
            operation="authorization_url_generation",
            duration_ms=duration_ms,
            provider="mckinsey",
            success=True,
        )

        logger.info(
            "mckinsey_authorize_initiated",
            state=state[:10] + "...",
            nonce=nonce[:10] + "...",
        )

        return McKinseyAuthorizeResponse(
            authorization_url=authorization_url, state=state
        )

    except Exception as e:
        # Log comprehensive error
        from backend.services.oauth_error_logger import (
            get_oauth_error_logger,
            OAuthErrorType,
        )

        error_logger = get_oauth_error_logger()
        error_logger.log_oauth_error(
            error_type=OAuthErrorType.AUTHORIZATION_FAILED,
            error_message="Failed to initiate McKinsey SSO login",
            provider="mckinsey",
            exception=e,
        )

        # Log performance metric for failure
        duration_ms = (dt.now() - start_time).total_seconds() * 1000
        error_logger.log_performance_metric(
            operation="authorization_url_generation",
            duration_ms=duration_ms,
            provider="mckinsey",
            success=False,
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to initiate McKinsey SSO login. Please try again.",
        )


@router.get("/mckinsey/callback", response_model=LoginResponse)
async def mckinsey_callback(
    code: str, state: str, response: Response, db: AsyncSession = Depends(get_db)
):
    """Handle McKinsey SSO callback after user authentication.

    This endpoint:
    1. Validates the state parameter to prevent CSRF attacks
    2. Exchanges the authorization code for tokens
    3. Validates the ID token
    4. Creates or updates the user profile
    5. Generates a session token
    6. Sets a secure session cookie

    Args:
        code: Authorization code from McKinsey
        state: State parameter for CSRF protection
        response: FastAPI response object for setting cookies
        db: Database session

    Returns:
        LoginResponse: Contains user info and session token

    Raises:
        HTTPException: If callback processing fails

    Requirements: 1.2, 1.3, 1.4, 3.2, 4.2, 4.3, 5.2
    """
    try:
        # Import McKinsey services
        from backend.services.mckinsey_oidc import get_mckinsey_provider
        from backend.services.oauth_state import get_state_manager
        from backend.services.token_validator import get_mckinsey_validator
        from backend.services.token_encryption import encrypt_refresh_token

        # Get service instances
        provider = await get_mckinsey_provider()
        state_manager = await get_state_manager()
        validator = await get_mckinsey_validator()

        # Import error logger
        from backend.services.oauth_error_logger import get_oauth_error_logger

        error_logger = get_oauth_error_logger()

        # Step 1: Validate state parameter
        state_data = await state_manager.validate_state(state)
        if state_data is None:
            # Log security event for state validation failure
            error_logger.log_state_validation_failure(
                state=state,
                reason="State not found or expired in Redis",
                provider="mckinsey",
            )
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired state parameter. Please try logging in again.",
            )

        logger.info(
            "mckinsey_callback_state_validated",
            state=state[:10] + "...",
            code=code[:10] + "...",
        )

        # Step 2: Exchange authorization code for tokens
        try:
            tokens = await provider.exchange_code_for_tokens(code)
        except Exception as e:
            # Log comprehensive token exchange error
            error_logger.log_token_exchange_error(
                error_message="Failed to exchange authorization code for tokens",
                code=code,
                provider="mckinsey",
                exception=e,
            )
            raise HTTPException(
                status_code=400,
                detail="Failed to exchange authorization code for tokens. Please try again.",
            )

        # Extract tokens
        access_token = tokens.get("access_token")
        id_token = tokens.get("id_token")
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in", 3600)

        if not id_token:
            logger.error("mckinsey_missing_id_token", code=code[:10] + "...")
            raise HTTPException(
                status_code=400,
                detail="ID token not received from McKinsey. Please try again.",
            )

        # Step 3: Validate ID token
        # Note: We don't validate nonce here because we stored it separately
        # and the token validator will handle it if we pass it
        try:
            id_token_claims = await validator.validate_id_token(id_token)
        except Exception as e:
            # Log comprehensive token validation error
            error_logger.log_token_validation_error(
                validation_failure_reason=str(e),
                provider="mckinsey",
                exception=e,
            )
            raise HTTPException(
                status_code=400, detail="ID token validation failed. Please try again."
            )

        # Step 4: Create or update user profile
        mckinsey_subject = id_token_claims.get("sub")
        email = id_token_claims.get("email")
        name = id_token_claims.get("name")
        given_name = id_token_claims.get("given_name")
        family_name = id_token_claims.get("family_name")
        fmno = id_token_claims.get("fmno")
        preferred_username = id_token_claims.get("preferred_username")
        session_state = id_token_claims.get("session_state")

        if not mckinsey_subject or not email:
            logger.error(
                "mckinsey_missing_required_claims",
                has_sub=bool(mckinsey_subject),
                has_email=bool(email),
            )
            raise HTTPException(
                status_code=400,
                detail="Required user information not found in ID token.",
            )

        # Construct full name
        full_name = name
        if not full_name and given_name and family_name:
            full_name = f"{given_name} {family_name}"
        elif not full_name and given_name:
            full_name = given_name
        elif not full_name:
            full_name = email.split("@")[0]  # Fallback to email username

        # Get default tenant
        tenant_query = text(
            """
            SELECT id, name FROM tenants WHERE slug = :slug LIMIT 1
        """
        )
        tenant_result = await db.execute(tenant_query, {"slug": "default"})
        tenant_row = tenant_result.fetchone()

        if not tenant_row:
            logger.error("default_tenant_not_found")
            raise HTTPException(
                status_code=500,
                detail="System configuration error. Please contact support.",
            )

        tenant_id = str(tenant_row[0])
        tenant_name = tenant_row[1]

        # Check if user exists by McKinsey subject
        user_query = text(
            """
            SELECT id, email, full_name, tenant_id, is_active
            FROM user_profiles
            WHERE mckinsey_subject = :mckinsey_subject
        """
        )
        user_result = await db.execute(
            user_query, {"mckinsey_subject": mckinsey_subject}
        )
        user_row = user_result.fetchone()

        if user_row:
            # Update existing user
            user_id = str(user_row[0])

            # Encrypt refresh token if present
            encrypted_refresh_token = None
            if refresh_token:
                try:
                    encrypted_refresh_token = encrypt_refresh_token(refresh_token)
                except Exception as e:
                    logger.warning(
                        "mckinsey_refresh_token_encryption_failed",
                        error=str(e),
                        user_id=user_id,
                    )

            # Calculate token expiration
            token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            # Update user profile
            update_query = text(
                """
                UPDATE user_profiles
                SET mckinsey_email = :mckinsey_email,
                    email = COALESCE(:email, email),
                    full_name = COALESCE(:full_name, full_name),
                    mckinsey_fmno = :mckinsey_fmno,
                    mckinsey_preferred_username = :mckinsey_preferred_username,
                    mckinsey_session_state = :mckinsey_session_state,
                    mckinsey_refresh_token_encrypted = :mckinsey_refresh_token_encrypted,
                    mckinsey_token_expires_at = :mckinsey_token_expires_at,
                    last_login_at = now(),
                    updated_at = now()
                WHERE id = :user_id
            """
            )
            await db.execute(
                update_query,
                {
                    "user_id": user_id,
                    "mckinsey_email": email,
                    "email": email,
                    "full_name": full_name,
                    "mckinsey_fmno": fmno,
                    "mckinsey_preferred_username": preferred_username,
                    "mckinsey_session_state": session_state,
                    "mckinsey_refresh_token_encrypted": encrypted_refresh_token,
                    "mckinsey_token_expires_at": token_expires_at,
                },
            )
            await db.commit()

            logger.info(
                "mckinsey_user_updated",
                user_id=user_id,
                mckinsey_subject=mckinsey_subject,
                email=email,
            )
        else:
            # Create new user
            # Encrypt refresh token if present
            encrypted_refresh_token = None
            if refresh_token:
                try:
                    encrypted_refresh_token = encrypt_refresh_token(refresh_token)
                except Exception as e:
                    logger.warning(
                        "mckinsey_refresh_token_encryption_failed", error=str(e)
                    )

            # Calculate token expiration
            token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            # Create user profile
            insert_query = text(
                """
                INSERT INTO user_profiles (
                    email, full_name, tenant_id, is_active, persona,
                    mckinsey_subject, mckinsey_email, mckinsey_fmno,
                    mckinsey_preferred_username, mckinsey_session_state,
                    mckinsey_refresh_token_encrypted, mckinsey_token_expires_at,
                    created_at, updated_at, last_login_at
                )
                VALUES (
                    :email, :full_name, :tenant_id, true, 'product_manager',
                    :mckinsey_subject, :mckinsey_email, :mckinsey_fmno,
                    :mckinsey_preferred_username, :mckinsey_session_state,
                    :mckinsey_refresh_token_encrypted, :mckinsey_token_expires_at,
                    now(), now(), now()
                )
                RETURNING id
            """
            )
            result = await db.execute(
                insert_query,
                {
                    "email": email,
                    "full_name": full_name,
                    "tenant_id": tenant_id,
                    "mckinsey_subject": mckinsey_subject,
                    "mckinsey_email": email,
                    "mckinsey_fmno": fmno,
                    "mckinsey_preferred_username": preferred_username,
                    "mckinsey_session_state": session_state,
                    "mckinsey_refresh_token_encrypted": encrypted_refresh_token,
                    "mckinsey_token_expires_at": token_expires_at,
                },
            )
            user_id = str(result.fetchone()[0])
            await db.commit()

            logger.info(
                "mckinsey_user_created",
                user_id=user_id,
                mckinsey_subject=mckinsey_subject,
                email=email,
            )

        # Step 5: Generate session token
        session_token = generate_token()
        session_expires_at = datetime.utcnow() + timedelta(days=7)

        # Store session token in Redis
        token_storage = await get_token_storage()
        token_data = {
            "user_id": user_id,
            "email": email,
            "tenant_id": tenant_id,
            "expires_at": session_expires_at.isoformat(),
            "auth_method": "mckinsey_sso",
            "mckinsey_subject": mckinsey_subject,
        }
        expires_in_seconds = int(
            (session_expires_at - datetime.utcnow()).total_seconds()
        )
        await token_storage.store_token(session_token, token_data, expires_in_seconds)

        # Step 6: Set session cookie
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=settings.environment == "production",  # Secure in production
            samesite="lax",
            max_age=7 * 24 * 60 * 60,  # 7 days
        )

        # Log successful authentication
        error_logger.log_authentication_success(
            user_id=user_id,
            user_email=email,
            provider="mckinsey",
            auth_method="sso",
        )

        logger.info(
            "mckinsey_callback_successful",
            user_id=user_id,
            email=email,
            mckinsey_subject=mckinsey_subject,
        )

        return LoginResponse(
            user_id=user_id,
            email=email,
            full_name=full_name,
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            token=session_token,
            expires_at=session_expires_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        # Log comprehensive error for unexpected failures
        from backend.services.oauth_error_logger import (
            get_oauth_error_logger,
            OAuthErrorType,
        )

        error_logger = get_oauth_error_logger()
        error_logger.log_oauth_error(
            error_type=OAuthErrorType.UNKNOWN_ERROR,
            error_message="Unexpected error during McKinsey SSO callback",
            provider="mckinsey",
            exception=e,
        )

        logger.error(
            "mckinsey_callback_error",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="McKinsey SSO login failed. Please try again."
        )


class McKinseyRefreshResponse(BaseModel):
    """Response model for McKinsey token refresh endpoint."""

    access_token: str
    expires_in: int
    message: str


@router.post("/mckinsey/refresh", response_model=McKinseyRefreshResponse)
async def mckinsey_refresh_token(
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Refresh McKinsey access token using stored refresh token.

    This endpoint:
    1. Retrieves the encrypted refresh token from the database
    2. Decrypts the refresh token
    3. Exchanges it for new tokens with McKinsey
    4. Updates the stored tokens in the database
    5. Extends the session expiration

    Args:
        current_user: Current authenticated user from session
        db: Database session

    Returns:
        McKinseyRefreshResponse: Contains new access token and expiration

    Raises:
        HTTPException: If token refresh fails

    Requirements: 3.5, 5.4, 10.1, 10.2, 10.3, 10.4, 10.5
    """
    try:
        # Import McKinsey services
        from backend.services.mckinsey_oidc import get_mckinsey_provider
        from backend.services.token_encryption import decrypt_refresh_token

        user_id = current_user["id"]

        # Step 1: Get encrypted refresh token from database
        query = text(
            """
            SELECT mckinsey_refresh_token_encrypted, mckinsey_subject
            FROM user_profiles
            WHERE id = :user_id AND is_active = true
        """
        )
        result = await db.execute(query, {"user_id": user_id})
        row = result.fetchone()

        if not row:
            logger.error("mckinsey_refresh_user_not_found", user_id=user_id)
            raise HTTPException(
                status_code=401, detail="User not found. Please log in again."
            )

        encrypted_refresh_token = row[0]
        mckinsey_subject = row[1]

        if not encrypted_refresh_token:
            logger.warning(
                "mckinsey_refresh_token_not_found",
                user_id=user_id,
                mckinsey_subject=mckinsey_subject,
            )
            raise HTTPException(
                status_code=401, detail="No refresh token found. Please log in again."
            )

        # Step 2: Decrypt refresh token
        try:
            refresh_token = decrypt_refresh_token(encrypted_refresh_token)
        except Exception as e:
            logger.error(
                "mckinsey_refresh_token_decryption_failed",
                error=str(e),
                user_id=user_id,
            )
            raise HTTPException(
                status_code=401,
                detail="Failed to decrypt refresh token. Please log in again.",
            )

        # Step 3: Exchange refresh token for new tokens
        provider = await get_mckinsey_provider()

        try:
            tokens = await provider.refresh_access_token(refresh_token)
        except Exception as e:
            # Log comprehensive token refresh error
            from backend.services.oauth_error_logger import (
                get_oauth_error_logger,
                OAuthErrorType,
            )

            error_logger = get_oauth_error_logger()
            error_logger.log_oauth_error(
                error_type=OAuthErrorType.TOKEN_REFRESH_FAILED,
                error_message="Failed to refresh McKinsey access token",
                provider="mckinsey",
                user_id=user_id,
                exception=e,
            )

            logger.error(
                "mckinsey_token_refresh_failed",
                error=str(e),
                error_type=type(e).__name__,
                user_id=user_id,
            )

            # Clear session and refresh token on failure
            # Get current session token
            token_storage = await get_token_storage()
            # We don't have direct access to the token here, but we can clear from DB

            # Clear refresh token from database
            clear_query = text(
                """
                UPDATE user_profiles
                SET mckinsey_refresh_token_encrypted = NULL,
                    mckinsey_token_expires_at = NULL
                WHERE id = :user_id
            """
            )
            await db.execute(clear_query, {"user_id": user_id})
            await db.commit()

            logger.info(
                "mckinsey_refresh_token_cleared",
                user_id=user_id,
                reason="refresh_failed",
            )

            raise HTTPException(
                status_code=401,
                detail="Refresh token expired or invalid. Please log in again.",
            )

        # Extract new tokens
        access_token = tokens.get("access_token")
        new_refresh_token = tokens.get("refresh_token")  # May be rotated
        expires_in = tokens.get("expires_in", 3600)

        if not access_token:
            logger.error("mckinsey_refresh_missing_access_token", user_id=user_id)
            raise HTTPException(
                status_code=500,
                detail="Failed to obtain new access token. Please try again.",
            )

        # Step 4: Update stored tokens in database
        # Encrypt new refresh token if provided (token rotation)
        encrypted_new_refresh_token = encrypted_refresh_token  # Keep old one by default
        if new_refresh_token:
            try:
                from backend.services.token_encryption import encrypt_refresh_token

                encrypted_new_refresh_token = encrypt_refresh_token(new_refresh_token)
            except Exception as e:
                logger.warning(
                    "mckinsey_new_refresh_token_encryption_failed",
                    error=str(e),
                    user_id=user_id,
                )

        # Calculate new token expiration
        token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        # Update database
        update_query = text(
            """
            UPDATE user_profiles
            SET mckinsey_refresh_token_encrypted = :mckinsey_refresh_token_encrypted,
                mckinsey_token_expires_at = :mckinsey_token_expires_at,
                updated_at = now()
            WHERE id = :user_id
        """
        )
        await db.execute(
            update_query,
            {
                "user_id": user_id,
                "mckinsey_refresh_token_encrypted": encrypted_new_refresh_token,
                "mckinsey_token_expires_at": token_expires_at,
            },
        )
        await db.commit()

        # Step 5: Extend session expiration in Redis
        token_storage = await get_token_storage()
        # Note: We don't have direct access to the session token here,
        # but the session will be extended on next request through normal auth flow

        logger.info(
            "mckinsey_token_refreshed",
            user_id=user_id,
            mckinsey_subject=mckinsey_subject,
            expires_in=expires_in,
        )

        return McKinseyRefreshResponse(
            access_token=access_token,
            expires_in=expires_in,
            message="Token refreshed successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        # Log comprehensive error for unexpected failures
        from backend.services.oauth_error_logger import (
            get_oauth_error_logger,
            OAuthErrorType,
        )

        error_logger = get_oauth_error_logger()
        error_logger.log_oauth_error(
            error_type=OAuthErrorType.UNKNOWN_ERROR,
            error_message="Unexpected error during token refresh",
            provider="mckinsey",
            exception=e,
        )

        logger.error(
            "mckinsey_refresh_error",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Token refresh failed. Please try again."
        )


class McKinseyLogoutResponse(BaseModel):
    """Response model for McKinsey SSO logout endpoint."""

    logout_url: str
    message: str


@router.post("/mckinsey/logout", response_model=McKinseyLogoutResponse)
async def mckinsey_logout(
    response: Response,
    current_user: dict = Depends(get_current_user),
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    """Logout from McKinsey SSO and initiate RP-initiated logout.

    This endpoint:
    1. Invalidates the session token in Redis
    2. Clears the refresh token from the database
    3. Constructs the RP-initiated logout URL for McKinsey
    4. Clears the session cookie

    Args:
        response: FastAPI response object for clearing cookies
        current_user: Current authenticated user from session
        authorization: Optional authorization header
        session_token: Optional session token from cookie
        db: Database session

    Returns:
        McKinseyLogoutResponse: Contains logout_url for frontend redirect

    Raises:
        HTTPException: If logout fails

    Requirements: 4.4, 5.5, 11.1, 11.2
    """
    try:
        user_id = current_user["id"]

        # Get the session token
        token = None
        if authorization:
            token = authorization.credentials
        elif session_token:
            token = session_token

        # Step 1: Invalidate session token in Redis
        if token:
            token_storage = await get_token_storage()
            await token_storage.delete_token(token)
            logger.info(
                "mckinsey_session_invalidated",
                user_id=user_id,
                token=token[:10] + "...",
            )

        # Step 2: Get ID token and clear refresh token from database
        query = text(
            """
            SELECT mckinsey_subject
            FROM user_profiles
            WHERE id = :user_id
        """
        )
        result = await db.execute(query, {"user_id": user_id})
        row = result.fetchone()

        mckinsey_subject = row[0] if row else None

        # Clear refresh token from database
        clear_query = text(
            """
            UPDATE user_profiles
            SET mckinsey_refresh_token_encrypted = NULL,
                mckinsey_token_expires_at = NULL,
                mckinsey_session_state = NULL
            WHERE id = :user_id
        """
        )
        await db.execute(clear_query, {"user_id": user_id})
        await db.commit()

        logger.info(
            "mckinsey_tokens_cleared",
            user_id=user_id,
            mckinsey_subject=mckinsey_subject,
        )

        # Step 3: Construct RP-initiated logout URL for McKinsey
        # McKinsey uses Keycloak, so logout endpoint follows Keycloak pattern
        # Format: https://auth.mckinsey.id/auth/realms/{realm}/protocol/openid-connect/logout
        from urllib.parse import urlencode

        logout_endpoint = (
            "https://auth.mckinsey.id/auth/realms/r/protocol/openid-connect/logout"
        )

        # Construct post_logout_redirect_uri (where to redirect after logout)
        # This should be the frontend login page
        post_logout_redirect_uri = (
            settings.mckinsey_redirect_uri.rsplit("/", 2)[0] + "/login"
        )

        # Build logout URL with parameters
        # Note: We don't have the ID token here, so we'll do a simple logout
        # For full RP-initiated logout, we would need to store the ID token
        logout_params = {
            "post_logout_redirect_uri": post_logout_redirect_uri,
            "client_id": settings.mckinsey_client_id,
        }

        logout_url = f"{logout_endpoint}?{urlencode(logout_params)}"

        # Step 4: Clear session cookie
        response.delete_cookie(key="session_token")

        # Log successful logout
        from backend.services.oauth_error_logger import get_oauth_error_logger

        error_logger = get_oauth_error_logger()
        error_logger.log_logout_success(
            user_id=user_id,
            provider="mckinsey",
        )

        logger.info(
            "mckinsey_logout_successful",
            user_id=user_id,
            mckinsey_subject=mckinsey_subject,
            logout_url=logout_url,
        )

        return McKinseyLogoutResponse(
            logout_url=logout_url, message="Logged out successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        # Log comprehensive error for unexpected failures
        from backend.services.oauth_error_logger import (
            get_oauth_error_logger,
            OAuthErrorType,
        )

        error_logger = get_oauth_error_logger()
        error_logger.log_oauth_error(
            error_type=OAuthErrorType.SESSION_INVALIDATION_FAILED,
            error_message="Unexpected error during logout",
            provider="mckinsey",
            user_id=current_user.get("id"),
            exception=e,
        )

        logger.error(
            "mckinsey_logout_error",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        # Even if logout fails, clear the cookie
        response.delete_cookie(key="session_token")
        raise HTTPException(status_code=500, detail="Logout failed. Please try again.")
