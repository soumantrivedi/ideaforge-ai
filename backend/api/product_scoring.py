"""
API endpoints for product idea scoring and multi-session operations
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import structlog

from backend.database import get_db
from backend.api.auth import get_current_user
from backend.agents.agno_enhanced_coordinator import AgnoEnhancedCoordinator
from backend.agents.agno_summary_agent import AgnoSummaryAgent
from backend.agents.agno_scoring_agent import AgnoScoringAgent
from backend.agents.agno_prd_authoring_agent import AgnoPRDAuthoringAgent

router = APIRouter(prefix="/api/products", tags=["product-scoring"])
logger = structlog.get_logger()

# Initialize agents
enhanced_coordinator = AgnoEnhancedCoordinator(enable_rag=True)
summary_agent = AgnoSummaryAgent(enable_rag=True)
scoring_agent = AgnoScoringAgent(enable_rag=True)
prd_agent = AgnoPRDAuthoringAgent(enable_rag=True)


@router.get("/{product_id}/sessions")
async def get_product_sessions(
    product_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all conversation sessions for a product."""
    try:
        query = text("""
            SELECT 
                cs.id,
                cs.title,
                cs.created_at,
                cs.updated_at,
                COUNT(am.id) as message_count,
                array_agg(DISTINCT am.agent_role) FILTER (WHERE am.agent_role IS NOT NULL) as agent_roles
            FROM conversation_sessions cs
            LEFT JOIN agent_messages am ON am.session_id = cs.id
            WHERE cs.product_id = :product_id
            GROUP BY cs.id, cs.title, cs.created_at, cs.updated_at
            ORDER BY cs.created_at DESC
        """)
        
        result = await db.execute(query, {"product_id": str(product_id)})
        rows = result.fetchall()
        
        sessions = [
            {
                "id": str(row[0]),
                "title": row[1],
                "created_at": row[2].isoformat() if row[2] else None,
                "updated_at": row[3].isoformat() if row[3] else None,
                "message_count": row[4] or 0,
                "agent_roles": row[5] or []
            }
            for row in rows
        ]
        
        return {"sessions": sessions}
    except Exception as e:
        logger.error("error_getting_sessions", error=str(e), product_id=str(product_id))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{product_id}/summarize")
