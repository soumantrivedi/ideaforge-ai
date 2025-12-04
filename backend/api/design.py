"""Design API endpoints for V0 and Lovable integration."""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Dict, Any, Optional, AsyncGenerator
from uuid import UUID
from pydantic import BaseModel, Field
import structlog
import asyncio
import json

from backend.database import get_db
from backend.api.auth import get_current_user
from backend.agents.v0_agent import V0Agent
from backend.agents.lovable_agent import LovableAgent
from backend.agents.agno_v0_agent import AgnoV0Agent
from backend.agents.agno_lovable_agent import AgnoLovableAgent
from backend.config import settings

logger = structlog.get_logger()
router = APIRouter(prefix="/api/design", tags=["design"])

# Initialize agents (use Agno agents for multi-agent integration)
# Keep legacy agents for backward compatibility
v0_agent = V0Agent()
lovable_agent = LovableAgent()

# Initialize Agno agents (these are registered in the orchestrator)
# These will be accessed through the orchestrator for multi-agent coordination


class GeneratePromptRequest(BaseModel):
    product_id: str
    phase_submission_id: Optional[str] = None
    provider: str  # "v0" or "lovable"
    context: Optional[Dict[str, Any]] = None
    force_new: bool = False  # If True, generate new prompt even if one exists


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
    prompt: Optional[str] = None  # Optional for create-project (only needed for storage)
    use_multi_agent: bool = False  # Not used in create-project (prompt enhancement happens in submit-chat)
    context: Optional[Dict[str, Any]] = None
    create_new: bool = False  # If False, reuse existing project; if True, create new one


class SubmitChatRequest(BaseModel):
    product_id: str
    phase_submission_id: Optional[str] = None
    provider: str  # "v0" or "lovable"
    prompt: str
    project_id: str = Field(..., alias="projectId")  # Required - accepts both project_id (snake_case) and projectId (camelCase)
    
    class Config:
        populate_by_name = True  # Allow both field name and alias


async def stream_design_prompt_generation(
    request: GeneratePromptRequest,
    user_id: str,
    db: AsyncSession
) -> AsyncGenerator[str, None]:
    """Stream prompt generation for V0 or Lovable. Optimized for fast, smooth streaming."""
    import json
    import asyncio
    
    try:
        # Get all previous phase submissions for context (optimized query)
        context_query = text("""
            SELECT ps.form_data, ps.generated_content, plp.phase_name
            FROM phase_submissions ps
            JOIN product_lifecycle_phases plp ON ps.phase_id = plp.id
            WHERE ps.product_id = :product_id
            ORDER BY plp.phase_order ASC
        """)
        
        result = await db.execute(context_query, {"product_id": request.product_id})
        rows = result.fetchall()
        
        # Build comprehensive context - include ALL form data and content
        context_parts = []
        
        for row in rows:
            phase_name = row[2]
            form_data_raw = row[0]
            generated_content = row[1] or ""
            
            # Ensure form_data is a dict, not a list
            if isinstance(form_data_raw, dict):
                form_data = form_data_raw
            elif isinstance(form_data_raw, list):
                logger.warning("form_data_is_list_in_stream_context", 
                             phase_name=phase_name, 
                             product_id=request.product_id)
                form_data = {}  # Convert list to empty dict to avoid errors
            else:
                form_data = form_data_raw or {}
                if not isinstance(form_data, dict):
                    logger.warning("form_data_unexpected_type_in_stream", 
                                 phase_name=phase_name, 
                                 product_id=request.product_id,
                                 form_data_type=type(form_data).__name__)
                    form_data = {}
            
            phase_text = f"## {phase_name} Phase\n"
            
            # Include ALL form data fields, not just key fields
            if form_data:
                phase_text += "Form Data:\n"
                for field, value in form_data.items():
                    if value:  # Only include non-empty fields
                        if isinstance(value, (dict, list)):
                            phase_text += f"- {field}: {json.dumps(value, indent=2)}\n"
                        else:
                            phase_text += f"- {field}: {value}\n"
            
            # Include full generated content
            if generated_content:
                phase_text += f"\nGenerated Content:\n{generated_content}\n"
            
            context_parts.append(phase_text)
        
        full_context = "\n".join(context_parts)
        
        # Generate prompt using appropriate agent
        product_context = {"context": full_context}
        if request.context:
            # Ensure context is a dict, not a list
            if isinstance(request.context, dict):
                product_context.update(request.context)
            elif isinstance(request.context, list):
                logger.warning("context_is_list_in_stream", 
                             provider=request.provider,
                             product_id=request.product_id)
            else:
                logger.warning("unexpected_context_type_in_stream", 
                             context_type=type(request.context).__name__)
        
        # Check for existing prompt
        existing_prompt = None
        if not request.force_new and request.phase_submission_id:
            try:
                submission_query = text("""
                    SELECT form_data
                    FROM phase_submissions
                    WHERE id = :phase_submission_id
                """)
                submission_result = await db.execute(submission_query, {"phase_submission_id": request.phase_submission_id})
                submission_row = submission_result.fetchone()
                if submission_row:
                    form_data = submission_row[0] or {}
                    # Ensure form_data is a dict, not a list
                    if isinstance(form_data, list):
                        logger.warning("form_data_is_list_in_existing_prompt_stream", 
                                     phase_submission_id=request.phase_submission_id)
                        form_data = {}
                    if isinstance(form_data, dict):
                        v0_lovable_prompts = form_data.get("v0_lovable_prompts", "")
                        if v0_lovable_prompts:
                            try:
                                import json
                                prompts_obj = json.loads(v0_lovable_prompts) if isinstance(v0_lovable_prompts, str) else v0_lovable_prompts
                                # Ensure prompts_obj is a dict before calling .get()
                                if isinstance(prompts_obj, dict):
                                    if request.provider == "v0":
                                        existing_prompt = prompts_obj.get("v0_prompt", "")
                                    elif request.provider == "lovable":
                                        existing_prompt = prompts_obj.get("lovable_prompt", "")
                                else:
                                    logger.warning("prompts_obj_not_dict_stream", 
                                                 prompts_obj_type=type(prompts_obj).__name__,
                                                 phase_submission_id=request.phase_submission_id)
                            except Exception as parse_error:
                                logger.warning("error_parsing_prompts_obj_stream", 
                                             error=str(parse_error),
                                             phase_submission_id=request.phase_submission_id)
                                pass
            except Exception as e:
                logger.warning("error_loading_existing_prompt", error=str(e))
        
        # Return existing prompt if found
        if existing_prompt and not request.force_new:
            yield f"data: {json.dumps({'type': 'complete', 'prompt': existing_prompt, 'is_existing': True})}\n\n"
            return
        
        # Load user-specific API keys
        from backend.services.api_key_loader import load_user_api_keys_from_db
        user_keys = await load_user_api_keys_from_db(db, user_id)
        
        # Send start event
        yield f"data: {json.dumps({'type': 'start', 'provider': request.provider})}\n\n"
        
        # Generate prompt with streaming
        prompt = ""
        if request.provider == "v0":
            from backend.agents import AGNO_AVAILABLE
            if AGNO_AVAILABLE:
                agno_v0_agent = AgnoV0Agent()
                v0_key = user_keys.get("v0") or settings.v0_api_key
                if v0_key:
                    agno_v0_agent.set_v0_api_key(v0_key)
                
                # Stream prompt generation
                try:
                    # Ensure product_context is a dict before passing to agent
                    if not isinstance(product_context, dict):
                        logger.error("product_context_not_dict_v0_stream", 
                                   product_context_type=type(product_context).__name__,
                                   product_id=request.product_id)
                        product_context = {"context": full_context}
                    
                    # Get phase data efficiently (same as Lovable) for comprehensive context
                    phase_submissions_query = text("""
                        SELECT ps.form_data, ps.generated_content, plp.phase_name, plp.phase_order
                        FROM phase_submissions ps
                        JOIN product_lifecycle_phases plp ON ps.phase_id = plp.id
                        WHERE ps.product_id = :product_id
                        ORDER BY plp.phase_order ASC
                    """)
                    phase_result = await db.execute(phase_submissions_query, {"product_id": request.product_id})
                    phase_rows = phase_result.fetchall()
                    
                    all_phases_data = []
                    current_phase_data = None
                    design_form_data = {}
                    for row in phase_rows:
                        form_data_raw = row[0]
                        # Ensure form_data is a dict, not a list
                        if isinstance(form_data_raw, dict):
                            form_data = form_data_raw
                        elif isinstance(form_data_raw, list):
                            logger.warning("form_data_is_list_in_stream_v0", 
                                         phase_name=row[2], 
                                         product_id=request.product_id)
                            form_data = {}  # Convert list to empty dict
                        else:
                            form_data = form_data_raw or {}
                            if not isinstance(form_data, dict):
                                form_data = {}
                        
                        phase_item = {
                            "phase_name": row[2],
                            "form_data": form_data,
                            "generated_content": row[1] or "",
                            "phase_order": row[3]
                        }
                        all_phases_data.append(phase_item)
                        # If this is the Design phase, mark it as current and extract form data
                        if row[2] and "design" in row[2].lower():
                            current_phase_data = phase_item
                            design_form_data = form_data
                    
                    # Fetch conversation history for the product to include in system context
                    # Note: We need to get tenant_id from current_user, but in streaming we only have user_id
                    # We'll fetch it from the database or use a default query
                    conversation_history_query = text("""
                        SELECT ch.message_type, ch.agent_name, ch.content, ch.created_at
                        FROM conversation_history ch
                        WHERE ch.product_id = :product_id
                        ORDER BY ch.created_at ASC
                        LIMIT 100
                    """)
                    conv_result = await db.execute(conversation_history_query, {
                        "product_id": request.product_id
                    })
                    conv_rows = conv_result.fetchall()
                    
                    # Summarize conversation history for system context
                    conversation_summary_parts = []
                    for conv_row in conv_rows:
                        msg_type = conv_row[0]
                        agent_name = conv_row[1] or ""
                        content = conv_row[2] or ""  # content is at index 2
                        if content:
                            agent_label = f" ({agent_name})" if agent_name else ""
                            conversation_summary_parts.append(f"{msg_type.upper()}{agent_label}: {content[:500]}")
                    
                    conversation_summary = "\n".join(conversation_summary_parts) if conversation_summary_parts else ""
                    
                    # Use Agno agent's process method which supports streaming via arun
                    # Pass comprehensive context with all phases data, conversation summary, and design form data
                    prompt = await agno_v0_agent.generate_v0_prompt(
                        product_context=product_context,
                        phase_data=current_phase_data,
                        all_phases_data=all_phases_data,
                        conversation_summary=conversation_summary,
                        design_form_data=design_form_data
                    )
                    
                    # Stream the prompt in chunks for smooth UX
                    chunk_size = 50
                    for i in range(0, len(prompt), chunk_size):
                        chunk = prompt[i:i+chunk_size]
                        yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                        await asyncio.sleep(0.01)  # Small delay for smooth streaming
                    
                    yield f"data: {json.dumps({'type': 'complete', 'prompt': prompt})}\n\n"
                except Exception as e:
                    error_msg = str(e)
                    if "api" in error_msg.lower() and ("key" in error_msg.lower() or "401" in error_msg):
                        yield f"data: {json.dumps({'type': 'error', 'error': 'V0 API key error. Please check your V0 API key in Settings.'})}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
            else:
                # Fallback to legacy
                prompt = await v0_agent.generate_v0_prompt(product_context=product_context)
                yield f"data: {json.dumps({'type': 'complete', 'prompt': prompt})}\n\n"
                
        elif request.provider == "lovable":
            agno_lovable_agent = AgnoLovableAgent()
            
            # Get phase data efficiently
            phase_submissions_query = text("""
                SELECT ps.form_data, ps.generated_content, plp.phase_name, plp.phase_order
                FROM phase_submissions ps
                JOIN product_lifecycle_phases plp ON ps.phase_id = plp.id
                WHERE ps.product_id = :product_id
                ORDER BY plp.phase_order ASC
            """)
            phase_result = await db.execute(phase_submissions_query, {"product_id": request.product_id})
            phase_rows = phase_result.fetchall()
            
            all_phases_data = []
            current_phase_data = None
            design_form_data = {}
            for row in phase_rows:
                form_data_raw = row[0]
                # Ensure form_data is a dict, not a list
                if isinstance(form_data_raw, dict):
                    form_data = form_data_raw
                elif isinstance(form_data_raw, list):
                    logger.warning("form_data_is_list_in_stream_lovable", 
                                 phase_name=row[2], 
                                 product_id=request.product_id)
                    form_data = {}  # Convert list to empty dict
                else:
                    form_data = form_data_raw or {}
                    if not isinstance(form_data, dict):
                        form_data = {}
                
                phase_item = {
                    "phase_name": row[2],
                    "form_data": form_data,
                    "generated_content": row[1] or "",
                    "phase_order": row[3]
                }
                all_phases_data.append(phase_item)
                if row[2] and "design" in row[2].lower():
                    current_phase_data = phase_item
                    design_form_data = form_data
            
            # Fetch conversation history for the product to include in system context
            conversation_history_query = text("""
                SELECT ch.message_type, ch.agent_name, ch.content, ch.created_at
                FROM conversation_history ch
                WHERE ch.product_id = :product_id
                ORDER BY ch.created_at ASC
                LIMIT 100
            """)
            conv_result = await db.execute(conversation_history_query, {
                "product_id": request.product_id
            })
            conv_rows = conv_result.fetchall()
            
            # Summarize conversation history for system context
            conversation_summary_parts = []
            for conv_row in conv_rows:
                msg_type = conv_row[0]
                agent_name = conv_row[1] or ""
                content = conv_row[3] or ""
                if content:
                    agent_label = f" ({agent_name})" if agent_name else ""
                    conversation_summary_parts.append(f"{msg_type.upper()}{agent_label}: {content[:500]}")
            
            conversation_summary = "\n".join(conversation_summary_parts) if conversation_summary_parts else ""
            
            # Ensure product_context is a dict before passing to agent
            if not isinstance(product_context, dict):
                logger.error("product_context_not_dict_lovable_stream", 
                           product_context_type=type(product_context).__name__,
                           product_id=request.product_id)
                product_context = {"context": full_context}
            
            # Stream prompt generation
            try:
                prompt = await agno_lovable_agent.generate_lovable_prompt(
                    product_context=product_context,
                    phase_data=current_phase_data,
                    all_phases_data=all_phases_data,
                    conversation_summary=conversation_summary,
                    design_form_data=design_form_data
                )
                
                # Stream the prompt in chunks
                chunk_size = 50
                for i in range(0, len(prompt), chunk_size):
                    chunk = prompt[i:i+chunk_size]
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                    await asyncio.sleep(0.01)
                
                yield f"data: {json.dumps({'type': 'complete', 'prompt': prompt})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'error', 'error': 'Invalid provider. Use v0 or lovable.'})}\n\n"
            
    except Exception as e:
        logger.error("error_streaming_design_prompt", error=str(e))
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"


