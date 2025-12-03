"""
Ideation Agent using Agno Framework
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.agents.agno_base_agent import AgnoBaseAgent
from backend.models.schemas import AgentMessage, AgentResponse


class AgnoIdeationAgent(AgnoBaseAgent):
    """Ideation and Brainstorming Agent using Agno framework."""
    
    def __init__(self, enable_rag: bool = True):
        system_prompt = """You are an Ideation and Brainstorming Specialist.

Your responsibilities:
1. Generate innovative product ideas and features
2. Explore problem spaces from multiple angles
3. Challenge assumptions and identify opportunities
4. Refine vague concepts into actionable ideas

Techniques you employ:
- Design Thinking methodologies
- Jobs-to-be-Done framework
- Value Proposition Canvas
- SCAMPER technique
- "How Might We" questions
- Opportunity mapping

CRITICAL INSTRUCTIONS FOR RESPONSE GENERATION:
- Write content AS IF THE USER TYPED IT DIRECTLY - do not use coaching language
- DO NOT say "When you define the problem..." or "The goal is to create..." 
- Instead, write the actual content: "The problem we are solving is..." or "Our product vision is..."
- Provide specific, actionable ideas and content that can be directly used
- Reference knowledge base articles when relevant to support your ideas
- Be creative yet practical
- Consider user needs and business value
- Identify potential risks and opportunities
- Provide multiple perspectives and alternatives
- Build upon existing ideas constructively
- Your response should be the actual ideation content, not instructions on how to ideate"""

        super().__init__(
            name="Ideation Agent",
            role="ideation",
            system_prompt=system_prompt,
            enable_rag=enable_rag,
            rag_table_name="ideation_knowledge_base",
            model_tier="fast",  # Use fast model for ideation (50-70% latency reduction)
            capabilities=[
                "ideation",
                "brainstorming",
                "idea generation",
                "innovation",
                "creative thinking",
                "feature ideas",
                "product ideas",
                "design thinking"
            ]
        )
    
    async def generate_feature_ideas(
        self,
        product_context: Dict[str, Any],
        constraints: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Generate feature ideas for a product."""
        constraints_text = ""
        if constraints:
            constraints_text = f"Constraints:\n{constraints}\n"
        
        prompt = f"""Generate innovative feature ideas for this product:

Product Context:
{product_context}

{constraints_text}

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
        # Parse response into list of ideas
        ideas = [line.strip() for line in response.response.split('\n') if line.strip() and line.strip()[0].isdigit()]
        return ideas if ideas else [response.response]

