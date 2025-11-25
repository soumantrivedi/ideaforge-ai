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
            
            import json
            metadata_json = json.dumps({"type": "pat"})
            
            query = text("""
                INSERT INTO user_api_keys (user_id, provider, api_key_encrypted, is_active, metadata)
                VALUES (:user_id, 'github', :api_key_encrypted, true, CAST(:metadata AS jsonb))
                ON CONFLICT (user_id, provider)
                DO UPDATE SET 
                  api_key_encrypted = :api_key_encrypted,
                  is_active = true,
                  updated_at = CURRENT_TIMESTAMP,
                  metadata = CAST(:metadata AS jsonb)
            """)
            
            await db.execute(query, {
                "user_id": user_id,
                "api_key_encrypted": encrypted_pat,
                "metadata": metadata_json
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
            metadata_json = json.dumps(metadata)
            
            query = text("""
                INSERT INTO user_api_keys (user_id, provider, api_key_encrypted, is_active, metadata)
                VALUES (:user_id, 'atlassian', :api_key_encrypted, true, CAST(:metadata AS jsonb))
                ON CONFLICT (user_id, provider)
                DO UPDATE SET 
                  api_key_encrypted = :api_key_encrypted,
                  is_active = true,
                  updated_at = CURRENT_TIMESTAMP,
                  metadata = CAST(:metadata AS jsonb)
            """)
            
            await db.execute(query, {
                "user_id": user_id,
                "api_key_encrypted": encrypted_token,
                "metadata": metadata_json
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


class IntegrationVerifyRequest(BaseModel):
    provider: str
    config: Dict[str, str]


class IntegrationVerifyResponse(BaseModel):
    provider: str
    valid: bool
    message: str


@router.post("/verify", response_model=IntegrationVerifyResponse)
async def verify_integration(
    payload: IntegrationVerifyRequest,
    current_user: dict = Depends(get_current_user)
):
    """Verify integration credentials (GitHub PAT, Atlassian SSO, etc.) without saving."""
    try:
        if payload.provider == "github":
            # Verify GitHub PAT
            if "pat" not in payload.config:
                return IntegrationVerifyResponse(
                    provider="github",
                    valid=False,
                    message="GitHub PAT is required"
                )
            
            pat = payload.config["pat"].strip()
            if not pat:
                return IntegrationVerifyResponse(
                    provider="github",
                    valid=False,
                    message="GitHub PAT cannot be empty"
                )
            
            # Verify GitHub PAT by making an API call
            try:
                from github import Github
                github_client = Github(pat)
                # Try to get the authenticated user
                user = github_client.get_user()
                return IntegrationVerifyResponse(
                    provider="github",
                    valid=True,
                    message=f"GitHub PAT verified successfully. Authenticated as: {user.login}"
                )
            except Exception as e:
                logger.warning("github_pat_verification_failed", error=str(e))
                return IntegrationVerifyResponse(
                    provider="github",
                    valid=False,
                    message=f"GitHub PAT verification failed: {str(e)}"
                )
        
        elif payload.provider == "atlassian":
            # Verify Atlassian SSO
            required_fields = ["url", "email", "api_token"]
            missing_fields = [f for f in required_fields if f not in payload.config or not payload.config[f].strip()]
            
            if missing_fields:
                return IntegrationVerifyResponse(
                    provider="atlassian",
                    valid=False,
                    message=f"Missing required fields: {', '.join(missing_fields)}"
                )
            
            url = payload.config["url"].strip()
            email = payload.config["email"].strip()
            api_token = payload.config["api_token"].strip()
            
            # Verify Atlassian credentials by making an API call
            try:
                from atlassian import Confluence
                confluence_client = Confluence(
                    url=url,
                    username=email,
                    password=api_token,
                    cloud=True
                )
                # Try to list spaces as a simple verification
                # This will fail if credentials are invalid
                spaces = confluence_client.get_all_spaces(limit=1)
                # If we get here, credentials are valid
                return IntegrationVerifyResponse(
                    provider="atlassian",
                    valid=True,
                    message=f"Atlassian credentials verified successfully. Connected to: {url}"
                )
            except Exception as e:
                logger.warning("atlassian_verification_failed", error=str(e))
                error_msg = str(e)
                # Provide more user-friendly error messages
                if "401" in error_msg or "Unauthorized" in error_msg or "authentication" in error_msg.lower():
                    error_msg = "Invalid credentials. Please check your email and API token."
                elif "404" in error_msg or "Not Found" in error_msg:
                    error_msg = "Invalid Atlassian URL. Please check the URL format."
                return IntegrationVerifyResponse(
                    provider="atlassian",
                    valid=False,
                    message=f"Atlassian verification failed: {error_msg}"
                )
        
        else:
            return IntegrationVerifyResponse(
                provider=payload.provider,
                valid=False,
                message=f"Unknown provider: {payload.provider}"
            )
    
    except Exception as e:
        logger.error("integration_verification_error", error=str(e), provider=payload.provider)
        return IntegrationVerifyResponse(
            provider=payload.provider,
            valid=False,
            message=f"Verification error: {str(e)}"
        )


@router.get("/status")
async def get_integration_status(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get status of all integrations for the current user."""
    try:
        await db.execute(text(f"SET LOCAL app.current_user_id = '{current_user['id']}'"))
        
        query = text("""
            SELECT provider, COALESCE(metadata, '{}'::jsonb) as metadata
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

