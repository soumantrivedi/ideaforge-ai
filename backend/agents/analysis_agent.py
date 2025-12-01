from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import AgentMessage, AgentResponse
from backend.config import settings


class AnalysisAgent(BaseAgent):
    """Analysis Agent for data analysis, requirements analysis, and strategic analysis."""
    
    def __init__(self):
        system_prompt = """You are a Strategic Analysis Specialist.

Your responsibilities:
1. Analyze product requirements and specifications
2. Perform SWOT analysis and strategic assessments
3. Evaluate technical feasibility and architecture
4. Analyze user feedback and metrics
5. Provide strategic recommendations

Analysis Types:
- Requirements analysis and gap identification
- SWOT (Strengths, Weaknesses, Opportunities, Threats) analysis
- Technical architecture analysis
- Risk analysis and mitigation strategies
- Cost-benefit analysis
- Performance and scalability analysis

Your output should:
- Be structured and comprehensive
- Identify key insights and patterns
- Highlight risks and opportunities
- Provide actionable recommendations
- Include quantitative assessments when possible"""

        super().__init__(
            name="Analysis Agent",
            role="analysis",
            system_prompt=system_prompt
        )

        self.capabilities = [
            "requirements analysis", "swot analysis", "feasibility analysis",
            "risk analysis", "cost-benefit analysis", "performance analysis",
            "gap analysis", "strategic analysis"
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
            self.logger.error("analysis_error", error=str(e))
            raise

    async def _process_with_openai(self, messages: List[Dict[str, str]]) -> str:
        from backend.config import get_openai_completion_param
        client = self._get_openai_client()
        model = settings.agent_model_primary
        param_name = get_openai_completion_param(model)
        completion_params = {param_name: 3000}
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.6,
            **completion_params
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
            temperature=0.6,
            max_tokens=3000
        )
        return response.content[0].text

    async def perform_swot_analysis(
        self,
        product_info: Dict[str, Any],
        market_context: Optional[Dict[str, Any]] = None
    ) -> str:
        market_context_text = ""
        if market_context:
            market_context_text = f"Market Context:\n{market_context}\n"
        
        prompt = f"""Perform a comprehensive SWOT analysis for this product:

Product Information:
{product_info}

{market_context_text}

Provide:
1. Strengths - Internal advantages
2. Weaknesses - Internal limitations
3. Opportunities - External favorable conditions
4. Threats - External challenges
5. Strategic recommendations based on the analysis"""

        message = AgentMessage(
            role="user",
            content=prompt,
            timestamp=datetime.utcnow()
        )

        response = await self.process([message], context={"task": "swot_analysis"})
        return response.response

