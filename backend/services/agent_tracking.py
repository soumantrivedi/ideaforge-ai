"""
Service for tracking agent interactions and saving them to conversation_history.
Used by Review, PRD Scoring, Export, and other direct agent calls.
"""
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json
import structlog

logger = structlog.get_logger()


async def save_agent_interaction_to_db(
    db: AsyncSession,
    user_id: UUID,
    product_id: Optional[UUID],
    session_id: Optional[str],
    agent_name: str,
    agent_role: str,
    user_message: str,
    agent_response: str,
    tenant_id: Optional[str] = None,
    phase_id: Optional[UUID] = None,
    interaction_metadata: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Save an agent interaction to conversation_history.
    Used by Review, PRD Scoring, Export, and other direct agent calls.
    
    Args:
        db: Database session
        user_id: User ID
        product_id: Product ID (optional)
        session_id: Session ID (optional, will create if not provided)
        agent_name: Name of the agent
        agent_role: Role of the agent (e.g., 'scoring', 'validation', 'export')
        user_message: User's message/request
        agent_response: Agent's response
        tenant_id: Tenant ID (optional)
        phase_id: Phase ID (optional)
        interaction_metadata: Metadata about agent interactions (optional)
        metadata: Additional metadata (optional)
    """
    try:
        # Ensure session_id exists
        if not session_id and product_id:
            # Try to find existing session
            session_check_query = text("""
                SELECT id FROM conversation_sessions
                WHERE product_id = :product_id
                AND user_id = :user_id
                ORDER BY created_at DESC
                LIMIT 1
            """)
            session_result = await db.execute(session_check_query, {
                "product_id": str(product_id),
                "user_id": str(user_id)
            })
            existing_session = session_result.fetchone()
            
            if existing_session:
                session_id = str(existing_session[0])
            else:
                # Create a new session
                import uuid
                session_id = str(uuid.uuid4())
                session_create_query = text("""
                    INSERT INTO conversation_sessions (id, user_id, product_id, tenant_id, title)
                    VALUES (:id, :user_id, :product_id, :tenant_id, :title)
                """)
                await db.execute(session_create_query, {
                    "id": session_id,
                    "user_id": str(user_id),
                    "product_id": str(product_id) if product_id else None,
                    "tenant_id": tenant_id,
                    "title": f"Product {str(product_id)[:8]}..." if product_id else "Agent Interaction"
                })
        
        # Build interaction metadata
        full_interaction_metadata = {
            "primary_agent": agent_name,
            "agent_role": agent_role,
            "phase_id": str(phase_id) if phase_id else None,
            **(interaction_metadata or {}),
            **(metadata or {})
        }
        
        # Save user message
        user_message_query = text("""
            INSERT INTO conversation_history
            (session_id, product_id, message_type, agent_name, agent_role, content, tenant_id, phase_id)
            VALUES (:session_id, :product_id, :message_type, :agent_name, :agent_role, :content, :tenant_id, :phase_id)
        """)
        await db.execute(user_message_query, {
            "session_id": session_id,
            "product_id": str(product_id) if product_id else None,
            "message_type": "user",
            "agent_name": None,
            "agent_role": None,
            "content": user_message,
            "tenant_id": tenant_id,
            "phase_id": str(phase_id) if phase_id else None
        })
        
        # Save agent response
        assistant_message_query = text("""
            INSERT INTO conversation_history
            (session_id, product_id, message_type, agent_name, agent_role, content, interaction_metadata, tenant_id, phase_id)
            VALUES (:session_id, :product_id, :message_type, :agent_name, :agent_role, :content, CAST(:interaction_metadata AS jsonb), :tenant_id, :phase_id)
        """)
        await db.execute(assistant_message_query, {
            "session_id": session_id,
            "product_id": str(product_id) if product_id else None,
            "message_type": "agent",
            "agent_name": agent_name,
            "agent_role": agent_role,
            "content": agent_response,
            "interaction_metadata": json.dumps(full_interaction_metadata),
            "tenant_id": tenant_id,
            "phase_id": str(phase_id) if phase_id else None
        })
        
        await db.commit()
        logger.info(
            "agent_interaction_saved",
            agent_name=agent_name,
            agent_role=agent_role,
            user_id=str(user_id),
            product_id=str(product_id) if product_id else None
        )
    except Exception as e:
        logger.error(
            "failed_to_save_agent_interaction",
            error=str(e),
            agent_name=agent_name,
            agent_role=agent_role,
            user_id=str(user_id)
        )
        await db.rollback()
        raise

