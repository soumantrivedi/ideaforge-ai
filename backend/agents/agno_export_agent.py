"""
Export Agent using Agno Framework
Generates comprehensive PRD documents using all available context
Includes review and missing content detection
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
5. Review content before export and identify missing critical sections
6. Highlight sections that need to be defined if user chooses to override

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
                "industry standards",
                "content review",
                "missing content detection"
            ]
        )

    async def review_content_before_export(
        self,
        product_id: str,
        phase_data: List[Dict[str, Any]],
        conversation_history: List[Dict[str, Any]],
        knowledge_base: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Review content before export and identify missing critical sections.
        
        Returns:
            Dict with:
            - is_complete: bool
            - missing_sections: List[str]
            - recommendations: List[str]
            - warnings: List[str]
        """
        review_prompt = f"""Review the following product content for completeness before PRD export.

**Phase Submissions:**
{self._format_phase_submissions(phase_data)}

**Conversation History:**
{self._format_conversation_history(conversation_history[:20])}  # Last 20 messages

**Knowledge Base:**
{self._format_knowledge_articles(knowledge_base[:10])}  # Top 10 articles

**Review Criteria:**
1. Check if market research is present (Market Research phase or research in conversation/knowledge base)
2. Check if user personas are defined
3. Check if functional requirements are clear
4. Check if technical architecture is outlined
5. Check if success metrics are defined
6. Check if go-to-market strategy is present

**Required Sections for Complete PRD:**
- Market Research / Competitive Analysis
- User Personas
- Functional Requirements
- Technical Architecture
- Success Metrics
- Go-to-Market Strategy

Respond in JSON format:
{{
    "status": "ready" or "needs_attention",
    "score": <0-100>,  // Overall completeness score as percentage
    "missing_sections": [
        {{
            "section": "section name",
            "phase_name": "Phase Name (if applicable)",
            "phase_id": "phase-uuid (if applicable)",
            "importance": "why this section matters",
            "recommendation": "what to do",
            "score": <0-100>  // Section-specific score
        }}
    ],
    "phase_scores": [
        {{
            "phase_name": "Phase Name",
            "phase_id": "phase-uuid",
            "score": <0-100>,
            "status": "complete" or "incomplete" or "missing"
        }}
    ],
    "summary": "Overall assessment summary"
}}"""

        messages = [
            AgentMessage(
                role="user",
                content=review_prompt,
                timestamp=datetime.utcnow()
            )
        ]

        enhanced_context = {
            **(context or {}),
            "task": "content_review",
            "product_id": product_id
        }

        response = await self.process(messages, enhanced_context)
        
        # Try to parse JSON from response
        import json
        import re
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response.response, re.DOTALL)
            if json_match:
                review_result = json.loads(json_match.group())
                return review_result
        except:
            pass
        
        # Fallback: analyze response text and calculate scores
        missing_sections = []
        phase_scores = []
        total_score = 100
        
        # Check each required section
        required_sections = [
            ("Market Research", "Market Research"),
            ("User Personas", "Ideation"),
            ("Functional Requirements", "Requirements"),
            ("Technical Architecture", "Design"),
            ("Success Metrics", "Requirements"),
            ("Go-to-Market Strategy", "Go-to-Market")
        ]
        
        for section_name, phase_name in required_sections:
            section_lower = section_name.lower()
            if section_lower not in response.response.lower():
                missing_sections.append({
                    "section": section_name,
                    "phase_name": phase_name,
                    "importance": f"{section_name} is critical for a complete PRD",
                    "recommendation": f"Complete the {phase_name} phase or add {section_name} content",
                    "score": 0
                })
                total_score -= 15  # Deduct 15 points per missing section
        
        # Calculate phase scores based on phase_data
        if phase_data:
            for phase in phase_data:
                phase_name = phase.get('phase_name', '')
                phase_id = phase.get('phase_id', '')
                form_data = phase.get('form_data', {})
                generated_content = phase.get('generated_content', '')
                
                # Calculate phase completeness score
                has_form_data = bool(form_data and any(v for v in form_data.values() if v))
                has_content = bool(generated_content and generated_content.strip())
                
                if has_form_data and has_content:
                    phase_score = 100
                    status = "complete"
                elif has_form_data or has_content:
                    phase_score = 50
                    status = "incomplete"
                else:
                    phase_score = 0
                    status = "missing"
                
                phase_scores.append({
                    "phase_name": phase_name,
                    "phase_id": phase_id,
                    "score": phase_score,
                    "status": status
                })
        
        # Ensure score is between 0-100
        total_score = max(0, min(100, total_score))
        
        return {
            "status": "ready" if total_score >= 80 else "needs_attention",
            "score": total_score,
            "missing_sections": missing_sections,
            "phase_scores": phase_scores,
            "summary": f"PRD completeness: {total_score}%. {'Ready for export' if total_score >= 80 else 'Some sections need attention'}."
        }

    async def generate_comprehensive_prd(
        self,
        product_id: str,
        product_info: Dict[str, Any],
        phase_data: List[Dict[str, Any]],
        conversation_history: List[Dict[str, Any]],
        knowledge_base: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        override_missing: bool = False
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
            override_missing: If True, mark missing sections as "To Be Defined"
            
        Returns:
            PRD content as markdown string
        """
        # Review content first if not overriding
        if not override_missing:
            review_result = await self.review_content_before_export(
                product_id=product_id,
                phase_data=phase_data,
                conversation_history=conversation_history,
                knowledge_base=knowledge_base,
                context=context
            )
            context = context or {}
            context["review_result"] = review_result
        
        response = await self.export_prd(
            product_id=product_id,
            phase_submissions=phase_data,
            conversation_history=conversation_history,
            knowledge_articles=knowledge_base,
            context={**(context or {}), "product_info": product_info, "override_missing": override_missing}
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
            context: Additional context (may include review_result and override_missing)
        """
        override_missing = context.get("override_missing", False) if context else False
        review_result = context.get("review_result") if context else None
        
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
6. Follow ICAgile standards strictly"""

        if override_missing and review_result:
            missing_sections = review_result.get("missing_sections", [])
            if missing_sections:
                export_prompt += f"""

**IMPORTANT - Missing Content Override:**
The following sections are missing but user has chosen to export anyway.
For each missing section listed below, include a placeholder section marked as "TO BE DEFINED":
{', '.join(missing_sections)}

For each missing section, create a section header and include:
## [Section Name] - TO BE DEFINED

**Status:** This section requires additional input from the user.
**Next Steps:** [Provide guidance on what information is needed]
**Related Phases:** [Suggest which lifecycle phases could help fill this section]"""

        export_prompt += "\n\nGenerate the complete PRD document now."

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
            generated_content = sub.get('generated_content', '')
            status = sub.get('status', 'unknown')
            formatted.append(f"\n### {phase_name} (Status: {status})")
            if form_data:
                for key, value in form_data.items():
                    if value and str(value).strip():
                        field_name = key.replace('_', ' ').title()
                        formatted.append(f"- **{field_name}**: {value}")
            if generated_content:
                formatted.append(f"\n**Generated Content:**\n{generated_content[:500]}")
        return '\n'.join(formatted)

    def _format_conversation_history(self, history: List[Dict[str, Any]]) -> str:
        """Format conversation history for export prompt."""
        if not history:
            return "No conversation history available."
        
        formatted = []
        for msg in history[-100:]:  # Last 100 messages
            role = msg.get('message_type', msg.get('role', 'unknown'))
            content = msg.get('content', '')
            agent_name = msg.get('agent_name', '')
            if content:
                agent_label = f" ({agent_name})" if agent_name else ""
                formatted.append(f"**{role}{agent_label}**: {content[:1000]}")
        return '\n'.join(formatted)

    def _format_knowledge_articles(self, articles: List[Dict[str, Any]]) -> str:
        """Format knowledge articles for export prompt."""
        if not articles:
            return "No knowledge base articles available."
        
        formatted = []
        for article in articles:
            title = article.get('title', 'Untitled')
            content = article.get('content', '')
            source_type = article.get('source_type', '')
            if content:
                formatted.append(f"### {title} ({source_type})\n{content[:1000]}")
        return '\n'.join(formatted)
