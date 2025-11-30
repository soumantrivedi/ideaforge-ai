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
            model_tier="fast",  # Use fast model for V0 prompt generation
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
        Clean V0 prompt by removing instructional headers/footers and notes.
        Removes text like "Below is a V0-ready prompt...", "Notes:", instructions, etc.
        """
        if not prompt:
            return prompt
        
        lines = prompt.split('\n')
        cleaned_lines = []
        skip_until_content = True
        in_notes_section = False
        
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
            "notes:",
            "note:",
            "instructions:",
            "this prompt follows",
            "guidelines:",
            "if you want",
            "tell me and i will",
            "encoded version",
            "url-encoded",
        ]
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Check for notes section start
            if "notes:" in line_lower or "note:" in line_lower:
                in_notes_section = True
                continue
            
            # Skip everything in notes section
            if in_notes_section:
                # Check if we've exited notes section (new major section)
                if line_lower and (line_lower.startswith("#") or len(line_lower) > 50):
                    # Might be a new section, but be conservative
                    if not any(note_word in line_lower for note_word in ["note", "instruction", "guideline", "follow"]):
                        in_notes_section = False
                else:
                    continue
            
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

    async def get_or_create_v0_project(
        self,
        v0_api_key: Optional[str] = None,
        user_id: Optional[str] = None,
        product_id: Optional[str] = None,
        db: Optional[Any] = None,
        create_new: bool = False
    ) -> Dict[str, Any]:
        """
        Get or create a V0 project. Returns projectId immediately.
        This is Step 1 of the workflow - project creation only, no chat submission.
        
        Returns:
            - projectId: The project ID (camelCase)
            - project_id: The project ID (snake_case for backward compatibility)
            - project_url: Project URL if available
            - existing: Whether project was existing or newly created
        """
        api_key = v0_api_key or self.v0_api_key or settings.v0_api_key
        if not api_key:
            raise ValueError("V0 API key is required")
        
        # Check database for existing project_id
        existing_project_id = None
        if db and product_id and user_id and not create_new:
            try:
                from sqlalchemy import text
                project_query = text("""
                    SELECT v0_project_id
                    FROM design_mockups
                    WHERE product_id = :product_id 
                      AND user_id = :user_id 
                      AND provider = 'v0'
                      AND v0_project_id IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                project_result = await db.execute(project_query, {
                    "product_id": product_id,
                    "user_id": user_id
                })
                project_row = project_result.fetchone()
                if project_row:
                    existing_project_id = project_row[0]
                    logger.info("existing_project_id_found",
                               user_id=user_id,
                               product_id=product_id,
                               project_id=existing_project_id)
            except Exception as db_error:
                logger.warning("database_check_failed",
                             error=str(db_error),
                             user_id=user_id,
                             product_id=product_id)
        
        # Get or create project
        project_id = existing_project_id
        project_name = f"V0 Project {product_id[:8] if product_id else 'Default'}"
        project_url = None
        
        try:
            if not project_id:
                async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                    
                    # List existing projects
                    try:
                        projects_resp = await client.get(
                            "https://api.v0.dev/v1/projects",
                            headers=headers
                        )
                        
                        if projects_resp.status_code == 200:
                            projects_data = projects_resp.json()
                            projects = projects_data.get("data", [])
                            
                            if isinstance(projects, list) and len(projects) > 0:
                                # Priority 1: Exact name match
                                for p in projects:
                                    if p.get("name") == project_name:
                                        project_id = p.get("id")
                                        project_url = p.get("webUrl") or p.get("web_url")
                                        break
                                
                                # Priority 2: Similar name
                                if not project_id:
                                    for p in projects:
                                        if project_name.lower() in p.get("name", "").lower():
                                            project_id = p.get("id")
                                            project_url = p.get("webUrl") or p.get("web_url")
                                            break
                                
                                # Priority 3: Most recent
                                if not project_id:
                                    project = projects[0]
                                    project_id = project.get("id")
                                    project_url = project.get("webUrl") or project.get("web_url")
                    except Exception as list_error:
                        logger.warning("v0_project_list_failed", error=str(list_error))
                    
                    # Create new project if none found
                    if not project_id:
                        create_resp = await client.post(
                            "https://api.v0.dev/v1/projects",
                            headers=headers,
                            json={"name": project_name}
                        )
                        
                        if create_resp.status_code in [200, 201]:
                            create_result = create_resp.json()
                            project_id = create_result.get("id")
                            project_url = create_result.get("webUrl") or create_result.get("web_url")
                        else:
                            raise ValueError(f"Failed to create project: {create_resp.status_code}")
                
                if not project_id:
                    raise ValueError("Failed to get or create V0 project")
            
            return {
                "projectId": project_id,
                "project_id": project_id,
                "project_url": project_url,
                "existing": existing_project_id is not None,
                "project_name": project_name
            }
        except Exception as e:
            logger.error("v0_project_creation_failed", error=str(e))
            raise ValueError(f"Failed to get or create V0 project: {str(e)}")
    
    async def submit_chat_to_v0_project(
        self,
        v0_prompt: str,
        project_id: str,
        v0_api_key: Optional[str] = None,
        user_id: Optional[str] = None,
        product_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit a chat to an existing V0 project. Does NOT wait for response.
        This is Step 2 of the workflow - chat submission only.
        
        Returns immediately with projectId, even if chat times out.
        """
        api_key = v0_api_key or self.v0_api_key or settings.v0_api_key
        if not api_key:
            raise ValueError("V0 API key is required")
        
        if not project_id:
            raise ValueError("project_id is required")
        
        # Submit chat with SHORT timeout (10 seconds) - don't wait for generation
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            try:
                response = await client.post(
                    "https://api.v0.dev/v1/chats",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "message": v0_prompt,
                        "model": "v0-1.5-md",
                        "scope": "mckinsey",
                        "projectId": project_id  # camelCase
                    }
                )
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    chat_id = result.get("id") or result.get("chat_id")
                    returned_projectId = result.get("projectId")
                    
                    return {
                        "success": True,
                        "chat_id": chat_id,
                        "projectId": returned_projectId or project_id,
                        "project_id": returned_projectId or project_id,
                        "immediate": True
                    }
                else:
                    raise ValueError(f"Failed to submit chat: {response.status_code}")
                    
            except httpx.TimeoutException:
                # Timeout is EXPECTED - return immediately with projectId
                logger.info("v0_chat_submission_timeout",
                           user_id=user_id,
                           product_id=product_id,
                           projectId=project_id,
                           note="Timeout expected - chat submitted in background")
                return {
                    "success": True,
                    "chat_id": None,  # Will be found via project polling
                    "projectId": project_id,
                    "project_id": project_id,
                    "immediate": False,
                    "note": "Chat submitted but timed out - will appear in project later"
                }
            except Exception as e:
                logger.error("v0_chat_submission_failed", error=str(e))
                raise ValueError(f"Failed to submit chat: {str(e)}")

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
        
        # Step 1: Check for existing project_id in database (unless create_new=True)
        # If project_id exists, we'll submit new chat to same project (not create new project)
        existing_project_id = None
        if db and product_id and user_id and not create_new:
            try:
                from sqlalchemy import text
                project_query = text("""
                    SELECT v0_project_id
                    FROM design_mockups
                    WHERE product_id = :product_id 
                      AND user_id = :user_id 
                      AND provider = 'v0'
                      AND v0_project_id IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                
                project_result = await db.execute(project_query, {
                    "product_id": product_id,
                    "user_id": user_id
                })
                project_row = project_result.fetchone()
                
                if project_row:
                    existing_project_id = project_row[0]
                    logger.info("existing_project_id_found",
                               user_id=user_id,
                               product_id=product_id,
                               project_id=existing_project_id,
                               note="Will submit new chat to existing project")
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
        
        # Step 2: Get or create project (IMMEDIATE - < 1 second)
        # This MUST happen BEFORE submitting chat - matches test workflow
        project_id = existing_project_id
        project_name = f"V0 Project {product_id[:8] if product_id else 'Default'}"
        project_url = None
        
        try:
            # If no existing project_id, get or create one using the same logic as test workflow
            if not project_id:
                async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                    
                    # Step 1: List existing projects - ALWAYS reuse if any exist (matches test workflow)
                    try:
                        projects_resp = await client.get(
                            "https://api.v0.dev/v1/projects",
                            headers=headers
                        )
                        
                        if projects_resp.status_code == 200:
                            projects_data = projects_resp.json()
                            projects = projects_data.get("data", [])
                            
                            if isinstance(projects, list) and len(projects) > 0:
                                logger.info("v0_projects_found",
                                           user_id=user_id,
                                           product_id=product_id,
                                           count=len(projects))
                                
                                # Priority 1: Look for project with exact matching name
                                for p in projects:
                                    if p.get("name") == project_name:
                                        project_id = p.get("id")
                                        project_url = p.get("webUrl") or p.get("web_url")
                                        logger.info("v0_project_found_exact_name",
                                                   user_id=user_id,
                                                   product_id=product_id,
                                                   project_id=project_id,
                                                   name=project_name)
                                        break
                                
                                # Priority 2: Look for projects containing the name
                                if not project_id:
                                    for p in projects:
                                        if project_name.lower() in p.get("name", "").lower():
                                            project_id = p.get("id")
                                            project_url = p.get("webUrl") or p.get("web_url")
                                            logger.info("v0_project_found_similar_name",
                                                       user_id=user_id,
                                                       product_id=product_id,
                                                       project_id=project_id,
                                                       name=p.get("name"))
                                            break
                                
                                # Priority 3: ALWAYS reuse the most recent project (first in list)
                                if not project_id:
                                    project = projects[0]
                                    project_id = project.get("id")
                                    project_url = project.get("webUrl") or project.get("web_url")
                                    logger.info("v0_project_reusing_most_recent",
                                               user_id=user_id,
                                               product_id=product_id,
                                               project_id=project_id,
                                               name=project.get("name", "Unnamed"))
                    except Exception as list_error:
                        logger.warning("v0_project_list_failed",
                                     error=str(list_error),
                                     user_id=user_id,
                                     product_id=product_id)
                    
                    # Step 2: Create new project ONLY if NO projects exist at all
                    if not project_id:
                        logger.info("v0_creating_new_project",
                                   user_id=user_id,
                                   product_id=product_id,
                                   name=project_name)
                        create_resp = await client.post(
                            "https://api.v0.dev/v1/projects",
                            headers=headers,
                            json={"name": project_name}
                        )
                        
                        if create_resp.status_code in [200, 201]:
                            create_result = create_resp.json()
                            project_id = create_result.get("id")
                            project_url = create_result.get("webUrl") or create_result.get("web_url")
                            logger.info("v0_project_created",
                                       user_id=user_id,
                                       product_id=product_id,
                                       project_id=project_id,
                                       project_url=project_url)
                        else:
                            error_text = create_resp.text[:200] if create_resp.text else "No error text"
                            logger.error("v0_project_creation_failed",
                                       user_id=user_id,
                                       product_id=product_id,
                                       status_code=create_resp.status_code,
                                       error=error_text)
                            raise ValueError(f"Failed to create V0 project: {create_resp.status_code} - {error_text}")
                
                if not project_id:
                    raise ValueError("Failed to get or create V0 project - no project_id returned")
            else:
                logger.info("v0_using_existing_project_id",
                           user_id=user_id,
                           product_id=product_id,
                           project_id=project_id)
        
        except Exception as project_error:
            logger.error("project_creation_failed",
                         error=str(project_error),
                         user_id=user_id,
                         product_id=product_id,
                         error_type=type(project_error).__name__)
            raise ValueError(f"Failed to get or create V0 project: {str(project_error)}")
        
        # Step 3: Submit chat to project with SHORT timeout (returns immediately)
        # Use projectId (camelCase) parameter to associate with project
        # This happens AFTER project is created/retrieved (matches test workflow)
        if not project_id:
            raise ValueError("Cannot submit chat: project_id is required but was not created/retrieved")
        
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:  # Short timeout
            try:
                # Log the request
                logger.info("v0_api_request",
                           user_id=user_id,
                           endpoint="https://api.v0.dev/v1/chats",
                           prompt_length=len(v0_prompt) if v0_prompt else 0,
                           project_id=project_id,
                           key_source=key_source)
                
                # Submit chat with projectId parameter (camelCase)
                chat_payload = {
                    "message": v0_prompt,
                    "model": "v0-1.5-md",
                    "scope": "mckinsey"
                }
                
                if project_id:
                    chat_payload["projectId"] = project_id  # camelCase - correct format
                
                response = await client.post(
                    "https://api.v0.dev/v1/chats",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json=chat_payload
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
                returned_project_id = result.get("projectId")  # camelCase in response
                
                # Use returned project_id if available, otherwise use the one we created/got
                final_project_id = returned_project_id or project_id
                
                web_url = result.get("webUrl") or result.get("web_url") or result.get("url")
                demo_url = result.get("demo") or result.get("demoUrl") or result.get("demo_url")
                files = result.get("files", [])
                code = "\n\n".join([f.get("content", "") for f in files if f.get("content")])
                
                if not chat_id:
                    logger.error("v0_api_no_chat_id",
                               user_id=user_id,
                               response_keys=list(result.keys()) if isinstance(result, dict) else "not_dict")
                    raise ValueError("No chat_id returned from V0 API. Response may be incomplete.")
                
                # If chat was created in different project, try to assign it
                if returned_project_id and returned_project_id != project_id and project_id:
                    try:
                        assign_resp = await client.patch(
                            f"https://api.v0.dev/v1/chats/{chat_id}",
                            headers={
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json"
                            },
                            json={"projectId": project_id}
                        )
                        if assign_resp.status_code in [200, 201, 204]:
                            final_project_id = project_id
                            logger.info("v0_chat_assigned_to_project",
                                       chat_id=chat_id,
                                       project_id=project_id)
                    except:
                        pass  # Assignment failed, use returned project_id
                
                logger.info("v0_chat_created",
                           chat_id=chat_id,
                           user_id=user_id,
                           product_id=product_id,
                           project_id=final_project_id,
                           has_demo=bool(demo_url),
                           has_web_url=bool(web_url),
                           num_files=len(files))
                
                # Return IMMEDIATELY with project_id - no waiting for generation
                initial_project_url = demo_url or web_url or (f"https://v0.dev/chat/{chat_id}" if chat_id else None)
                initial_status = "completed" if (demo_url or web_url or files) else "in_progress"
                project_name_result = result.get("name") or f"V0 Project {final_project_id[:8] if final_project_id else 'N/A'}"
                
                return {
                    "chat_id": chat_id,
                    "projectId": final_project_id,  # Use projectId (camelCase) to match V0 API format
                    "project_id": final_project_id,  # Keep for backward compatibility
                    "project_url": initial_project_url,
                    "web_url": web_url,
                    "demo_url": demo_url,
                    "project_name": project_name_result,
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
                        "workflow": "project_based_immediate",
                        "key_source": key_source
                    }
                }
                
            except httpx.TimeoutException as timeout_error:
                # Timeout is EXPECTED - V0 API generates in background
                # Return immediately with project_id - user can check status later
                # CRITICAL: project_id MUST be set at this point (created in Step 2)
                if not project_id:
                    logger.error("v0_timeout_without_project_id",
                               user_id=user_id,
                               product_id=product_id,
                               error="Project creation failed but timeout occurred - this should not happen")
                    raise ValueError("V0 project creation failed. Cannot submit chat without project_id.")
                
                logger.info("v0_chat_submission_timeout",
                           user_id=user_id,
                           product_id=product_id,
                           projectId=project_id,
                           note="Timeout expected - chat is being generated in background, projectId is available")
                
                # Return immediately with projectId - chat will appear in project
                return {
                    "chat_id": None,  # Will be found via project polling
                    "projectId": project_id,  # Use projectId (camelCase) - MUST be set (created in Step 2)
                    "project_id": project_id,  # Keep for backward compatibility
                    "project_url": None,
                    "web_url": None,
                    "demo_url": None,
                    "project_name": project_name,
                    "code": None,
                    "files": [],
                    "prompt": v0_prompt,
                    "image_url": None,
                    "thumbnail_url": None,
                    "project_status": "in_progress",
                    "is_existing": False,
                    "metadata": {
                        "api_version": "v1",
                        "model_used": "v0-1.5-md",
                        "workflow": "project_based_timeout",
                        "key_source": key_source,
                        "note": "Chat submitted but timed out - check status later via projectId"
                    }
                }
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
    
    async def check_v0_project_status(
        self,
        project_id: str,
        v0_api_key: Optional[str] = None,
        user_id: Optional[str] = None,
        product_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check status of V0 project by getting latest chat and checking its status.
        This is used for the "Check Status" button - can be called multiple times.
        
        Returns:
            - projectId: The project ID (camelCase to match V0 API format)
            - project_id: The project ID (snake_case for backward compatibility)
            - chat_id: Latest chat ID in the project
            - project_status: "completed", "in_progress", or "unknown"
            - project_url: URL to the prototype (if completed)
            - web_url: Web URL
            - demo_url: Demo URL
            - is_complete: Boolean indicating if prototype is ready
        """
        api_key = v0_api_key or self.v0_api_key or settings.v0_api_key
        
        if not api_key:
            raise ValueError("V0 API key is not configured")
        
        if not project_id:
            raise ValueError("project_id is required")
        
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            try:
                # Step 1: Get project to find latest chat
                project_resp = await client.get(
                    f"https://api.v0.dev/v1/projects/{project_id}",
                    headers=headers
                )
                
                if project_resp.status_code == 404:
                    return {
                        "projectId": project_id,  # Use projectId (camelCase)
                        "project_id": project_id,  # Keep for backward compatibility
                        "chat_id": None,
                        "project_status": "unknown",
                        "project_url": None,
                        "web_url": None,
                        "demo_url": None,
                        "is_complete": False,
                        "error": "Project not found"
                    }
                
                if project_resp.status_code != 200:
                    raise ValueError(f"Failed to get project: {project_resp.status_code}")
                
                project_data = project_resp.json()
                chats = project_data.get("chats", [])
                
                if not chats or len(chats) == 0:
                    return {
                        "projectId": project_id,  # Use projectId (camelCase)
                        "project_id": project_id,  # Keep for backward compatibility
                        "chat_id": None,
                        "project_status": "pending",
                        "project_url": None,
                        "web_url": None,
                        "demo_url": None,
                        "is_complete": False,
                        "note": "No chats found in project"
                    }
                
                # Get latest chat (first in list, usually sorted by date)
                latest_chat = chats[0]
                chat_id = latest_chat.get("id")
                
                if not chat_id:
                    return {
                        "projectId": project_id,  # Use projectId (camelCase)
                        "project_id": project_id,  # Keep for backward compatibility
                        "chat_id": None,
                        "project_status": "unknown",
                        "project_url": None,
                        "web_url": None,
                        "demo_url": None,
                        "is_complete": False,
                        "error": "No chat ID found"
                    }
                
                # Step 2: Check chat status
                chat_resp = await client.get(
                    f"https://api.v0.dev/v1/chats/{chat_id}",
                    headers=headers
                )
                
                if chat_resp.status_code != 200:
                    return {
                        "projectId": project_id,  # Use projectId (camelCase)
                        "project_id": project_id,  # Keep for backward compatibility
                        "chat_id": chat_id,
                        "project_status": "unknown",
                        "project_url": None,
                        "web_url": None,
                        "demo_url": None,
                        "is_complete": False,
                        "error": f"Failed to get chat: {chat_resp.status_code}"
                    }
                
                chat_data = chat_resp.json()
                web_url = chat_data.get("webUrl") or chat_data.get("web_url")
                demo_url = chat_data.get("demo") or chat_data.get("demoUrl") or chat_data.get("demo_url")
                files = chat_data.get("files", [])
                
                # Determine status
                is_complete = bool(demo_url or web_url or (files and len(files) > 0))
                project_status = "completed" if is_complete else "in_progress"
                project_url = demo_url or web_url or (f"https://v0.dev/chat/{chat_id}" if chat_id else None)
                
                logger.info("v0_status_checked",
                           projectId=project_id,
                           chat_id=chat_id,
                           status=project_status,
                           is_complete=is_complete,
                           user_id=user_id,
                           product_id=product_id)
                
                return {
                    "projectId": project_id,  # Use projectId (camelCase) to match V0 API format
                    "project_id": project_id,  # Keep for backward compatibility
                    "chat_id": chat_id,
                    "project_status": project_status,
                    "project_url": project_url,
                    "web_url": web_url,
                    "demo_url": demo_url,
                    "is_complete": is_complete,
                    "num_files": len(files),
                    "files": files
                }
                
            except httpx.RequestError as e:
                logger.error("v0_status_check_error",
                           projectId=project_id,
                           error=str(e),
                           user_id=user_id)
                raise ValueError(f"V0 API connection error: {str(e)}")
            except Exception as e:
                logger.error("v0_status_check_error",
                           projectId=project_id,
                           error=str(e),
                           error_type=type(e).__name__,
                           user_id=user_id)
                raise ValueError(f"V0 status check error: {str(e)}")
    
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
                # V0 project URLs already contain the correct path (e.g., ideation/design)
                final_project_url = final_demo_url or final_web_url or (f"https://v0.dev/chat/{chat_id}" if chat_id else None)
                
                final_status = "completed"
                
                logger.info("v0_background_polling_completed",
                           chat_id=chat_id,
                           mockup_id=mockup_id,
                           project_url=final_project_url,
                           poll_count=poll_result.get("poll_count", 0),
                           elapsed_seconds=poll_result.get("elapsed_seconds", 0))
            else:
                # V0 project URLs already contain the correct path (e.g., ideation/design)
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

