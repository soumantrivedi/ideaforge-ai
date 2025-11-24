"""API endpoints for managing integration configurations (GitHub, Atlassian, etc.)."""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, Dict, Any
from pydantic import BaseModel
import structlog

from backend.database import get_db
from backend.api.auth import get_current_user
from backend.utils.encryption import get_encryption

logger = structlog.get_logger()
router = APIRouter(prefix="/api/integrations", tags=["integrations"])


class IntegrationConfigRequest(BaseModel):
    provider: str  # 'github' or 'atlassian'
    config: Dict[str, str]  # Provider-specific configuration


class IntegrationConfigResponse(BaseModel):
    provider: str
    configured: bool
    message: str


@router.post("/configure", response_model=IntegrationConfigResponse)
async def configure_integration(
    payload: IntegrationConfigRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Configure integration credentials (GitHub PAT, Atlassian SSO, etc.)."""
    try:
        await db.execute(text(f"SET LOCAL app.current_user_id = '{current_user['id']}'"))
        
        encryption = get_encryption()
        user_id = current_user["id"]
        
        if payload.provider == "github":
            # GitHub PAT configuration
            if "pat" not in payload.config:
                raise HTTPException(status_code=400, detail="GitHub PAT is required")
            
            pat = payload.config["pat"].strip()
            if not pat:
                raise HTTPException(status_code=400, detail="GitHub PAT cannot be empty")
            
            # Encrypt and save
            encrypted_pat = encryption.encrypt(pat)
            
            query = text("""
                INSERT INTO user_api_keys (user_id, provider, api_key_encrypted, is_active, metadata)
                VALUES (:user_id, 'github', :api_key_encrypted, true, '{"type": "pat"}'::jsonb)
                ON CONFLICT (user_id, provider)
                DO UPDATE SET 
                  api_key_encrypted = :api_key_encrypted,
                  is_active = true,
                  updated_at = CURRENT_TIMESTAMP,
                  metadata = '{"type": "pat"}'::jsonb
            """)
            
            await db.execute(query, {
                "user_id": user_id,
                "api_key_encrypted": encrypted_pat
            })
            await db.commit()
            
            logger.info("github_pat_configured", user_id=str(user_id))
            return IntegrationConfigResponse(
                provider="github",
                configured=True,
                message="GitHub PAT configured successfully"
            )
        
        elif payload.provider == "atlassian":
            # Atlassian SSO configuration
            required_fields = ["url", "email", "api_token"]
            missing_fields = [f for f in required_fields if f not in payload.config or not payload.config[f].strip()]
            
            if missing_fields:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required fields: {', '.join(missing_fields)}"
                )
            
            # Encrypt API token
            api_token = payload.config["api_token"].strip()
            encrypted_token = encryption.encrypt(api_token)
            
            # Store configuration in metadata
            metadata = {
                "type": "sso",
                "url": payload.config["url"].strip(),
                "email": payload.config["email"].strip(),
            }
            
            import json
            query = text("""
                INSERT INTO user_api_keys (user_id, provider, api_key_encrypted, is_active, metadata)
                VALUES (:user_id, 'atlassian', :api_key_encrypted, true, :metadata::jsonb)
                ON CONFLICT (user_id, provider)
                DO UPDATE SET 
                  api_key_encrypted = :api_key_encrypted,
                  is_active = true,
                  updated_at = CURRENT_TIMESTAMP,
                  metadata = :metadata::jsonb
            """)
            
            await db.execute(query, {
                "user_id": user_id,
                "api_key_encrypted": encrypted_token,
                "metadata": json.dumps(metadata)
            })
            await db.commit()
            
            logger.info("atlassian_sso_configured", user_id=str(user_id), url=metadata["url"])
            return IntegrationConfigResponse(
                provider="atlassian",
                configured=True,
                message="Atlassian SSO configured successfully"
            )
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {payload.provider}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("integration_configuration_failed", error=str(e), provider=payload.provider)
        raise HTTPException(status_code=500, detail=f"Failed to configure {payload.provider} integration")


@router.get("/status")
async def get_integration_status(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get status of all integrations for the current user."""
    try:
        await db.execute(text(f"SET LOCAL app.current_user_id = '{current_user['id']}'"))
        
        query = text("""
            SELECT provider, metadata
            FROM user_api_keys
            WHERE user_id = :user_id 
            AND provider IN ('github', 'atlassian')
            AND is_active = true
        """)
        
        result = await db.execute(query, {"user_id": current_user["id"]})
        rows = result.fetchall()
        
        integrations = {}
        for row in rows:
            provider = row[0]
            metadata = row[1] or {}
            integrations[provider] = {
                "configured": True,
                "metadata": metadata
            }
        
        # Add unconfigured providers
        if "github" not in integrations:
            integrations["github"] = {"configured": False, "metadata": {}}
        if "atlassian" not in integrations:
            integrations["atlassian"] = {"configured": False, "metadata": {}}
        
        return {"integrations": integrations}
    
    except Exception as e:
        logger.error("get_integration_status_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get integration status")

