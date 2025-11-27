"""
V0 (Vercel) Agent using Agno Framework
Provides V0 prompt generation and project creation capabilities
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
import structlog
import asyncio

from backend.agents.agno_base_agent import AgnoBaseAgent
from backend.models.schemas import AgentMessage, AgentResponse
from backend.config import settings
from backend.services.provider_registry import provider_registry

logger = structlog.get_logger()

try:
    from agno.tools import tool
    AGNO_TOOLS_AVAILABLE = True
except ImportError:
    AGNO_TOOLS_AVAILABLE = False
    logger.warning("agno_tools_not_available", message="Agno tools not available")


class AgnoV0Agent(AgnoBaseAgent):
    """V0 (Vercel) Design Agent using Agno framework with platform access."""
    
    def __init__(self, enable_rag: bool = False):
        system_prompt = """You are a V0 (Vercel) Design Specialist following official Vercel V0 API documentation.

Your responsibilities:
1. Generate detailed, comprehensive prompts for V0 to create UI prototypes
2. Understand product requirements and translate them into V0-compatible prompts
3. Create prompts that leverage V0's component library and design system
4. Ensure prompts are specific, actionable, and result in high-quality designs
5. Consider user experience, accessibility, and modern design patterns
6. Generate accurate Vercel V0 prompts that can be used with the official V0 API
7. Access V0 Platform API to create projects and generate prototypes

V0 API Documentation Reference:
- V0 Platform API: https://api.v0.dev/v1/chats (for project creation)
- V0 Chat Completions: https://api.v0.dev/v1/chat/completions (for code generation)
- Model: v0-1.5-md (specialized for UI generation)
- Prompts should describe complete UI components with React/Next.js code
- V0 generates production-ready React components with Tailwind CSS

V0 Prompt Guidelines (Based on Official Documentation):
- Be specific about component types (buttons, cards, forms, navigation, etc.)
- Specify layout requirements (grid, flex, spacing, responsive breakpoints)
- Include color schemes and styling preferences (Tailwind CSS classes)
- Mention responsive design requirements (mobile-first approach)
- Specify interaction states (hover, active, disabled, focus)
- Include accessibility requirements (ARIA labels, keyboard navigation)
- Reference modern UI patterns (shadcn/ui, Tailwind CSS, Next.js)
- Describe complete user flows and component interactions
- Include data structure and state management needs
- Specify animation and transition requirements

