from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import AgentMessage, AgentResponse
from backend.config import settings


class StrategyAgent(BaseAgent):
    """Strategy Agent for strategic planning, roadmap development, and business strategy."""
    
    def __init__(self):
        system_prompt = """You are a Strategic Planning and Business Strategy Specialist.

Your responsibilities:
1. Develop product strategy and roadmaps
2. Define go-to-market strategies
3. Create strategic plans and initiatives
4. Analyze business models and value propositions
5. Provide strategic recommendations

Strategic Areas:
- Product strategy and vision
- Go-to-market (GTM) strategy
- Business model design
- Roadmap planning and prioritization
- Competitive positioning
- Strategic partnerships and alliances

Your output should:
- Be strategic and forward-looking
- Consider market dynamics and competition
- Align with business objectives
- Provide clear action plans
- Include success metrics and KPIs"""

        super().__init__(
            name="Strategy Agent",
            role="strategy",
            system_prompt=system_prompt
        )

        self.capabilities = [
            "strategic planning", "roadmap development", "go-to-market strategy",
            "business model design", "competitive positioning", "strategic recommendations",
            "initiative planning", "value proposition"
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
                    "capabilities_used": self.capabilities
                },
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            self.logger.error("strategy_error", error=str(e))
            raise

    async def _process_with_openai(self, messages: List[Dict[str, str]]) -> str:
        client = self._get_openai_client()
        response = client.chat.completions.create(
            model=settings.agent_model_primary,
            messages=messages,
            temperature=0.8,
            max_tokens=3000
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
            temperature=0.8,
            max_tokens=3000
        )
        return response.content[0].text

    async def develop_product_strategy(
        self,
        product_info: Dict[str, Any],
        market_context: Optional[Dict[str, Any]] = None
    ) -> str:
        market_context_text = ""
        if market_context:
            market_context_text = f"Market Context:\n{market_context}\n"
        
        prompt = f"""Develop a comprehensive product strategy for:

Product Information:
{product_info}

{market_context_text}

Provide:
1. Product vision and positioning
2. Target market and customer segments
3. Value proposition
4. Competitive differentiation
5. Go-to-market strategy
6. Key success metrics and KPIs
7. Strategic roadmap (short-term and long-term)"""

        message = AgentMessage(
            role="user",
            content=prompt,
            timestamp=datetime.utcnow()
        )

        response = await self.process([message], context={"task": "strategy_development"})
        return response.response

