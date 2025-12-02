"""Database API endpoints for frontend."""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
import structlog

from backend.database import get_db, AsyncSessionLocal
from backend.api.auth import get_current_user
from backend.models.schemas import (
    Product,
    PRDDocument,
    ConversationSession,
    AgentMessage,
    KnowledgeArticle,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/api/db", tags=["database"])


@router.get("/phases")
async def get_lifecycle_phases(db: AsyncSession = Depends(get_db)):
    """Get all product lifecycle phases."""
    try:
        result = await db.execute(
            text("""
                SELECT id, phase_name, phase_order, description, icon, 
                       required_fields, template_prompts, created_at
                FROM product_lifecycle_phases
                ORDER BY phase_order ASC
            """)
        )
        rows = result.fetchall()
        phases = [
            {
                "id": str(row[0]),
                "phase_name": row[1],
                "phase_order": row[2],
                "description": row[3],
                "icon": row[4],
                "required_fields": row[5],
                "template_prompts": row[6],
                "created_at": row[7].isoformat() if row[7] else None,
            }
            for row in rows
        ]
        return {"phases": phases}
    except Exception as e:
        logger.error("error_getting_phases", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-articles")
async def get_knowledge_articles(
    product_id: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get knowledge articles (tenant-isolated)."""
    try:
        # Set user context for RLS
        await db.execute(text(f"SET LOCAL app.current_user_id = '{current_user['id']}'"))
        
        # Filter through products table since knowledge_articles doesn't have tenant_id
        query = """
            SELECT ka.id, ka.product_id, ka.title, ka.content, ka.source, ka.metadata, ka.created_at
            FROM knowledge_articles ka
            INNER JOIN products p ON ka.product_id = p.id
            WHERE p.tenant_id = :tenant_id
        """
        params = {"tenant_id": current_user["tenant_id"]}
        
        if product_id:
            # Verify product access
            product_check = text("""
                SELECT id FROM products 
                WHERE id = :product_id 
                AND tenant_id = :tenant_id
                AND (
                  user_id = :user_id
                  OR id IN (SELECT product_id FROM product_shares WHERE shared_with_user_id = :user_id)
                )
            """)
            check_result = await db.execute(product_check, {
                "product_id": product_id,
                "tenant_id": current_user["tenant_id"],
                "user_id": current_user["id"]
            })
            if not check_result.fetchone():
                raise HTTPException(status_code=403, detail="Access denied to product")
            
            query += " AND ka.product_id = :product_id"
            params["product_id"] = product_id
        else:
            # Only show articles from accessible products
            query += " AND (p.user_id = :user_id OR p.id IN (SELECT product_id FROM product_shares WHERE shared_with_user_id = :user_id))"
            params["user_id"] = current_user["id"]
        
        if search:
            query += " AND (ka.title ILIKE :search OR ka.content ILIKE :search)"
            params["search"] = f"%{search}%"
        
        query += " ORDER BY ka.created_at DESC LIMIT :limit"
        params["limit"] = limit
        
        result = await db.execute(text(query), params)
        rows = result.fetchall()
        
        articles = [
            {
                "id": str(row[0]),
                "product_id": str(row[1]) if row[1] else None,
                "title": row[2],
                "content": row[3],
                "source": row[4],
                "metadata": row[5] or {},
                "created_at": row[6].isoformat() if row[6] else None,
            }
            for row in rows
        ]
        return {"articles": articles}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("error_getting_knowledge_articles", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversation-history")
async def get_conversation_history(
    session_id: Optional[str] = None,
    product_id: Optional[str] = None,
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get conversation history (tenant-isolated)."""
    try:
        # Set user context for RLS
        await db.execute(text(f"SET LOCAL app.current_user_id = '{current_user['id']}'"))
        
        query = """
            SELECT id, session_id, product_id, phase_id, message_type,
                   agent_name, agent_role, content, formatted_content,
                   parent_message_id, interaction_metadata, created_at
            FROM conversation_history
            WHERE tenant_id = :tenant_id
        """
        params = {"tenant_id": current_user["tenant_id"]}
        
        if session_id:
            query += " AND session_id = :session_id"
            params["session_id"] = session_id
        
        if product_id:
            # Verify product access
            product_check = text("""
                SELECT id FROM products 
                WHERE id = :product_id 
                AND tenant_id = :tenant_id
                AND (
                  user_id = :user_id
                  OR id IN (SELECT product_id FROM product_shares WHERE shared_with_user_id = :user_id)
                )
            """)
            check_result = await db.execute(product_check, {
                "product_id": product_id,
                "tenant_id": current_user["tenant_id"],
                "user_id": current_user["id"]
            })
            if not check_result.fetchone():
                raise HTTPException(status_code=403, detail="Access denied to product")
            
            query += " AND product_id = :product_id"
            params["product_id"] = product_id
        
        query += " ORDER BY created_at ASC LIMIT :limit"
        params["limit"] = limit
        
        result = await db.execute(text(query), params)
        rows = result.fetchall()
        
        messages = [
            {
                "id": str(row[0]),
                "session_id": str(row[1]) if row[1] else None,
                "product_id": str(row[2]) if row[2] else None,
                "phase_id": str(row[3]) if row[3] else None,
                "message_type": row[4],
                "agent_name": row[5],
                "agent_role": row[6],
                "content": row[7],
                "formatted_content": row[8],
                "parent_message_id": str(row[9]) if row[9] else None,
                "interaction_metadata": row[10] or {},
                "created_at": row[11].isoformat() if row[11] else None,
            }
            for row in rows
        ]
        return {"messages": messages}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("error_getting_conversation_history", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge-articles")
async def create_knowledge_article(
    article: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a knowledge article (tenant-isolated)."""
    try:
        # Set user context for RLS
        await db.execute(text(f"SET LOCAL app.current_user_id = '{current_user['id']}'"))
        
        product_id = article.get("product_id")
        if product_id:
            # Verify product access
            product_check = text("""
                SELECT id, tenant_id FROM products 
                WHERE id = :product_id
                AND (
                  user_id = :user_id
                  OR id IN (SELECT product_id FROM product_shares WHERE shared_with_user_id = :user_id AND permission IN ('edit', 'admin'))
                )
            """)
            check_result = await db.execute(product_check, {
                "product_id": product_id,
                "user_id": current_user["id"]
            })
            product_row = check_result.fetchone()
            if not product_row:
                raise HTTPException(status_code=403, detail="Access denied to product")
            if str(product_row[1]) != current_user["tenant_id"]:
                raise HTTPException(status_code=403, detail="Product belongs to different tenant")
        
        query = text("""
            INSERT INTO knowledge_articles 
            (product_id, title, content, source, metadata)
            VALUES (:product_id, :title, :content, :source, :metadata)
            RETURNING id, created_at
        """)
        
        import json
        metadata = article.get("metadata", {})
        # Ensure metadata is a dict, then JSON-encode it for JSONB column
        if not isinstance(metadata, dict):
            metadata = {}
        
        result = await db.execute(query, {
            "product_id": product_id,
            "title": article.get("title"),
            "content": article.get("content"),
            "source": article.get("source", "manual"),
            "metadata": json.dumps(metadata),  # JSON-encode for JSONB column
        })
        
        await db.commit()
        row = result.fetchone()
        article_id = str(row[0])
        
        # CRITICAL: Also add to RAG agent's vector database for semantic search
        # This ensures the document is available for RAG retrieval
        try:
            from backend.agents.rag_agent import RAGAgent
            rag_agent = RAGAgent()
            
            # Prepare content with title for better context
            full_content = f"Title: {article.get('title', 'Untitled')}\n\n{article.get('content', '')}"
            
            # Prepare metadata with product_id for filtering
            rag_metadata = {
                "product_id": str(product_id) if product_id else None,
                "article_id": article_id,
                "title": article.get("title", "Untitled"),
                "source": article.get("source", "manual"),
                **metadata  # Include any additional metadata
            }
            
            # Add to vector database
            success = await rag_agent.add_knowledge(full_content, rag_metadata)
            if success:
                logger.info("knowledge_article_added_to_rag",
                          article_id=article_id,
                          product_id=product_id,
                          title=article.get("title"))
            else:
                logger.warning("knowledge_article_rag_add_failed",
                             article_id=article_id,
                             product_id=product_id)
        except Exception as e:
            # Log error but don't fail the request - document is still in database
            logger.error("failed_to_add_to_rag_vector_db",
                        article_id=article_id,
                        product_id=product_id,
                        error=str(e))
        
        return {
            "id": article_id,
            "created_at": row[1].isoformat() if row[1] else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("error_creating_knowledge_article", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversation-history")
async def create_conversation_message(
    message: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a conversation message (tenant-isolated)."""
    try:
        import json
        from sqlalchemy import func
        
        # Set user context for RLS
        await db.execute(text(f"SET LOCAL app.current_user_id = '{current_user['id']}'"))
        
        session_id = message.get("session_id")
        product_id = message.get("product_id")
        
        # Verify product access if product_id is provided
        if product_id:
            product_check = text("""
                SELECT id, tenant_id FROM products 
                WHERE id = :product_id
                AND (
                  user_id = :user_id
                  OR id IN (SELECT product_id FROM product_shares WHERE shared_with_user_id = :user_id)
                )
            """)
            check_result = await db.execute(product_check, {
                "product_id": product_id,
                "user_id": current_user["id"]
            })
            product_row = check_result.fetchone()
            if not product_row:
                raise HTTPException(status_code=403, detail="Access denied to product")
            # Ensure tenant matches
            if str(product_row[1]) != current_user["tenant_id"]:
                raise HTTPException(status_code=403, detail="Product belongs to different tenant")
        
        # Ensure session exists
        if session_id:
            session_check = text("""
                SELECT id FROM conversation_sessions WHERE id = :session_id
            """)
            session_result = await db.execute(session_check, {"session_id": session_id})
            if not session_result.fetchone():
                # Create session if it doesn't exist
                create_session = text("""
                    INSERT INTO conversation_sessions (id, user_id, product_id, title)
                    VALUES (:session_id, :user_id, :product_id, :title)
                    ON CONFLICT (id) DO NOTHING
                """)
                await db.execute(create_session, {
                    "session_id": session_id,
                    "user_id": current_user["id"],
                    "product_id": product_id,
                    "title": "Product Lifecycle Session",
                })
        
        # Convert metadata dict to JSON string for JSONB
        interaction_metadata = message.get("interaction_metadata", {})
        if isinstance(interaction_metadata, dict):
            interaction_metadata = json.dumps(interaction_metadata)
        
        query = text("""
            INSERT INTO conversation_history
            (session_id, product_id, phase_id, message_type, agent_name,
             agent_role, content, formatted_content, parent_message_id, interaction_metadata, tenant_id)
            VALUES (:session_id, :product_id, :phase_id, :message_type, :agent_name,
                    :agent_role, :content, :formatted_content, :parent_message_id, CAST(:interaction_metadata AS jsonb), :tenant_id)
            RETURNING id, created_at
        """)
        
        result = await db.execute(query, {
            "session_id": session_id,
            "product_id": product_id,
            "phase_id": message.get("phase_id"),
            "message_type": message.get("message_type"),
            "agent_name": message.get("agent_name"),
            "agent_role": message.get("agent_role"),
            "content": message.get("content"),
            "formatted_content": message.get("formatted_content"),
            "parent_message_id": message.get("parent_message_id"),
            "interaction_metadata": interaction_metadata,
            "tenant_id": current_user["tenant_id"],
        })
        
        await db.commit()
        row = result.fetchone()
        
        return {
            "id": str(row[0]),
            "created_at": row[1].isoformat() if row[1] else None,
        }
    except Exception as e:
        await db.rollback()
        logger.error("error_creating_conversation_message", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products")
async def get_products(
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get products."""
    try:
        query = """
            SELECT id, user_id, name, description, status, metadata, created_at, updated_at
            FROM products
            WHERE 1=1
        """
        params = {}
        
        if user_id:
            query += " AND user_id = :user_id"
            params["user_id"] = user_id
        
        query += " ORDER BY created_at DESC"
        
        result = await db.execute(text(query), params)
        rows = result.fetchall()
        
        products = [
            {
                "id": str(row[0]),
                "user_id": str(row[1]) if row[1] else None,
                "name": row[2],
                "description": row[3],
                "status": row[4],
                "metadata": row[5] or {},
                "created_at": row[6].isoformat() if row[6] else None,
                "updated_at": row[7].isoformat() if row[7] else None,
            }
            for row in rows
        ]
        return {"products": products}
    except Exception as e:
        logger.error("error_getting_products", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/products")
async def create_product(
    product: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Create a product."""
    try:
        import json
        
        # Use anonymous user UUID if user_id is not a valid UUID
        user_id = product.get("user_id", "00000000-0000-0000-0000-000000000000")
        if user_id == "anonymous-user" or not user_id:
            user_id = "00000000-0000-0000-0000-000000000000"
        
        # Convert metadata dict to JSON string for JSONB
        metadata = product.get("metadata", {})
        if isinstance(metadata, dict):
            metadata = json.dumps(metadata)
        
        query = text("""
            INSERT INTO products 
            (id, user_id, name, description, status, metadata)
            VALUES (:id, CAST(:user_id AS uuid), :name, :description, :status, CAST(:metadata AS jsonb))
            RETURNING id, created_at, updated_at
        """)
        
        result = await db.execute(query, {
            "id": product.get("id"),
            "user_id": user_id,
            "name": product.get("name"),
            "description": product.get("description", ""),
            "status": product.get("status", "ideation"),
            "metadata": metadata,
        })
        
        await db.commit()
        row = result.fetchone()
        
        return {
            "id": str(row[0]),
            "created_at": row[1].isoformat() if row[1] else None,
            "updated_at": row[2].isoformat() if row[2] else None,
        }
    except Exception as e:
        await db.rollback()
        logger.error("error_creating_product", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/phase-submissions")
async def get_phase_submissions(
    product_id: Optional[str] = None,
    phase_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get phase submissions (tenant-isolated)."""
    try:
        # Set user context for RLS
        await db.execute(text(f"SET LOCAL app.current_user_id = '{current_user['id']}'"))
        
        query = """
            SELECT ps.id, ps.product_id, ps.phase_id, ps.user_id, ps.form_data, ps.generated_content,
                   ps.status, ps.metadata, ps.created_at, ps.updated_at
            FROM phase_submissions ps
            JOIN products p ON ps.product_id = p.id
            WHERE ps.tenant_id = :tenant_id
        """
        params = {"tenant_id": current_user["tenant_id"]}
        
        if product_id:
            # Verify product access
            product_check = text("""
                SELECT id FROM products 
                WHERE id = :product_id 
                AND tenant_id = :tenant_id
                AND (
                  user_id = :user_id
                  OR id IN (SELECT product_id FROM product_shares WHERE shared_with_user_id = :user_id)
                )
            """)
            check_result = await db.execute(product_check, {
                "product_id": product_id,
                "tenant_id": current_user["tenant_id"],
                "user_id": current_user["id"]
            })
            if not check_result.fetchone():
                raise HTTPException(status_code=403, detail="Access denied to product")
            
            query += " AND ps.product_id = :product_id"
            params["product_id"] = product_id
        
        if phase_id:
            query += " AND ps.phase_id = :phase_id"
            params["phase_id"] = phase_id
        
        query += " ORDER BY ps.created_at ASC"
        
        result = await db.execute(text(query), params)
        rows = result.fetchall()
        
        submissions = [
            {
                "id": str(row[0]),
                "product_id": str(row[1]) if row[1] else None,
                "phase_id": str(row[2]) if row[2] else None,
                "user_id": str(row[3]) if row[3] else None,
                "form_data": row[4] or {},
                "generated_content": row[5],
                "status": row[6],
                "metadata": row[7] or {},
                "created_at": row[8].isoformat() if row[8] else None,
                "updated_at": row[9].isoformat() if row[9] else None,
            }
            for row in rows
        ]
        return {"submissions": submissions}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("error_getting_phase_submissions", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/phase-submissions/{product_id}/{phase_id}")
async def get_phase_submission(
    product_id: str,
    phase_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific phase submission (tenant-isolated)."""
    try:
        # Set user context for RLS
        await db.execute(text(f"SET LOCAL app.current_user_id = '{current_user['id']}'"))
        
        # Verify product access
        product_check = text("""
            SELECT id, tenant_id FROM products 
            WHERE id = :product_id
            AND (
              user_id = :user_id
              OR id IN (SELECT product_id FROM product_shares WHERE shared_with_user_id = :user_id)
            )
        """)
        check_result = await db.execute(product_check, {
            "product_id": product_id,
            "user_id": current_user["id"]
        })
        product_row = check_result.fetchone()
        if not product_row:
            raise HTTPException(status_code=403, detail="Access denied to product")
        if str(product_row[1]) != current_user["tenant_id"]:
            raise HTTPException(status_code=403, detail="Product belongs to different tenant")
        
        query = text("""
            SELECT id, product_id, phase_id, user_id, form_data, generated_content,
                   status, metadata, created_at, updated_at
            FROM phase_submissions
            WHERE product_id = :product_id AND phase_id = :phase_id AND tenant_id = :tenant_id
            LIMIT 1
        """)
        
        result = await db.execute(query, {
            "product_id": product_id,
            "phase_id": phase_id,
            "tenant_id": current_user["tenant_id"],
        })
        row = result.fetchone()
        
        if not row:
            return None
        
        return {
            "id": str(row[0]),
            "product_id": str(row[1]) if row[1] else None,
            "phase_id": str(row[2]) if row[2] else None,
            "user_id": str(row[3]) if row[3] else None,
            "form_data": row[4] or {},
            "generated_content": row[5],
            "status": row[6],
            "metadata": row[7] or {},
            "created_at": row[8].isoformat() if row[8] else None,
            "updated_at": row[9].isoformat() if row[9] else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("error_getting_phase_submission", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/phase-submissions")
async def create_phase_submission(
    submission: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a phase submission (tenant-isolated)."""
    try:
        import json
        
        # Set user context for RLS
        await db.execute(text(f"SET LOCAL app.current_user_id = '{current_user['id']}'"))
        
        product_id = submission.get("product_id")
        if product_id:
            # Verify product access
            product_check = text("""
                SELECT id, tenant_id FROM products 
                WHERE id = :product_id
                AND (
                  user_id = :user_id
                  OR id IN (SELECT product_id FROM product_shares WHERE shared_with_user_id = :user_id AND permission IN ('edit', 'admin'))
                )
            """)
            check_result = await db.execute(product_check, {
                "product_id": product_id,
                "user_id": current_user["id"]
            })
            product_row = check_result.fetchone()
            if not product_row:
                raise HTTPException(status_code=403, detail="Access denied to product")
            if str(product_row[1]) != current_user["tenant_id"]:
                raise HTTPException(status_code=403, detail="Product belongs to different tenant")
        
        # Get tenant_id from product or current user
        tenant_id = current_user["tenant_id"]
        if product_id and product_row:
            # Use product's tenant_id to ensure consistency
            tenant_id = str(product_row[1])
        
        # Convert JSONB fields to JSON strings
        form_data = submission.get("form_data", {})
        if isinstance(form_data, dict):
            form_data = json.dumps(form_data)
        
        metadata = submission.get("metadata", {})
        if isinstance(metadata, dict):
            metadata = json.dumps(metadata)
        
        query = text("""
            INSERT INTO phase_submissions
            (product_id, phase_id, user_id, tenant_id, form_data, status, metadata)
            VALUES (:product_id, :phase_id, :user_id, :tenant_id, CAST(:form_data AS jsonb), :status, CAST(:metadata AS jsonb))
            ON CONFLICT (product_id, phase_id) 
            DO UPDATE SET 
                form_data = EXCLUDED.form_data,
                status = EXCLUDED.status,
                metadata = EXCLUDED.metadata,
                tenant_id = EXCLUDED.tenant_id,
                updated_at = now()
            RETURNING id, created_at, updated_at
        """)
        
        result = await db.execute(query, {
            "product_id": submission.get("product_id"),
            "phase_id": submission.get("phase_id"),
            "user_id": submission.get("user_id"),
            "tenant_id": tenant_id,
            "form_data": form_data,
            "status": submission.get("status", "draft"),
            "metadata": metadata,
        })
        
        await db.commit()
        row = result.fetchone()
        
        return {
            "id": str(row[0]),
            "created_at": row[1].isoformat() if row[1] else None,
            "updated_at": row[2].isoformat() if row[2] else None,
        }
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error("error_creating_phase_submission", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/knowledge-articles/{article_id}")
async def delete_knowledge_article(
    article_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a knowledge article (tenant-isolated)."""
    try:
        # Set user context for RLS
        await db.execute(text(f"SET LOCAL app.current_user_id = '{current_user['id']}'"))
        
        # Verify article exists and user has access
        # Join with products table to get tenant_id since knowledge_articles doesn't have tenant_id
        check_query = text("""
            SELECT ka.id, ka.product_id, p.tenant_id
            FROM knowledge_articles ka
            INNER JOIN products p ON ka.product_id = p.id
            WHERE ka.id = :article_id AND p.tenant_id = :tenant_id
        """)
        check_result = await db.execute(check_query, {
            "article_id": article_id,
            "tenant_id": current_user["tenant_id"]
        })
        article_row = check_result.fetchone()
        
        if not article_row:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # If article is product-specific, verify product access
        if article_row[1]:  # product_id is not None
            product_check = text("""
                SELECT id FROM products 
                WHERE id = :product_id
                AND (
                  user_id = :user_id
                  OR id IN (SELECT product_id FROM product_shares WHERE shared_with_user_id = :user_id AND permission IN ('edit', 'admin'))
                )
            """)
            check_result = await db.execute(product_check, {
                "product_id": article_row[1],
                "user_id": current_user["id"]
            })
            if not check_result.fetchone():
                raise HTTPException(status_code=403, detail="Access denied to article")
        
        # Delete the article (no tenant_id needed in WHERE clause since we already verified it)
        delete_query = text("""
            DELETE FROM knowledge_articles
            WHERE id = :article_id
        """)
        await db.execute(delete_query, {
            "article_id": article_id
        })
        
        await db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("error_deleting_knowledge_article", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/phase-submissions/{submission_id}")
async def update_phase_submission(
    submission_id: str,
    updates: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Update a phase submission."""
    try:
        import json
        
        # Build dynamic update query
        update_fields = []
        params = {"submission_id": submission_id}
        
        if "form_data" in updates:
            form_data = updates["form_data"]
            if isinstance(form_data, dict):
                form_data = json.dumps(form_data)
            update_fields.append("form_data = CAST(:form_data AS jsonb)")
            params["form_data"] = form_data
        
        if "generated_content" in updates:
            update_fields.append("generated_content = :generated_content")
            params["generated_content"] = updates["generated_content"]
        
        if "status" in updates:
            update_fields.append("status = :status")
            params["status"] = updates["status"]
        
        if "metadata" in updates:
            metadata = updates["metadata"]
            if isinstance(metadata, dict):
                metadata = json.dumps(metadata)
            update_fields.append("metadata = CAST(:metadata AS jsonb)")
            params["metadata"] = metadata
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        update_fields.append("updated_at = now()")
        
        query = text(f"""
            UPDATE phase_submissions
            SET {', '.join(update_fields)}
            WHERE id = :submission_id
            RETURNING id, product_id, phase_id, user_id, form_data, generated_content,
                     status, metadata, created_at, updated_at
        """)
        
        result = await db.execute(query, params)
        await db.commit()
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Submission not found")
        
        return {
            "id": str(row[0]),
            "product_id": str(row[1]) if row[1] else None,
            "phase_id": str(row[2]) if row[2] else None,
            "user_id": str(row[3]) if row[3] else None,
            "form_data": row[4] or {},
            "generated_content": row[5],
            "status": row[6],
            "metadata": row[7] or {},
            "created_at": row[8].isoformat() if row[8] else None,
            "updated_at": row[9].isoformat() if row[9] else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("error_updating_phase_submission", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

