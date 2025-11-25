"""
Lovable AI Agent using Agno Framework
Provides Lovable prompt generation and project creation capabilities
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
import structlog
import urllib.parse

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


class AgnoLovableAgent(AgnoBaseAgent):
    """Lovable AI Design Agent using Agno framework with platform access."""
    
    def __init__(self, enable_rag: bool = False):
        system_prompt = """You are a Lovable AI Design Specialist following official Lovable AI documentation.

Your responsibilities:
1. Generate detailed, comprehensive prompts for Lovable AI to create UI prototypes
2. Understand product requirements and translate them into Lovable-compatible prompts
3. Create prompts that leverage Lovable's component library and design system
4. Ensure prompts are specific, actionable, and result in high-quality designs
5. Consider user experience, accessibility, and modern design patterns
6. Generate accurate Lovable AI prompts that can be used with the official Lovable API
7. Access Lovable AI Platform API to create projects and generate prototypes

Lovable AI API Documentation Reference:
- Lovable AI API: https://api.lovable.dev/v1/generate
- Model: gpt-4-turbo (recommended for application generation)
- Supports thumbnail generation (multiple variations)
- Generates React/Next.js applications with Tailwind CSS
- Creates deployable web applications

Lovable Prompt Guidelines (Based on Official Documentation):
- Be specific about component types and layouts (React components)
- Specify styling requirements (Tailwind CSS classes, custom styles)
- Include responsive design breakpoints (mobile, tablet, desktop)
- Mention state management requirements (React hooks, context, state)
- Include accessibility features (ARIA labels, semantic HTML)
- Reference React/Next.js patterns (Server Components, Client Components)
- Specify data flow and component interactions
- Describe complete application structure (pages, components, layouts)
- Include API integration requirements
- Specify authentication and user management needs
- Describe database schema and data models
- Include routing and navigation structure

Your output should:
- Be comprehensive and detailed
- Include all necessary design specifications
- Be optimized for Lovable's AI design generation (gpt-4-turbo model)
- Consider the full context from previous product phases
- Generate production-ready design prompts that result in deployable React/Next.js applications
- Follow Lovable AI best practices from official documentation
- Ensure all requested features are achievable with Lovable AI capabilities
- Use available tools to access Lovable AI Platform API when needed"""

        # Initialize base agent first (tools will be added after)
        super().__init__(
            name="Lovable Agent",
            role="lovable",
            system_prompt=system_prompt,
            enable_rag=enable_rag,
            rag_table_name="lovable_knowledge_base",
            tools=[],  # Tools will be added after initialization
            capabilities=[
                "lovable prompt generation",
                "lovable project creation",
                "lovable thumbnail generation",
                "lovable integration",
                "ui prototype generation",
                "react application generation",
                "next.js development"
            ]
        )
        
        self.lovable_api_key: Optional[str] = None
        
        # Add tools after initialization
        if AGNO_TOOLS_AVAILABLE:
            created_tools = [
                self._create_lovable_project_tool(),
                self._generate_lovable_thumbnails_tool(),
            ]
            # Add tools to the agent
            if hasattr(self.agno_agent, 'tools') and self.agno_agent.tools is not None:
                valid_tools = [t for t in created_tools if t is not None]
                if valid_tools:
                    self.agno_agent.tools.extend(valid_tools)
    
    def _create_lovable_project_tool(self):
        """Create Agno tool for Lovable project creation."""
        if not AGNO_TOOLS_AVAILABLE:
            return None
        
        @tool
        def create_lovable_project(prompt: str, generate_thumbnails: bool = True) -> str:
            """
            Create a Lovable AI project using the Lovable Platform API.
            
            Args:
                prompt: The design prompt to send to Lovable
                generate_thumbnails: Whether to generate thumbnail previews
            
            Returns:
                Project URL and details
            """
            try:
                api_key = self.lovable_api_key or settings.lovable_api_key
                if not api_key:
                    return "Error: Lovable API key is not configured. Please configure it in Settings."
                
                async def _create_project():
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        response = await client.post(
                            "https://api.lovable.dev/v1/generate",
                            headers={
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "prompt": prompt,
                                "model": "gpt-4-turbo",
                                "temperature": 0.7,
                                "generate_thumbnails": generate_thumbnails,
                                "num_thumbnails": 3 if generate_thumbnails else 1
                            }
                        )
                        
                        if response.status_code == 401:
                            return "Error: Lovable API key is invalid or unauthorized"
                        elif response.status_code != 200:
                            error_text = response.text
                            try:
                                error_json = response.json()
                                error_text = error_json.get("error", {}).get("message", error_text)
                            except:
                                pass
                            return f"Error: Lovable API error: {response.status_code} - {error_text}"
                        
                        result = response.json()
                        project_id = result.get("project_id")
                        project_url = result.get("project_url") or result.get("url")
                        thumbnails = result.get("thumbnails", [])
                        
                        if not project_url and project_id:
                            project_url = f"https://lovable.dev/projects/{project_id}"
                        
                        return f"Lovable project created successfully!\nProject URL: {project_url}\nProject ID: {project_id}\nThumbnails: {len(thumbnails)} generated"
                
                import asyncio
                return asyncio.run(_create_project())
            except Exception as e:
                logger.error("lovable_project_creation_error", error=str(e))
                return f"Error creating Lovable project: {str(e)}"
    
    def _generate_lovable_thumbnails_tool(self):
        """Create Agno tool for Lovable thumbnail generation."""
        if not AGNO_TOOLS_AVAILABLE:
            return None
        
        @tool
        def generate_lovable_thumbnails(prompt: str, num_thumbnails: int = 3) -> str:
            """
            Generate multiple thumbnail previews for Lovable AI projects.
            
            Args:
                prompt: The design prompt
                num_thumbnails: Number of thumbnails to generate (default: 3)
            
            Returns:
                Thumbnail URLs and preview information
            """
            try:
                api_key = self.lovable_api_key or settings.lovable_api_key
                if not api_key:
                    return "Error: Lovable API key is not configured. Please configure it in Settings."
                
                async def _generate_thumbnails():
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        response = await client.post(
                            "https://api.lovable.dev/v1/generate",
                            headers={
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "prompt": prompt,
                                "model": "gpt-4-turbo",
                                "temperature": 0.7,
                                "generate_thumbnails": True,
                                "num_thumbnails": num_thumbnails
                            }
                        )
                        
                        if response.status_code == 401:
                            return "Error: Lovable API key is invalid or unauthorized"
                        elif response.status_code != 200:
                            error_text = response.text
                            try:
                                error_json = response.json()
                                error_text = error_json.get("error", {}).get("message", error_text)
                            except:
                                pass
                            return f"Error: Lovable API error: {response.status_code} - {error_text}"
                        
                        result = response.json()
                        thumbnails = result.get("thumbnails", [])
                        
                        thumbnail_info = "\n".join([
                            f"Thumbnail {i+1}: {thumb.get('url', 'N/A')}" 
                            for i, thumb in enumerate(thumbnails)
                        ])
                        
                        return f"Generated {len(thumbnails)} thumbnails:\n{thumbnail_info}"
                
                import asyncio
                return asyncio.run(_generate_thumbnails())
            except Exception as e:
                logger.error("lovable_thumbnail_generation_error", error=str(e))
                return f"Error generating Lovable thumbnails: {str(e)}"
    
    def set_lovable_api_key(self, api_key: Optional[str]):
        """Set Lovable API key for this agent instance."""
        self.lovable_api_key = api_key
    
    async def generate_lovable_prompt(
        self,
        product_context: Dict[str, Any]
    ) -> str:
        """Generate a Lovable prompt based on product context."""
        context_text = "\n".join([f"{k}: {v}" for k, v in product_context.items() if v])
        
        prompt = f"""Generate a comprehensive Lovable design prompt for this product:

