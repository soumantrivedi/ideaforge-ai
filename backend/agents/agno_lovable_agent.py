"""
Lovable AI Agent using Agno Framework
Provides Lovable prompt generation and Lovable Link Generator integration
Uses Lovable Build with URL API: https://docs.lovable.dev/integrations/build-with-url
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
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
    """Lovable AI Design Agent using Agno framework with Lovable Link Generator."""
    
    def __init__(self, enable_rag: bool = False):
        system_prompt = """You are a Lovable AI Design Specialist following official Lovable AI documentation.

Your responsibilities:
1. Generate detailed, comprehensive prompts for Lovable AI to create UI prototypes
2. Understand product requirements and translate them into Lovable-compatible prompts
3. Create prompts that leverage Lovable's component library and design system
4. Ensure prompts are specific, actionable, and result in high-quality designs
5. Consider user experience, accessibility, and modern design patterns
6. Generate accurate Lovable AI prompts that can be used with the Lovable Link Generator

Lovable AI Documentation Reference:
- Lovable Link Generator: https://lovable.dev/links
- Build with URL API: https://docs.lovable.dev/integrations/build-with-url
- Base URL: https://lovable.dev/?autosubmit=true#prompt=YOUR_PROMPT
- Supports up to 50,000 characters in prompts
- Supports up to 10 reference images (JPEG, PNG, WebP)
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
- Be optimized for Lovable's AI design generation
- Consider the full context from previous product phases
- Generate production-ready design prompts that result in deployable React/Next.js applications
- Follow Lovable AI best practices from official documentation
- Ensure all requested features are achievable with Lovable AI capabilities
- Generate Lovable links using the Build with URL format"""

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
                "lovable link generation",
                "lovable integration",
                "ui prototype generation",
                "react application generation",
                "next.js development"
            ]
        )
        
        # Add tools after initialization
        if AGNO_TOOLS_AVAILABLE:
            created_tools = [
                self._generate_lovable_link_tool(),
            ]
            # Add tools to the agent
            if hasattr(self.agno_agent, 'tools') and self.agno_agent.tools is not None:
                valid_tools = [t for t in created_tools if t is not None]
                if valid_tools:
                    self.agno_agent.tools.extend(valid_tools)
    
    def _generate_lovable_link_tool(self):
        """Create Agno tool for Lovable link generation."""
        if not AGNO_TOOLS_AVAILABLE:
            return None
        
        @tool
        def generate_lovable_link(prompt: str, image_urls: Optional[List[str]] = None) -> str:
            """
            Generate a Lovable AI shareable link using the Build with URL API.
            
            Args:
                prompt: The design prompt (up to 50,000 characters)
                image_urls: Optional list of image URLs (up to 10, JPEG/PNG/WebP)
            
            Returns:
                Lovable shareable link URL
            """
            try:
                # Base URL for Lovable Build with URL
                base_url = "https://lovable.dev/?autosubmit=true#"
                
                # URL encode the prompt
                encoded_prompt = urllib.parse.quote(prompt)
                
                # Build URL with prompt
                url = f"{base_url}prompt={encoded_prompt}"
                
                # Add image URLs if provided
                if image_urls and len(image_urls) > 0:
                    # Limit to 10 images as per Lovable API
                    image_urls = image_urls[:10]
                    for img_url in image_urls:
                        encoded_img = urllib.parse.quote(img_url)
                        url += f"&images={encoded_img}"
                
                return f"Lovable link generated successfully!\nLink: {url}\n\nThis link will automatically open Lovable and start building your app when clicked."
            except Exception as e:
                logger.error("lovable_link_generation_error", error=str(e))
                return f"Error generating Lovable link: {str(e)}"
    
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

The prompt should be ready to use with the Lovable Link Generator."""

        message = AgentMessage(
            role="user",
            content=prompt,
            timestamp=datetime.utcnow()
        )

        response = await self.process([message], context={"task": "lovable_prompt_generation"})
        return response.response
    
    def generate_lovable_link(
        self,
        lovable_prompt: str,
        image_urls: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate a Lovable shareable link using the Build with URL API.
        Based on: https://docs.lovable.dev/integrations/build-with-url
        
        Args:
            lovable_prompt: The design prompt (up to 50,000 characters)
            image_urls: Optional list of publicly accessible image URLs (up to 10)
        
        Returns:
            Dictionary with project_url and metadata
        """
        try:
            # Base URL for Lovable Build with URL
            base_url = "https://lovable.dev/?autosubmit=true#"
            
            # URL encode the prompt
            encoded_prompt = urllib.parse.quote(lovable_prompt)
            
            # Build URL with prompt
            project_url = f"{base_url}prompt={encoded_prompt}"
            
            # Add image URLs if provided
            if image_urls and len(image_urls) > 0:
                # Limit to 10 images as per Lovable API
                image_urls = image_urls[:10]
                for img_url in image_urls:
                    encoded_img = urllib.parse.quote(img_url)
                    project_url += f"&images={encoded_img}"
            
            logger.info("lovable_link_generated", 
                       prompt_length=len(lovable_prompt),
                       num_images=len(image_urls) if image_urls else 0)
            
            return {
                "project_url": project_url,
                "prompt": lovable_prompt,
                "image_urls": image_urls or [],
                "metadata": {
                    "api_version": "build-with-url",
                    "link_type": "shareable",
                    "auto_submit": True,
                    "num_images": len(image_urls) if image_urls else 0,
                    "prompt_length": len(lovable_prompt)
                }
            }
        except Exception as e:
            logger.error("lovable_link_generation_error", error=str(e))
            raise ValueError(f"Error generating Lovable link: {str(e)}")
