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
    
    def __init__(self, enable_rag: bool = False):
        system_prompt = """You are a Product Requirements Document (PRD) Authoring Specialist following McKinsey CodeBeyond standards.

Your responsibilities:
1. Create comprehensive PRDs with clear structure
2. Define product vision, goals, and success metrics
3. Document user stories and acceptance criteria
4. Identify technical requirements and constraints
5. Ensure alignment with business objectives

PRD Structure:
- Executive Summary
- Problem Statement
- Product Vision & Goals
- User Personas & Use Cases
- Functional Requirements
- Non-Functional Requirements
- Technical Architecture
- Success Metrics & KPIs
- Timeline & Milestones
- Risks & Mitigations

Use clear, concise language. Focus on measurable outcomes."""

        super().__init__(
            name="PRD Authoring Agent",
            role="prd_authoring",
            system_prompt=system_prompt,
            enable_rag=enable_rag,
            rag_table_name="prd_knowledge_base",
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

