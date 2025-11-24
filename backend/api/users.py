"""User management and profile API endpoints."""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
from pydantic import BaseModel, EmailStr
from uuid import UUID
import structlog

from backend.database import get_db
from backend.api.auth import get_current_user

logger = structlog.get_logger()
router = APIRouter(prefix="/api/users", tags=["users"])


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    persona: Optional[str] = None
    avatar_url: Optional[str] = None


class UserPreferencesRequest(BaseModel):
    theme: Optional[str] = None
    language: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    email_notifications: Optional[bool] = None
    preferences: Optional[dict] = None


@router.get("/profile")
async def get_profile(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user profile."""
    try:
        query = text("""
            SELECT id, email, full_name, persona, avatar_url, tenant_id, 
                   created_at, updated_at, last_login_at
            FROM user_profiles
            WHERE id = :user_id
        """)
        
        result = await db.execute(query, {"user_id": current_user["id"]})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "id": str(row[0]),
            "email": row[1],
            "full_name": row[2],
            "persona": row[3],
            "avatar_url": row[4],
            "tenant_id": str(row[5]),
            "created_at": row[6].isoformat() if row[6] else None,
            "updated_at": row[7].isoformat() if row[7] else None,
            "last_login_at": row[8].isoformat() if row[8] else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_profile_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get profile")


@router.put("/profile")
async def update_profile(
    request: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user profile."""
    try:
        update_fields = []
        params = {"user_id": current_user["id"]}
        
        if request.full_name is not None:
            update_fields.append("full_name = :full_name")
            params["full_name"] = request.full_name
        
        if request.persona is not None:
            if request.persona not in ['product_manager', 'leadership', 'tech_lead']:
                raise HTTPException(status_code=400, detail="Invalid persona")
            update_fields.append("persona = :persona")
            params["persona"] = request.persona
        
        if request.avatar_url is not None:
            update_fields.append("avatar_url = :avatar_url")
            params["avatar_url"] = request.avatar_url
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        update_fields.append("updated_at = now()")
        
        query = text(f"""
            UPDATE user_profiles
            SET {', '.join(update_fields)}
            WHERE id = :user_id
            RETURNING id, email, full_name, persona, avatar_url
        """)
        
        result = await db.execute(query, params)
        await db.commit()
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "id": str(row[0]),
            "email": row[1],
            "full_name": row[2],
            "persona": row[3],
            "avatar_url": row[4],
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("update_profile_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update profile")


@router.get("/preferences")
async def get_preferences(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user preferences."""
    try:
        query = text("""
            SELECT theme, language, notifications_enabled, email_notifications, preferences
            FROM user_preferences
            WHERE user_id = :user_id
        """)
        
        result = await db.execute(query, {"user_id": current_user["id"]})
        row = result.fetchone()
        
        if not row:
            # Create default preferences
            insert_query = text("""
                INSERT INTO user_preferences (user_id, theme, language, notifications_enabled)
                VALUES (:user_id, 'light', 'en', true)
                RETURNING theme, language, notifications_enabled, email_notifications, preferences
            """)
            result = await db.execute(insert_query, {"user_id": current_user["id"]})
            await db.commit()
            row = result.fetchone()
        
        return {
            "theme": row[0],
            "language": row[1],
            "notifications_enabled": row[2],
            "email_notifications": row[3] if row[3] is not None else False,
            "preferences": row[4] if row[4] else {},
        }
    except Exception as e:
        logger.error("get_preferences_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get preferences")


@router.put("/preferences")
async def update_preferences(
    request: UserPreferencesRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user preferences."""
    try:
        # Check if preferences exist
        check_query = text("""
            SELECT id FROM user_preferences WHERE user_id = :user_id
        """)
        result = await db.execute(check_query, {"user_id": current_user["id"]})
        exists = result.fetchone()
        
        if not exists:
            # Create preferences
            insert_query = text("""
                INSERT INTO user_preferences (user_id, theme, language, notifications_enabled, email_notifications, preferences)
                VALUES (:user_id, :theme, :language, :notifications_enabled, :email_notifications, CAST(:preferences AS jsonb))
                RETURNING theme, language, notifications_enabled, email_notifications, preferences
            """)
            
            result = await db.execute(insert_query, {
                "user_id": current_user["id"],
                "theme": request.theme or "light",
                "language": request.language or "en",
                "notifications_enabled": request.notifications_enabled if request.notifications_enabled is not None else True,
                "email_notifications": request.email_notifications if request.email_notifications is not None else False,
                "preferences": str(request.preferences or {})
            })
            await db.commit()
        else:
            # Update preferences
            update_fields = []
            params = {"user_id": current_user["id"]}
            
            if request.theme is not None:
                if request.theme not in ['light', 'dark', 'retro']:
                    raise HTTPException(status_code=400, detail="Invalid theme")
                update_fields.append("theme = :theme")
                params["theme"] = request.theme
            
            if request.language is not None:
                update_fields.append("language = :language")
                params["language"] = request.language
            
            if request.notifications_enabled is not None:
                update_fields.append("notifications_enabled = :notifications_enabled")
                params["notifications_enabled"] = request.notifications_enabled
            
            if request.email_notifications is not None:
                update_fields.append("email_notifications = :email_notifications")
                params["email_notifications"] = request.email_notifications
            
            if request.preferences is not None:
                update_fields.append("preferences = CAST(:preferences AS jsonb)")
                params["preferences"] = str(request.preferences)
            
            if not update_fields:
                raise HTTPException(status_code=400, detail="No fields to update")
            
            update_fields.append("updated_at = now()")
            
            update_query = text(f"""
                UPDATE user_preferences
                SET {', '.join(update_fields)}
                WHERE user_id = :user_id
                RETURNING theme, language, notifications_enabled, email_notifications, preferences
            """)
            
            result = await db.execute(update_query, params)
            await db.commit()
        
        row = result.fetchone()
        
        return {
            "theme": row[0],
            "language": row[1],
            "notifications_enabled": row[2],
            "email_notifications": row[3] if row[3] is not None else False,
            "preferences": row[4] if row[4] else {},
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("update_preferences_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update preferences")

