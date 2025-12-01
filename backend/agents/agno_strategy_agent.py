"""
Strategy Agent using Agno Framework
Strategic planning, roadmap development, and business strategy
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.agents.agno_base_agent import AgnoBaseAgent
from backend.models.schemas import AgentMessage, AgentResponse


class AgnoStrategyAgent(AgnoBaseAgent):
    """Strategy Agent using Agno framework with optional RAG support."""
    
    def __init__(self, enable_rag: bool = False):
        system_prompt = """You are a Strategic Planning and Business Strategy Specialist following industry standards from:
- BCS (British Computer Society) Product Management Framework
- ICAgile (International Consortium for Agile) Product Ownership
- AIPMM (Association of International Product Marketing and Management)
- Pragmatic Institute Product Management Framework
- McKinsey CodeBeyond standards

Your responsibilities:
1. Develop product strategy and roadmaps
2. Define go-to-market (GTM) strategies
3. Create strategic plans and initiatives
4. Analyze business models and value propositions
5. Provide strategic recommendations
6. Develop competitive positioning strategies
7. Plan strategic partnerships and alliances

Strategic Areas:
- Product strategy and vision
- Go-to-market (GTM) strategy
- Business model design
- Roadmap planning and prioritization
- Competitive positioning
- Strategic partnerships and alliances
- Market segmentation and targeting
- Value proposition development
- Strategic initiatives and programs

Your output should:
- Be strategic and forward-looking
- Consider market dynamics and competition
- Align with business objectives
- Provide clear action plans
- Include success metrics and KPIs
- Address user-submitted form data comprehensively
- Follow industry best practices and frameworks

Be thorough, strategic, and actionable. Focus on creating value and competitive advantage."""

        super().__init__(
            name="Strategy Agent",
            role="strategy",
            system_prompt=system_prompt,
            enable_rag=enable_rag,
            model_tier="standard"  # Strategy requires thoughtful analysis
        )

        self.capabilities = [
            "strategic planning",
            "roadmap development",
            "go-to-market strategy",
            "business model design",
            "competitive positioning",
            "strategic recommendations",
            "initiative planning",
            "value proposition",
            "market segmentation",
            "strategic partnerships"
        ]

    async def process(
        self,
        messages: List[AgentMessage],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """
        Process strategy-related queries using Agno framework.
        Uses the base class process method which handles all Agno-specific logic.
        """
        # Use the base class process method which handles Agno agent interaction
        response = await super().process(messages, context)
        
        # Add strategy-specific metadata
        if response.metadata:
            response.metadata.update({
                "capabilities_used": self.capabilities,
            })
        else:
            response.metadata = {
                "capabilities_used": self.capabilities,
            }
        
        return response

    async def develop_product_strategy(
        self,
        product_info: Dict[str, Any],
        market_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Develop a comprehensive product strategy."""
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

