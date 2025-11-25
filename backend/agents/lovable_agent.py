from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
import structlog

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import AgentMessage, AgentResponse
from backend.config import settings

logger = structlog.get_logger()


class LovableAgent(BaseAgent):
    """Agent for generating Lovable design prompts and prototypes."""
    
    def __init__(self):
        system_prompt = """You are a Lovable AI Design Specialist following official Lovable AI documentation.

Your responsibilities:
1. Generate detailed, comprehensive prompts for Lovable AI to create UI prototypes
2. Understand product requirements and translate them into Lovable-compatible prompts
3. Create prompts that leverage Lovable's component library and design system
4. Ensure prompts are specific, actionable, and result in high-quality designs
5. Consider user experience, accessibility, and modern design patterns
6. Generate accurate Lovable AI prompts that can be used with the official Lovable API

Lovable AI API Documentation Reference:
- Lovable AI uses API at https://api.lovable.dev/v1/generate
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
- Ensure all requested features are achievable with Lovable AI capabilities"""

        super().__init__(
            name="Lovable Agent",
            role="lovable_design",
            system_prompt=system_prompt
        )
        
        self.capabilities = [
            "lovable prompt generation",
            "ui design specification",
            "react component design",
            "next.js integration",
            "responsive design",
            "accessibility design"
        ]

    async def process(
        self,
        messages: List[AgentMessage],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        formatted_messages = self._prepare_messages(messages)
        formatted_messages = self._add_context(formatted_messages, context)

        try:
            if self._has_claude():
                response = await self._process_with_claude(formatted_messages)
            elif self._has_openai():
                response = await self._process_with_openai(formatted_messages)
            else:
                raise ValueError("No AI provider configured")

            return AgentResponse(
                agent_type=self.role,
                response=response,
                metadata={
                    "has_context": context is not None,
                    "message_count": len(messages),
                    "agent": "lovable"
                },
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            self.logger.error("lovable_agent_error", error=str(e))
            raise

    async def _process_with_openai(self, messages: List[Dict[str, str]]) -> str:
        client = self._get_openai_client()
        response = client.chat.completions.create(
            model=settings.agent_model_primary,
            messages=messages,
            temperature=0.7,
            max_tokens=4000
        )
        return response.choices[0].message.content

    async def _process_with_claude(self, messages: List[Dict[str, str]]) -> str:
        client = self._get_claude_client()
        system_message = messages[0]["content"]
        user_messages = messages[1:]

        response = client.messages.create(
            model=settings.agent_model_secondary,
            system=system_message,
            messages=user_messages,
            temperature=0.7,
            max_tokens=4000
        )
        return response.content[0].text

    async def generate_lovable_prompt(
        self,
        product_context: Dict[str, Any],
        design_requirements: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a detailed Lovable prompt based on product context."""
        requirements_text = ""
        if design_requirements:
            requirements_text = f"\n\nDesign Requirements:\n{design_requirements}\n"
        
        prompt = f"""Generate a comprehensive Lovable design prompt for this product:

Product Context:
{product_context}
{requirements_text}

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

    async def generate_design_mockup(
        self,
        lovable_prompt: str,
        lovable_api_key: Optional[str] = None,
        user_id: Optional[str] = None,
        generate_thumbnails: bool = True
    ) -> Dict[str, Any]:
        """
        Generate design mockup using Lovable AI API.
        Based on official Lovable AI documentation: https://docs.lovable.dev
        
        Lovable AI generates React/Next.js applications from prompts.
        """
        api_key = lovable_api_key or settings.lovable_api_key
        
        if not api_key:
            raise ValueError("Lovable API key is not configured")
        
        # Lovable AI API endpoint (official API)
        # Documentation: https://docs.lovable.dev/api
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                # Lovable API for generating applications
                response = await client.post(
                    "https://api.lovable.dev/v1/generate",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "prompt": lovable_prompt,
                        "model": "gpt-4-turbo",  # Lovable's recommended model
                        "temperature": 0.7,
                        "generate_thumbnails": generate_thumbnails,  # Request thumbnail generation
                        "num_thumbnails": 3 if generate_thumbnails else 1  # Generate 3 thumbnail options
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
                
                # Extract generated application data
                project_id = result.get("project_id")
                project_url = result.get("project_url") or result.get("url")
                thumbnails = result.get("thumbnails", [])
                code = result.get("code") or result.get("generated_code", "")
                
                return {
                    "project_id": project_id,
                    "project_url": project_url,
                    "code": code,
                    "prompt": lovable_prompt,
                    "thumbnails": thumbnails,  # Array of thumbnail URLs
                    "thumbnail_url": thumbnails[0] if thumbnails else None,  # First thumbnail as default
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
    
    async def generate_thumbnail_previews(
        self,
        lovable_prompt: str,
        lovable_api_key: Optional[str] = None,
        num_previews: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple thumbnail previews for user selection.
        Returns 3 different design variations.
        """
        api_key = lovable_api_key or settings.lovable_api_key
        
        if not api_key:
            raise ValueError("Lovable API key is not configured")
        
        # Generate multiple variations
        previews = []
        for i in range(num_previews):
            try:
                # Add variation to prompt for diversity
                variation_prompt = f"{lovable_prompt}\n\nVariation {i+1}: Please create a unique design variation with different styling, layout, or color scheme."
                
                result = await self.generate_design_mockup(
                    variation_prompt,
                    api_key,
                    generate_thumbnails=True
                )
                
                previews.append({
                    "index": i + 1,
                    "thumbnail_url": result.get("thumbnail_url"),
                    "project_url": result.get("project_url"),
                    "prompt": variation_prompt,
                    "metadata": result.get("metadata", {})
                })
            except Exception as e:
                logger.warning("lovable_thumbnail_generation_failed", variation=i+1, error=str(e))
                # Continue with other variations even if one fails
        
        return previews

