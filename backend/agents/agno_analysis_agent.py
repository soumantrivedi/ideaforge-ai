"""Analysis Agent using Agno Framework"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.agents.agno_base_agent import AgnoBaseAgent
from backend.models.schemas import AgentMessage, AgentResponse


class AgnoAnalysisAgent(AgnoBaseAgent):
    """Analysis Agent using Agno framework."""
    
    def __init__(self, enable_rag: bool = False):
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
            system_prompt=system_prompt,
            enable_rag=enable_rag,
            rag_table_name="analysis_knowledge_base",
            capabilities=[
                "requirements analysis",
                "swot analysis",
                "feasibility analysis",
                "risk analysis",
                "cost-benefit analysis",
                "performance analysis",
                "gap analysis",
                "strategic analysis"
            ]
        )
    
    async def perform_swot_analysis(
        self,
        product_info: Dict[str, Any],
        market_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Perform SWOT analysis."""
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

