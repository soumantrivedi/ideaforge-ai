from typing import List, Dict, Any, Optional
from datetime import datetime
import openai
from anthropic import Anthropic

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import AgentMessage, AgentResponse
from backend.config import settings


class IdeationAgent(BaseAgent):
    def __init__(self):
        system_prompt = """You are an Ideation and Brainstorming Specialist.

Your responsibilities:
1. Facilitate creative brainstorming sessions
2. Generate innovative product ideas and features
3. Explore problem spaces from multiple angles
4. Challenge assumptions and identify opportunities
5. Help refine vague concepts into actionable ideas

Techniques you employ:
- Design Thinking methodologies
- Jobs-to-be-Done framework
- Value Proposition Canvas
- SCAMPER technique
- "How Might We" questions
- Opportunity mapping

Your output should:
- Be creative yet practical
- Consider user needs and business value
- Identify potential risks and opportunities
- Provide multiple perspectives and alternatives
- Build upon existing ideas constructively"""

        super().__init__(
            name="Ideation Agent",
            role="ideation",
            system_prompt=system_prompt
        )

        self.openai_client = openai.OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self.claude_client = Anthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None

    async def process(
        self,
        messages: List[AgentMessage],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        formatted_messages = self._prepare_messages(messages)
        formatted_messages = self._add_context(formatted_messages, context)

        try:
            if self.claude_client:
                response = await self._process_with_claude(formatted_messages)
            elif self.openai_client:
                response = await self._process_with_openai(formatted_messages)
            else:
                raise ValueError("No AI provider configured")

            return AgentResponse(
                agent_type=self.role,
                response=response,
                metadata={
                    "has_context": context is not None,
                    "message_count": len(messages)
                },
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            self.logger.error("ideation_error", error=str(e))
            raise

    async def _process_with_openai(self, messages: List[Dict[str, str]]) -> str:
        response = self.openai_client.chat.completions.create(
            model=settings.agent_model_primary,
            messages=messages,
            temperature=0.9,
            max_tokens=3000
        )
        return response.choices[0].message.content

    async def _process_with_claude(self, messages: List[Dict[str, str]]) -> str:
        system_message = messages[0]["content"]
        user_messages = messages[1:]

        response = self.claude_client.messages.create(
            model=settings.agent_model_secondary,
            system=system_message,
            messages=user_messages,
            temperature=0.9,
            max_tokens=3000
        )
        return response.content[0].text

    async def generate_feature_ideas(
        self,
        product_context: Dict[str, Any],
        constraints: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        prompt = f"""Generate innovative feature ideas for this product:

Product Context:
{product_context}

{f"Constraints:\n{constraints}\n" if constraints else ""}

Generate 5-10 creative, actionable feature ideas. For each idea, provide:
1. Feature name
2. Brief description
3. User value proposition
4. Implementation complexity (Low/Medium/High)"""

        message = AgentMessage(
            role="user",
            content=prompt,
            timestamp=datetime.utcnow()
        )

        response = await self.process([message], context={"task": "feature_generation"})
        return [line.strip() for line in response.response.split('\n') if line.strip()]
