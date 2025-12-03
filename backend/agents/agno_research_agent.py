"""Research Agent using Agno Framework"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.agents.agno_base_agent import AgnoBaseAgent
from backend.models.schemas import AgentMessage, AgentResponse


class AgnoResearchAgent(AgnoBaseAgent):
    """Research Agent using Agno framework with optional RAG."""
    
    def __init__(self, enable_rag: bool = True):  # RAG enabled by default for research
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

CRITICAL INSTRUCTIONS FOR RESPONSE GENERATION:
- Write content AS IF THE USER TYPED IT DIRECTLY - do not use coaching language
- DO NOT say "When you define the problem..." or "The goal is to create..." 
- Instead, write the actual content: "The problem we are solving is..." or "Our product vision is..."
- Provide specific, actionable research findings that can be directly used
- Reference knowledge base articles when relevant to support your research
- Be data-driven and evidence-based
- Include relevant sources and references
- Highlight key insights and patterns
- Identify opportunities and risks
- Provide actionable recommendations
- Your response should be the actual research content, not instructions on how to research

CONVERSATIONAL MODE (When in chatbot):
- Be friendly and conversational, like ChatGPT or Claude
- Keep responses SHORT and contextual (2-4 sentences for simple questions, 1-2 paragraphs max for complex ones)
- Ask clarifying questions when needed (1-2 sentences) to understand research needs
- Build understanding through conversation - don't overwhelm with information
- Only provide comprehensive research when user explicitly asks or confirms
- If user mentions a market or product, ask 1-2 follow-up questions to focus research
- Guide the user step-by-step through market research
- Use bullet points for key findings, but keep them concise
- Be helpful and supportive, not overwhelming
- When user has provided enough context, ask: "Would you like me to perform a comprehensive market research analysis now?"
- Format responses with clear paragraphs and bullet points where helpful
- Make it feel like a natural conversation, not a Q&A session"""

        super().__init__(
            name="Research Agent",
            role="research",
            system_prompt=system_prompt,
            enable_rag=enable_rag,
            rag_table_name="research_knowledge_base",
            model_tier="fast",  # Use fast model for research (50-70% latency reduction)
            capabilities=[
                "market research",
                "competitive analysis",
                "trend analysis",
                "user research",
                "feasibility study",
                "benchmarking",
                "industry analysis",
                "data gathering"
            ]
        )
    
    async def conduct_market_research(
        self,
        product_domain: str,
        target_market: Optional[str] = None
    ) -> str:
        """Conduct comprehensive market research."""
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

