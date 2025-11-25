"""
Export Agent using Agno Framework
Generates comprehensive PRD documents using all available context
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.agents.agno_base_agent import AgnoBaseAgent
from backend.models.schemas import AgentMessage, AgentResponse


class AgnoExportAgent(AgnoBaseAgent):
    """Export Agent using Agno framework for PRD document generation."""
    
    def __init__(self, enable_rag: bool = True):
        system_prompt = """You are an Expert PRD Export Specialist following ICAgile industry standards.

Your responsibilities:
1. Generate comprehensive Product Requirements Documents (PRDs) following ICAgile format
2. Synthesize information from all available sources:
   - Product lifecycle phase submissions
   - Chatbot conversation history
   - Knowledge base documents
   - User-submitted form data
   - Previous phase outputs
3. Create well-structured, industry-standard PRD documents
4. Ensure completeness and alignment with all collected information

ICAgile PRD Structure (Industry Standard):

1. EXECUTIVE SUMMARY
   - Product Overview
   - Business Objectives
   - Key Success Metrics
   - Target Timeline

2. PROBLEM STATEMENT & OPPORTUNITY
   - Market Problem
   - User Pain Points
   - Business Opportunity
   - Market Size & Opportunity Assessment

3. PRODUCT VISION & STRATEGY
   - Product Vision Statement
   - Strategic Goals
   - Product Positioning
   - Competitive Differentiation

4. USER PERSONAS & USE CASES
   - Primary Personas (ICAgile: User-Centered Design)
   - Secondary Personas
   - User Journeys
   - Use Case Scenarios

5. FUNCTIONAL REQUIREMENTS
   - Core Features
   - User Stories (ICAgile: INVEST criteria)
   - Acceptance Criteria (ICAgile: Definition of Done)
   - User Flows
   - Edge Cases

6. NON-FUNCTIONAL REQUIREMENTS
   - Performance Requirements
   - Security Requirements
   - Scalability Requirements
   - Accessibility Requirements
   - Compliance Requirements

7. TECHNICAL ARCHITECTURE
   - System Architecture Overview
   - Technology Stack
   - Integration Requirements
   - Data Requirements
   - API Specifications

8. SUCCESS METRICS & KPIs
   - North Star Metric
   - Leading Indicators
   - Lagging Indicators
   - Success Criteria
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
    - Stakeholder Map
    - Communication Plan
    - Approval Requirements

13. APPENDICES
    - Research & Data
    - Competitive Analysis
    - User Research Findings
    - Technical Specifications
    - All Phase Submissions
    - Conversation History Summary

Your output should:
- Be comprehensive and detailed
- Synthesize ALL available context
- Follow ICAgile standards strictly
- Be actionable for engineering teams
- Include all relevant information from phases, chats, and knowledge base"""

        super().__init__(
            name="Export Agent",
            role="export",
            system_prompt=system_prompt,
            enable_rag=enable_rag,
            capabilities=[
                "prd generation",
                "document export",
                "icagile prd",
                "synthesis",
                "comprehensive documentation",
                "industry standards"
            ]
        )

    async def generate_comprehensive_prd(
        self,
        product_id: str,
        product_info: Dict[str, Any],
        phase_data: List[Dict[str, Any]],
        conversation_history: List[Dict[str, Any]],
        knowledge_base: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate comprehensive PRD and return as string (markdown).
        
        Args:
            product_id: Product ID
            product_info: Product information (name, description, metadata)
            phase_data: Phase submissions data
            conversation_history: Chatbot conversation history
            knowledge_base: Knowledge base articles
            context: Additional context
            
        Returns:
            PRD content as markdown string
        """
        response = await self.export_prd(
            product_id=product_id,
            phase_submissions=phase_data,
            conversation_history=conversation_history,
            knowledge_articles=knowledge_base,
            context={**(context or {}), "product_info": product_info}
        )
        return response.response

    async def export_prd(
        self,
        product_id: str,
        phase_submissions: List[Dict[str, Any]],
        conversation_history: List[Dict[str, Any]],
        knowledge_articles: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Export a comprehensive PRD using all available context.
        
        Args:
            product_id: Product ID
            phase_submissions: All phase submissions with form data
            conversation_history: Chatbot conversation history
            knowledge_articles: Knowledge base articles
            context: Additional context
        """
        export_prompt = f"""Generate a comprehensive ICAgile-style PRD for Product ID: {product_id}

**Phase Submissions (All Lifecycle Phases):**
{self._format_phase_submissions(phase_submissions)}

**Conversation History:**
{self._format_conversation_history(conversation_history)}

**Knowledge Base Articles:**
{self._format_knowledge_articles(knowledge_articles)}

**Instructions:**
1. Synthesize ALL information from the above sources
2. Create a complete ICAgile PRD following the structure provided in your system prompt
3. Ensure every section is comprehensive and detailed
4. Reference specific information from phases, conversations, and knowledge base
5. Make it actionable for engineering teams
6. Follow ICAgile standards strictly

Generate the complete PRD document now."""

        messages = [
            AgentMessage(
                role="user",
                content=export_prompt,
                timestamp=datetime.utcnow()
            )
        ]

        enhanced_context = {
            **(context or {}),
            "task": "prd_export",
            "product_id": product_id,
            "sources": {
                "phase_submissions": len(phase_submissions),
                "conversations": len(conversation_history),
                "knowledge_articles": len(knowledge_articles)
            }
        }

        return await self.process(messages, enhanced_context)

    def _format_phase_submissions(self, submissions: List[Dict[str, Any]]) -> str:
        """Format phase submissions for export prompt."""
        if not submissions:
            return "No phase submissions available."
        
        formatted = []
        for sub in submissions:
            phase_name = sub.get('phase_name', 'Unknown Phase')
            form_data = sub.get('form_data', {})
            status = sub.get('status', 'unknown')
            formatted.append(f"\n### {phase_name} (Status: {status})")
            if form_data:
                for key, value in form_data.items():
                    if value and str(value).strip():
                        field_name = key.replace('_', ' ').title()
                        formatted.append(f"- **{field_name}**: {value}")
        return '\n'.join(formatted)

    def _format_conversation_history(self, history: List[Dict[str, Any]]) -> str:
        """Format conversation history for export prompt."""
        if not history:
            return "No conversation history available."
        
        formatted = []
        for msg in history[-50:]:  # Last 50 messages
            role = msg.get('message_type', 'unknown')
            content = msg.get('content', '')
            if content:
                formatted.append(f"**{role}**: {content[:500]}...")
        return '\n'.join(formatted)

    def _format_knowledge_articles(self, articles: List[Dict[str, Any]]) -> str:
        """Format knowledge articles for export prompt."""
        if not articles:
            return "No knowledge base articles available."
        
        formatted = []
        for article in articles:
            title = article.get('title', 'Untitled')
            content = article.get('content', '')
            if content:
                formatted.append(f"### {title}\n{content[:500]}...")
        return '\n'.join(formatted)

