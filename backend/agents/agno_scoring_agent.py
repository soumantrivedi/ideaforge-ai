"""
Product Idea Scoring Agent using Agno Framework
Scores product ideas based on industry standards and best practices
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from backend.agents.agno_base_agent import AgnoBaseAgent
from backend.models.schemas import AgentMessage, AgentResponse


class AgnoScoringAgent(AgnoBaseAgent):
    """Product Idea Scoring Agent based on industry standards."""
    
    def __init__(self, enable_rag: bool = True):
        system_prompt = """You are a Product Idea Scoring Specialist following industry standards from:
- BCS (British Computer Society) Product Management Framework
- ICAgile (International Consortium for Agile) Product Ownership
- AIPMM (Association of International Product Marketing and Management)
- Pragmatic Institute Product Management Framework

Your responsibilities:
1. Score product ideas across multiple dimensions
2. Assess market viability and business value
3. Evaluate technical feasibility
4. Analyze user needs and market fit
5. Provide actionable recommendations
6. Calculate success probability

Scoring Dimensions (0-100 scale):
1. Market Opportunity (25 points)
   - Market size and growth potential
   - Competitive landscape
   - Market timing
   - Market accessibility

2. User Value (25 points)
   - Problem-solution fit
   - User pain point severity
   - User adoption likelihood
   - User experience potential

3. Business Value (20 points)
   - Revenue potential
   - Strategic alignment
   - Business model viability
   - ROI potential

4. Technical Feasibility (15 points)
   - Technical complexity
   - Resource requirements
   - Technology readiness
   - Implementation timeline

5. Risk Assessment (15 points)
   - Market risks
   - Technical risks
   - Execution risks
   - Competitive risks

Your scoring should:
- Be objective and data-driven
- Consider industry best practices
- Provide detailed rationale for each score
- Include specific recommendations for improvement
- Calculate overall success probability
- Be contextualized to the specific product and market"""

        super().__init__(
            name="Product Scoring Agent",
            role="scoring",
            system_prompt=system_prompt,
            enable_rag=enable_rag,
            rag_table_name="scoring_knowledge_base",
            capabilities=[
                "product scoring",
                "idea evaluation",
                "market analysis",
                "feasibility assessment",
                "success probability",
                "risk assessment",
                "recommendations"
            ]
        )
    
    async def score_product_idea(
        self,
        product_summary: str,
        market_context: Optional[Dict[str, Any]] = None,
        user_feedback: Optional[List[str]] = None,
        technical_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Score a product idea and return detailed scoring breakdown."""
        context = {
            "market_context": market_context or {},
            "user_feedback": user_feedback or [],
            "technical_context": technical_context or {}
        }
        
        market_text = ""
        if market_context:
            market_text = f"\n\nMarket Context:\n{json.dumps(market_context, indent=2)}\n"
        
        user_feedback_text = ""
        if user_feedback:
            user_feedback_text = f"\n\nUser Feedback:\n" + "\n".join(f"- {fb}" for fb in user_feedback) + "\n"
        
        technical_text = ""
        if technical_context:
            technical_text = f"\n\nTechnical Context:\n{json.dumps(technical_context, indent=2)}\n"
        
        prompt = f"""Score this product idea following industry standards (BCS, ICAgile, AIPMM, Pragmatic Institute):

Product Summary:
{product_summary}
{market_text}{user_feedback_text}{technical_text}

Provide a comprehensive scoring in JSON format with the following structure:
{{
    "overall_score": <0-100>,
    "success_probability": <0-100>,
    "dimensions": {{
        "market_opportunity": {{
            "score": <0-100>,
            "rationale": "<detailed explanation>",
            "sub_scores": {{
                "market_size": <0-25>,
                "competitive_landscape": <0-25>,
                "market_timing": <0-25>,
                "market_accessibility": <0-25>
            }}
        }},
        "user_value": {{
            "score": <0-100>,
            "rationale": "<detailed explanation>",
            "sub_scores": {{
                "problem_solution_fit": <0-25>,
                "pain_point_severity": <0-25>,
                "adoption_likelihood": <0-25>,
                "ux_potential": <0-25>
            }}
        }},
        "business_value": {{
            "score": <0-100>,
            "rationale": "<detailed explanation>",
            "sub_scores": {{
                "revenue_potential": <0-20>,
                "strategic_alignment": <0-20>,
                "business_model_viability": <0-20>,
                "roi_potential": <0-20>
            }}
        }},
        "technical_feasibility": {{
            "score": <0-100>,
            "rationale": "<detailed explanation>",
            "sub_scores": {{
                "technical_complexity": <0-15>,
                "resource_requirements": <0-15>,
                "technology_readiness": <0-15>,
                "implementation_timeline": <0-15>
            }}
        }},
        "risk_assessment": {{
            "score": <0-100>,
            "rationale": "<detailed explanation>",
            "sub_scores": {{
                "market_risks": <0-15>,
                "technical_risks": <0-15>,
                "execution_risks": <0-15>,
                "competitive_risks": <0-15>
            }}
        }}
    }},
    "recommendations": [
        {{
            "dimension": "<dimension_name>",
            "priority": "<high|medium|low>",
            "recommendation": "<specific actionable recommendation>",
            "expected_impact": "<expected score improvement>"
        }}
    ],
    "success_factors": [
        "<key factor that contributes to success>"
    ],
    "risk_factors": [
        "<key risk that could impact success>"
    ],
    "next_steps": [
        "<actionable next step>"
    ]
}}

Ensure scores are realistic and based on the provided context."""

        message = AgentMessage(
            role="user",
            content=prompt,
            timestamp=datetime.utcnow()
        )

        response = await self.process([message], context=context)
        
        # Parse JSON response
        try:
            # Extract JSON from response (might have markdown formatting)
            response_text = response.response
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            
            scoring_result = json.loads(response_text)
            return scoring_result
        except json.JSONDecodeError as e:
            self.logger.error("failed_to_parse_scoring", error=str(e), response=response.response)
            # Return a fallback structure
            return {
                "overall_score": 50,
                "success_probability": 50,
                "error": "Failed to parse scoring response",
                "raw_response": response.response
            }
    
    async def get_scoring_criteria(self) -> Dict[str, Any]:
        """Get the scoring criteria and methodology."""
        prompt = """Provide a detailed explanation of the scoring criteria and methodology used,
        following industry standards from BCS, ICAgile, AIPMM, and Pragmatic Institute."""

        message = AgentMessage(
            role="user",
            content=prompt,
            timestamp=datetime.utcnow()
        )

        response = await self.process([message])
        return {
            "criteria": response.response,
            "standards": ["BCS", "ICAgile", "AIPMM", "Pragmatic Institute"]
        }