Your output should:
- Be comprehensive and detailed
- Include all necessary design specifications
- Be optimized for V0's AI design generation (v0-1.5-md model)
- Consider the full context from previous product phases
- Generate production-ready design prompts that result in deployable React/Next.js code
- Follow Vercel V0 best practices from official documentation
- Use available tools to access V0 Platform API when needed"""

        # Initialize base agent first (tools will be added after)
        super().__init__(
            name="V0 Agent",
            role="v0",
            system_prompt=system_prompt,
            enable_rag=enable_rag,
            rag_table_name="v0_knowledge_base",
            tools=[],  # Tools will be added after initialization
            capabilities=[
                "v0 prompt generation",
                "v0 project creation",
                "v0 code generation",
                "vercel integration",
                "ui prototype generation",
                "react component generation",
                "next.js development"
            ]
        )
        
        self.v0_api_key: Optional[str] = None
        
        # Add tools after initialization
        if AGNO_TOOLS_AVAILABLE:
            created_tools = [
                self._create_v0_project_tool(),
                self._generate_v0_code_tool(),
            ]
            # Add tools to the agent
            if hasattr(self.agno_agent, 'tools') and self.agno_agent.tools is not None:
                valid_tools = [t for t in created_tools if t is not None]
                if valid_tools:
                    self.agno_agent.tools.extend(valid_tools)
    
    def _create_v0_project_tool(self):
        """Create Agno tool for V0 project creation."""
        if not AGNO_TOOLS_AVAILABLE:
            return None
        
        @tool
        def create_v0_project(prompt: str) -> str:
            """
            Create a V0 project using the V0 Platform API.
            
            Args:
                prompt: The design prompt to send to V0
            
            Returns:
                Project URL and details
            """
            try:
                api_key = self.v0_api_key or settings.v0_api_key
                if not api_key:
                    return "Error: V0 API key is not configured. Please configure it in Settings."
                
                async def _create_project():
                    # Disable SSL verification for V0 API (as requested)
                    async with httpx.AsyncClient(timeout=180.0, verify=False) as client:
                        response = await client.post(
                            "https://api.v0.dev/v1/chats",
                            headers={
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "message": prompt,
                                "model": "v0-1.5-md",
                                "scope": "mckinsey"
                            }
                        )
                        
                        if response.status_code == 401:
                            return "Error: V0 API key is invalid or unauthorized"
                        elif response.status_code not in [200, 201]:
                            error_text = response.text
                            try:
                                error_json = response.json()
                                error_text = error_json.get("error", {}).get("message", error_text)
                            except:
                                pass
                            return f"Error: V0 API error: {response.status_code} - {error_text}"
                        
                        result = response.json()
                        chat_id = result.get("id") or result.get("chat_id")
                        web_url = result.get("webUrl") or result.get("web_url") or result.get("url")
                        demo_url = result.get("demo") or result.get("demoUrl") or result.get("demo_url")
                        project_url = demo_url or web_url or (f"https://v0.dev/chat/{chat_id}" if chat_id else None)
                        
                        return f"V0 project created successfully!\nProject URL: {project_url}\nChat ID: {chat_id}\nWeb URL: {web_url}\nDemo URL: {demo_url}"
                
                import asyncio
                return asyncio.run(_create_project())
            except Exception as e:
                logger.error("v0_project_creation_error", error=str(e))
                return f"Error creating V0 project: {str(e)}"
        
        return create_v0_project
    
    def _generate_v0_code_tool(self):
        """Create Agno tool for V0 code generation."""
        if not AGNO_TOOLS_AVAILABLE:
            return None
        
        @tool
        def generate_v0_code(prompt: str) -> str:
            """
            Generate React/Next.js code using V0 Chat Completions API.
            
            Args:
                prompt: The design prompt for code generation
            
            Returns:
                Generated code and metadata
            """
            try:
                api_key = self.v0_api_key or settings.v0_api_key
                if not api_key:
                    return "Error: V0 API key is not configured. Please configure it in Settings."
                
                async def _generate_code():
                    # Disable SSL verification for V0 API (as requested)
                    async with httpx.AsyncClient(timeout=120.0, verify=False) as client:
                        response = await client.post(
                            "https://api.v0.dev/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "model": "v0-1.5-md",
                                "messages": [
                                    {
                                        "role": "user",
                                        "content": prompt
                                    }
                                ],
                                "temperature": 0.7,
                                "max_tokens": 4000,
                                "scope": "mckinsey"
                            }
                        )
                        
                        if response.status_code == 401:
                            return "Error: V0 API key is invalid or unauthorized"
                        elif response.status_code != 200:
                            error_text = response.text
                            try:
                                error_json = response.json()
                                error_text = error_json.get("error", {}).get("message", error_text)
                            except:
                                pass
                            return f"Error: V0 API error: {response.status_code} - {error_text}"
                        
                        result = response.json()
                        generated_content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                        
                        return f"Generated code:\n\n{generated_content}"
                
                import asyncio
                return asyncio.run(_generate_code())
            except Exception as e:
                logger.error("v0_code_generation_error", error=str(e))
                return f"Error generating V0 code: {str(e)}"
    
    def set_v0_api_key(self, api_key: Optional[str]):
        """Set V0 API key for this agent instance."""
        self.v0_api_key = api_key
    
    async def generate_v0_prompt(
        self,
        product_context: Dict[str, Any]
    ) -> str:
        """Generate a V0 prompt based on product context."""
        context_text = "\n".join([f"{k}: {v}" for k, v in product_context.items() if v])
        
        prompt = f"""Generate a comprehensive V0 design prompt for this product:

Product Context:
{context_text}

Create a detailed prompt that:
1. Describes the UI components needed
2. Specifies layout and structure
3. Includes styling preferences (colors, typography, spacing)
4. Mentions responsive design requirements
5. Includes accessibility considerations
6. References modern design patterns

