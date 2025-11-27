"""
Export API endpoints for generating PRD documents in HTML and Markdown formats
Includes content review, missing content detection, and Confluence publishing
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
import structlog
import markdown
import base64
import json
from pydantic import BaseModel

from backend.database import get_db
from backend.api.auth import get_current_user
from backend.api.product_permissions import check_product_permission
from backend.agents import AGNO_AVAILABLE

router = APIRouter(prefix="/api/products", tags=["export"])
logger = structlog.get_logger()

# Initialize export agent conditionally
export_agent = None

if AGNO_AVAILABLE:
    try:
        from backend.agents.agno_export_agent import AgnoExportAgent
        export_agent = AgnoExportAgent(enable_rag=True)
    except Exception as e:
        logger.warning("export_agent_initialization_failed", error=str(e))


class ExportRequest(BaseModel):
    conversation_history: Optional[List[Dict[str, Any]]] = None
    format: str = "html"  # "html" or "markdown"
    include_metadata: bool = True
    override_missing: bool = False  # If True, export even with missing content


class ReviewRequest(BaseModel):
    conversation_history: Optional[List[Dict[str, Any]]] = None


class PublishToConfluenceRequest(BaseModel):
    space_id: str
    title: str  # Will be made unique if needed
    prd_content: str  # Markdown content
    parent_page_id: Optional[str] = None


@router.post("/{product_id}/generate-progress-report")
async def generate_progress_report(
    product_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate and store a progress report using the review agent.
    Returns phase scores, recommendations, and overall progress.
    """
    try:
        # Check permission
        has_permission = await check_product_permission(db, product_id, current_user["id"], "view")
        if not has_permission:
            raise HTTPException(status_code=403, detail="Access denied to product")
        
        # Get product info
        product_query = text("SELECT name, description, metadata FROM products WHERE id = :product_id")
        product_result = await db.execute(product_query, {"product_id": str(product_id)})
        product_row = product_result.fetchone()
        
        if not product_row:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Get all phase submissions with phase IDs
        phase_query = text("""
            SELECT ps.form_data, ps.generated_content, plp.phase_name, plp.phase_order, plp.id as phase_id
            FROM phase_submissions ps
            JOIN product_lifecycle_phases plp ON ps.phase_id = plp.id
            WHERE ps.product_id = :product_id
            ORDER BY plp.phase_order ASC
        """)
        phase_result = await db.execute(phase_query, {"product_id": str(product_id)})
        phase_rows = phase_result.fetchall()
        
        phase_data = []
        for row in phase_rows:
            phase_data.append({
                "phase_name": row[2],
                "phase_order": row[3],
                "phase_id": str(row[4]),
                "form_data": row[0] or {},
                "generated_content": row[1] or ""
            })
        
        # Get conversation history
        conv_query = text("""
            SELECT ch.message_type, ch.content, ch.agent_name, ch.created_at
            FROM conversation_history ch
            WHERE ch.product_id = :product_id
            ORDER BY ch.created_at ASC
        """)
        conv_result = await db.execute(conv_query, {"product_id": str(product_id)})
        conv_rows = conv_result.fetchall()
        conversation_history = [
            {
                "role": row[0],
                "content": row[1],
                "agent_name": row[2],
                "timestamp": row[3].isoformat() if row[3] else None
            }
            for row in conv_rows
        ]
        
        # Get knowledge base articles
        knowledge_base = []
        try:
            kb_query = text("""
                SELECT title, content, source, metadata
                FROM knowledge_articles
                WHERE product_id = :product_id
                ORDER BY created_at DESC
                LIMIT 50
            """)
            kb_result = await db.execute(kb_query, {"product_id": str(product_id)})
            kb_rows = kb_result.fetchall()
            
            knowledge_base = [
                {
                    "title": row[0],
                    "content": row[1],
                    "source_type": row[2] or "manual",
                    "source_url": row[3].get("source_url", "") if isinstance(row[3], dict) else ""
                }
                for row in kb_rows
            ]
        except Exception as e:
            logger.warning(f"Could not fetch knowledge articles: {str(e)}")
            knowledge_base = []
        
        # Get design mockups/prototypes
        design_mockups = []
        try:
            mockup_query = text("""
                SELECT id, provider, prompt, project_url, v0_chat_id, v0_project_id,
                       project_status, thumbnail_url, image_url, metadata, created_at
                FROM design_mockups
                WHERE product_id = :product_id
                ORDER BY created_at DESC
            """)
            mockup_result = await db.execute(mockup_query, {"product_id": str(product_id)})
            mockup_rows = mockup_result.fetchall()
            
            design_mockups = [
                {
                    "id": str(row[0]),
                    "provider": row[1],
                    "prompt": row[2],
                    "project_url": row[3],
                    "v0_chat_id": row[4] if len(row) > 4 else None,
                    "v0_project_id": row[5] if len(row) > 5 else None,
                    "project_status": row[6] if len(row) > 6 else None,
                    "thumbnail_url": row[7] if len(row) > 7 else None,
                    "image_url": row[8] if len(row) > 8 else None,
                    "metadata": row[9] if len(row) > 9 and row[9] else {},
                    "created_at": row[10].isoformat() if len(row) > 10 and row[10] else None
                }
                for row in mockup_rows
            ]
        except Exception as e:
            logger.warning(f"Could not fetch design mockups: {str(e)}")
            design_mockups = []
        
        # Generate review using export agent
        if export_agent:
            review_result = await export_agent.review_content_before_export(
                product_id=str(product_id),
                phase_data=phase_data,
                conversation_history=conversation_history,
                knowledge_base=knowledge_base,
                design_mockups=design_mockups,
                context=None
            )
        else:
            # Fallback review
            review_result = {
                "status": "needs_attention",
                "score": 50,
                "missing_sections": [],
                "phase_scores": [],
                "summary": "Review agent not available. Please configure export agent."
            }
        
        # Store report in database
        report_data = {
            "review_result": review_result,
            "phase_data": phase_data,
            "product_info": {
                "name": product_row[0],
                "description": product_row[1]
            }
        }
        
        # Rollback any previous failed transaction
        try:
            await db.rollback()
        except:
            pass  # Ignore if no transaction to rollback
        
        # Upsert report (update if exists, insert if not)
        try:
            upsert_query = text("""
                INSERT INTO review_reports 
                (product_id, user_id, overall_score, status, phase_scores, missing_sections, 
                 recommendations, summary, report_data, updated_at)
                VALUES (:product_id, :user_id, :overall_score, :status, 
                        CAST(:phase_scores AS jsonb), CAST(:missing_sections AS jsonb),
                        CAST(:recommendations AS jsonb), :summary, CAST(:report_data AS jsonb), now())
                ON CONFLICT (product_id, user_id)
                DO UPDATE SET
                    overall_score = EXCLUDED.overall_score,
                    status = EXCLUDED.status,
                    phase_scores = EXCLUDED.phase_scores,
                    missing_sections = EXCLUDED.missing_sections,
                    recommendations = EXCLUDED.recommendations,
                    summary = EXCLUDED.summary,
                    report_data = EXCLUDED.report_data,
                    updated_at = now()
                RETURNING id, created_at, updated_at
            """)
            
            result = await db.execute(upsert_query, {
                "product_id": str(product_id),
                "user_id": str(current_user["id"]),
                "overall_score": review_result.get("score", 0),
                "status": review_result.get("status", "needs_attention"),
                "phase_scores": json.dumps(review_result.get("phase_scores", [])),
                "missing_sections": json.dumps(review_result.get("missing_sections", [])),
                "recommendations": json.dumps(review_result.get("recommendations", [])),
                "summary": review_result.get("summary", ""),
                "report_data": json.dumps(report_data)
            })
            
            await db.commit()
            row = result.fetchone()
        except Exception as db_error:
            await db.rollback()
            logger.error("error_inserting_review_report", error=str(db_error))
            raise HTTPException(status_code=500, detail=f"Failed to save review report: {str(db_error)}")
        
        return {
            "id": str(row[0]),
            "product_id": str(product_id),
            "overall_score": review_result.get("score", 0),
            "status": review_result.get("status", "needs_attention"),
            "phase_scores": review_result.get("phase_scores", []),
            "missing_sections": review_result.get("missing_sections", []),
            "recommendations": review_result.get("recommendations", []),
            "summary": review_result.get("summary", ""),
            "created_at": row[1].isoformat() if row[1] else None,
            "updated_at": row[2].isoformat() if row[2] else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("error_generating_progress_report", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{product_id}/progress-report")
async def get_progress_report(
    product_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the latest progress report for a product."""
    try:
        # Check if table exists first
        try:
            query = text("""
                SELECT id, overall_score, status, phase_scores, missing_sections,
                       recommendations, summary, report_data, created_at, updated_at
                FROM review_reports
                WHERE product_id = :product_id AND user_id = :user_id
                ORDER BY updated_at DESC
                LIMIT 1
            """)
            
            result = await db.execute(query, {
                "product_id": str(product_id),
                "user_id": str(current_user["id"])
            })
            row = result.fetchone()
            
            if not row:
                return {
                    "exists": False,
                    "message": "No progress report found. Generate one to see your progress."
                }
            
            return {
                "exists": True,
                "id": str(row[0]),
                "product_id": str(product_id),
                "overall_score": row[1],
                "status": row[2],
                "phase_scores": row[3] if row[3] else [],
                "missing_sections": row[4] if row[4] else [],
                "recommendations": row[5] if row[5] else [],
                "summary": row[6],
                "report_data": row[7] if row[7] else {},
                "created_at": row[8].isoformat() if row[8] else None,
                "updated_at": row[9].isoformat() if row[9] else None
            }
        except Exception as table_error:
            # If table doesn't exist, return not found
            if "does not exist" in str(table_error) or "relation" in str(table_error).lower():
                logger.warning("review_reports_table_not_found", error=str(table_error))
                return {
                    "exists": False,
                    "message": "No progress report found. Generate one to see your progress."
                }
            raise
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("error_getting_progress_report", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{product_id}/review-prd")
async def review_prd_content(
    product_id: UUID,
    request: ReviewRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Review PRD content before export and identify missing sections."""
    try:
        # Check permission
        has_permission = await check_product_permission(db, product_id, current_user["id"], "view")
        if not has_permission:
            raise HTTPException(status_code=403, detail="Access denied to product")
        
        # Get product info
        product_query = text("SELECT name, description, metadata FROM products WHERE id = :product_id")
        product_result = await db.execute(product_query, {"product_id": str(product_id)})
        product_row = product_result.fetchone()
        
        if not product_row:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Get all phase submissions
        phase_query = text("""
            SELECT ps.form_data, ps.generated_content, plp.phase_name, plp.phase_order
            FROM phase_submissions ps
            JOIN product_lifecycle_phases plp ON ps.phase_id = plp.id
            WHERE ps.product_id = :product_id
            ORDER BY plp.phase_order ASC
        """)
        phase_result = await db.execute(phase_query, {"product_id": str(product_id)})
        phase_rows = phase_result.fetchall()
        
        phase_data = []
        for row in phase_rows:
            phase_data.append({
                "phase_name": row[2],
                "phase_order": row[3],
                "form_data": row[0] or {},
                "generated_content": row[1] or ""
            })
        
        # Get conversation history if not provided
        conversation_history = request.conversation_history
        if not conversation_history:
            conv_query = text("""
                SELECT ch.message_type, ch.content, ch.agent_name, ch.created_at
                FROM conversation_history ch
                WHERE ch.product_id = :product_id
                ORDER BY ch.created_at ASC
            """)
            conv_result = await db.execute(conv_query, {"product_id": str(product_id)})
            conv_rows = conv_result.fetchall()
            conversation_history = [
                {
                    "role": row[0],
                    "content": row[1],
                    "agent_name": row[2],
                    "timestamp": row[3].isoformat() if row[3] else None
                }
                for row in conv_rows
            ]
        
        # Get knowledge base articles
        # Handle case where table might not exist or has different schema
        knowledge_base = []
        try:
            kb_query = text("""
                SELECT title, content, source, metadata
                FROM knowledge_articles
                WHERE product_id = :product_id
                ORDER BY created_at DESC
                LIMIT 50
            """)
            kb_result = await db.execute(kb_query, {"product_id": str(product_id)})
            kb_rows = kb_result.fetchall()
            
            knowledge_base = [
                {
                    "title": row[0],
                    "content": row[1],
                    "source_type": row[2] or "manual",  # source column
                    "source_url": row[3].get("source_url", "") if isinstance(row[3], dict) else ""  # from metadata
                }
                for row in kb_rows
            ]
        except Exception as e:
            # If knowledge_articles table doesn't exist or query fails, continue without it
            logger.warning(f"Could not fetch knowledge articles: {str(e)}")
            knowledge_base = []
        
        # Get design mockups/prototypes
        design_mockups = []
        try:
            mockup_query = text("""
                SELECT id, provider, prompt, project_url, v0_chat_id, v0_project_id,
                       project_status, thumbnail_url, image_url, metadata, created_at
                FROM design_mockups
                WHERE product_id = :product_id
                ORDER BY created_at DESC
            """)
            mockup_result = await db.execute(mockup_query, {"product_id": str(product_id)})
            mockup_rows = mockup_result.fetchall()
            
            design_mockups = [
                {
                    "id": str(row[0]),
                    "provider": row[1],
                    "prompt": row[2],
                    "project_url": row[3],
                    "v0_chat_id": row[4] if len(row) > 4 else None,
                    "v0_project_id": row[5] if len(row) > 5 else None,
                    "project_status": row[6] if len(row) > 6 else None,
                    "thumbnail_url": row[7] if len(row) > 7 else None,
                    "image_url": row[8] if len(row) > 8 else None,
                    "metadata": row[9] if len(row) > 9 and row[9] else {},
                    "created_at": row[10].isoformat() if len(row) > 10 and row[10] else None
                }
                for row in mockup_rows
            ]
        except Exception as e:
            # If design_mockups table doesn't exist or query fails, continue without it
            logger.warning(f"Could not fetch design mockups: {str(e)}")
            design_mockups = []
        
        # Review content using export agent
        if export_agent:
            review_result = await export_agent.review_content_before_export(
                product_id=str(product_id),
                phase_data=phase_data,
                conversation_history=conversation_history,
                design_mockups=design_mockups,
                knowledge_base=knowledge_base
            )
            return JSONResponse(content=review_result)
        else:
            # Fallback: basic review
            missing_sections = []
            has_market_research = any(
                phase.get('phase_name', '').lower() in ['market research', 'research'] 
                or 'market' in phase.get('form_data', {}).get('content', '').lower()
                for phase in phase_data
            )
            if not has_market_research:
                missing_sections.append("Market Research")
            
            return JSONResponse(content={
                "is_complete": len(missing_sections) == 0,
                "missing_sections": missing_sections,
                "recommendations": [f"Consider adding {section}" for section in missing_sections],
                "warnings": []
            })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("review_prd_error", error=str(e), product_id=str(product_id))
        raise HTTPException(status_code=500, detail=f"Failed to review PRD: {str(e)}")


@router.post("/{product_id}/export-prd")
async def export_prd_document(
    product_id: UUID,
    request: ExportRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Export PRD document in HTML or Markdown format from conversation history and product data."""
    try:
        # Check permission
        has_permission = await check_product_permission(db, product_id, current_user["id"], "view")
        if not has_permission:
            raise HTTPException(status_code=403, detail="Access denied to product")
        
        # Get product info
        product_query = text("SELECT name, description, metadata FROM products WHERE id = :product_id")
        product_result = await db.execute(product_query, {"product_id": str(product_id)})
        product_row = product_result.fetchone()
        
        if not product_row:
            raise HTTPException(status_code=404, detail="Product not found")
        
        product_info = {
            "name": product_row[0] or "",
            "description": product_row[1] or "",
            "metadata": product_row[2] or {}
        }
        
        # Get all phase submissions
        phase_query = text("""
            SELECT ps.form_data, ps.generated_content, plp.phase_name, plp.phase_order
            FROM phase_submissions ps
            JOIN product_lifecycle_phases plp ON ps.phase_id = plp.id
            WHERE ps.product_id = :product_id
            ORDER BY plp.phase_order ASC
        """)
        phase_result = await db.execute(phase_query, {"product_id": str(product_id)})
        phase_rows = phase_result.fetchall()
        
        phase_data = []
        for row in phase_rows:
            phase_data.append({
                "phase_name": row[2],
                "phase_order": row[3],
                "form_data": row[0] or {},
                "generated_content": row[1] or ""
            })
        
        # Get conversation history if not provided
        conversation_history = request.conversation_history
        if not conversation_history:
            conv_query = text("""
                SELECT ch.message_type, ch.content, ch.agent_name, ch.created_at
                FROM conversation_history ch
                WHERE ch.product_id = :product_id
                ORDER BY ch.created_at ASC
            """)
            conv_result = await db.execute(conv_query, {"product_id": str(product_id)})
            conv_rows = conv_result.fetchall()
            conversation_history = [
                {
                    "role": row[0],
                    "content": row[1],
                    "agent_name": row[2],
                    "timestamp": row[3].isoformat() if row[3] else None
                }
                for row in conv_rows
            ]
        
        # Get knowledge base articles
        # Handle case where table might not exist or has different schema
        knowledge_base = []
        try:
            kb_query = text("""
                SELECT title, content, source, metadata
                FROM knowledge_articles
                WHERE product_id = :product_id
                ORDER BY created_at DESC
                LIMIT 50
            """)
            kb_result = await db.execute(kb_query, {"product_id": str(product_id)})
            kb_rows = kb_result.fetchall()
            
            knowledge_base = [
                {
                    "title": row[0],
                    "content": row[1],
                    "source_type": row[2] or "manual",  # source column
                    "source_url": row[3].get("source_url", "") if isinstance(row[3], dict) else ""  # from metadata
                }
                for row in kb_rows
            ]
        except Exception as e:
            # If knowledge_articles table doesn't exist or query fails, continue without it
            logger.warning(f"Could not fetch knowledge articles: {str(e)}")
            knowledge_base = []
        
        # Generate PRD using export agent
        if export_agent:
            prd_content = await export_agent.generate_comprehensive_prd(
                product_id=str(product_id),
                product_info=product_info,
                phase_data=phase_data,
                conversation_history=conversation_history,
                knowledge_base=knowledge_base,
                design_mockups=design_mockups,
                override_missing=request.override_missing
            )
        else:
            # Fallback: generate basic PRD
            prd_content = f"""# Product Requirements Document

## Product: {product_info['name']}

### Description
{product_info['description']}

## Phase Submissions
"""
            for phase in phase_data:
                prd_content += f"\n### {phase['phase_name']}\n"
                if phase['form_data']:
                    for key, value in phase['form_data'].items():
                        prd_content += f"- **{key.replace('_', ' ').title()}**: {value}\n"
                if phase['generated_content']:
                    prd_content += f"\n{phase['generated_content']}\n"
            
            # Add design prototypes section
            if design_mockups:
                prd_content += "\n## Design Prototypes\n"
                for mockup in design_mockups:
                    provider = mockup.get('provider', 'unknown').upper()
                    status = mockup.get('project_status', 'unknown')
                    project_url = mockup.get('project_url', '')
                    thumbnail_url = mockup.get('thumbnail_url') or mockup.get('image_url', '')
                    
                    prd_content += f"\n### {provider} Prototype\n"
                    prd_content += f"- **Status**: {status}\n"
                    if project_url:
                        prd_content += f"- **Prototype URL**: [{project_url}]({project_url})\n"
                    if thumbnail_url:
                        prd_content += f"- **Thumbnail**: ![Prototype Thumbnail]({thumbnail_url})\n"
                    if mockup.get('prompt'):
                        prd_content += f"- **Prompt Used**: {mockup['prompt'][:200]}...\n"
            
            prd_content += "\n## Conversation History\n"
            for msg in conversation_history:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                prd_content += f"\n### {role.title()}\n{content}\n"
        
        # Return based on format
        if request.format == "markdown":
            # Return markdown directly
            return Response(
                content=prd_content,
                media_type="text/markdown",
                headers={
                    "Content-Disposition": f'attachment; filename="PRD_{product_info["name"].replace(" ", "_")}_{datetime.utcnow().strftime("%Y%m%d")}.md"'
                }
            )
        else:
            # Convert markdown to HTML
            html_content = markdown.markdown(
                prd_content,
                extensions=['extra', 'codehilite', 'tables', 'toc']
            )
            
            # Create styled HTML document
            styled_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PRD - {product_info['name']}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2563eb;
            border-bottom: 3px solid #2563eb;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #1e40af;
            margin-top: 30px;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 5px;
        }}
        h3 {{
            color: #3b82f6;
            margin-top: 20px;
        }}
        .to-be-defined {{
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 15px;
            margin: 20px 0;
        }}
        .to-be-defined h3 {{
            color: #d97706;
        }}
        code {{
            background: #f3f4f6;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
        pre {{
            background: #1f2937;
            color: #f9fafb;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #e5e7eb;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background: #f9fafb;
            font-weight: 600;
        }}
        .metadata {{
            background: #f0f9ff;
            border-left: 4px solid #2563eb;
            padding: 15px;
            margin: 20px 0;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            text-align: center;
            color: #6b7280;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="metadata">
            <strong>Generated:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}<br>
            <strong>Product ID:</strong> {product_id}<br>
            <strong>Format:</strong> HTML (rendered from Markdown)
        </div>
        {html_content}
        <div class="footer">
            <p>Generated by IdeaForge AI - Agentic Product Management Platform</p>
        </div>
    </div>
</body>
</html>"""
            
            # Return HTML response
            return Response(
                content=styled_html,
                media_type="text/html",
                headers={
                    "Content-Disposition": f'attachment; filename="PRD_{product_info["name"].replace(" ", "_")}_{datetime.utcnow().strftime("%Y%m%d")}.html"'
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("export_prd_error", error=str(e), product_id=str(product_id))
        raise HTTPException(status_code=500, detail=f"Failed to export PRD: {str(e)}")


@router.post("/{product_id}/publish-to-confluence")
async def publish_prd_to_confluence(
    product_id: UUID,
    request: PublishToConfluenceRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Publish PRD to Confluence space using Atlassian MCP agent."""
    try:
        # Check permission
        has_permission = await check_product_permission(db, product_id, current_user["id"], "view")
        if not has_permission:
            raise HTTPException(status_code=403, detail="Access denied to product")
        
        if not AGNO_AVAILABLE:
            raise HTTPException(status_code=500, detail="Agno framework not available")
        
        # Import Atlassian agent
        from backend.agents.agno_atlassian_agent import AgnoAtlassianAgent
        from backend.services.api_key_loader import load_user_api_keys_from_db
        
        # Load user API keys
        user_keys = await load_user_api_keys_from_db(db, str(current_user["id"]))
        
        # Check for Atlassian credentials
        atlassian_email = user_keys.get("atlassian_email") or user_keys.get("ATLASSIAN_EMAIL")
        atlassian_token = user_keys.get("atlassian_api_token") or user_keys.get("ATLASSIAN_API_TOKEN")
        
        if not atlassian_email or not atlassian_token:
            raise HTTPException(
                status_code=400, 
                detail="Atlassian credentials not configured. Please configure Atlassian email and API token in Settings."
            )
        
        # Generate unique title to avoid name clashes
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        unique_title = f"{request.title} - {timestamp}"
        
        # Use MCP server to publish to Confluence
        # Note: This requires the Atlassian MCP server to be configured and accessible
        # The MCP server should have createConfluencePage tool available
        try:
            # For now, we'll use a direct API call approach
            # In production, this should use the MCP server tools
            import httpx
            
            # Get cloud ID from user's Atlassian instance
            # This would typically come from the MCP server or user configuration
            cloud_id = user_keys.get("atlassian_cloud_id")
            if not cloud_id:
                # Try to get from settings or prompt user
                raise HTTPException(
                    status_code=400,
                    detail="Atlassian Cloud ID not configured. Please configure it in Settings."
                )
            
            # Create Confluence page via REST API
            # Note: In production, use MCP server tools instead
            confluence_url = f"https://api.atlassian.com/ex/confluence/{cloud_id}/wiki/api/v2/pages"
            
            headers = {
                "Authorization": f"Basic {base64.b64encode(f'{atlassian_email}:{atlassian_token}'.encode()).decode()}",
                "Content-Type": "application/json"
            }
            
            # Convert markdown to Confluence storage format (simplified)
            # In production, use proper Confluence storage format converter
            body_content = {
                "value": request.prd_content,
                "representation": "markdown"
            }
            
            payload = {
                "spaceId": request.space_id,
                "title": unique_title,
                "body": body_content,
                "status": "current"
            }
            
            if request.parent_page_id:
                payload["parentId"] = request.parent_page_id
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    confluence_url,
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code not in [200, 201]:
                    error_msg = response.text
                    logger.error(
                        "confluence_publish_error",
                        status_code=response.status_code,
                        error=error_msg,
                        product_id=str(product_id)
                    )
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Failed to publish to Confluence: {error_msg}"
                    )
                
                result = response.json()
                page_id = result.get("id")
                page_url = result.get("_links", {}).get("webui", "")
                
                logger.info(
                    "prd_published_to_confluence",
                    product_id=str(product_id),
                    page_id=page_id,
                    space_id=request.space_id,
                    title=unique_title
                )
                
                return JSONResponse(content={
                    "success": True,
                    "page_id": page_id,
                    "page_url": page_url,
                    "title": unique_title,
                    "space_id": request.space_id
                })
        
        except ImportError:
            # Fallback: Use MCP server if available
            # This would require MCP client setup
            raise HTTPException(
                status_code=501,
                detail="Confluence publishing via MCP server not yet implemented. Please use the REST API approach."
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("publish_confluence_error", error=str(e), product_id=str(product_id))
        raise HTTPException(status_code=500, detail=f"Failed to publish to Confluence: {str(e)}")