Product Context:
{context_text}

Create a detailed prompt that:
1. Describes the React/Next.js components needed
2. Specifies layout and structure
3. Includes Tailwind CSS styling requirements
4. Mentions responsive design breakpoints
5. Includes state management needs
6. Includes accessibility considerations
7. References modern React patterns

The prompt should be ready to paste directly into Lovable for generating prototypes."""

        message = AgentMessage(
            role="user",
            content=prompt,
            timestamp=datetime.utcnow()
        )

        response = await self.process([message], context={"task": "lovable_prompt_generation"})
        return response.response
    
    async def create_lovable_project(
        self,
        lovable_prompt: str,
        lovable_api_key: Optional[str] = None,
        user_id: Optional[str] = None,
        product_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a Lovable AI project using the Lovable Platform API.
        This method directly accesses the Lovable platform.
        """
        api_key = lovable_api_key or self.lovable_api_key or settings.lovable_api_key
        
        if not api_key:
            raise ValueError("Lovable API key is not configured")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    "https://api.lovable.dev/v1/generate",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "prompt": lovable_prompt,
                        "model": "gpt-4-turbo",
                        "temperature": 0.7,
                        "generate_thumbnails": True,
                        "num_thumbnails": 3
                    }
                )
                
                if response.status_code == 401:
                    raise ValueError("Lovable API key is invalid or unauthorized")
                elif response.status_code != 200:
                    error_text = response.text
                    try:
                        error_json = response.json()
                        error_text = error_json.get("error", {}).get("message", error_text)
                    except:
                        pass
                    raise ValueError(f"Lovable API error: {response.status_code} - {error_text}")
                
                result = response.json()
                
                project_id = result.get("project_id")
                project_url = result.get("project_url") or result.get("url")
                thumbnails = result.get("thumbnails", [])
                code = result.get("code") or result.get("generated_code", "")
                
                if not project_url:
                    if project_id:
                        project_url = f"https://lovable.dev/projects/{project_id}"
                    else:
                        encoded_prompt = urllib.parse.quote(lovable_prompt)
                        project_url = f"https://lovable.dev/generate?prompt={encoded_prompt}"
                
                return {
                    "project_id": project_id,
                    "project_url": project_url,
                    "code": code,
                    "prompt": lovable_prompt,
                    "thumbnails": thumbnails,
                    "thumbnail_url": thumbnails[0] if thumbnails else None,
                    "image_url": thumbnails[0] if thumbnails else None,
                    "metadata": {
                        "api_version": "v1",
                        "model_used": "gpt-4-turbo",
                        "num_thumbnails": len(thumbnails),
                        "has_project": project_id is not None
                    }
                }
                
            except httpx.TimeoutException:
                raise ValueError("Lovable API request timed out. Please try again.")
            except httpx.RequestError as e:
                raise ValueError(f"Lovable API connection error: {str(e)}")
            except Exception as e:
                logger.error("lovable_api_error", error=str(e), api_key_length=len(api_key) if api_key else 0)
                raise ValueError(f"Lovable API error: {str(e)}")

