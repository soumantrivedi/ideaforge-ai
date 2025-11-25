"""Design API endpoints for V0 and Lovable integration."""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Dict, Any, Optional
from uuid import UUID
from pydantic import BaseModel
import structlog

from backend.database import get_db
from backend.api.auth import get_current_user
from backend.agents.v0_agent import V0Agent
from backend.agents.lovable_agent import LovableAgent
from backend.config import settings

logger = structlog.get_logger()
router = APIRouter(prefix="/api/design", tags=["design"])

# Initialize agents
v0_agent = V0Agent()
lovable_agent = LovableAgent()


class GeneratePromptRequest(BaseModel):
    product_id: str
    phase_submission_id: Optional[str] = None
    provider: str  # "v0" or "lovable"
    context: Optional[Dict[str, Any]] = None


class GenerateDesignRequest(BaseModel):
    product_id: str
    phase_submission_id: Optional[str] = None
    provider: str  # "v0" or "lovable"
    prompt: str
    context: Optional[Dict[str, Any]] = None


class GenerateThumbnailsRequest(BaseModel):
    product_id: str
    phase_submission_id: Optional[str] = None
    lovable_prompt: str
    num_previews: int = 3


class CreateProjectRequest(BaseModel):
    product_id: str
    phase_submission_id: Optional[str] = None
    provider: str  # "v0" or "lovable"
    prompt: str
    use_multi_agent: bool = True  # Use multi-agent to enhance prompt
    context: Optional[Dict[str, Any]] = None


