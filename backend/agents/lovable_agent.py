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
        system_prompt = """You are a Lovable Design Specialist.

Your responsibilities:
1. Generate detailed, comprehensive prompts for Lovable to create UI prototypes
2. Understand product requirements and translate them into Lovable-compatible prompts
3. Create prompts that leverage Lovable's component library and design system
4. Ensure prompts are specific, actionable, and result in high-quality designs
5. Consider user experience, accessibility, and modern design patterns

Lovable Prompt Guidelines:
- Be specific about component types and layouts
- Specify styling requirements (Tailwind CSS classes, custom styles)
- Include responsive design breakpoints
- Mention state management requirements
- Include accessibility features
- Reference React/Next.js patterns
- Specify data flow and component interactions

Your output should:
- Be comprehensive and detailed
- Include all necessary design specifications
- Be optimized for Lovable's AI design generation
- Consider the full context from previous product phases
- Generate production-ready design prompts"""

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
        lovable_api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a design mockup using Lovable API."""
        api_key = lovable_api_key or settings.lovable_api_key
        
        if not api_key:
            raise ValueError("Lovable API key is not configured")
        
        # Lovable API endpoint (this is a placeholder - actual Lovable API may differ)
        # Note: Lovable may use different endpoints, this needs to be updated based on actual API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.lovable.dev/v1/generate",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "prompt": lovable_prompt,
                    "model": "gpt-4",
                    "temperature": 0.7
                },
                timeout=60.0
            )
            
            if response.status_code != 200:
                raise ValueError(f"Lovable API error: {response.status_code} - {response.text}")
            
            return response.json()

