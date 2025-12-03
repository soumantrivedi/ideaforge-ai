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
        all_providers = ['openai', 'anthropic', 'google', 'v0', 'lovable', 'ai_gateway']
        
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
    valid_providers = ['openai', 'anthropic', 'google', 'v0', 'lovable', 'ai_gateway']
    if provider not in valid_providers:
        raise ValueError(f"Invalid provider. Must be one of: {', '.join(valid_providers)}")
    
    # AI Gateway requires special handling (client_id + client_secret)
    if provider == 'ai_gateway':
        raise ValueError("AI Gateway credentials must be saved via /api/providers/configure endpoint")
    
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
    """Save or update an API key for a provider. Reinitializes Agno framework if AI provider key is updated."""
    try:
        result = await _save_api_key_internal(
            request.provider,
            request.api_key,
            current_user["id"],
            db
        )
        
        # If this is an AI provider key (openai, anthropic, google, ai_gateway), reinitialize Agno framework
        ai_providers = ['openai', 'anthropic', 'google', 'ai_gateway']
        if request.provider in ai_providers:
            try:
                from backend.services.api_key_loader import load_user_api_keys_from_db
                from backend.services.provider_registry import provider_registry
                from backend.main import reinitialize_orchestrator
                
                # Load user's API keys and update provider registry
                user_keys = await load_user_api_keys_from_db(db, str(current_user["id"]))
                
                # Map provider names (database uses 'anthropic' and 'google', registry uses 'claude' and 'gemini')
                provider_mapping = {
                    'openai': 'openai',
                    'anthropic': 'claude',
                    'google': 'gemini'
                }
                
                # Update provider registry with user's keys (user keys override .env keys)
                # Only update the key that was just saved, others remain unchanged
                update_params = {}
                if request.provider == 'openai':
                    update_params['openai_key'] = user_keys.get("openai")
                elif request.provider == 'anthropic':
                    update_params['claude_key'] = user_keys.get("claude")
                elif request.provider == 'google':
                    update_params['gemini_key'] = user_keys.get("gemini")
                
                provider_registry.update_keys(**update_params)
                
                # Reinitialize orchestrator with new keys
                reinitialize_orchestrator()
                
                logger.info(
                    "agno_reinitialized_after_api_key_update",
                    provider=request.provider,
                    user_id=str(current_user["id"]),
                    has_openai=provider_registry.has_openai_key(),
                    has_claude=provider_registry.has_claude_key(),
                    has_gemini=provider_registry.has_gemini_key(),
                    configured_providers=provider_registry.get_configured_providers()
                )
            except Exception as e:
                logger.warning(
                    "agno_reinitialization_failed_after_api_key_update",
                    provider=request.provider,
                    error=str(e)
                )
                # Don't fail the API key save if reinitialization fails
        
        return result
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
    """Delete an API key for a provider. Reinitializes Agno framework if AI provider key is deleted."""
    try:
        valid_providers = ['openai', 'anthropic', 'google', 'v0', 'lovable', 'ai_gateway']
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
        
        # If this is an AI provider key, reinitialize Agno framework (will fall back to .env keys)
        ai_providers = ['openai', 'anthropic', 'google', 'ai_gateway']
        if provider in ai_providers:
            try:
                from backend.services.api_key_loader import load_user_api_keys_from_db
                from backend.services.provider_registry import provider_registry
                from backend.main import reinitialize_orchestrator
                
                # Load remaining user's API keys
                user_keys = await load_user_api_keys_from_db(db, str(current_user["id"]))
                
                # Update provider registry (deleted key will fall back to .env)
                provider_registry.update_keys(
                    openai_key=user_keys.get("openai"),
                    claude_key=user_keys.get("claude"),
                    gemini_key=user_keys.get("gemini"),
                )
                
                # Reinitialize orchestrator
                reinitialize_orchestrator()
                
                logger.info(
                    "agno_reinitialized_after_api_key_deletion",
                    provider=provider,
                    user_id=str(current_user["id"]),
                    has_openai=provider_registry.has_openai_key(),
                    has_claude=provider_registry.has_claude_key(),
                    has_gemini=provider_registry.has_gemini_key(),
                    configured_providers=provider_registry.get_configured_providers()
                )
            except Exception as e:
                logger.warning(
                    "agno_reinitialization_failed_after_api_key_deletion",
                    provider=provider,
                    error=str(e)
                )
        
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

