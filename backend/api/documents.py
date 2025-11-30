"""API endpoints for document upload and management."""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
from pydantic import BaseModel
import structlog
import re
from uuid import UUID
import io

from backend.database import get_db
from backend.api.auth import get_current_user
from backend.agents.agno_github_agent import AgnoGitHubAgent
from backend.agents.agno_atlassian_agent import AgnoAtlassianAgent

logger = structlog.get_logger()
router = APIRouter(prefix="/api/documents", tags=["documents"])


class GitHubUploadRequest(BaseModel):
    github_url: str
    product_id: Optional[str] = None


class ConfluenceUploadRequest(BaseModel):
    confluence_url: str
    product_id: Optional[str] = None


def extract_text_from_pdf(content: bytes) -> str:
    """Extract text content from PDF bytes."""
    try:
        from pypdf import PdfReader
        pdf_file = io.BytesIO(content)
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        logger.error("pdf_extraction_failed", error=str(e))
        raise HTTPException(status_code=400, detail=f"Failed to extract text from PDF: {str(e)}")


@router.post("/upload")
async def upload_local_file(
    file: UploadFile = File(...),
    product_id: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload a local file to the knowledge base."""
    try:
        await db.execute(text(f"SET LOCAL app.current_user_id = '{current_user['id']}'"))
        
        # Read file content
        content = await file.read()
        
        # Extract text based on file type
        content_type = file.content_type or ""
        if content_type == "application/pdf" or (file.filename and file.filename.lower().endswith('.pdf')):
            # Extract text from PDF
            content_str = extract_text_from_pdf(content)
        elif content_type.startswith("text/") or content_type in ["application/json", "application/xml"]:
            # Decode text files
            try:
                content_str = content.decode('utf-8')
            except UnicodeDecodeError:
                # Try other encodings
                try:
                    content_str = content.decode('latin-1')
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Failed to decode text file: {str(e)}")
        else:
            # For other file types, try to decode as text, but log a warning
            try:
                content_str = content.decode('utf-8', errors='replace')
                logger.warning("non_text_file_uploaded", filename=file.filename, content_type=content_type)
            except Exception as e:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Unsupported file type. Please upload PDF or text files. Error: {str(e)}"
                )
        
        # Save to knowledge base
        # Note: knowledge_articles table requires product_id, so if no product_id, we'll need to handle it
        if not product_id:
            raise HTTPException(status_code=400, detail="product_id is required for knowledge articles")
        
        query = text("""
            INSERT INTO knowledge_articles (product_id, title, content, source, metadata)
            VALUES (:product_id, :title, :content, 'local_upload', :metadata)
            RETURNING id
        """)
        
        metadata = {
            "filename": file.filename,
            "content_type": content_type,
            "size": len(content),
            "user_id": str(current_user["id"])
        }
        
        import json
        result = await db.execute(query, {
            "product_id": UUID(product_id),
            "title": file.filename or "Untitled Document",
            "content": content_str,
            "metadata": json.dumps(metadata)
        })
        
        document_id = result.scalar_one()
        await db.commit()
        
        logger.info("document_uploaded", user_id=str(current_user["id"]), document_id=str(document_id))
        
        return {
            "document_id": str(document_id),
            "message": "File uploaded successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("document_upload_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.post("/upload-from-github")
async def upload_from_github(
    request: GitHubUploadRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Fetch and upload a document from GitHub using GitHub MCP agent."""
    try:
        await db.execute(text(f"SET LOCAL app.current_user_id = '{current_user['id']}'"))
        
        # Initialize GitHub agent
        github_agent = AgnoGitHubAgent(enable_rag=True)
        
        # Fetch content from GitHub
        fetched_data = await github_agent.fetch_from_github_url(
            github_url=request.github_url,
            user_id=str(current_user["id"]),
            product_id=request.product_id
        )
        
        if not fetched_data.get("success"):
            raise HTTPException(status_code=400, detail="Failed to fetch from GitHub")
        
        # Extract metadata
        metadata = fetched_data.get("metadata", {})
        content = fetched_data.get("content", "")
        
        # Save to knowledge base
        if not request.product_id:
            raise HTTPException(status_code=400, detail="product_id is required for knowledge articles")
        
        query = text("""
            INSERT INTO knowledge_articles (product_id, title, content, source, metadata)
            VALUES (:product_id, :title, :content, 'github', :metadata)
            RETURNING id
        """)
        
        import json
        title = metadata.get("path", "GitHub Document") or "GitHub Document"
        
        result = await db.execute(query, {
            "product_id": UUID(request.product_id),
            "title": title,
            "content": content,
            "metadata": json.dumps({
                **metadata,
                "github_url": request.github_url,
                "user_id": str(current_user["id"])
            })
        })
        
        document_id = result.scalar_one()
        await db.commit()
        
        logger.info("github_document_uploaded", user_id=str(current_user["id"]), document_id=str(document_id))
        
        return {
            "document_id": str(document_id),
            "message": "Document fetched from GitHub and added to knowledge base"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("github_upload_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to upload from GitHub: {str(e)}")


@router.post("/upload-from-confluence")
async def upload_from_confluence(
    request: ConfluenceUploadRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Fetch and upload a document from Confluence using Atlassian MCP agent."""
    try:
        await db.execute(text(f"SET LOCAL app.current_user_id = '{current_user['id']}'"))
        
        # Extract page ID from URL or use as-is if it's just an ID
        page_id = request.confluence_url
        url_match = re.search(r'/pages/(\d+)/', request.confluence_url)
        if url_match:
            page_id = url_match.group(1)
        elif not page_id.isdigit():
            raise HTTPException(status_code=400, detail="Invalid Confluence URL or page ID")
        
        # Load user API keys to pass credentials via context
        from backend.services.api_key_loader import load_user_api_keys_from_db
        user_keys = await load_user_api_keys_from_db(db, str(current_user["id"]))
        
        # Prepare context with Atlassian credentials
        context = {
            "atlassian_email": user_keys.get("atlassian_email") or user_keys.get("ATLASSIAN_EMAIL"),
            "atlassian_token": user_keys.get("atlassian_api_token") or user_keys.get("ATLASSIAN_API_TOKEN"),
            "user_keys": user_keys
        }
        
        # Initialize Atlassian agent
        atlassian_agent = AgnoAtlassianAgent(enable_rag=True)
        
        # Fetch content from Confluence with credentials in context
        fetched_data = await atlassian_agent.fetch_confluence_page(
            page_id=page_id,
            user_id=str(current_user["id"]),
            product_id=request.product_id,
            confluence_url=request.confluence_url,
            context=context
        )
        
        if not fetched_data.get("success"):
            raise HTTPException(status_code=400, detail="Failed to fetch from Confluence")
        
        # Extract metadata
        metadata = fetched_data.get("metadata", {})
        content = fetched_data.get("content", "")
        
        # Save to knowledge base
        if not request.product_id:
            raise HTTPException(status_code=400, detail="product_id is required for knowledge articles")
        
        query = text("""
            INSERT INTO knowledge_articles (product_id, title, content, source, metadata)
            VALUES (:product_id, :title, :content, 'confluence', :metadata)
            RETURNING id
        """)
        
        import json
        title = metadata.get("title", "Confluence Document") or "Confluence Document"
        
        result = await db.execute(query, {
            "product_id": UUID(request.product_id),
            "title": title,
            "content": content,
            "metadata": json.dumps({
                **metadata,
                "confluence_url": request.confluence_url,
                "page_id": page_id,
                "user_id": str(current_user["id"])
            })
        })
        
        document_id = result.scalar_one()
        await db.commit()
        
        logger.info("confluence_document_uploaded", user_id=str(current_user["id"]), document_id=str(document_id))
        
        return {
            "document_id": str(document_id),
            "message": "Document fetched from Confluence and added to knowledge base"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("confluence_upload_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to upload from Confluence: {str(e)}")