async def create_product_summary(
    product_id: UUID,
    session_ids: List[UUID],
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a summary from selected sessions."""
    try:
        # Fetch messages from selected sessions
        query = text("""
            SELECT 
                am.session_id,
                am.role,
                am.content,
                am.agent_role,
                am.created_at,
                cs.title as session_title
            FROM agent_messages am
            JOIN conversation_sessions cs ON cs.id = am.session_id
            WHERE am.session_id = ANY(:session_ids)
            AND cs.product_id = :product_id
            ORDER BY am.created_at ASC
        """)
        
        result = await db.execute(query, {
            "session_ids": [str(sid) for sid in session_ids],
            "product_id": str(product_id)
        })
        rows = result.fetchall()
        
        # Group messages by session
        sessions_data = {}
        for row in rows:
            session_id = str(row[0])
            if session_id not in sessions_data:
                sessions_data[session_id] = {
                    "session_id": session_id,
                    "title": row[5],
                    "messages": [],
                    "participants": set()
                }
            
            sessions_data[session_id]["messages"].append({
                "role": row[1],
                "content": row[2],
                "agent_role": row[3],
                "timestamp": row[4].isoformat() if row[4] else None
            })
            
            if row[1] == "user":
                # Extract user from context if available
                sessions_data[session_id]["participants"].add("user")
        
        # Convert to list
        sessions_list = [
            {
                **data,
                "participants": list(data["participants"])
            }
            for data in sessions_data.values()
        ]
        
        # Create summary using agent
        summary_content = await summary_agent.create_multi_session_summary(
            sessions=sessions_list,
            product_context={"product_id": str(product_id)}
        )
        
        # Save summary to database
        insert_query = text("""
            INSERT INTO product_summaries 
            (product_id, tenant_id, summary_type, session_ids, summary_content, created_by)
            VALUES (:product_id, :tenant_id, 'multi_session', :session_ids, :summary_content, :created_by)
            RETURNING id, created_at
        """)
        
        result = await db.execute(insert_query, {
            "product_id": str(product_id),
            "tenant_id": current_user.get("tenant_id"),
            "session_ids": [str(sid) for sid in session_ids],
            "summary_content": summary_content,
            "created_by": current_user["id"]
        })
        
        await db.commit()
        row = result.fetchone()
        
        return {
            "summary_id": str(row[0]),
            "summary": summary_content,
            "created_at": row[1].isoformat() if row[1] else None
        }
        
    except Exception as e:
        logger.error("error_creating_summary", error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{product_id}/score")
async def score_product_idea(
    product_id: UUID,
    summary_id: Optional[UUID] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Score a product idea based on summary and context."""
    try:
        # Get product summary
        summary_content = ""
        if summary_id:
            query = text("SELECT summary_content FROM product_summaries WHERE id = :summary_id")
            result = await db.execute(query, {"summary_id": str(summary_id)})
            row = result.fetchone()
            if row:
                summary_content = row[0]
        
        # If no summary provided, create one from all sessions
        if not summary_content:
            # Get all sessions for product
            sessions_query = text("""
                SELECT id FROM conversation_sessions 
                WHERE product_id = :product_id
                ORDER BY created_at DESC
            """)
            sessions_result = await db.execute(sessions_query, {"product_id": str(product_id)})
            session_ids = [UUID(row[0]) for row in sessions_result.fetchall()]
            
            if session_ids:
                # Create summary first
                summary_response = await create_product_summary(product_id, session_ids, current_user, db)
                summary_content = summary_response["summary"]
                summary_id = UUID(summary_response["summary_id"])
        
        # Get product details
        product_query = text("""
            SELECT name, description, metadata, status
            FROM products
            WHERE id = :product_id
        """)
        product_result = await db.execute(product_query, {"product_id": str(product_id)})
        product_row = product_result.fetchone()
        
        product_info = {
            "name": product_row[0] if product_row else "",
            "description": product_row[1] if product_row else "",
            "metadata": product_row[2] if product_row else {},
            "status": product_row[3] if product_row else "ideation"
        }
        
        # Score the product idea
        scoring_result = await scoring_agent.score_product_idea(
            product_summary=summary_content or product_info.get("description", ""),
            market_context=product_info.get("metadata", {}).get("market_context"),
            technical_context=product_info.get("metadata", {}).get("technical_context")
        )
        
        # Save score to database
        insert_query = text("""
            INSERT INTO product_idea_scores
            (product_id, tenant_id, overall_score, success_probability, scoring_data, 
             recommendations, success_factors, risk_factors, scoring_criteria, created_by)
            VALUES (:product_id, :tenant_id, :overall_score, :success_probability, :scoring_data,
                    :recommendations, :success_factors, :risk_factors, :scoring_criteria, :created_by)
            RETURNING id, created_at
        """)
        
        result = await db.execute(insert_query, {
            "product_id": str(product_id),
            "tenant_id": current_user.get("tenant_id"),
            "overall_score": scoring_result.get("overall_score", 0),
            "success_probability": scoring_result.get("success_probability", 0),
            "scoring_data": scoring_result.get("dimensions", {}),
            "recommendations": scoring_result.get("recommendations", []),
            "success_factors": scoring_result.get("success_factors", []),
            "risk_factors": scoring_result.get("risk_factors", []),
            "scoring_criteria": {"standards": ["BCS", "ICAgile", "AIPMM", "Pragmatic Institute"]},
            "created_by": current_user["id"]
        })
        
        await db.commit()
        row = result.fetchone()
        
        return {
            "score_id": str(row[0]),
            "overall_score": scoring_result.get("overall_score"),
            "success_probability": scoring_result.get("success_probability"),
            "dimensions": scoring_result.get("dimensions", {}),
            "recommendations": scoring_result.get("recommendations", []),
            "success_factors": scoring_result.get("success_factors", []),
            "risk_factors": scoring_result.get("risk_factors", []),
            "created_at": row[1].isoformat() if row[1] else None
        }
        
    except Exception as e:
        logger.error("error_scoring_product", error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{product_id}/generate-prd")
async def generate_standardized_prd(
    product_id: UUID,
    summary_id: Optional[UUID] = None,
    score_id: Optional[UUID] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate standardized PRD from summary and score."""
    try:
        # Get summary
        summary_content = ""
        if summary_id:
            query = text("SELECT summary_content FROM product_summaries WHERE id = :summary_id")
            result = await db.execute(query, {"summary_id": str(summary_id)})
            row = result.fetchone()
            if row:
                summary_content = row[0]
        
        # Get score
        score_data = {}
        if score_id:
            query = text("SELECT scoring_data, recommendations FROM product_idea_scores WHERE id = :score_id")
            result = await db.execute(query, {"score_id": str(score_id)})
            row = result.fetchone()
            if row:
                score_data = {
                    "scoring": row[0] or {},
                    "recommendations": row[1] or []
                }
        
        # Get product info
        product_query = text("SELECT name, description, metadata FROM products WHERE id = :product_id")
        product_result = await db.execute(product_query, {"product_id": str(product_id)})
        product_row = product_result.fetchone()
        
        product_info = {
            "name": product_row[0] if product_row else "",
            "description": product_row[1] if product_row else "",
            "metadata": product_row[2] if product_row else {}
        }
        
        # Generate PRD using enhanced coordinator with heavy context
        prd_prompt = f"""Generate a comprehensive Product Requirements Document following industry standards 
        (BCS, ICAgile, AIPMM, Pragmatic Institute) for this product:

Product: {product_info['name']}
Description: {product_info['description']}

Summary from Conversations:
{summary_content}

Idea Score and Analysis:
{score_data}

Generate a complete PRD following the standard template with all sections."""

        # Use enhanced coordinator for contextualized PRD generation
        response = await enhanced_coordinator.process_with_context(
            query=prd_prompt,
            product_id=str(product_id),
            user_context={
                "user_id": current_user["id"],
                "tenant_id": current_user.get("tenant_id")
            }
        )
        
        prd_content = response.response
        
        # Save PRD to database
        insert_query = text("""
            INSERT INTO product_prd_documents
            (product_id, tenant_id, prd_content, summary_id, score_id, created_by)
            VALUES (:product_id, :tenant_id, :prd_content, :summary_id, :score_id, :created_by)
            RETURNING id, created_at
        """)
        
        result = await db.execute(insert_query, {
            "product_id": str(product_id),
            "tenant_id": current_user.get("tenant_id"),
            "prd_content": {"content": prd_content, "template": "industry_standard"},
            "summary_id": str(summary_id) if summary_id else None,
            "score_id": str(score_id) if score_id else None,
            "created_by": current_user["id"]
        })
        
        await db.commit()
        row = result.fetchone()
        
        return {
            "prd_id": str(row[0]),
            "prd_content": prd_content,
            "created_at": row[1].isoformat() if row[1] else None
        }
        
    except Exception as e:
        logger.error("error_generating_prd", error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{product_id}/scores")
async def get_product_scores(
    product_id: UUID,
    tenant_id: Optional[UUID] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all scores for a product (tenant-level if tenant_id provided)."""
    try:
        query = text("""
            SELECT 
                id,
                overall_score,
                success_probability,
                scoring_data,
                recommendations,
                success_factors,
                risk_factors,
                scoring_criteria,
                created_at,
                updated_at
            FROM product_idea_scores
            WHERE product_id = :product_id
            AND (:tenant_id IS NULL OR tenant_id = :tenant_id)
            ORDER BY created_at DESC
        """)
        
        result = await db.execute(query, {
            "product_id": str(product_id),
            "tenant_id": str(tenant_id) if tenant_id else None
        })
        rows = result.fetchall()
        
        scores = [
            {
                "id": str(row[0]),
                "overall_score": float(row[1]) if row[1] else 0,
                "success_probability": float(row[2]) if row[2] else 0,
                "dimensions": row[3] or {},
                "recommendations": row[4] or [],
                "success_factors": row[5] or [],
                "risk_factors": row[6] or [],
                "scoring_criteria": row[7] or {},
                "created_at": row[8].isoformat() if row[8] else None,
                "updated_at": row[9].isoformat() if row[9] else None
            }
            for row in rows
        ]
        
        return {"scores": scores}
    except Exception as e:
        logger.error("error_getting_scores", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tenant/{tenant_id}/scores")
async def get_tenant_scores(
    tenant_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all product scores for a tenant (Idea Score Dashboard)."""
    try:
        query = text("""
            SELECT 
                pis.id,
                pis.product_id,
                p.name as product_name,
                pis.overall_score,
                pis.success_probability,
                pis.scoring_data,
                pis.recommendations,
                pis.success_factors,
                pis.risk_factors,
                pis.created_at,
                pis.updated_at
            FROM product_idea_scores pis
            JOIN products p ON p.id = pis.product_id
            WHERE pis.tenant_id = :tenant_id
            ORDER BY pis.created_at DESC
        """)
        
        result = await db.execute(query, {"tenant_id": str(tenant_id)})
        rows = result.fetchall()
        
        scores = [
            {
                "id": str(row[0]),
                "product_id": str(row[1]),
                "product_name": row[2],
                "overall_score": float(row[3]) if row[3] else 0,
                "success_probability": float(row[4]) if row[4] else 0,
                "dimensions": row[5] or {},
                "recommendations": row[6] or [],
                "success_factors": row[7] or [],
                "risk_factors": row[8] or [],
                "created_at": row[9].isoformat() if row[9] else None,
                "updated_at": row[10].isoformat() if row[10] else None
            }
            for row in rows
        ]
        
        return {"scores": scores, "tenant_id": str(tenant_id)}
    except Exception as e:
        logger.error("error_getting_tenant_scores", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

