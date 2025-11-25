"""
Export API endpoints for generating PRD documents in HTML format
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
import structlog
import markdown
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


@router.post("/{product_id}/export-prd")
async def export_prd_document(
    product_id: UUID,
    request: ExportRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Export PRD document in HTML format from conversation history and product data."""
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
        kb_query = text("""
            SELECT title, content, source_type, source_url
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
                "source_type": row[2],
                "source_url": row[3]
            }
            for row in kb_rows
        ]
        
        # Generate PRD using export agent
        if export_agent:
            prd_content = await export_agent.generate_comprehensive_prd(
                product_id=str(product_id),
                product_info=product_info,
                phase_data=phase_data,
                conversation_history=conversation_history,
                knowledge_base=knowledge_base
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
            
            prd_content += "\n## Conversation History\n"
            for msg in conversation_history:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                prd_content += f"\n### {role.title()}\n{content}\n"
        
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

