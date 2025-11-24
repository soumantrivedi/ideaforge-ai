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


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    tenant_id: Optional[str] = None


# Simple token storage (in production, use Redis or JWT)
active_tokens: dict[str, dict] = {}


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    try:
        # Use bcrypt directly to avoid passlib issues
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        # Fallback to passlib if bcrypt fails
        return pwd_context.verify(plain_password, hashed_password)


def generate_token() -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(32)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session_token: Optional[str] = Cookie(None),
) -> dict:
    """Get current authenticated user from token."""
    token = None
    if authorization:
        token = authorization.credentials
    elif session_token:
        token = session_token
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check token in active_tokens
    if token not in active_tokens:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    token_data = active_tokens[token]
    if datetime.utcnow() > datetime.fromisoformat(token_data["expires_at"]):
        del active_tokens[token]
        raise HTTPException(status_code=401, detail="Token expired")
    
    # Verify user still exists and is active
    query = text("""
        SELECT id, email, full_name, tenant_id, is_active, persona, avatar_url
        FROM user_profiles
        WHERE id = :user_id AND is_active = true
    """)
    
    result = await db.execute(query, {"user_id": token_data["user_id"]})
    row = result.fetchone()
    
    if not row:
        del active_tokens[token]
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    return {
        "id": str(row[0]),
        "email": row[1],
        "full_name": row[2],
        "tenant_id": str(row[3]),
        "persona": row[5],
        "avatar_url": row[6],
    }


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user and return session token."""
    try:
        # Get user from database
        query = text("""
            SELECT up.id, up.email, up.full_name, up.password_hash, up.tenant_id, 
                   up.is_active, t.name as tenant_name
            FROM user_profiles up
            JOIN tenants t ON up.tenant_id = t.id
            WHERE up.email = :email
        """)
        
        result = await db.execute(query, {"email": request.email.lower()})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        user_id, email, full_name, password_hash, tenant_id, is_active, tenant_name = row
        
        if not is_active:
            raise HTTPException(status_code=403, detail="User account is inactive")
        
        # Verify password
        if not password_hash or not verify_password(request.password, password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Generate token
        token = generate_token()
        expires_at = datetime.utcnow() + timedelta(days=7)
        
        # Store token
        active_tokens[token] = {
            "user_id": str(user_id),
            "email": email,
            "tenant_id": str(tenant_id),
            "expires_at": expires_at.isoformat(),
        }
        
        # Update last login
        update_query = text("""
            UPDATE user_profiles
            SET last_login_at = now()
            WHERE id = :user_id
        """)
        await db.execute(update_query, {"user_id": user_id})
        await db.commit()
        
        # Set cookie
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=7 * 24 * 60 * 60,  # 7 days
        )
        
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
        logger.error("login_error", error=str(e))
        raise HTTPException(status_code=500, detail="Login failed")


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
    
    if token and token in active_tokens:
        del active_tokens[token]
    
    response.delete_cookie(key="session_token")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user information."""
    try:
        # Get tenant name
        query = text("""
            SELECT name FROM tenants WHERE id = :tenant_id
        """)
        result = await db.execute(query, {"tenant_id": current_user["tenant_id"]})
        row = result.fetchone()
        tenant_name = row[0] if row else "Unknown"
        
        return UserInfo(
            id=current_user["id"],
            email=current_user["email"],
            full_name=current_user["full_name"],
            tenant_id=current_user["tenant_id"],
            tenant_name=tenant_name,
            persona=current_user["persona"],
            avatar_url=current_user.get("avatar_url"),
        )
    except Exception as e:
        logger.error("get_user_info_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get user info")


@router.get("/users")
async def list_users(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all users in the same tenant."""
    try:
        query = text("""
            SELECT id, email, full_name, persona, avatar_url, created_at, last_login_at
            FROM user_profiles
            WHERE tenant_id = :tenant_id AND is_active = true
            ORDER BY full_name, email
        """)
        
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

