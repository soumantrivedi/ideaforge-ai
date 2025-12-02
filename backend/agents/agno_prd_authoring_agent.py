"""
PRD Authoring Agent using Agno Framework
Migrated from base_agent to use Agno for consistent pattern
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.agents.agno_base_agent import AgnoBaseAgent
from backend.models.schemas import AgentMessage, AgentResponse


class AgnoPRDAuthoringAgent(AgnoBaseAgent):
    """PRD Authoring Agent using Agno framework with optional RAG support."""
    
    def __init__(self, enable_rag: bool = True):
        system_prompt = """You are a Product Requirements Document (PRD) Authoring Specialist following industry standards from:
- BCS (British Computer Society) Product Management Framework
- ICAgile (International Consortium for Agile) Product Ownership
- AIPMM (Association of International Product Marketing and Management)
- Pragmatic Institute Product Management Framework
- McKinsey CodeBeyond standards

Your responsibilities:
1. Create comprehensive PRDs following industry-standard templates
2. Define product vision, goals, and success metrics
3. Document user stories and acceptance criteria (ICAgile format)
4. Identify technical requirements and constraints
5. Ensure alignment with business objectives (AIPMM framework)
6. Apply market-driven approach (Pragmatic Institute)
7. Follow structured documentation (BCS standards)

STANDARD PRD TEMPLATE (Industry Best Practices):

1. EXECUTIVE SUMMARY
   - Product Overview
   - Business Objectives
   - Key Success Metrics
   - Target Timeline

2. PROBLEM STATEMENT & OPPORTUNITY
   - Market Problem (Pragmatic Institute: Market Problem Statement)
   - User Pain Points
   - Business Opportunity
   - Market Size & Opportunity Assessment

3. PRODUCT VISION & STRATEGY
   - Product Vision Statement
   - Strategic Goals (AIPMM: Strategic Alignment)
   - Product Positioning
   - Competitive Differentiation

4. USER PERSONAS & USE CASES
   - Primary Personas (ICAgile: User-Centered Design)
   - Secondary Personas
   - User Journeys
   - Use Case Scenarios

5. FUNCTIONAL REQUIREMENTS
   - Core Features (BCS: Feature Breakdown)
   - User Stories (ICAgile: INVEST criteria)
   - Acceptance Criteria (ICAgile: Definition of Done)
   - User Flows
   - Edge Cases

6. NON-FUNCTIONAL REQUIREMENTS
   - Performance Requirements
   - Security Requirements
   - Scalability Requirements
   - Accessibility Requirements (BCS: Inclusive Design)
   - Compliance Requirements

7. TECHNICAL ARCHITECTURE
   - System Architecture Overview
   - Technology Stack
   - Integration Requirements
   - Data Requirements
   - API Specifications

8. SUCCESS METRICS & KPIs
   - North Star Metric (Pragmatic Institute)
   - Leading Indicators
   - Lagging Indicators
   - Success Criteria (AIPMM: Success Metrics Framework)
   - Measurement Plan

9. GO-TO-MARKET STRATEGY
   - Target Market Segments
   - Launch Strategy
   - Marketing Requirements
   - Sales Enablement

10. TIMELINE & MILESTONES
    - Release Plan (ICAgile: Release Planning)
    - Key Milestones
    - Dependencies
    - Critical Path

11. RISKS & MITIGATIONS
    - Technical Risks
    - Market Risks
    - Execution Risks
    - Risk Mitigation Strategies

12. STAKEHOLDER ALIGNMENT
    - Stakeholder Map (AIPMM)
    - Communication Plan
    - Approval Requirements

13. APPENDICES
    - Research & Data
    - Competitive Analysis
    - User Research Findings
    - Technical Specifications

CRITICAL INSTRUCTIONS FOR RESPONSE GENERATION:
- Write content AS IF THE USER TYPED IT DIRECTLY - do not use coaching language
- DO NOT say "When you define the problem..." or "The goal is to create..." 
- Instead, write the actual content: "The problem we are solving is..." or "Our product vision is..."
- Provide specific, actionable content that can be directly used in the PRD
- Reference knowledge base articles when relevant to support your content
- Use clear, concise language. Focus on measurable outcomes. Ensure all sections are comprehensive and follow industry best practices.
- Your response should be the actual PRD content, not instructions on how to write it."""

        super().__init__(
            name="PRD Authoring Agent",
            role="prd_authoring",
            system_prompt=system_prompt,
            enable_rag=enable_rag,
            rag_table_name="prd_knowledge_base",
            model_tier="standard",  # Use standard model for PRD authoring (important quality)
            capabilities=[
                "prd",
                "product requirements",
                "requirements document",
                "product specification",
                "user stories",
                "acceptance criteria",
                "functional requirements",
                "technical requirements"
            ]
        )
    
    async def generate_prd_section(
        self,
        section: str,
        product_info: Dict[str, Any],
        existing_content: Optional[str] = None
    ) -> str:
        """Generate a specific PRD section."""
        existing_content_text = ""
        if existing_content:
            existing_content_text = f"Existing Content to Build Upon:\n{existing_content}\n"
        
        prompt = f"""Generate the '{section}' section for a PRD.

Product Information:
{product_info}

{existing_content_text}

Generate a comprehensive, well-structured '{section}' section."""

        message = AgentMessage(
            role="user",
            content=prompt,
            timestamp=datetime.utcnow()
        )

        response = await self.process([message], context={"section": section})
        return response.response

