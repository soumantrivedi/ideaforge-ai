from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
import structlog

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import AgentMessage, AgentResponse
from backend.config import settings

logger = structlog.get_logger()


class V0Agent(BaseAgent):
    """Agent for generating V0 (Vercel) design prompts and prototypes."""
    
    def __init__(self):
        system_prompt = """You are a V0 (Vercel) Design Specialist.

Your responsibilities:
1. Generate detailed, comprehensive prompts for V0 to create UI prototypes
2. Understand product requirements and translate them into V0-compatible prompts
3. Create prompts that leverage V0's component library and design system
4. Ensure prompts are specific, actionable, and result in high-quality designs
5. Consider user experience, accessibility, and modern design patterns

V0 Prompt Guidelines:
- Be specific about component types (buttons, cards, forms, etc.)
- Specify layout requirements (grid, flex, spacing)
- Include color schemes and styling preferences
- Mention responsive design requirements
- Specify interaction states (hover, active, disabled)
- Include accessibility requirements
- Reference modern UI patterns (shadcn/ui, Tailwind CSS)

Your output should:
- Be comprehensive and detailed
- Include all necessary design specifications
- Be optimized for V0's AI design generation
- Consider the full context from previous product phases
- Generate production-ready design prompts"""

        super().__init__(
            name="V0 Agent",
            role="v0_design",
            system_prompt=system_prompt
        )
        
        self.capabilities = [
            "v0 prompt generation",
            "ui design specification",
            "component design",
            "design system integration",
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
                    "agent": "v0"
                },
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            self.logger.error("v0_agent_error", error=str(e))
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

    async def generate_v0_prompt(
        self,
        product_context: Dict[str, Any],
        design_requirements: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a detailed V0 prompt based on product context."""
        requirements_text = ""
        if design_requirements:
            requirements_text = f"\n\nDesign Requirements:\n{design_requirements}\n"
        
        prompt = f"""Generate a comprehensive V0 (Vercel) design prompt for this product:

Product Context:
{product_context}
{requirements_text}

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

    async def generate_design_mockup(
        self,
        v0_prompt: str,
        v0_api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a design mockup using V0 API."""
        api_key = v0_api_key or settings.v0_api_key
        
        if not api_key:
            raise ValueError("V0 API key is not configured")
        
        # V0 API endpoint (this is a placeholder - actual V0 API may differ)
        # Note: V0 may use different endpoints, this needs to be updated based on actual API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://v0.dev/api/generate",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "prompt": v0_prompt,
                    "model": "gpt-4",
                    "temperature": 0.7
                },
                timeout=60.0
            )
            
            if response.status_code != 200:
                raise ValueError(f"V0 API error: {response.status_code} - {response.text}")
            
            return response.json()