@router.post("/generate-prompt")
async def generate_design_prompt(
    request: GeneratePromptRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate a detailed prompt for V0 or Lovable based on product context. Optimized for fast generation."""
    try:
        # Optimized context building (limit to essential info to reduce processing time)
        context_query = text("""
            SELECT ps.form_data, ps.generated_content, plp.phase_name
            FROM phase_submissions ps
            JOIN product_lifecycle_phases plp ON ps.phase_id = plp.id
            WHERE ps.product_id = :product_id
            ORDER BY plp.phase_order ASC
        """)
        
        result = await db.execute(context_query, {"product_id": request.product_id})
        rows = result.fetchall()
        
        # Build comprehensive context - include ALL form data and content
        context_parts = []
        
        for row in rows:
            phase_name = row[2]
            form_data_raw = row[0]
            generated_content = row[1] or ""
            
            # Ensure form_data is a dict, not a list
            if isinstance(form_data_raw, dict):
                form_data = form_data_raw
            elif isinstance(form_data_raw, list):
                logger.warning("form_data_is_list_in_context", 
                             phase_name=phase_name, 
                             product_id=request.product_id)
                form_data = {}  # Convert list to empty dict to avoid errors
            else:
                form_data = form_data_raw or {}
                if not isinstance(form_data, dict):
                    logger.warning("form_data_unexpected_type", 
                                 phase_name=phase_name, 
                                 product_id=request.product_id,
                                 form_data_type=type(form_data).__name__)
                    form_data = {}
            
            phase_text = f"## {phase_name} Phase\n"
            
            # Include ALL form data fields, not just key fields
            if form_data:
                phase_text += "Form Data:\n"
                for field, value in form_data.items():
                    if value:  # Only include non-empty fields
                        if isinstance(value, (dict, list)):
                            import json
                            phase_text += f"- {field}: {json.dumps(value, indent=2)}\n"
                        else:
                            phase_text += f"- {field}: {value}\n"
            
            # Include full generated content
            if generated_content:
                phase_text += f"\nGenerated Content:\n{generated_content}\n"
            
            context_parts.append(phase_text)
        
        full_context = "\n".join(context_parts)
        
        # Generate prompt using appropriate agent
        product_context = {"context": full_context}
        if request.context:
            # Ensure context is a dict, not a list
            if isinstance(request.context, dict):
                product_context.update(request.context)
            elif isinstance(request.context, list):
                # If context is a list, log warning and skip
                logger.warning("context_is_list_in_generate_prompt", 
                             provider=request.provider,
                             product_id=request.product_id,
                             context_type=type(request.context).__name__)
            else:
                logger.warning("unexpected_context_type", 
                             context_type=type(request.context).__name__)
        
        # Ensure product_context is always a dict before passing to agents
        if not isinstance(product_context, dict):
            logger.error("product_context_not_dict_before_agent", 
                        product_context_type=type(product_context).__name__,
                        provider=request.provider,
                        product_id=request.product_id)
            product_context = {"context": full_context}  # Reset to safe default
        
        # Check for existing prompt in phase submission (unless force_new=True)
        existing_prompt = None
        if not request.force_new and request.phase_submission_id:
            try:
                submission_query = text("""
                    SELECT form_data
                    FROM phase_submissions
                    WHERE id = :phase_submission_id
                """)
                submission_result = await db.execute(submission_query, {"phase_submission_id": request.phase_submission_id})
                submission_row = submission_result.fetchone()
                if submission_row:
                    form_data = submission_row[0] or {}
                    # Ensure form_data is a dict, not a list
                    if isinstance(form_data, list):
                        logger.warning("form_data_is_list_in_existing_prompt", 
                                     phase_submission_id=request.phase_submission_id)
                        form_data = {}
                    if isinstance(form_data, dict):
                        v0_lovable_prompts = form_data.get("v0_lovable_prompts", "")
                        if v0_lovable_prompts:
                            try:
                                import json
                                prompts_obj = json.loads(v0_lovable_prompts) if isinstance(v0_lovable_prompts, str) else v0_lovable_prompts
                                # Ensure prompts_obj is a dict before calling .get()
                                if isinstance(prompts_obj, dict):
                                    if request.provider == "v0":
                                        existing_prompt = prompts_obj.get("v0_prompt", "")
                                    elif request.provider == "lovable":
                                        existing_prompt = prompts_obj.get("lovable_prompt", "")
                                else:
                                    logger.warning("prompts_obj_not_dict", 
                                                 prompts_obj_type=type(prompts_obj).__name__,
                                                 phase_submission_id=request.phase_submission_id)
                            except Exception as parse_error:
                                logger.warning("error_parsing_prompts_obj", 
                                             error=str(parse_error),
                                             phase_submission_id=request.phase_submission_id)
                                pass
            except Exception as e:
                logger.warning("error_loading_existing_prompt", error=str(e))
        
        # Return existing prompt if found and not forcing new
        if existing_prompt and not request.force_new:
            logger.info("returning_existing_prompt",
                       provider=request.provider,
                       product_id=request.product_id,
                       phase_submission_id=request.phase_submission_id)
            return {
                "prompt": existing_prompt,
                "provider": request.provider,
                "product_id": request.product_id,
                "is_existing": True
            }
        
        # Load user-specific API keys
        from backend.services.api_key_loader import load_user_api_keys_from_db
        user_keys = await load_user_api_keys_from_db(db, str(current_user["id"]))
        
        if request.provider == "v0":
            # Use AgnoV0Agent when Agno is available, otherwise use legacy V0Agent
            from backend.agents import AGNO_AVAILABLE
            if AGNO_AVAILABLE:
                agno_v0_agent = AgnoV0Agent()
                # Set V0 API key if user has one, otherwise use global settings
                # Note: V0 API key is needed if agent tools are invoked, but not for prompt generation
                v0_key = user_keys.get("v0") or settings.v0_api_key
                if v0_key:
                    agno_v0_agent.set_v0_api_key(v0_key)
                try:
                    # Ensure product_context is a dict before passing to agent
                    if not isinstance(product_context, dict):
                        logger.error("product_context_not_dict_v0", 
                                   product_context_type=type(product_context).__name__,
                                   product_id=request.product_id)
                        product_context = {"context": full_context}
                    
                    # Get phase data efficiently (same as Lovable) for comprehensive context
                    phase_submissions_query = text("""
                        SELECT ps.form_data, ps.generated_content, plp.phase_name, plp.phase_order
                        FROM phase_submissions ps
                        JOIN product_lifecycle_phases plp ON ps.phase_id = plp.id
                        WHERE ps.product_id = :product_id
                        ORDER BY plp.phase_order ASC
                    """)
                    phase_result = await db.execute(phase_submissions_query, {"product_id": request.product_id})
                    phase_rows = phase_result.fetchall()
                    
                    all_phases_data = []
                    current_phase_data = None
                    design_form_data = {}
                    for row in phase_rows:
                        form_data_raw = row[0]
                        # Ensure form_data is a dict, not a list
                        if isinstance(form_data_raw, dict):
                            form_data = form_data_raw
                        elif isinstance(form_data_raw, list):
                            logger.warning("form_data_is_list_in_v0", 
                                         phase_name=row[2], 
                                         product_id=request.product_id)
                            form_data = {}  # Convert list to empty dict
                        else:
                            form_data = form_data_raw or {}
                            if not isinstance(form_data, dict):
                                form_data = {}
                        
                        phase_item = {
                            "phase_name": row[2],
                            "form_data": form_data,
                            "generated_content": row[1] or "",
                            "phase_order": row[3]
                        }
                        all_phases_data.append(phase_item)
                        # If this is the Design phase, mark it as current and extract form data
                        if row[2] and "design" in row[2].lower():
                            current_phase_data = phase_item
                            design_form_data = form_data
                    
                    # Fetch conversation history for the product to include in system context
                    conversation_history_query = text("""
                        SELECT ch.message_type, ch.agent_name, ch.content, ch.created_at
                        FROM conversation_history ch
                        WHERE ch.product_id = :product_id
                        AND ch.tenant_id = :tenant_id
                        ORDER BY ch.created_at ASC
                        LIMIT 100
                    """)
                    conv_result = await db.execute(conversation_history_query, {
                        "product_id": request.product_id,
                        "tenant_id": current_user["tenant_id"]
                    })
                    conv_rows = conv_result.fetchall()
                    
                    # Summarize conversation history for system context
                    conversation_summary_parts = []
                    for conv_row in conv_rows:
                        msg_type = conv_row[0]
                        agent_name = conv_row[1] or ""
                        content = conv_row[2] or ""  # content is at index 2
                        if content:
                            agent_label = f" ({agent_name})" if agent_name else ""
                            conversation_summary_parts.append(f"{msg_type.upper()}{agent_label}: {content[:500]}")
                    
                    conversation_summary = "\n".join(conversation_summary_parts) if conversation_summary_parts else ""
                    
                    # Optimized prompt generation with comprehensive context (uses fast model tier and optimized system prompt)
                    prompt = await agno_v0_agent.generate_v0_prompt(
                        product_context=product_context,
                        phase_data=current_phase_data,
                        all_phases_data=all_phases_data,
                        conversation_summary=conversation_summary,
                        design_form_data=design_form_data
                    )
                except Exception as e:
                    # If error mentions V0 API key, provide helpful message
                    error_msg = str(e)
                    if "api" in error_msg.lower() and ("key" in error_msg.lower() or "401" in error_msg or "authentication" in error_msg.lower()):
                        logger.error("v0_api_key_error_in_prompt_generation", 
                                   user_id=str(current_user["id"]),
                                   has_user_key=bool(user_keys.get("v0")),
                                   has_global_key=bool(settings.v0_api_key),
                                   error=error_msg)
                        raise HTTPException(
                            status_code=400,
                            detail="V0 API key error during prompt generation. Please check your V0 API key in Settings. Error: " + error_msg
                        )
                    raise
            else:
                # Fallback to legacy V0Agent
                prompt = await v0_agent.generate_v0_prompt(
                    product_context=product_context
                )
        elif request.provider == "lovable":
            # Use Agno Lovable agent for prompt generation
            agno_lovable_agent = AgnoLovableAgent()
            
            # Get phase data efficiently (limit to essential info)
            phase_submissions_query = text("""
                SELECT ps.form_data, ps.generated_content, plp.phase_name, plp.phase_order
                FROM phase_submissions ps
                JOIN product_lifecycle_phases plp ON ps.phase_id = plp.id
                WHERE ps.product_id = :product_id
                ORDER BY plp.phase_order ASC
            """)
            phase_result = await db.execute(phase_submissions_query, {"product_id": request.product_id})
            phase_rows = phase_result.fetchall()
            
            # Build all phases data (limit to essential info)
            all_phases_data = []
            current_phase_data = None
            design_form_data = {}
            for row in phase_rows:
                form_data_raw = row[0]
                # Ensure form_data is a dict, not a list
                if isinstance(form_data_raw, dict):
                    form_data = form_data_raw
                elif isinstance(form_data_raw, list):
                    logger.warning("form_data_is_list_in_lovable", 
                                 phase_name=row[2], 
                                 product_id=request.product_id)
                    form_data = {}  # Convert list to empty dict
                else:
                    form_data = form_data_raw or {}
                    if not isinstance(form_data, dict):
                        form_data = {}
                
                phase_item = {
                    "phase_name": row[2],
                    "form_data": form_data,
                    "generated_content": row[1] or "",
                    "phase_order": row[3]
                }
                all_phases_data.append(phase_item)
                # If this is the Design phase, mark it as current and extract form data
                if row[2] and "design" in row[2].lower():
                    current_phase_data = phase_item
                    design_form_data = form_data
            
            # Fetch conversation history for the product to include in system context
            conversation_history_query = text("""
                SELECT ch.message_type, ch.agent_name, ch.content, ch.created_at
                FROM conversation_history ch
                WHERE ch.product_id = :product_id
                AND ch.tenant_id = :tenant_id
                ORDER BY ch.created_at ASC
                LIMIT 100
            """)
            conv_result = await db.execute(conversation_history_query, {
                "product_id": request.product_id,
                "tenant_id": current_user["tenant_id"]
            })
            conv_rows = conv_result.fetchall()
            
            # Summarize conversation history for system context
            conversation_summary_parts = []
            for conv_row in conv_rows:
                msg_type = conv_row[0]
                agent_name = conv_row[1] or ""
                content = conv_row[3] or ""
                if content:
                    agent_label = f" ({agent_name})" if agent_name else ""
                    conversation_summary_parts.append(f"{msg_type.upper()}{agent_label}: {content[:500]}")
            
            conversation_summary = "\n".join(conversation_summary_parts) if conversation_summary_parts else ""
            
            # Ensure product_context is a dict before passing to agent
            if not isinstance(product_context, dict):
                logger.error("product_context_not_dict_lovable", 
                           product_context_type=type(product_context).__name__,
                           product_id=request.product_id)
                product_context = {"context": full_context}
            
            # Generate optimized prompt with all context (uses fast model tier and optimized system prompt)
            prompt = await agno_lovable_agent.generate_lovable_prompt(
                product_context=product_context,
                phase_data=current_phase_data,
                all_phases_data=all_phases_data,
                conversation_summary=conversation_summary,
                design_form_data=design_form_data
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


@router.post("/generate-prompt/stream")
async def stream_generate_design_prompt(
    request: GeneratePromptRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Stream prompt generation for V0 or Lovable. Returns Server-Sent Events for smooth UX."""
    from fastapi.responses import StreamingResponse
    
    user_id = str(current_user["id"])
    
    return StreamingResponse(
        stream_design_prompt_generation(request, user_id, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


async def poll_v0_status_background(
    mockup_id: str,
    v0_chat_id: str,
    v0_api_key: str,
    user_id: str,
    product_id: str,
    max_duration_seconds: int = 900,  # 15 minutes
    poll_interval_seconds: int = 10
):
    """
    Background task to poll V0 API for prototype status.
    Polls every 10 seconds for up to 15 minutes.
    If no response after 15 mins, sets status to indicate manual check needed.
    """
    import asyncio
    from backend.database import AsyncSessionLocal
    from sqlalchemy import text
    import httpx
    
    start_time = asyncio.get_event_loop().time()
    poll_count = 0
    max_polls = max_duration_seconds // poll_interval_seconds
    
    async with AsyncSessionLocal() as db:
        try:
            while poll_count < max_polls:
                await asyncio.sleep(poll_interval_seconds)
                poll_count += 1
                elapsed = int((asyncio.get_event_loop().time() - start_time))
                
                try:
                    # Check V0 API status
                    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                        response = await client.get(
                            f"https://api.v0.dev/v1/chats/{v0_chat_id}",
                            headers={
                                "Authorization": f"Bearer {v0_api_key.strip()}",
                                "Content-Type": "application/json"
                            }
                        )
                    
                    if response.status_code == 200:
                        v0_result = response.json()
                        web_url = v0_result.get("webUrl") or v0_result.get("web_url")
                        demo_url = v0_result.get("demo") or v0_result.get("demoUrl")
                        files = v0_result.get("files", [])
                        
                        # If prototype is ready, update database
                        if demo_url or web_url or (files and len(files) > 0):
                            new_status = "completed"
                            new_project_url = demo_url or web_url
                            
                            update_query = text("""
                                UPDATE design_mockups
                                SET project_status = :status,
                                    project_url = :project_url,
                                    updated_at = now()
                                WHERE id = :id
                            """)
                            await db.execute(update_query, {
                                "id": mockup_id,
                                "status": new_status,
                                "project_url": new_project_url
                            })
                            await db.commit()
                            
                            logger.info("v0_background_polling_completed",
                                       mockup_id=mockup_id,
                                       chat_id=v0_chat_id,
                                       poll_count=poll_count,
                                       elapsed_seconds=elapsed)
                            return  # Success - exit polling
                    
                    # Still in progress, continue polling
                    logger.debug("v0_background_polling_in_progress",
                               mockup_id=mockup_id,
                               chat_id=v0_chat_id,
                               poll_count=poll_count,
                               elapsed_seconds=elapsed)
                    
                except Exception as poll_error:
                    logger.warning("v0_background_polling_error",
                                 mockup_id=mockup_id,
                                 chat_id=v0_chat_id,
                                 poll_count=poll_count,
                                 error=str(poll_error))
                    # Continue polling despite errors
                    continue
            
            # Timeout reached - update status to indicate manual check needed
            update_query = text("""
                UPDATE design_mockups
                SET project_status = 'pending_manual_check',
                    updated_at = now()
                WHERE id = :id
            """)
            await db.execute(update_query, {"id": mockup_id})
            await db.commit()
            
            logger.info("v0_background_polling_timeout",
                      mockup_id=mockup_id,
                      chat_id=v0_chat_id,
                      poll_count=poll_count,
                      elapsed_seconds=elapsed,
                      message="Polling timeout - user should check manually in V0 dashboard")
            
        except Exception as e:
            logger.error("v0_background_polling_fatal_error",
                        mockup_id=mockup_id,
                        chat_id=v0_chat_id,
                        error=str(e))
            # Don't update status on fatal error - let user check manually


@router.post("/generate-mockup")
async def generate_design_mockup(
    request: GenerateDesignRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a design mockup using V0 or Lovable API.
    
    For V0: Delegates to create-project and submit-chat endpoints (new workflow).
    For Lovable: Uses the original generate-mockup flow.
    
    DEPRECATED for V0: Use /create-project and /submit-chat endpoints instead.
    """
    try:
        from backend.services.api_key_loader import load_user_api_keys_from_db
        
        # Load user-specific API keys
        user_keys = await load_user_api_keys_from_db(db, str(current_user["id"]))
        
        # For V0, delegate to the new two-step workflow
        if request.provider == "v0":
            v0_key = user_keys.get("v0") or settings.v0_api_key
            if not v0_key:
                raise HTTPException(status_code=400, detail="V0 API key is not configured. Please configure it in Settings.")
            
            # Step 1: Create/get project
            agno_v0_agent = AgnoV0Agent()
            agno_v0_agent.set_v0_api_key(v0_key.strip())
            project_result = await agno_v0_agent.get_or_create_v0_project(
                v0_api_key=v0_key.strip(),
                user_id=str(current_user["id"]),
                product_id=request.product_id,
                db=db,
                create_new=False
            )
            
            project_id = project_result.get("projectId")
            if not project_id:
                raise HTTPException(status_code=500, detail="Failed to get projectId from create-project")
            
            # Step 2: Submit chat to project
            chat_result = await agno_v0_agent.submit_chat_to_v0_project(
                v0_prompt=request.prompt,
                project_id=project_id,
                v0_api_key=v0_key.strip(),
                user_id=str(current_user["id"]),
                product_id=request.product_id
            )
            
            # Store in database
            async with db.begin():
                await db.execute(
                    text("""
                        INSERT INTO design_mockups 
                        (product_id, phase_submission_id, user_id, provider, v0_project_id, v0_chat_id, project_status, metadata, created_at)
                        VALUES (:product_id, :phase_submission_id, :user_id, :provider, :v0_project_id, :v0_chat_id, :project_status, :metadata, NOW())
                        ON CONFLICT (product_id, phase_submission_id, user_id, provider)
                        DO UPDATE SET
                            v0_project_id = EXCLUDED.v0_project_id,
                            v0_chat_id = EXCLUDED.v0_chat_id,
                            project_status = EXCLUDED.project_status,
                            metadata = EXCLUDED.metadata,
                            updated_at = NOW()
                    """),
                    {
                        "product_id": request.product_id,
                        "phase_submission_id": request.phase_submission_id,
                        "user_id": str(current_user["id"]),
                        "provider": "v0",
                        "v0_project_id": project_id,
                        "v0_chat_id": chat_result.get("chat_id"),
                        "project_status": "in_progress",
                        "metadata": {
                            "prompt": request.prompt,
                            "project_url": project_result.get("project_url"),
                        }
                    }
                )
            
            # Start background status checking
            background_tasks.add_task(
                check_v0_status_background,
                v0_key.strip(),
                project_id,
                request.product_id,
                str(current_user["id"]),
                db
            )
            
            return {
                "id": None,
                "provider": "v0",
                "projectId": project_id,
                "v0_project_id": project_id,
                "project_url": project_result.get("project_url"),
                "project_status": "in_progress",
                "v0_chat_id": chat_result.get("chat_id"),
                "message": "V0 prototype request submitted. Use /check-status to monitor progress.",
                "status": "submitted"
            }
        
        # For Lovable, use the original flow
        elif request.provider == "lovable":
            # Use Lovable Link Generator (no API key needed)
            # Based on: https://docs.lovable.dev/integrations/build-with-url
            from backend.agents.agno_lovable_agent import AgnoLovableAgent
            
            lovable_agent = AgnoLovableAgent()
            result = lovable_agent.generate_lovable_link(
                lovable_prompt=request.prompt,
                image_urls=None  # Can be extended to support images in the future
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid provider. Use 'v0' or 'lovable'")
        
        # Save mockup to database (with error handling for missing table)
        # Rollback any previous failed transaction first
        try:
            await db.rollback()
        except:
            pass  # Ignore if no transaction to rollback
        
        try:
            # Extract URLs and V0-specific fields from result
            import json
            # Handle different result formats for V0 vs Lovable
            if request.provider == "lovable":
                image_url = ""  # Lovable links don't have images
                thumbnail_url = ""
                project_url = result.get("project_url", "")
                v0_chat_id = None
                v0_project_id = None
                project_status = "completed"
            else:  # V0
                image_url = result.get("image_url") or result.get("thumbnail_url") or ""
                thumbnail_url = result.get("thumbnail_url") or image_url
                # V0 project URLs already contain the correct path (e.g., ideation/design)
                project_url = result.get("project_url") or result.get("demo_url") or result.get("web_url") or result.get("url") or ""
                
                # V0 API uses projectId (camelCase) in responses, prefer that over project_id
                v0_chat_id = result.get("chat_id")
                v0_project_id = result.get("projectId") or result.get("project_id")  # Prefer projectId (camelCase)
                project_status = result.get("project_status", "submitted")  # Default to "submitted" for new requests
            
            # Convert metadata to JSON string
            metadata_json = json.dumps(result) if isinstance(result, dict) else json.dumps({"result": str(result)})
            
            # Check if V0 tracking columns exist and insert accordingly
            try:
                if request.provider == "v0" and v0_chat_id:
                    insert_query = text("""
                        INSERT INTO design_mockups 
                        (product_id, phase_submission_id, user_id, provider, prompt, 
                         image_url, thumbnail_url, project_url, v0_chat_id, v0_project_id, 
                         project_status, metadata)
                        VALUES (:product_id, :phase_submission_id, :user_id, :provider, :prompt, 
                                :image_url, :thumbnail_url, :project_url, :v0_chat_id, :v0_project_id, 
                                :project_status, CAST(:metadata AS jsonb))
                        RETURNING id, created_at
                    """)
                    insert_result = await db.execute(insert_query, {
                        "product_id": request.product_id,
                        "phase_submission_id": request.phase_submission_id,
                        "user_id": str(current_user["id"]),
                        "provider": request.provider,
                        "prompt": request.prompt,
                        "image_url": image_url,
                        "thumbnail_url": thumbnail_url,
                        "project_url": project_url,
                        "v0_chat_id": v0_chat_id,
                        "v0_project_id": v0_project_id,
                        "project_status": project_status,
                        "metadata": metadata_json
                    })
                else:
                    insert_query = text("""
                        INSERT INTO design_mockups 
                        (product_id, phase_submission_id, user_id, provider, prompt, image_url, thumbnail_url, project_url, metadata)
                        VALUES (:product_id, :phase_submission_id, :user_id, :provider, :prompt, :image_url, :thumbnail_url, :project_url, CAST(:metadata AS jsonb))
                        RETURNING id, created_at
                    """)
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
            except Exception as col_error:
                # Fallback if V0 tracking columns don't exist
                if "column" in str(col_error).lower() and ("v0_chat_id" in str(col_error) or "project_status" in str(col_error)):
                    logger.warning("v0_tracking_columns_not_found_in_generate_mockup", error=str(col_error))
                    await db.rollback()
                    insert_query = text("""
                        INSERT INTO design_mockups 
                        (product_id, phase_submission_id, user_id, provider, prompt, image_url, thumbnail_url, project_url, metadata)
                        VALUES (:product_id, :phase_submission_id, :user_id, :provider, :prompt, :image_url, :thumbnail_url, :project_url, CAST(:metadata AS jsonb))
                        RETURNING id, created_at
                    """)
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
                else:
                    await db.rollback()
                    raise
            
            await db.commit()
            row = insert_result.fetchone()
            mockup_id = str(row[0]) if row else None
            
            # Start background polling for V0 prototypes
            # Even if chat_id is None (due to timeout), we can still poll later when it becomes available
            if request.provider == "v0" and mockup_id:
                import asyncio
                # If we have chat_id, start polling immediately
                # If not (due to timeout), we'll need to get it from the database later
                if v0_chat_id:
                    # Start background task to poll V0 status
                    # Poll every 10 seconds for up to 15 minutes
                    asyncio.create_task(poll_v0_status_background(
                        mockup_id=mockup_id,
                        v0_chat_id=v0_chat_id,
                        v0_api_key=v0_key,
                        user_id=str(current_user["id"]),
                        product_id=request.product_id,
                        max_duration_seconds=900,  # 15 minutes
                        poll_interval_seconds=10
                    ))
                    logger.info("v0_background_polling_started",
                               mockup_id=mockup_id,
                               chat_id=v0_chat_id,
                               user_id=str(current_user["id"]))
                else:
                    # No chat_id yet (timeout case) - log but don't start polling
                    # User can check status manually or we can retry later
                    logger.warning("v0_background_polling_deferred",
                                 mockup_id=mockup_id,
                                 reason="No chat_id available yet (timeout during submission)",
                                 message="User should check status manually or retry later")
        except Exception as db_error:
            await db.rollback()
            # If table doesn't exist, log but don't fail
            if "does not exist" in str(db_error) or "relation" in str(db_error).lower():
                logger.warning("design_mockups_table_not_found", error=str(db_error))
                mockup_id = None
            else:
                logger.error("error_saving_design_mockup", error=str(db_error), error_type=type(db_error).__name__)
                raise HTTPException(status_code=500, detail=f"Failed to save design mockup: {str(db_error)}")
        
        # Return comprehensive project details for chatbot response
        # For V0, always return "submitted" status - user can check status separately
        # V0 project URLs already contain the correct path (e.g., ideation/design)
        response_project_url = result.get("project_url") or result.get("demo_url") or result.get("web_url") or result.get("url") or ""
        
        response_data = {
            "id": mockup_id,
            "provider": request.provider,
            "image_url": result.get("image_url") or result.get("thumbnail_url") or "",
            "thumbnail_url": result.get("thumbnail_url") or result.get("image_url") or "",
            "project_url": response_project_url,
            "thumbnails": result.get("thumbnails", []),  # For Lovable multi-thumbnail support
            "code": result.get("code", ""),  # Generated code for V0
            "created_at": None,
            "metadata": result,
            "status": "submitted" if request.provider == "v0" else "completed",  # V0 is submitted, not completed yet
            "message": "V0 prototype request submitted successfully. Background polling has started and will check status every 10 seconds for up to 15 minutes. If not ready by then, please check manually in the V0 dashboard." if request.provider == "v0" else None
        }
        
        # Add V0-specific fields for chatbot response
        if request.provider == "v0":
            response_data.update({
                "v0_chat_id": result.get("chat_id"),
                "v0_project_id": result.get("project_id") or result.get("chat_id"),
                "project_name": result.get("project_name") or f"V0 Project {result.get('chat_id', '')[:8] if result.get('chat_id') else 'N/A'}",
                "project_status": result.get("project_status", "in_progress"),
                "web_url": result.get("web_url"),
                "demo_url": result.get("demo_url"),
                "is_existing": result.get("is_existing", False),
                "is_updated": result.get("is_updated", False)
            })
        
        return response_data
        
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
        
        # Lovable uses link generator, not API keys
        # Generate Lovable link using the Build with URL format
        from backend.agents.agno_lovable_agent import AgnoLovableAgent
        
        lovable_agent = AgnoLovableAgent()
        result = lovable_agent.generate_lovable_link(
            lovable_prompt=request.lovable_prompt,
            image_urls=None
        )
        
        # Return link as preview (Lovable doesn't support thumbnail generation via API)
        previews = [{
            "url": result["project_url"],
            "type": "lovable_link",
            "prompt": request.lovable_prompt
        }]
        
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
            # Include V0 tracking fields if they exist
            try:
                if provider:
                    query = text("""
                        SELECT id, product_id, phase_submission_id, user_id, provider, prompt,
                               image_url, thumbnail_url, project_url, v0_chat_id, v0_project_id,
                               project_status, metadata, created_at, updated_at
                        FROM design_mockups
                        WHERE product_id = :product_id
                        AND provider = :provider
                        ORDER BY created_at DESC
                    """)
                    params = {"product_id": product_id, "provider": provider}
                else:
                    query = text("""
                        SELECT id, product_id, phase_submission_id, user_id, provider, prompt,
                               image_url, thumbnail_url, project_url, v0_chat_id, v0_project_id,
                               project_status, metadata, created_at, updated_at
                        FROM design_mockups
                        WHERE product_id = :product_id
                        ORDER BY created_at DESC
                    """)
                    params = {"product_id": product_id}
                
                result = await db.execute(query, params)
                rows = result.fetchall()
                
                mockups = []
                for row in rows:
                    mockup = {
                        "id": str(row[0]),
                        "product_id": str(row[1]) if row[1] else None,
                        "phase_submission_id": str(row[2]) if row[2] else None,
                        "user_id": str(row[3]) if row[3] else None,
                        "provider": row[4],
                        "prompt": row[5],
                        "image_url": row[6],
                        "thumbnail_url": row[7],
                        "project_url": row[8] if len(row) > 8 else None,
                        "v0_chat_id": row[9] if len(row) > 9 else None,
                        "v0_project_id": row[10] if len(row) > 10 else None,
                        "project_status": row[11] if len(row) > 11 else None,
                        "metadata": row[12] if len(row) > 12 and row[12] else {},
                        "created_at": row[13].isoformat() if len(row) > 13 and row[13] else None,
                        "updated_at": row[14].isoformat() if len(row) > 14 and row[14] else None,
                    }
                    mockups.append(mockup)
            except Exception as col_error:
                # Fallback if V0 tracking columns don't exist yet
                if "column" in str(col_error).lower() and ("v0_chat_id" in str(col_error) or "project_status" in str(col_error)):
                    logger.warning("v0_tracking_columns_not_found_in_get", error=str(col_error))
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
                else:
                    raise
            
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


@router.get("/prototypes/{product_id}")
async def get_prototypes_for_review(
    product_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all prototypes for a product - optimized for review agent access.
    Returns thumbnail URLs, project URLs, and status information.
    """
    try:
        query = text("""
            SELECT id, provider, prompt, project_url, v0_chat_id, v0_project_id,
                   project_status, thumbnail_url, image_url, metadata, created_at, updated_at
            FROM design_mockups
            WHERE product_id = :product_id
            ORDER BY created_at DESC
        """)
        
        result = await db.execute(query, {"product_id": product_id})
        rows = result.fetchall()
        
        prototypes = []
        for row in rows:
            prototypes.append({
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
                "created_at": row[10].isoformat() if len(row) > 10 and row[10] else None,
                "updated_at": row[11].isoformat() if len(row) > 11 and row[11] else None
            })
        
        return {"prototypes": prototypes}
    except Exception as e:
        logger.error("error_getting_prototypes_for_review", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mockups/{product_id}/status")
async def check_project_status(
    product_id: str,
    provider: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Check status of existing V0/Lovable project without creating a new one.
    Allows users to come back and check status later.
    """
    try:
        from backend.services.api_key_loader import load_user_api_keys_from_db
        
        # Get the most recent prototype for this product
        # First try with user_id filter, then without if not found (in case prototype was created by different user)
        query = text("""
            SELECT id, v0_chat_id, v0_project_id, project_url, project_status, 
                   metadata, created_at, updated_at, user_id
            FROM design_mockups
            WHERE product_id = :product_id 
              AND user_id = :user_id 
              AND provider = :provider
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        result = await db.execute(query, {
            "product_id": product_id,
            "user_id": str(current_user["id"]),
            "provider": provider
        })
        row = result.fetchone()
        
        # If not found with user_id filter, try without user_id filter (for shared products)
        if not row:
            query_no_user = text("""
                SELECT id, v0_chat_id, v0_project_id, project_url, project_status, 
                       metadata, created_at, updated_at, user_id
                FROM design_mockups
                WHERE product_id = :product_id 
                  AND provider = :provider
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            result_no_user = await db.execute(query_no_user, {
                "product_id": product_id,
                "provider": provider
            })
            row = result_no_user.fetchone()
        
        if not row:
            return {
                "status": "not_found",
                "message": "No prototype found for this product"
            }
        
        # Unpack row (user_id is always included in SELECT, so we always have 9 columns)
        mockup_id, v0_chat_id, v0_project_id, project_url, project_status, \
            metadata, created_at, updated_at, row_user_id = row
        
        # If it's a V0 project and has a chat_id, use Agno V0 Agent to check status
        if provider == "v0" and v0_chat_id:
            try:
                user_keys = await load_user_api_keys_from_db(db, str(current_user["id"]))
                v0_key = user_keys.get("v0") or settings.v0_api_key
                
                if v0_key:
                    # Use Agno V0 Agent for status checking
                    from backend.agents import AGNO_AVAILABLE
                    if AGNO_AVAILABLE:
                        from backend.agents.agno_v0_agent import AgnoV0Agent
                        agno_v0_agent = AgnoV0Agent()
                        agno_v0_agent.set_v0_api_key(v0_key)
                        
                        # Check status using V0 agent
                        import httpx
                        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                            response = await client.get(
                                f"https://api.v0.dev/v1/chats/{v0_chat_id}",
                                headers={
                                    "Authorization": f"Bearer {v0_key.strip()}",
                                    "Content-Type": "application/json"
                                }
                            )
                        
                        if response.status_code == 200:
                            v0_result = response.json()
                            web_url = v0_result.get("webUrl") or v0_result.get("web_url")
                            demo_url = v0_result.get("demo") or v0_result.get("demoUrl")
                            files = v0_result.get("files", [])
                            
                            # Update status if we have URLs
                            if demo_url or web_url or (files and len(files) > 0):
                                new_status = "completed"
                                # V0 project URLs already contain the correct path (e.g., ideation/design)
                                new_project_url = demo_url or web_url
                                
                                # Update database
                                update_query = text("""
                                    UPDATE design_mockups
                                    SET project_status = :status,
                                        project_url = :project_url,
                                        updated_at = now()
                                    WHERE id = :id
                                """)
                                await db.execute(update_query, {
                                    "id": mockup_id,
                                    "status": new_status,
                                    "project_url": new_project_url
                                })
                                await db.commit()
                                
                                project_name = v0_result.get("name") or (metadata.get("name") if isinstance(metadata, dict) else None) or f"V0 Project {v0_chat_id[:8] if v0_chat_id else 'N/A'}"
                                
                                return {
                                    "status": new_status,
                                    "mockup_id": str(mockup_id),
                                    "v0_chat_id": v0_chat_id,
                                    "v0_project_id": v0_project_id or v0_chat_id,
                                    "project_name": project_name,
                                    "project_url": new_project_url,
                                    "web_url": web_url,
                                    "demo_url": demo_url,
                                    "has_files": len(files) > 0,
                                    "message": "Prototype is ready"
                                }
                            else:
                                project_name = (metadata.get("name") if isinstance(metadata, dict) else None) or f"V0 Project {v0_chat_id[:8] if v0_chat_id else 'N/A'}"
                                
                                return {
                                    "status": project_status or "in_progress",
                                    "mockup_id": str(mockup_id),
                                    "v0_chat_id": v0_chat_id,
                                    "v0_project_id": v0_project_id or v0_chat_id,
                                    "project_name": project_name,
                                    "project_url": project_url,
                                    "message": "Prototype is still being generated"
                                }
            except Exception as poll_error:
                logger.warning("status_poll_error", error=str(poll_error))
                # Return cached status if polling fails
                pass
        
        project_name = (metadata.get("name") if isinstance(metadata, dict) else None) or f"V0 Project {v0_chat_id[:8] if v0_chat_id else 'N/A'}"
        
        return {
            "status": project_status or "unknown",
            "mockup_id": str(mockup_id),
            "v0_chat_id": v0_chat_id,
            "v0_project_id": v0_project_id or v0_chat_id,
            "project_name": project_name,
            "project_url": project_url,
            "created_at": created_at.isoformat() if created_at else None,
            "updated_at": updated_at.isoformat() if updated_at else None
        }
        
    except Exception as e:
        logger.error("error_checking_project_status", error=str(e))
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
    
    If create_new=False (default), checks for existing prototype for this product_id
    and returns it if found. If create_new=True, creates a new prototype.
    """
    try:
        from backend.services.api_key_loader import load_user_api_keys_from_db
        from backend.agents.agno_orchestrator import AgnoAgenticOrchestrator
        from backend.models.schemas import MultiAgentRequest
        
        # Step 1: Check for existing prototype (unless create_new=True)
        if not request.create_new:
            existing_query = text("""
                SELECT id, v0_chat_id, v0_project_id, project_url, project_status, 
                       image_url, thumbnail_url, metadata, created_at, updated_at
                FROM design_mockups
                WHERE product_id = :product_id 
                  AND user_id = :user_id 
                  AND provider = :provider
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            existing_result = await db.execute(existing_query, {
                "product_id": request.product_id,
                "user_id": str(current_user["id"]),
                "provider": request.provider
            })
            existing_row = existing_result.fetchone()
            
            if existing_row:
                existing_id, v0_chat_id, v0_project_id, project_url, project_status, \
                    image_url, thumbnail_url, metadata, created_at, updated_at = existing_row
                
                logger.info("existing_prototype_found",
                           user_id=str(current_user["id"]),
                           product_id=request.product_id,
                           provider=request.provider,
                           mockup_id=str(existing_id),
                           status=project_status)
                
                # Return existing prototype
                return {
                    "id": str(existing_id),
                    "provider": request.provider,
                    "project_url": project_url or "",
                    "image_url": image_url or "",
                    "thumbnail_url": thumbnail_url or "",
                    "v0_chat_id": v0_chat_id,
                    "v0_project_id": v0_project_id,
                    "project_status": project_status or "unknown",
                    "is_existing": True,
                    "created_at": created_at.isoformat() if created_at else None,
                    "updated_at": updated_at.isoformat() if updated_at else None,
                    "metadata": metadata if metadata else {}
                }
        
        # Load user-specific API keys
        user_keys = await load_user_api_keys_from_db(db, str(current_user["id"]))
        
        # For create-project, we only create/get project, no prompt enhancement needed yet
        # Prompt will be used in submit-chat endpoint
        
        # Import json for metadata serialization
        import json
        
        # Create/get project using appropriate agent
        if request.provider == "v0":
            # Prioritize user's API key over global settings
            v0_key = user_keys.get("v0")
            key_source = "user_database"
            if not v0_key:
                v0_key = settings.v0_api_key
                key_source = "global_settings"
            
            if not v0_key:
                raise HTTPException(status_code=400, detail="V0 API key is not configured. Please configure it in Settings.")
            
            # Use AgnoV0Agent to get or create project (ONLY project, no chat submission)
            try:
                from backend.main import agno_enabled
                if agno_enabled:
                    from backend.agents.agno_v0_agent import AgnoV0Agent
                    agno_v0_agent = AgnoV0Agent()
                    agno_v0_agent.set_v0_api_key(v0_key.strip())
                    
                    # Call get_or_create_v0_project - returns projectId immediately
                    result = await agno_v0_agent.get_or_create_v0_project(
                        v0_api_key=v0_key.strip(),
                        user_id=str(current_user["id"]),
                        product_id=request.product_id,
                        db=db,
                        create_new=request.create_new
                    )
                    
                    # Store projectId in database
                    # Check if record exists first, then insert or update
                    try:
                        # First check if a record exists
                        check_query = text("""
                            SELECT id, v0_project_id
                            FROM design_mockups
                            WHERE product_id = :product_id 
                              AND user_id = :user_id 
                              AND provider = 'v0'
                              AND (phase_submission_id = :phase_submission_id OR (:phase_submission_id IS NULL AND phase_submission_id IS NULL))
                            ORDER BY created_at DESC
                            LIMIT 1
                        """)
                        check_result = await db.execute(check_query, {
                            "product_id": request.product_id,
                            "user_id": str(current_user["id"]),
                            "phase_submission_id": request.phase_submission_id
                        })
                        existing_row = check_result.fetchone()
                        
                        if existing_row:
                            # Update existing record
                            existing_id, existing_v0_project_id = existing_row
                            update_query = text("""
                                UPDATE design_mockups
                                SET v0_project_id = COALESCE(:v0_project_id, v0_project_id),
                                    project_status = COALESCE(:project_status, project_status),
                                    metadata = COALESCE(CAST(:metadata AS jsonb), metadata),
                                    updated_at = now()
                                WHERE id = :id
                            """)
                            await db.execute(update_query, {
                                "id": existing_id,
                                "v0_project_id": result.get("projectId"),
                                "project_status": "in_progress",
                                "metadata": json.dumps({"project_created": True, "project_url": result.get("project_url")})
                            })
                            logger.info("v0_project_updated", 
                                       product_id=request.product_id,
                                       user_id=str(current_user["id"]),
                                       v0_project_id=result.get("projectId"),
                                       existing_id=str(existing_id))
                        else:
                            # Insert new record
                            insert_query = text("""
                                INSERT INTO design_mockups 
                                (product_id, phase_submission_id, user_id, provider, prompt, 
                                 v0_project_id, project_status, metadata)
                                VALUES (:product_id, :phase_submission_id, :user_id, :provider, :prompt, 
                                        :v0_project_id, 'in_progress', CAST(:metadata AS jsonb))
                                RETURNING id
                            """)
                            insert_result = await db.execute(insert_query, {
                                "product_id": request.product_id,
                                "phase_submission_id": request.phase_submission_id,
                                "user_id": str(current_user["id"]),
                                "provider": "v0",
                                "prompt": request.prompt or "",
                                "v0_project_id": result.get("projectId"),
                                "metadata": json.dumps({"project_created": True, "project_url": result.get("project_url")})
                            })
                            logger.info("v0_project_stored", 
                                       product_id=request.product_id,
                                       user_id=str(current_user["id"]),
                                       v0_project_id=result.get("projectId"))
                        
                        await db.commit()
                    except Exception as db_error:
                        logger.warning("failed_to_store_project", 
                                     error=str(db_error),
                                     product_id=request.product_id,
                                     user_id=str(current_user["id"]))
                        await db.rollback()
                    
                    return {
                        "id": None,  # Will be set after chat submission
                        "provider": "v0",
                        "projectId": result.get("projectId"),
                        "v0_project_id": result.get("projectId"),
                        "project_url": result.get("project_url"),
                        "project_status": "in_progress",
                        "is_existing": result.get("existing", False),
                        "message": f"Project {'found' if result.get('existing') else 'created'}. Use /submit-chat to submit your prompt."
                    }
                else:
                    raise HTTPException(status_code=500, detail="Agno framework is required for V0 project creation")
            except ValueError as e:
                error_msg = str(e)
                if "401" in error_msg or "invalid" in error_msg.lower() or "unauthorized" in error_msg.lower():
                    raise HTTPException(status_code=401, detail=f"V0 API authentication error: {error_msg}")
                else:
                    raise HTTPException(status_code=500, detail=f"V0 API error: {error_msg}")
            except Exception as e:
                logger.error("v0_project_creation_error", error=str(e), user_id=str(current_user["id"]))
                raise HTTPException(status_code=500, detail=f"V0 API error: {str(e)}")
        elif request.provider == "lovable":
            # Lovable doesn't use API keys - it uses Build with URL feature
            # Based on: https://docs.lovable.dev/integrations/build-with-url
            try:
                from backend.agents.agno_lovable_agent import AgnoLovableAgent
                agno_lovable_agent = AgnoLovableAgent()
                
                # Extract image URLs from context if available
                image_urls = None
                if request.context:
                    # Check if there are any image URLs in the context
                    if isinstance(request.context, dict):
                        image_urls = request.context.get("image_urls") or request.context.get("images")
                        if isinstance(image_urls, str):
                            image_urls = [image_urls]
                
                # Generate Lovable link using Build with URL API
                result = agno_lovable_agent.generate_lovable_link(
                    lovable_prompt=enhanced_prompt,
                    image_urls=image_urls
                )
                
                # Add additional metadata for consistency with V0 response format
                result["prompt"] = enhanced_prompt
                result["user_id"] = str(current_user["id"])
                result["product_id"] = request.product_id
                result["provider"] = "lovable"
                
                logger.info("lovable_link_created", 
                           user_id=str(current_user["id"]),
                           product_id=request.product_id,
                           prompt_length=len(enhanced_prompt))
            except Exception as e:
                logger.error("lovable_link_creation_error", error=str(e), user_id=str(current_user["id"]))
                raise HTTPException(status_code=500, detail=f"Lovable link generation error: {str(e)}")
        else:
            raise HTTPException(status_code=400, detail="Invalid provider. Use 'v0' or 'lovable'")
        
        # Save project to database with V0 tracking fields
        try:
            import json
            
            # Extract V0-specific fields
            # V0 API uses projectId (camelCase) in responses, but we store as v0_project_id in DB
            v0_chat_id = result.get("chat_id") if request.provider == "v0" else None
            v0_project_id = result.get("projectId") or result.get("project_id") if request.provider == "v0" else None  # Prefer projectId (camelCase)
            project_status = "in_progress"  # Will be updated when polling completes
            
            # Determine project status from result
            if result.get("error"):
                project_status = "failed"
            elif result.get("project_url") or result.get("demo_url") or result.get("web_url"):
                project_status = "completed"
            elif v0_chat_id:
                project_status = "in_progress"  # Will poll for completion
            
            image_url = result.get("image_url") or result.get("thumbnail_url") or ""
            thumbnail_url = result.get("thumbnail_url") or image_url
            project_url = result.get("project_url") or result.get("demo_url") or result.get("web_url") or result.get("url") or ""
            
            metadata_json = json.dumps({
                "enhanced_prompt": enhanced_prompt,
                "original_prompt": request.prompt,
                "use_multi_agent": request.use_multi_agent,
                "chat_id": v0_chat_id,
                "project_id": v0_project_id,
                **result
            })
            
            # Check if columns exist (for backward compatibility)
            try:
                insert_query = text("""
                    INSERT INTO design_mockups 
                    (product_id, phase_submission_id, user_id, provider, prompt, 
                     image_url, thumbnail_url, project_url, v0_chat_id, v0_project_id, 
                     project_status, metadata)
                    VALUES (:product_id, :phase_submission_id, :user_id, :provider, :prompt, 
                            :image_url, :thumbnail_url, :project_url, :v0_chat_id, :v0_project_id, 
                            :project_status, CAST(:metadata AS jsonb))
                    RETURNING id, created_at
                """)
                
                insert_result = await db.execute(insert_query, {
                    "product_id": request.product_id,
                    "phase_submission_id": request.phase_submission_id,
                    "user_id": str(current_user["id"]),
                    "provider": request.provider,
                    "prompt": enhanced_prompt,
                    "image_url": image_url,
                    "thumbnail_url": thumbnail_url,
                    "project_url": project_url,
                    "v0_chat_id": v0_chat_id,
                    "v0_project_id": v0_project_id,
                    "project_status": project_status,
                    "metadata": metadata_json
                })
            except Exception as col_error:
                # Fallback if new columns don't exist yet (backward compatibility)
                if "column" in str(col_error).lower() and ("v0_chat_id" in str(col_error) or "project_status" in str(col_error)):
                    logger.warning("v0_tracking_columns_not_found", error=str(col_error))
                    insert_query = text("""
                        INSERT INTO design_mockups 
                        (product_id, phase_submission_id, user_id, provider, prompt, 
                         image_url, thumbnail_url, project_url, metadata)
                        VALUES (:product_id, :phase_submission_id, :user_id, :provider, :prompt, 
                                :image_url, :thumbnail_url, :project_url, CAST(:metadata AS jsonb))
                        RETURNING id, created_at
                    """)
                    
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
                else:
                    raise
            
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
            "v0_chat_id": v0_chat_id,
            "v0_project_id": v0_project_id,  # Database field (snake_case)
            "projectId": v0_project_id,  # V0 API format (camelCase) for frontend
            "project_status": project_status,
            "code": result.get("code", ""),
            "enhanced_prompt": enhanced_prompt,
            "original_prompt": request.prompt,
            "is_existing": False,
            "metadata": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("error_creating_design_project", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check-status/{product_id}")
async def check_v0_project_status(
    product_id: str,
    projectId: Optional[str] = None,  # Optional: if provided, use directly instead of looking up from database
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Check status of V0 project.
    
    Can be called in two ways:
    1. With projectId query parameter: Checks status directly using V0 API (no database lookup needed)
    2. Without projectId: Looks up projectId from database using product_id, then checks V0 API
    
    Can be called multiple times (for "Check Status" button).
    Returns latest chat status from the project.
    """
    try:
        from backend.services.api_key_loader import load_user_api_keys_from_db
        from sqlalchemy import text
        
        v0_project_id = None
        v0_chat_id = None
        current_status = None
        current_url = None
        
        # If projectId is provided directly, use it (V0 API doesn't know about product_id)
        if projectId:
            logger.info("check_status_using_projectId", 
                       product_id=product_id,
                       projectId=projectId,
                       user_id=str(current_user["id"]),
                       message="Using projectId directly from query parameter")
            v0_project_id = projectId
            # Try to get additional info from database if available, but don't require it
            try:
                query_by_project = text("""
                    SELECT v0_chat_id, project_status, project_url
                    FROM design_mockups
                    WHERE v0_project_id = :v0_project_id 
                      AND provider = 'v0'
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                result_by_project = await db.execute(query_by_project, {
                    "v0_project_id": projectId
                })
                row_by_project = result_by_project.fetchone()
                if row_by_project:
                    v0_chat_id, current_status, current_url = row_by_project
            except Exception as db_lookup_error:
                logger.debug("check_status_db_lookup_optional", 
                           error=str(db_lookup_error),
                           message="Optional database lookup failed, continuing with direct V0 API call")
        else:
            # Get project_id from database (original behavior)
            # First try with user_id filter, then without (for shared products or cross-user access)
            query = text("""
                SELECT v0_project_id, v0_chat_id, project_status, project_url
                FROM design_mockups
                WHERE product_id = :product_id 
                  AND user_id = :user_id 
                  AND provider = 'v0'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            result = await db.execute(query, {
                "product_id": product_id,
                "user_id": str(current_user["id"])
            })
            row = result.fetchone()
            
            # If not found with user_id filter, try without user_id filter (for shared products)
            if not row:
                logger.info("check_status_no_user_match", 
                           product_id=product_id, 
                           user_id=str(current_user["id"]),
                           message="No record found with user_id filter, trying without user_id")
                query_no_user = text("""
                    SELECT v0_project_id, v0_chat_id, project_status, project_url
                    FROM design_mockups
                    WHERE product_id = :product_id 
                      AND provider = 'v0'
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                result_no_user = await db.execute(query_no_user, {
                    "product_id": product_id
                })
                row = result_no_user.fetchone()
            
            if not row:
                logger.warning("check_status_no_record", 
                              product_id=product_id, 
                              user_id=str(current_user["id"]),
                              message="No V0 project record found in database")
                raise HTTPException(
                    status_code=404, 
                    detail=f"No V0 project found for product_id: {product_id}. Please provide projectId query parameter or create a project first using /api/design/create-project"
                )
            
            v0_project_id, v0_chat_id, current_status, current_url = row
            
            # If v0_project_id is NULL but we have a project_url, try to extract project_id from URL
            # This handles cases where old records might have project_id stored in the URL
            if not v0_project_id and current_url:
                # Check if current_url is a project URL (not a chat URL)
                if "/project/" in current_url:
                    # Extract project ID from project URL: https://v0.dev/project/{project_id} or https://v0.app/project/{project_id}
                    extracted_project_id = current_url.split("/project/")[-1].split("?")[0].split("#")[0]
                    if extracted_project_id:
                        logger.info("check_status_extracted_project_id_from_url",
                                  product_id=product_id,
                                  extracted_project_id=extracted_project_id,
                                  original_url=current_url)
                        v0_project_id = extracted_project_id
                        # Update the database to store project_id in the correct field
                        try:
                            update_project_id_query = text("""
                                UPDATE design_mockups
                                SET v0_project_id = :v0_project_id
                                WHERE product_id = :product_id 
                                  AND user_id = :user_id 
                                  AND provider = 'v0'
                                  AND v0_project_id IS NULL
                                ORDER BY created_at DESC
                                LIMIT 1
                            """)
                            await db.execute(update_project_id_query, {
                                "product_id": product_id,
                                "user_id": str(current_user["id"]),
                                "v0_project_id": extracted_project_id
                            })
                            await db.commit()
                            logger.info("check_status_updated_project_id_in_db",
                                      product_id=product_id,
                                      v0_project_id=extracted_project_id)
                        except Exception as update_error:
                            logger.warning("check_status_failed_to_update_project_id",
                                         error=str(update_error))
                            await db.rollback()
                elif "/chat/" in current_url:
                    # If it's a chat URL, we can't extract project_id directly from the slug
                    # The slug is not the actual chat ID that the API expects
                    logger.error("check_status_chat_url_instead_of_project_id",
                               product_id=product_id,
                               chat_url=current_url,
                               message="project_url contains chat URL instead of project URL - cannot extract project_id from chat slug")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid project URL format: {current_url}. "
                               f"Chat URLs cannot be used to check project status. "
                               f"Please provide projectId query parameter or create a new project. "
                               f"Project URLs should be in format: https://v0.dev/project/{{project_id}}"
                    )
            
            if not v0_project_id:
                logger.warning("check_status_no_project_id", 
                              product_id=product_id, 
                              user_id=str(current_user["id"]),
                              v0_chat_id=v0_chat_id,
                              current_url=current_url,
                              message="Record found but v0_project_id is NULL and could not be extracted from URL")
                raise HTTPException(
                    status_code=404, 
                    detail="No V0 project_id found in database. Please provide projectId query parameter or create a project first using /api/design/create-project"
                )
        
        # Load user's V0 API key
        user_keys = await load_user_api_keys_from_db(db, str(current_user["id"]))
        v0_key = user_keys.get("v0") or settings.v0_api_key
        
        if not v0_key:
            raise HTTPException(status_code=400, detail="V0 API key is not configured")
        
        # Use AgnoV0Agent to check status
        from backend.main import agno_enabled
        if agno_enabled:
            from backend.agents.agno_v0_agent import AgnoV0Agent
            agno_v0_agent = AgnoV0Agent()
            agno_v0_agent.set_v0_api_key(v0_key.strip())
            
            status_result = await agno_v0_agent.check_v0_project_status(
                project_id=v0_project_id,
                v0_api_key=v0_key.strip(),
                user_id=str(current_user["id"]),
                product_id=product_id
            )
        else:
            # Fallback - basic status check
            status_result = {
                "project_id": v0_project_id,
                "chat_id": v0_chat_id,
                "project_status": current_status or "unknown",
                "project_url": current_url,
                "is_complete": current_status == "completed"
            }
        
        # Update database with latest status
        if status_result.get("project_status") and status_result.get("project_status") != current_status:
            try:
                update_query = text("""
                    UPDATE design_mockups
                    SET project_status = :status,
                        project_url = :project_url,
                        v0_chat_id = COALESCE(:chat_id, v0_chat_id),
                        updated_at = now()
                    WHERE product_id = :product_id 
                      AND user_id = :user_id 
                      AND provider = 'v0'
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                await db.execute(update_query, {
                    "product_id": product_id,
                    "user_id": str(current_user["id"]),
                    "status": status_result.get("project_status"),
                    "project_url": status_result.get("project_url"),
                    "chat_id": status_result.get("chat_id")
                })
                await db.commit()
            except Exception as update_error:
                logger.warning("failed_to_update_status_in_db", error=str(update_error))
        
        return {
            "projectId": v0_project_id,  # Use projectId (camelCase) to match V0 API format
            "project_id": v0_project_id,  # Keep for backward compatibility
            "chat_id": status_result.get("chat_id"),
            "project_status": status_result.get("project_status"),
            "project_url": status_result.get("project_url"),
            "web_url": status_result.get("web_url"),
            "demo_url": status_result.get("demo_url"),
            "is_complete": status_result.get("is_complete", False),
            "can_submit_new": status_result.get("is_complete", False)  # Can submit new changes only if completed
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("error_checking_v0_status", error=str(e), product_id=product_id)
        raise HTTPException(status_code=500, detail=f"Error checking status: {str(e)}")


@router.post("/submit-chat")
async def submit_chat_to_project(
    request: SubmitChatRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a chat/prompt to an existing V0 project. Does NOT wait for response.
    This is Step 2 - chat submission only, returns immediately.
    
    After this, use /check-status/{product_id} to check prototype status.
    A background task will also periodically check status.
    """
    try:
        from backend.services.api_key_loader import load_user_api_keys_from_db
        import json
        
        if request.provider == "v0":
            if not request.project_id:
                raise HTTPException(status_code=400, detail="project_id is required for V0")
            
            # Load user's V0 API key
            user_keys = await load_user_api_keys_from_db(db, str(current_user["id"]))
            v0_key = user_keys.get("v0") or settings.v0_api_key
            
            if not v0_key:
                raise HTTPException(status_code=400, detail="V0 API key is not configured")
            
            # Use AgnoV0Agent to submit chat
            try:
                from backend.main import agno_enabled
                if agno_enabled:
                    from backend.agents.agno_v0_agent import AgnoV0Agent
                    agno_v0_agent = AgnoV0Agent()
                    agno_v0_agent.set_v0_api_key(v0_key.strip())
                    
                    # Submit chat - returns immediately, doesn't wait
                    result = await agno_v0_agent.submit_chat_to_v0_project(
                        v0_prompt=request.prompt,
                        project_id=request.project_id,
                        v0_api_key=v0_key.strip(),
                        user_id=str(current_user["id"]),
                        product_id=request.product_id
                    )
                    
                    # Update database with chat submission
                    try:
                        update_query = text("""
                            UPDATE design_mockups
                            SET v0_chat_id = COALESCE(:chat_id, v0_chat_id),
                                prompt = :prompt,
                                project_status = 'in_progress',
                                updated_at = now()
                            WHERE product_id = :product_id 
                              AND user_id = :user_id 
                              AND provider = 'v0'
                              AND v0_project_id = :project_id
                            ORDER BY created_at DESC
                            LIMIT 1
                        """)
                        await db.execute(update_query, {
                            "product_id": request.product_id,
                            "user_id": str(current_user["id"]),
                            "project_id": request.project_id,
                            "chat_id": result.get("chat_id"),
                            "prompt": request.prompt
                        })
                        await db.commit()
                    except Exception as db_error:
                        logger.warning("failed_to_update_chat", error=str(db_error))
                        await db.rollback()
                    
                    # Start background task to check status periodically
                    background_tasks.add_task(
                        check_v0_status_background,
                        v0_key.strip(),
                        request.project_id,
                        request.product_id,
                        str(current_user["id"]),
                        db
                    )
                    
                    return {
                        "success": True,
                        "chat_id": result.get("chat_id"),
                        "projectId": result.get("projectId"),
                        "project_id": result.get("project_id"),
                        "message": "Chat submitted successfully. Use /check-status to monitor progress.",
                        "status": "submitted"
                    }
                else:
                    raise HTTPException(status_code=500, detail="Agno framework is required")
            except ValueError as e:
                error_msg = str(e)
                if "401" in error_msg or "unauthorized" in error_msg.lower():
                    raise HTTPException(status_code=401, detail=f"V0 API authentication error: {error_msg}")
                else:
                    raise HTTPException(status_code=500, detail=f"V0 API error: {error_msg}")
            except Exception as e:
                logger.error("v0_chat_submission_error", error=str(e), user_id=str(current_user["id"]))
                raise HTTPException(status_code=500, detail=f"V0 API error: {str(e)}")
        elif request.provider == "lovable":
            # Lovable doesn't use projects - handle differently
            raise HTTPException(status_code=400, detail="Lovable doesn't use submit-chat endpoint. Use generate-mockup directly.")
        else:
            raise HTTPException(status_code=400, detail="Invalid provider. Use 'v0' or 'lovable'")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("submit_chat_error", error=str(e), user_id=str(current_user["id"]))
        raise HTTPException(status_code=500, detail=f"Error submitting chat: {str(e)}")


async def check_v0_status_background(
    api_key: str,
    project_id: str,
    product_id: str,
    user_id: str,
    db: AsyncSession
):
    """
    Background task to periodically check V0 project status.
    Runs every 30 seconds for up to 15 minutes (30 checks).
    """
    import asyncio
    from backend.agents.agno_v0_agent import AgnoV0Agent
    
    max_checks = 30  # 15 minutes (30 * 30 seconds)
    check_interval = 30  # 30 seconds
    
    agno_v0_agent = AgnoV0Agent()
    agno_v0_agent.set_v0_api_key(api_key)
    
    for check_num in range(1, max_checks + 1):
        try:
            await asyncio.sleep(check_interval)
            
            # Check status
            status_result = await agno_v0_agent.check_v0_project_status(
                project_id=project_id,
                v0_api_key=api_key,
                user_id=user_id,
                product_id=product_id
            )
            
            # Update database
            if status_result.get("project_status"):
                try:
                    update_query = text("""
                        UPDATE design_mockups
                        SET project_status = :status,
                            project_url = :project_url,
                            v0_chat_id = COALESCE(:chat_id, v0_chat_id),
                            updated_at = now()
                        WHERE product_id = :product_id 
                          AND user_id = :user_id 
                          AND provider = 'v0'
                          AND v0_project_id = :project_id
                        ORDER BY created_at DESC
                        LIMIT 1
                    """)
                    await db.execute(update_query, {
                        "product_id": product_id,
                        "user_id": user_id,
                        "project_id": project_id,
                        "status": status_result.get("project_status"),
                        "project_url": status_result.get("project_url"),
                        "chat_id": status_result.get("chat_id")
                    })
                    await db.commit()
                except Exception as db_error:
                    logger.warning("background_status_update_failed", error=str(db_error))
                    await db.rollback()
            
            # If completed, stop checking
            if status_result.get("is_complete"):
                logger.info("v0_prototype_completed",
                           project_id=project_id,
                           product_id=product_id,
                           check_num=check_num)
                break
                
        except Exception as e:
            logger.error("background_status_check_failed",
                        project_id=project_id,
                        check_num=check_num,
                        error=str(e))
            # Continue checking even if one check fails
    
    logger.info("background_status_checking_completed",
               project_id=project_id,
               product_id=product_id,
               total_checks=check_num)