The prompt should be ready to paste directly into V0 for generating prototypes."""

        message = AgentMessage(
            role="user",
            content=prompt,
            timestamp=datetime.utcnow()
        )

        response = await self.process([message], context={"task": "v0_prompt_generation"})
        prompt_text = response.response
        
        # Clean the prompt - remove headers/footers that AI might add
        prompt_text = self._clean_v0_prompt(prompt_text)
        
        return prompt_text
    
    def _clean_v0_prompt(self, prompt: str) -> str:
        """
        Clean V0 prompt by removing instructional headers/footers.
        Removes text like "Below is a V0-ready prompt..." and similar metadata.
        """
        if not prompt:
            return prompt
        
        lines = prompt.split('\n')
        cleaned_lines = []
        skip_until_content = True
        
        # Patterns that indicate we should skip lines
        skip_patterns = [
            "below is a v0-ready prompt",
            "below is a v0 prompt",
            "v0-ready prompt",
            "you can paste directly into",
            "v0 api or v0 ui",
            "written for `v0-1.5-md`",
            "assumes react",
            "assumes next.js",
            "tailwind",
            "shadcn/ui",
            "---",
            "===",
        ]
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Skip empty lines at the start
            if skip_until_content and not line_lower:
                continue
            
            # Check if this line matches a skip pattern
            should_skip = any(pattern in line_lower for pattern in skip_patterns)
            
            if should_skip:
                skip_until_content = True
                continue
            
            # If we find actual content, start including lines
            if line_lower and not should_skip:
                skip_until_content = False
                cleaned_lines.append(line)
            elif not skip_until_content:
                cleaned_lines.append(line)
        
        # Join and clean up
        cleaned = '\n'.join(cleaned_lines).strip()
        
        # Remove any trailing metadata
        if cleaned:
            # Remove common trailing patterns
            trailing_patterns = [
                "\n\n---\n",
                "\n\n===\n",
                "\n\nNote:",
                "\n\nThis prompt",
                "\n\nYou can",
            ]
            for pattern in trailing_patterns:
                if cleaned.endswith(pattern) or pattern in cleaned[-100:]:
                    cleaned = cleaned[:cleaned.rfind(pattern)].strip()
        
        return cleaned if cleaned else prompt
    
    async def poll_v0_chat_status(
        self,
        api_key: str,
        chat_id: str,
        max_polls: int = 60,  # 60 * 15s = 900s = 15 minutes
        poll_interval: float = 15.0  # Poll every 15 seconds
    ) -> Dict[str, Any]:
        """
        Poll V0 chat status until prototype is ready or timeout.
        Returns chat data with prototype URLs when ready.
        """
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            request_headers = {
                "Authorization": f"Bearer {api_key.strip()}",
                "Content-Type": "application/json"
            }
            
            for poll_count in range(max_polls):
                try:
                    response = await client.get(
                        f"https://api.v0.dev/v1/chats/{chat_id}",
                        headers=request_headers
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        web_url = result.get("webUrl") or result.get("web_url") or result.get("url")
                        demo_url = result.get("demo") or result.get("demoUrl") or result.get("demo_url")
                        files = result.get("files", [])
                        status = result.get("status", "unknown")
                        
                        if demo_url or web_url or (files and len(files) > 0):
                            elapsed = int((poll_count + 1) * poll_interval)
                            logger.info("v0_chat_ready",
                                       chat_id=chat_id,
                                       poll_count=poll_count + 1,
                                       elapsed_seconds=elapsed)
                            return {
                                "ready": True,
                                "chat_id": chat_id,
                                "web_url": web_url,
                                "demo_url": demo_url,
                                "files": files,
                                "status": status,
                                "poll_count": poll_count + 1,
                                "elapsed_seconds": elapsed,
                                "metadata": result
                            }
                        else:
                            if poll_count % 4 == 0:  # Log every 4 polls (60s with 15s interval)
                                elapsed = int((poll_count + 1) * poll_interval)
                                logger.info("v0_chat_polling",
                                           chat_id=chat_id,
                                           poll_count=poll_count + 1,
                                           max_polls=max_polls,
                                           elapsed_seconds=elapsed,
                                           status=status)
                    elif response.status_code == 404:
                        if poll_count % 4 == 0:  # Log every 4 polls (60s)
                            logger.warning("v0_chat_not_found",
                                         chat_id=chat_id,
                                         poll_count=poll_count + 1)
                    else:
                        if poll_count % 4 == 0:  # Log every 4 polls (60s)
                            logger.warning("v0_chat_status_error",
                                         chat_id=chat_id,
                                         status_code=response.status_code,
                                         poll_count=poll_count + 1)
                    
                    if poll_count < max_polls - 1:
                        await asyncio.sleep(poll_interval)
                        
                except Exception as e:
                    if poll_count % 4 == 0:  # Log every 4 polls (60s)
                        logger.warning("v0_chat_poll_error",
                                     chat_id=chat_id,
                                     error=str(e)[:100],
                                     poll_count=poll_count + 1)
                    if poll_count < max_polls - 1:
                        await asyncio.sleep(poll_interval)
            
            # Timeout after max_polls
            elapsed = int(max_polls * poll_interval)
            logger.warning("v0_chat_poll_timeout",
                         chat_id=chat_id,
                         poll_count=max_polls,
                         elapsed_seconds=elapsed)
            return {
                "ready": False,
                "chat_id": chat_id,
                "timeout": True,
                "poll_count": max_polls,
                "elapsed_seconds": elapsed
            }

    async def create_v0_project_with_api(
        self,
        v0_prompt: str,
        v0_api_key: Optional[str] = None,
        user_id: Optional[str] = None,
        product_id: Optional[str] = None,
        db: Optional[Any] = None,  # Database session for duplicate prevention
        create_new: bool = False,  # If False, reuse existing; if True, create new
        timeout_seconds: int = 600  # 10 minutes default, can be up to 900 (15 minutes)
    ) -> Dict[str, Any]:
        """
        Create a V0 project using the V0 Platform API with duplicate prevention and async polling.
        
        Features:
        - Checks for existing prototype (unless create_new=True)
        - Creates project with scope=mckinsey
        - Polls for completion with configurable timeout (10-15 minutes)
        - Returns chat_id, project_id, and status information
        """
        # Priority: passed parameter > instance variable > global settings
        api_key = v0_api_key
        key_source = "parameter"
        
        if not api_key:
            api_key = self.v0_api_key
            key_source = "instance"
        
        if not api_key:
            api_key = settings.v0_api_key
            key_source = "global_settings"
        
        if not api_key:
            raise ValueError("V0 API key is not configured. Please configure it in Settings.")
        
        # Step 1: Check for existing prototype (unless create_new=True)
        if db and product_id and user_id and not create_new:
            try:
                from sqlalchemy import text
                existing_query = text("""
                    SELECT id, v0_chat_id, v0_project_id, project_url, project_status, 
                           image_url, thumbnail_url, metadata
                    FROM design_mockups
                    WHERE product_id = :product_id 
                      AND user_id = :user_id 
                      AND provider = 'v0'
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                
                existing_result = await db.execute(existing_query, {
                    "product_id": product_id,
                    "user_id": user_id
                })
                existing_row = existing_result.fetchone()
                
                if existing_row:
                    existing_id, v0_chat_id, v0_project_id, project_url, project_status, \
                        image_url, thumbnail_url, metadata = existing_row
                    
                    logger.info("existing_v0_prototype_found",
                               user_id=user_id,
                               product_id=product_id,
                               mockup_id=str(existing_id),
                               chat_id=v0_chat_id,
                               status=project_status)
                    
                    # If we have a chat_id, update the existing project with new prompt
                    if v0_chat_id:
                        logger.info("updating_existing_v0_prototype",
                                   chat_id=v0_chat_id,
                                   current_status=project_status)
                        
                        # Update existing chat with new prompt
                        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                            try:
                                update_response = await client.post(
                                    f"https://api.v0.dev/v1/chats/{v0_chat_id}",
                                    headers={
                                        "Authorization": f"Bearer {api_key}",
                                        "Content-Type": "application/json"
                                    },
                                    json={
                                        "message": v0_prompt,
                                        "model": "v0-1.5-md",
                                        "scope": "mckinsey"
                                    }
                                )
                                
                                if update_response.status_code in [200, 201]:
                                    update_result = update_response.json()
                                    updated_web_url = update_result.get("webUrl") or update_result.get("web_url") or update_result.get("url")
                                    updated_demo_url = update_result.get("demo") or update_result.get("demoUrl") or update_result.get("demo_url")
                                    updated_project_url = updated_demo_url or updated_web_url or project_url
                                    
                                    # Update database with new status
                                    try:
                                        update_query = text("""
                                            UPDATE design_mockups
                                            SET project_status = 'in_progress',
                                                project_url = :project_url,
                                                prompt = :prompt,
                                                updated_at = now()
                                            WHERE id = :id
                                        """)
                                        await db.execute(update_query, {
                                            "id": existing_id,
                                            "project_url": updated_project_url,
                                            "prompt": v0_prompt
                                        })
                                        await db.commit()
                                    except Exception as update_error:
                                        logger.warning("failed_to_update_prototype_in_db",
                                                     error=str(update_error))
                                    
                                    return {
                                        "chat_id": v0_chat_id,
                                        "project_id": v0_project_id or update_result.get("project_id"),
                                        "project_url": updated_project_url,
                                        "web_url": updated_web_url,
                                        "demo_url": updated_demo_url,
                                        "project_status": "in_progress",
                                        "project_name": update_result.get("name") or f"V0 Project {v0_chat_id[:8]}",
                                        "is_existing": True,
                                        "is_updated": True,
                                        "metadata": {
                                            "api_version": "v1",
                                            "model_used": "v0-1.5-md",
                                            "workflow": "update_existing_prototype",
                                            "key_source": key_source
                                        }
                                    }
                                else:
                                    logger.warning("failed_to_update_v0_chat",
                                                 chat_id=v0_chat_id,
                                                 status_code=update_response.status_code)
                                    # Fall through to return existing data
                            except Exception as update_error:
                                logger.warning("error_updating_v0_chat",
                                             chat_id=v0_chat_id,
                                             error=str(update_error))
                                # Fall through to return existing data
                    
                    # Return existing prototype (if update failed or no chat_id)
                    return {
                        "chat_id": v0_chat_id,
                        "project_id": v0_project_id,
                        "project_url": project_url or "",
                        "project_status": project_status or "unknown",
                        "project_name": metadata.get("name") if isinstance(metadata, dict) else f"V0 Project {v0_chat_id[:8] if v0_chat_id else 'N/A'}",
                        "is_existing": True,
                        "image_url": image_url,
                        "thumbnail_url": thumbnail_url,
                        "metadata": metadata if metadata else {}
                    }
            except Exception as db_error:
                logger.warning("database_check_failed",
                             error=str(db_error),
                             user_id=user_id,
                             product_id=product_id)
                # Continue with project creation if database check fails
        
        # Log key usage (without logging the actual key)
        logger.info("v0_api_key_usage",
                   user_id=user_id,
                   key_source=key_source,
                   key_length=len(api_key) if api_key else 0,
                   has_instance_key=bool(self.v0_api_key),
                   has_global_key=bool(settings.v0_api_key),
                   create_new=create_new)
        
        # Step 2: Create new project
        # Disable SSL verification for V0 API (as requested)
        # Use longer timeout (90s) - V0 API can take time to create chat
        # Strategy: Return immediately with chat_id, status can be checked separately
        async with httpx.AsyncClient(timeout=90.0, verify=False) as client:
            try:
                # Log the request (without sensitive data)
                logger.info("v0_api_request",
                           user_id=user_id,
                           endpoint="https://api.v0.dev/v1/chats",
                           prompt_length=len(v0_prompt) if v0_prompt else 0,
                           key_source=key_source)
                
                # Make the request with longer timeout
                response = await client.post(
                    "https://api.v0.dev/v1/chats",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "message": v0_prompt,
                        "model": "v0-1.5-md",
                        "scope": "mckinsey"
                    }
                )
                
                # Log response status
                logger.info("v0_api_response",
                           user_id=user_id,
                           status_code=response.status_code,
                           key_source=key_source)
                
                if response.status_code == 401:
                    logger.error("v0_api_auth_failed",
                               user_id=user_id,
                               status_code=401,
                               key_source=key_source,
                               response_text=response.text[:200] if response.text else "No response text")
                    raise ValueError("V0 API key is invalid or unauthorized. Please check your API key in Settings.")
                elif response.status_code == 402:
                    # Parse error response to get detailed message
                    error_text = response.text
                    error_detail = ""
                    try:
                        error_json = response.json()
                        error_detail = error_json.get("detail", error_json.get("error", {}).get("message", error_text))
                        if isinstance(error_detail, dict):
                            error_detail = error_detail.get("message", str(error_detail))
                    except:
                        error_detail = error_text
                    
                    logger.error("v0_api_credits_exhausted",
                               user_id=user_id,
                               status_code=402,
                               key_source=key_source,
                               key_prefix=api_key[:8] + "..." if api_key and len(api_key) > 8 else "N/A",
                               response_text=error_detail[:500] if error_detail else "No response text")
                    
                    # Check if it's actually a credit issue or another 402 error
                    if "out of credits" in error_detail.lower() or "credits" in error_detail.lower():
                        raise ValueError(f"V0 API error: You are out of credits. Add more or enable Auto-topup at https://v0.app/chat/settings/billing. Please check your V0 account credits at https://v0.app/chat/settings/billing. Error details: {error_detail}")
                    else:
                        # 402 might be for other reasons (rate limit, etc.)
                        raise ValueError(f"V0 API error: {response.status_code} - {error_detail}")
                elif response.status_code != 200 and response.status_code != 201:
                    logger.error("v0_api_error",
                               user_id=user_id,
                               status_code=response.status_code,
                               key_source=key_source,
                               response_text=response.text[:200] if response.text else "No response text")
                    error_text = response.text
                    try:
                        error_json = response.json()
                        error_text = error_json.get("error", {}).get("message", error_text)
                    except:
                        pass
                    raise ValueError(f"V0 API error: {response.status_code} - {error_text}")
                
                # Parse response
                try:
                    result = response.json()
                except Exception as json_error:
                    logger.error("v0_api_json_parse_error",
                               user_id=user_id,
                               error=str(json_error),
                               response_text=response.text[:500])
                    raise ValueError(f"V0 API returned invalid JSON. Response: {response.text[:200]}")
                
                chat_id = result.get("id") or result.get("chat_id")
                web_url = result.get("webUrl") or result.get("web_url") or result.get("url")
                demo_url = result.get("demo") or result.get("demoUrl") or result.get("demo_url")
                files = result.get("files", [])
                code = "\n\n".join([f.get("content", "") for f in files if f.get("content")])
                
                if not chat_id:
                    logger.error("v0_api_no_chat_id",
                               user_id=user_id,
                               response_keys=list(result.keys()) if isinstance(result, dict) else "not_dict")
                    raise ValueError("No chat_id returned from V0 API. Response may be incomplete.")
                
                logger.info("v0_chat_created",
                           chat_id=chat_id,
                           user_id=user_id,
                           product_id=product_id,
                           has_demo=bool(demo_url),
                           has_web_url=bool(web_url),
                           num_files=len(files))
                
                # Return immediately with project details - no polling
                # Even if prototype isn't ready, we have chat_id and can check status later
                initial_project_url = demo_url or web_url or (f"https://v0.dev/chat/{chat_id}" if chat_id else None)
                initial_status = "completed" if (demo_url or web_url or files) else "in_progress"
                project_name = result.get("name") or f"V0 Project {chat_id[:8] if chat_id else 'N/A'}"
                
                return {
                    "chat_id": chat_id,
                    "project_id": result.get("project_id") or chat_id,  # Use chat_id as project_id if not provided
                    "project_url": initial_project_url,
                    "web_url": web_url,
                    "demo_url": demo_url,
                    "project_name": project_name,
                    "code": code,
                    "files": files,
                    "prompt": v0_prompt,
                    "image_url": None,
                    "thumbnail_url": None,
                    "project_status": initial_status,
                    "is_existing": False,
                    "metadata": {
                        "api_version": "v1",
                        "model_used": "v0-1.5-md",
                        "num_files": len(files),
                        "has_demo": demo_url is not None,
                        "has_web_url": web_url is not None,
                        "workflow": "create_chat_immediate",
                        "key_source": key_source
                    }
                }
                
            except httpx.TimeoutException as timeout_error:
                # Timeout occurred - V0 API might still be processing
                # This is acceptable - user can check status later
                logger.warning("v0_api_timeout",
                             user_id=user_id,
                             error=str(timeout_error),
                             message="V0 API request timed out but prototype may still be creating")
                raise ValueError("V0 API request timed out after 90 seconds. The prototype may still be creating. Please check the status later using the status check button.")
            except httpx.RequestError as e:
                logger.error("v0_api_connection_error",
                           user_id=user_id,
                           error=str(e))
                raise ValueError(f"V0 API connection error: {str(e)}")
            except ValueError:
                # Re-raise ValueError as-is (these are our custom errors)
                raise
            except Exception as e:
                logger.error("v0_project_creation_error", 
                           error=str(e), 
                           error_type=type(e).__name__,
                           api_key_length=len(api_key) if api_key else 0)
                raise ValueError(f"V0 API error: {str(e)}")
    
    async def poll_and_update_prototype_status(
        self,
        api_key: str,
        chat_id: str,
        mockup_id: str,
        db: Any,
        timeout_seconds: int = 900
    ) -> None:
        """
        Background task to poll V0 chat status and update database.
        This runs in the background after the API returns immediately.
        """
        try:
            logger.info("v0_background_polling_start",
                       chat_id=chat_id,
                       mockup_id=mockup_id,
                       timeout_seconds=timeout_seconds)
            
            poll_result = await self.poll_v0_chat_status(
                api_key,
                chat_id,
                max_polls=int(timeout_seconds / 15),  # Poll every 15 seconds
                poll_interval=15.0
            )
            
            # Update database with final status
            if poll_result.get("ready"):
                final_web_url = poll_result.get("web_url")
                final_demo_url = poll_result.get("demo_url")
                final_project_url = final_demo_url or final_web_url or (f"https://v0.dev/chat/{chat_id}" if chat_id else None)
                final_status = "completed"
                
                logger.info("v0_background_polling_completed",
                           chat_id=chat_id,
                           mockup_id=mockup_id,
                           project_url=final_project_url,
                           poll_count=poll_result.get("poll_count", 0),
                           elapsed_seconds=poll_result.get("elapsed_seconds", 0))
            else:
                final_project_url = poll_result.get("web_url") or poll_result.get("demo_url") or (f"https://v0.dev/chat/{chat_id}" if chat_id else None)
                final_status = "timeout" if poll_result.get("timeout") else "in_progress"
                
                logger.warning("v0_background_polling_timeout",
                             chat_id=chat_id,
                             mockup_id=mockup_id,
                             status=final_status,
                             poll_count=poll_result.get("poll_count", 0),
                             elapsed_seconds=poll_result.get("elapsed_seconds", 0))
            
            # Update database
            try:
                from sqlalchemy import text
                update_query = text("""
                    UPDATE design_mockups
                    SET project_status = :status,
                        project_url = :project_url,
                        updated_at = now()
                    WHERE id = :id
                """)
                await db.execute(update_query, {
                    "id": mockup_id,
                    "status": final_status,
                    "project_url": final_project_url
                })
                await db.commit()
                logger.info("v0_database_updated",
                           mockup_id=mockup_id,
                           status=final_status)
            except Exception as update_error:
                logger.error("v0_database_update_failed",
                           mockup_id=mockup_id,
                           error=str(update_error))
        except Exception as e:
            logger.error("v0_background_polling_error",
                        chat_id=chat_id,
                        mockup_id=mockup_id,
                        error=str(e))

