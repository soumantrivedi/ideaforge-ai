"""
V0 (Vercel) Agent using Agno Framework
Provides V0 prompt generation and project creation capabilities
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
import structlog

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
                                "model": "v0-1.5-md"
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
                                "max_tokens": 4000
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
        return response.response
    
    async def create_v0_project_with_api(
        self,
        v0_prompt: str,
        v0_api_key: Optional[str] = None,
        user_id: Optional[str] = None,
        product_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a V0 project using the V0 Platform API.
        This method directly accesses the V0 platform.
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
        
        # Log key usage (without logging the actual key)
        logger.info("v0_api_key_usage",
                   user_id=user_id,
                   key_source=key_source,
                   key_length=len(api_key) if api_key else 0,
                   has_instance_key=bool(self.v0_api_key),
                   has_global_key=bool(settings.v0_api_key))
        
        # Disable SSL verification for V0 API (as requested)
        async with httpx.AsyncClient(timeout=180.0, verify=False) as client:
            try:
                # Log the request (without sensitive data)
                logger.info("v0_api_request",
                           user_id=user_id,
                           endpoint="https://api.v0.dev/v1/chats",
                           prompt_length=len(v0_prompt) if v0_prompt else 0,
                           key_source=key_source)
                
                response = await client.post(
                    "https://api.v0.dev/v1/chats",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "message": v0_prompt,
                        "model": "v0-1.5-md"
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
                    logger.error("v0_api_credits_exhausted",
                               user_id=user_id,
                               status_code=402,
                               key_source=key_source,
                               response_text=response.text[:200] if response.text else "No response text")
                    error_text = response.text
                    try:
                        error_json = response.json()
                        error_text = error_json.get("error", {}).get("message", error_text)
                    except:
                        pass
                    raise ValueError(f"V0 API error: {response.status_code} - {error_text}")
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
                
                result = response.json()
                
                chat_id = result.get("id") or result.get("chat_id")
                web_url = result.get("webUrl") or result.get("web_url") or result.get("url")
                demo_url = result.get("demo") or result.get("demoUrl") or result.get("demo_url")
                files = result.get("files", [])
                code = "\n\n".join([f.get("content", "") for f in files if f.get("content")])
                
                project_url = demo_url or web_url or (f"https://v0.dev/chat/{chat_id}" if chat_id else None)
                
                return {
                    "chat_id": chat_id,
                    "project_url": project_url,
                    "web_url": web_url,
                    "demo_url": demo_url,
                    "code": code,
                    "files": files,
                    "prompt": v0_prompt,
                    "image_url": None,
                    "thumbnail_url": None,
                    "metadata": {
                        "api_version": "v1",
                        "model_used": "v0-1.5-md",
                        "num_files": len(files),
                        "has_demo": demo_url is not None
                    }
                }
                
            except httpx.TimeoutException:
                raise ValueError("V0 API request timed out. Please try again.")
            except httpx.RequestError as e:
                raise ValueError(f"V0 API connection error: {str(e)}")
            except Exception as e:
                logger.error("v0_project_creation_error", error=str(e), api_key_length=len(api_key) if api_key else 0)
                raise ValueError(f"V0 API error: {str(e)}")

