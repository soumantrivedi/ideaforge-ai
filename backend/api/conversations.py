"""Conversation history API endpoints."""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
from pydantic import BaseModel
import structlog

from backend.database import get_db
from backend.api.auth import get_current_user

logger = structlog.get_logger()
router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("/history")
async def get_conversation_history(
    product_id: Optional[str] = None,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get conversation history for current user or specific product."""
    try:
        await db.execute(text(f"SET LOCAL app.current_user_id = '{current_user['id']}'"))
        
        if product_id:
            # Verify product access
            access_query = text("""
                SELECT p.id FROM products p
                LEFT JOIN product_shares ps ON p.id = ps.product_id AND ps.shared_with_user_id = :user_id
                WHERE p.id = :product_id
                AND p.tenant_id = :tenant_id
                AND (
                  p.user_id = :user_id
                  OR ps.id IS NOT NULL
                )
            """)
            access_result = await db.execute(access_query, {
                "product_id": product_id,
                "user_id": current_user["id"],
                "tenant_id": current_user["tenant_id"]
            })
            if not access_result.fetchone():
                raise HTTPException(status_code=403, detail="Access denied to product")
            
            query = text("""
                SELECT ch.id, ch.message_type, ch.agent_name, ch.agent_role, 
                       ch.content, ch.formatted_content, ch.created_at,
                       cs.title as session_title
                FROM conversation_history ch
                JOIN conversation_sessions cs ON ch.session_id = cs.id
                WHERE ch.product_id = :product_id
                AND ch.tenant_id = :tenant_id
                ORDER BY ch.created_at DESC
                LIMIT :limit
            """)
            params = {
                "product_id": product_id,
                "tenant_id": current_user["tenant_id"],
                "limit": limit
            }
        else:
            # Get all conversations for user
            query = text("""
                SELECT ch.id, ch.message_type, ch.agent_name, ch.agent_role,
                       ch.content, ch.formatted_content, ch.created_at,
                       cs.title as session_title, ch.product_id,
                       p.name as product_name
                FROM conversation_history ch
                JOIN conversation_sessions cs ON ch.session_id = cs.id
                LEFT JOIN products p ON ch.product_id = p.id
                WHERE ch.tenant_id = :tenant_id
                AND (
                  cs.user_id = :user_id
                  OR ch.product_id IN (
                    SELECT product_id FROM product_shares
                    WHERE shared_with_user_id = :user_id
                  )
                )
                ORDER BY ch.created_at DESC
                LIMIT :limit
            """)
            params = {
                "user_id": current_user["id"],
                "tenant_id": current_user["tenant_id"],
                "limit": limit
            }
        
        result = await db.execute(query, params)
        rows = result.fetchall()
        
        conversations = [
            {
                "id": str(row[0]),
                "message_type": row[1],
                "agent_name": row[2],
                "agent_role": row[3],
                "content": row[4],
                "formatted_content": row[5],
                "created_at": row[6].isoformat() if row[6] else None,
                "session_title": row[7],
                "product_id": str(row[8]) if len(row) > 8 and row[8] else None,
                "product_name": row[9] if len(row) > 9 else None,
            }
            for row in rows
        ]
        
        return {"conversations": conversations, "count": len(conversations)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_conversation_history_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get conversation history")

