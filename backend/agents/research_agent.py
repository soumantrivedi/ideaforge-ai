from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import AgentMessage, AgentResponse
from backend.config import settings


class ResearchAgent(BaseAgent):
    """Research Agent for market research, competitive analysis, and data gathering."""
    
    def __init__(self):
        system_prompt = """You are a Research and Market Intelligence Specialist.

Your responsibilities:
1. Conduct market research and competitive analysis
2. Gather industry trends and insights
3. Analyze user needs and market gaps
4. Research technical feasibility and best practices
5. Provide data-driven recommendations

Research Areas:
- Market trends and opportunities
- Competitive landscape analysis
- User behavior and preferences
- Technical feasibility studies
- Industry benchmarks and standards
- Regulatory and compliance requirements

Your output should:
- Be data-driven and evidence-based
- Include relevant sources and references
- Highlight key insights and patterns
- Identify opportunities and risks
- Provide actionable recommendations"""

        super().__init__(
            name="Research Agent",
            role="research",
            system_prompt=system_prompt
        )

        self.capabilities = [
            "market research", "competitive analysis", "trend analysis",
            "user research", "feasibility study", "benchmarking",
            "industry analysis", "data gathering"
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
            self.logger.error("research_error", error=str(e))
            raise

    async def _process_with_openai(self, messages: List[Dict[str, str]]) -> str:
        client = self._get_openai_client()
        response = client.chat.completions.create(
            model=settings.agent_model_primary,
            messages=messages,
            temperature=0.7,
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
            temperature=0.7,
            max_tokens=3000
        )
        return response.content[0].text

    async def conduct_market_research(
        self,
        product_domain: str,
        target_market: Optional[str] = None
    ) -> str:
        prompt = f"""Conduct comprehensive market research for:
- Product Domain: {product_domain}
{f"- Target Market: {target_market}" if target_market else ""}

Provide:
1. Market size and growth trends
2. Competitive landscape
3. Key market players and their strategies
4. Market gaps and opportunities
5. User needs and pain points
6. Regulatory considerations"""

        message = AgentMessage(
            role="user",
            content=prompt,
            timestamp=datetime.utcnow()
        )

        response = await self.process([message], context={"task": "market_research"})
        return response.response

