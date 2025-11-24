"""API endpoints for managing user API keys."""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, List
from pydantic import BaseModel
import structlog

from backend.database import get_db
from backend.api.auth import get_current_user
from backend.utils.encryption import get_encryption

logger = structlog.get_logger()
router = APIRouter(prefix="/api/api-keys", tags=["api-keys"])


class APIKeyRequest(BaseModel):
    provider: str
    api_key: str


class APIKeyResponse(BaseModel):
    provider: str
    is_configured: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class APIKeysStatusResponse(BaseModel):
    keys: List[APIKeyResponse]


@router.get("", response_model=APIKeysStatusResponse)
async def get_api_keys_status(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get status of all API keys for the current user (which are configured)."""
    try:
        await db.execute(text(f"SET LOCAL app.current_user_id = '{current_user['id']}'"))
        
        query = text("""
            SELECT provider, created_at, updated_at
            FROM user_api_keys
            WHERE user_id = :user_id AND is_active = true
        """)
        
        result = await db.execute(query, {"user_id": current_user["id"]})
        rows = result.fetchall()
        
        configured_providers = {row[0]: {"created_at": row[1], "updated_at": row[2]} for row in rows}
        
        # All supported providers
        all_providers = ['openai', 'anthropic', 'google', 'v0', 'lovable']
        
        keys = [
            APIKeyResponse(
                provider=provider,
                is_configured=provider in configured_providers,
                created_at=configured_providers[provider]["created_at"].isoformat() if provider in configured_providers and configured_providers[provider]["created_at"] else None,
                updated_at=configured_providers[provider]["updated_at"].isoformat() if provider in configured_providers and configured_providers[provider]["updated_at"] else None,
            )
            for provider in all_providers
        ]
        
        return APIKeysStatusResponse(keys=keys)
    except Exception as e:
        logger.error("get_api_keys_status_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get API keys status")


async def _save_api_key_internal(
    provider: str,
    api_key: str,
    user_id: str,
    db: AsyncSession
) -> APIKeyResponse:
    """Internal function to save API key (can be called from other modules)."""
    # Validate provider
    valid_providers = ['openai', 'anthropic', 'google', 'v0', 'lovable']
    if provider not in valid_providers:
        raise ValueError(f"Invalid provider. Must be one of: {', '.join(valid_providers)}")
    
    if not api_key or not api_key.strip():
        raise ValueError("API key cannot be empty")
    
    await db.execute(text(f"SET LOCAL app.current_user_id = '{user_id}'"))
    
    # Encrypt the API key
    encryption = get_encryption()
    encrypted_key = encryption.encrypt(api_key.strip())
    
    # Insert or update
    query = text("""
        INSERT INTO user_api_keys (user_id, provider, api_key_encrypted, is_active)
        VALUES (:user_id, :provider, :api_key_encrypted, true)
        ON CONFLICT (user_id, provider)
        DO UPDATE SET 
          api_key_encrypted = :api_key_encrypted,
          is_active = true,
          updated_at = now()
        RETURNING created_at, updated_at
    """)
    
    result = await db.execute(query, {
        "user_id": user_id,
        "provider": provider,
        "api_key_encrypted": encrypted_key
    })
    await db.commit()
    row = result.fetchone()
    
    return APIKeyResponse(
        provider=provider,
        is_configured=True,
        created_at=row[0].isoformat() if row[0] else None,
        updated_at=row[1].isoformat() if row[1] else None,
    )


@router.post("", response_model=APIKeyResponse)
async def save_api_key(
    request: APIKeyRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Save or update an API key for a provider."""
    try:
        return await _save_api_key_internal(
            request.provider,
            request.api_key,
            current_user["id"],
            db
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error("save_api_key_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to save API key: {str(e)}")


@router.delete("/{provider}")
async def delete_api_key(
    provider: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an API key for a provider."""
    try:
        valid_providers = ['openai', 'anthropic', 'google', 'v0', 'lovable']
        if provider not in valid_providers:
            raise HTTPException(status_code=400, detail=f"Invalid provider")
        
        await db.execute(text(f"SET LOCAL app.current_user_id = '{current_user['id']}'"))
        
        query = text("""
            UPDATE user_api_keys
            SET is_active = false, updated_at = now()
            WHERE user_id = :user_id AND provider = :provider
            RETURNING id
        """)
        
        result = await db.execute(query, {
            "user_id": current_user["id"],
            "provider": provider
        })
        await db.commit()
        
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="API key not found")
        
        return {"message": "API key deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("delete_api_key_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete API key")


@router.get("/decrypt/{provider}")
async def get_decrypted_api_key(
    provider: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get decrypted API key for a provider (for internal use only)."""
    try:
        await db.execute(text(f"SET LOCAL app.current_user_id = '{current_user['id']}'"))
        
        query = text("""
            SELECT api_key_encrypted
            FROM user_api_keys
            WHERE user_id = :user_id AND provider = :provider AND is_active = true
        """)
        
        result = await db.execute(query, {
            "user_id": current_user["id"],
            "provider": provider
        })
        row = result.fetchone()
        
        if not row:
            return {"api_key": None}
        
        # Decrypt the key
        encryption = get_encryption()
        decrypted_key = encryption.decrypt(row[0])
        
        return {"api_key": decrypted_key}
    except Exception as e:
        logger.error("get_decrypted_api_key_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get API key")