@router.post("/generate-prompt")
async def generate_design_prompt(
    request: GeneratePromptRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate a detailed prompt for V0 or Lovable based on product context."""
    try:
        # Get all previous phase submissions for context
        context_query = text("""
            SELECT ps.form_data, ps.generated_content, plp.phase_name
            FROM phase_submissions ps
            JOIN product_lifecycle_phases plp ON ps.phase_id = plp.id
            WHERE ps.product_id = :product_id
            ORDER BY plp.phase_order ASC
        """)
        
        result = await db.execute(context_query, {"product_id": request.product_id})
        rows = result.fetchall()
        
        # Build context from previous phases
        context_parts = []
        for row in rows:
            phase_name = row[2]
            form_data = row[0] or {}
            generated_content = row[1] or ""
            
            context_parts.append(f"## {phase_name} Phase")
            if form_data:
                for key, value in form_data.items():
                    if value and isinstance(value, str) and value.strip():
                        field_name = key.replace('_', ' ').title()
                        context_parts.append(f"- **{field_name}**: {value[:500]}")
            if generated_content:
                context_parts.append(f"\n**Generated Content**: {generated_content[:1000]}")
            context_parts.append("")
        
        full_context = "\n".join(context_parts)
        
        # Generate prompt using appropriate agent
        product_context = {"context": full_context}
        if request.context:
            product_context.update(request.context)
        
        if request.provider == "v0":
            prompt = await v0_agent.generate_v0_prompt(
                product_context=product_context
            )
        elif request.provider == "lovable":
            prompt = await lovable_agent.generate_lovable_prompt(
                product_context=product_context
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid provider. Use 'v0' or 'lovable'")
        
        return {
            "prompt": prompt,
            "provider": request.provider,
            "product_id": request.product_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("error_generating_design_prompt", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-mockup")
async def generate_design_mockup(
    request: GenerateDesignRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate a design mockup using V0 or Lovable API."""
    try:
        from backend.services.api_key_loader import load_user_api_keys_from_db
        
        # Load user-specific API keys
        user_keys = await load_user_api_keys_from_db(db, str(current_user["id"]))
        
        # Generate mockup using appropriate agent
        if request.provider == "v0":
            v0_key = user_keys.get("v0") or settings.v0_api_key
            if not v0_key:
                raise HTTPException(status_code=400, detail="V0 API key is not configured. Please configure it in Settings.")
            
            result = await v0_agent.generate_design_mockup(
                v0_prompt=request.prompt,
                v0_api_key=v0_key,
                user_id=str(current_user["id"])
            )
        elif request.provider == "lovable":
            lovable_key = user_keys.get("lovable") or settings.lovable_api_key
            if not lovable_key:
                raise HTTPException(status_code=400, detail="Lovable API key is not configured. Please configure it in Settings.")
            
            result = await lovable_agent.generate_design_mockup(
                lovable_prompt=request.prompt,
                lovable_api_key=lovable_key,
                user_id=str(current_user["id"]),
                generate_thumbnails=True
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid provider. Use 'v0' or 'lovable'")
        
        # Save mockup to database (with error handling for missing table)
        try:
            insert_query = text("""
                INSERT INTO design_mockups 
                (product_id, phase_submission_id, user_id, provider, prompt, image_url, thumbnail_url, project_url, metadata)
                VALUES (:product_id, :phase_submission_id, :user_id, :provider, :prompt, :image_url, :thumbnail_url, :project_url, CAST(:metadata AS jsonb))
                RETURNING id, created_at
            """)
            
            # Extract URLs from result
            import json
            image_url = result.get("image_url") or result.get("thumbnail_url") or ""
            thumbnail_url = result.get("thumbnail_url") or image_url
            project_url = result.get("project_url") or result.get("url") or ""
            
            # Convert metadata to JSON string
            metadata_json = json.dumps(result) if isinstance(result, dict) else json.dumps({"result": str(result)})
            
            insert_result = await db.execute(insert_query, {
                "product_id": request.product_id,
                "phase_submission_id": request.phase_submission_id,
                "user_id": str(current_user["id"]),
                "provider": request.provider,
                "prompt": request.prompt,
                "image_url": image_url,
                "thumbnail_url": thumbnail_url,
                "project_url": project_url,
                "metadata": metadata_json
            })
            
            await db.commit()
            row = insert_result.fetchone()
            mockup_id = str(row[0]) if row else None
        except Exception as db_error:
            # If table doesn't exist, log but don't fail
            if "does not exist" in str(db_error) or "relation" in str(db_error).lower():
                logger.warning("design_mockups_table_not_found", error=str(db_error))
                mockup_id = None
            else:
                await db.rollback()
                raise
        
        return {
            "id": mockup_id,
            "provider": request.provider,
            "image_url": result.get("image_url") or result.get("thumbnail_url") or "",
            "thumbnail_url": result.get("thumbnail_url") or result.get("image_url") or "",
            "project_url": result.get("project_url") or result.get("url") or "",
            "thumbnails": result.get("thumbnails", []),  # For Lovable multi-thumbnail support
            "code": result.get("code", ""),  # Generated code for V0
            "created_at": None,
            "metadata": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("error_generating_design_mockup", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-thumbnails")
async def generate_thumbnail_previews(
    request: GenerateThumbnailsRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate multiple thumbnail previews for Lovable (3 choices)."""
    try:
        from backend.services.api_key_loader import load_user_api_keys_from_db
        
        # Load user-specific API keys
        user_keys = await load_user_api_keys_from_db(db, str(current_user["id"]))
        lovable_key = user_keys.get("lovable") or settings.lovable_api_key
        
        if not lovable_key:
            raise HTTPException(status_code=400, detail="Lovable API key is not configured. Please configure it in Settings.")
        
        # Generate 3 thumbnail previews
        previews = await lovable_agent.generate_thumbnail_previews(
            lovable_prompt=request.lovable_prompt,
            lovable_api_key=lovable_key,
            num_previews=request.num_previews
        )
        
        return {
            "previews": previews,
            "product_id": request.product_id,
            "num_previews": len(previews)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("error_generating_thumbnails", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mockups/{product_id}")
async def get_design_mockups(
    product_id: str,
    provider: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all design mockups for a product."""
    try:
        # Check if table exists, if not return empty list
        try:
            # Build query conditionally to avoid PostgreSQL type inference issues with NULL
            if provider:
                query = text("""
                    SELECT id, product_id, phase_submission_id, user_id, provider, prompt,
                           image_url, thumbnail_url, project_url, metadata, created_at, updated_at
                    FROM design_mockups
                    WHERE product_id = :product_id
                    AND provider = :provider
                    ORDER BY created_at DESC
                """)
                params = {"product_id": product_id, "provider": provider}
            else:
                query = text("""
                    SELECT id, product_id, phase_submission_id, user_id, provider, prompt,
                           image_url, thumbnail_url, project_url, metadata, created_at, updated_at
                    FROM design_mockups
                    WHERE product_id = :product_id
                    ORDER BY created_at DESC
                """)
                params = {"product_id": product_id}
            
            result = await db.execute(query, params)
            rows = result.fetchall()
            
            mockups = [
                {
                    "id": str(row[0]),
                    "product_id": str(row[1]) if row[1] else None,
                    "phase_submission_id": str(row[2]) if row[2] else None,
                    "user_id": str(row[3]) if row[3] else None,
                    "provider": row[4],
                    "prompt": row[5],
                    "image_url": row[6],
                    "thumbnail_url": row[7],
                    "project_url": row[8] if len(row) > 8 else None,
                    "metadata": row[9] if len(row) > 9 and row[9] else {},
                    "created_at": row[10].isoformat() if len(row) > 10 and row[10] else None,
                    "updated_at": row[11].isoformat() if len(row) > 11 and row[11] else None,
                }
                for row in rows
            ]
            
            return {"mockups": mockups}
        except Exception as table_error:
            # Table doesn't exist - return empty list
            if "does not exist" in str(table_error) or "relation" in str(table_error).lower():
                logger.warning("design_mockups_table_not_found", error=str(table_error))
                return {"mockups": []}
            raise
        
    except Exception as e:
        logger.error("error_getting_design_mockups", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/mockups/{mockup_id}")
async def delete_design_mockup(
    mockup_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a design mockup."""
    try:
        delete_query = text("""
            DELETE FROM design_mockups
            WHERE id = :mockup_id
            RETURNING id
        """)
        
        result = await db.execute(delete_query, {"mockup_id": mockup_id})
        await db.commit()
        
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Mockup not found")
        
        return {"success": True, "id": mockup_id}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("error_deleting_design_mockup", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-project")
async def create_design_project(
    request: CreateProjectRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a V0 or Lovable project using multi-agent enhanced prompts.
    Uses multi-agent system to refine prompts before submission.
    """
    try:
        from backend.services.api_key_loader import load_user_api_keys_from_db
        from backend.agents.agno_orchestrator import AgnoAgenticOrchestrator
        from backend.models.schemas import MultiAgentRequest
        
        # Load user-specific API keys
        user_keys = await load_user_api_keys_from_db(db, str(current_user["id"]))
        
        # Enhance prompt using multi-agent system if requested
        enhanced_prompt = request.prompt
        if request.use_multi_agent:
            try:
                orchestrator = AgnoAgenticOrchestrator()
                
                # Build context for multi-agent enhancement
                enhancement_context = request.context or {}
                enhancement_context.update({
                    "product_id": request.product_id,
                    "provider": request.provider,
                    "original_prompt": request.prompt,
                    "task": "enhance_prototype_prompt"
                })
                
                # Determine primary agent based on provider
                # Use ideation agent for prompt enhancement (it's available in orchestrator)
                primary_agent = "ideation"  # Generic agent for design prompt enhancement
                supporting_agents = ["rag", "analysis", "strategy"]
                
                # Create enhancement query
                enhancement_query = f"""Enhance and optimize the following {request.provider.upper()} prototype generation prompt to ensure it will create a high-quality, production-ready prototype:

Original Prompt:
{request.prompt}

Context:
{enhancement_context.get('phase_name', 'Design phase')}
{enhancement_context.get('form_data', {})}

Please enhance this prompt to:
1. Be more specific and detailed
2. Include all necessary technical requirements
3. Ensure it follows {request.provider.upper()} best practices
4. Include all context from previous phases
5. Be optimized for the {request.provider.upper()} API

Return only the enhanced prompt, ready to use with the {request.provider.upper()} API."""
                
                multi_agent_request = MultiAgentRequest(
                    query=enhancement_query,
                    coordination_mode="enhanced_collaborative",
                    primary_agent=primary_agent,
                    supporting_agents=supporting_agents,
                    context=enhancement_context
                )
                
                multi_agent_response = await orchestrator.process_multi_agent_request(
                    user_id=UUID(current_user["id"]),
                    request=multi_agent_request
                )
                
                enhanced_prompt = multi_agent_response.response.strip()
                logger.info("prompt_enhanced", 
                           provider=request.provider,
                           original_length=len(request.prompt),
                           enhanced_length=len(enhanced_prompt))
            except Exception as e:
                logger.warning("multi_agent_enhancement_failed", error=str(e))
                # Continue with original prompt if enhancement fails
                enhanced_prompt = request.prompt
        
        # Generate project using appropriate agent
        if request.provider == "v0":
            v0_key = user_keys.get("v0") or settings.v0_api_key
            if not v0_key:
                raise HTTPException(status_code=400, detail="V0 API key is not configured. Please configure it in Settings.")
            
            # Use V0 Platform API to create project
            result = await v0_agent.create_v0_project_with_api(
                v0_prompt=enhanced_prompt,
                v0_api_key=v0_key,
                user_id=str(current_user["id"]),
                product_id=request.product_id
            )
        elif request.provider == "lovable":
            lovable_key = user_keys.get("lovable") or settings.lovable_api_key
            if not lovable_key:
                raise HTTPException(status_code=400, detail="Lovable API key is not configured. Please configure it in Settings.")
            
            # Use Lovable API to create project
            result = await lovable_agent.create_lovable_project(
                lovable_prompt=enhanced_prompt,
                lovable_api_key=lovable_key,
                user_id=str(current_user["id"]),
                product_id=request.product_id
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid provider. Use 'v0' or 'lovable'")
        
        # Save project to database
        try:
            import json
            insert_query = text("""
                INSERT INTO design_mockups 
                (product_id, phase_submission_id, user_id, provider, prompt, image_url, thumbnail_url, project_url, metadata)
                VALUES (:product_id, :phase_submission_id, :user_id, :provider, :prompt, :image_url, :thumbnail_url, :project_url, CAST(:metadata AS jsonb))
                RETURNING id, created_at
            """)
            
            image_url = result.get("image_url") or result.get("thumbnail_url") or ""
            thumbnail_url = result.get("thumbnail_url") or image_url
            project_url = result.get("project_url") or result.get("url") or result.get("demo") or ""
            
            metadata_json = json.dumps({
                "enhanced_prompt": enhanced_prompt,
                "original_prompt": request.prompt,
                "use_multi_agent": request.use_multi_agent,
                **result
            })
            
            insert_result = await db.execute(insert_query, {
                "product_id": request.product_id,
                "phase_submission_id": request.phase_submission_id,
                "user_id": str(current_user["id"]),
                "provider": request.provider,
                "prompt": enhanced_prompt,
                "image_url": image_url,
                "thumbnail_url": thumbnail_url,
                "project_url": project_url,
                "metadata": metadata_json
            })
            
            await db.commit()
            row = insert_result.fetchone()
            project_id = str(row[0]) if row else None
        except Exception as db_error:
            if "does not exist" in str(db_error) or "relation" in str(db_error).lower():
                logger.warning("design_mockups_table_not_found", error=str(db_error))
                project_id = None
            else:
                await db.rollback()
                raise
        
        return {
            "id": project_id,
            "provider": request.provider,
            "project_url": project_url,
            "image_url": image_url,
            "thumbnail_url": thumbnail_url,
            "code": result.get("code", ""),
            "enhanced_prompt": enhanced_prompt,
            "original_prompt": request.prompt,
            "metadata": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("error_creating_design_project", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
