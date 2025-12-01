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
            model_tier="standard",  # Use standard model for export (important quality)
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
        design_mockups: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
        all_phases: Optional[List[Dict[str, Any]]] = None,
        missing_phases: Optional[List[Dict[str, Any]]] = None,
        db: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Review content before export and identify missing critical sections.
        CRITICAL: Reviews based on ALL lifecycle phases, not just conversation history.
        
        Args:
            product_id: Product ID
            phase_data: Submitted phase data
            conversation_history: Chatbot conversation history (for context only, not primary source)
            knowledge_base: Knowledge base articles
            design_mockups: Design mockups/prototypes
            context: Additional context
            all_phases: ALL lifecycle phases from database (required for accurate review)
            missing_phases: Phases that don't have submissions (required for accurate review)
            db: Database session (optional, for additional queries)
        
        Returns:
            Dict with:
            - status: "ready" or "needs_attention"
            - score: 0-100 (completion percentage based on ACTUAL phase completion)
            - missing_sections: List of missing sections/phases
            - phase_scores: List of phase scores
            - summary: Overall assessment
        """
        # CRITICAL: Calculate completion based on ALL lifecycle phases, not just conversation history
        # First, get all phases if not provided
        if all_phases is None or missing_phases is None:
            # Try to get from database if db session provided
            if db:
                from sqlalchemy import text
                try:
                    all_phases_query = text("""
                        SELECT id, phase_name, phase_order, description
                        FROM product_lifecycle_phases
                        ORDER BY phase_order ASC
                    """)
                    all_phases_result = await db.execute(all_phases_query)
                    all_phases_rows = all_phases_result.fetchall()
                    
                    all_phases = []
                    submitted_phase_ids = {p.get("phase_id") for p in phase_data if p.get("phase_id")}
                    missing_phases = []
                    
                    for row in all_phases_rows:
                        phase_id = str(row[0])
                        phase_info = {
                            "phase_id": phase_id,
                            "phase_name": row[1],
                            "phase_order": row[2],
                            "description": row[3],
                            "has_submission": phase_id in submitted_phase_ids
                        }
                        all_phases.append(phase_info)
                        if not phase_info["has_submission"]:
                            missing_phases.append(phase_info)
                except Exception as e:
                    self.logger.warning("failed_to_fetch_all_phases", error=str(e))
                    # Fallback: use phase_data to infer phases
                    all_phases = [{"phase_id": p.get("phase_id"), "phase_name": p.get("phase_name"), "phase_order": p.get("phase_order")} for p in phase_data]
                    missing_phases = []
        
        # Calculate actual completion based on ALL phases
        total_phases = len(all_phases) if all_phases else len(phase_data)
        completed_phases = 0
        phase_scores = []
        missing_sections = []
        
        # Create a map of submitted phases for quick lookup
        submitted_phases_map = {p.get("phase_id"): p for p in phase_data if p.get("phase_id")}
        
        # Review each phase (ALL phases, not just submitted ones)
        for phase_info in (all_phases or []):
            phase_id = phase_info.get("phase_id")
            phase_name = phase_info.get("phase_name", "Unknown Phase")
            phase_order = phase_info.get("phase_order", 999)
            
            if phase_id in submitted_phases_map:
                # Phase has submission - check completeness
                submitted_phase = submitted_phases_map[phase_id]
                form_data = submitted_phase.get("form_data", {})
                generated_content = submitted_phase.get("generated_content", "")
                status = submitted_phase.get("status", "draft")
                
                # Calculate phase completeness score
                has_form_data = bool(form_data and any(v for v in form_data.values() if v and str(v).strip()))
                has_content = bool(generated_content and generated_content.strip())
                is_completed_status = status in ["completed", "reviewed"]
                
                # Phase is complete only if it has both form data AND generated content AND completed status
                if has_form_data and has_content and is_completed_status:
                    phase_score = 100
                    phase_status = "complete"
                    completed_phases += 1
                elif has_form_data and has_content:
                    phase_score = 75  # Has content but not marked complete
                    phase_status = "incomplete"
                elif has_form_data or has_content:
                    phase_score = 50  # Partial content
                    phase_status = "incomplete"
                else:
                    phase_score = 0
                    phase_status = "incomplete"
            else:
                # Phase is missing - no submission
                phase_score = 0
                phase_status = "missing"
                missing_sections.append({
                    "section": phase_name,
                    "phase_name": phase_name,
                    "phase_id": phase_id,
                    "phase_order": phase_order,
                    "importance": f"{phase_name} phase is required for a complete PRD. This phase provides critical information for product development.",
                    "recommendation": f"Complete the {phase_name} phase in the Product Lifecycle workflow to add this essential content.",
                    "score": 0
                })
            
            phase_scores.append({
                "phase_name": phase_name,
                "phase_id": phase_id,
                "phase_order": phase_order,
                "score": phase_score,
                "status": phase_status
            })
        
        # Calculate overall completion score based on ACTUAL phase completion
        if total_phases > 0:
            # Score = (completed_phases / total_phases) * 100
            # But also consider partial completion (phases with some content)
            partial_phases = sum(1 for ps in phase_scores if ps["score"] >= 50 and ps["status"] != "complete")
            # Weight: complete phases = 100%, partial phases = 50%, missing = 0%
            weighted_score = (completed_phases * 100 + partial_phases * 50) / total_phases
            total_score = round(weighted_score, 1)
        else:
            total_score = 0
        
        # Format design mockups if available
        design_mockups_text = ""
        if design_mockups:
            design_mockups_text = "\n**Design Prototypes:**\n"
            for mockup in design_mockups:
                provider = mockup.get('provider', 'unknown').upper()
                status = mockup.get('project_status', 'unknown')
                project_url = mockup.get('project_url', '')
                design_mockups_text += f"- {provider} Prototype: Status={status}, URL={project_url}\n"
        
        # Build comprehensive review prompt that focuses on PHASE COMPLETION
        review_prompt = f"""Review the following product content for completeness before PRD export.

**CRITICAL: Review based on ACTUAL lifecycle phase completion, not just conversation history.**

**All Required Lifecycle Phases:**
{self._format_all_phases_for_review(all_phases or [], phase_scores)}

**Phase Submissions (Submitted Phases):**
{self._format_phase_submissions(phase_data)}

**Missing Phases (No Submissions):**
{self._format_missing_phases(missing_phases or [])}

**Conversation History (Context Only - NOT primary source for completion):**
{self._format_conversation_history(conversation_history[:10])}  # Limited to 10 messages for context

**Knowledge Base (Supporting Information):**
{self._format_knowledge_articles(knowledge_base[:5])}  # Top 5 articles
{design_mockups_text}

**Review Instructions:**
1. PRIMARY FOCUS: Check which lifecycle phases have been completed (have submissions with form_data AND generated_content AND status='completed')
2. Identify missing phases (phases with no submissions)
3. Identify incomplete phases (phases with submissions but missing form_data, generated_content, or not marked complete)
4. Calculate completion percentage: (completed_phases / total_phases) * 100
5. DO NOT rely on conversation history to determine completion - only actual phase submissions count
6. DO NOT say PRD is 100% complete unless ALL phases are completed

**Current Status:**
- Total Phases: {total_phases}
- Completed Phases: {completed_phases}
- Missing Phases: {len(missing_phases) if missing_phases else 0}
- Calculated Completion: {total_score}%

**Required Response Format (JSON):**
{{
    "status": "ready" or "needs_attention",
    "score": {total_score},  // MUST match calculated completion percentage
    "completed_phases": {completed_phases},
    "total_phases": {total_phases},
    "missing_sections": [
        {{
            "section": "phase name",
            "phase_name": "Phase Name",
            "phase_id": "phase-uuid",
            "phase_order": <number>,
            "importance": "why this phase matters",
            "recommendation": "what to do to complete this phase",
            "score": 0
        }}
    ],
    "phase_scores": [
        {{
            "phase_name": "Phase Name",
            "phase_id": "phase-uuid",
            "phase_order": <number>,
            "score": <0-100>,
            "status": "complete" or "incomplete" or "missing"
        }}
    ],
    "summary": "Accurate assessment based on actual phase completion. PRD is {total_score}% complete ({completed_phases}/{total_phases} phases completed)."
}}

**IMPORTANT:**
- Score MUST reflect actual phase completion: {total_score}%
- Status MUST be "needs_attention" if score < 100%
- DO NOT say PRD is 100% complete unless ALL {total_phases} phases are completed
- Focus on missing phases: {', '.join([p.get('phase_name', 'Unknown') for p in (missing_phases or [])]) if missing_phases else 'None'}"""

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
        
        # Fallback: Use pre-calculated scores (more reliable than parsing AI response)
        # The scores were already calculated above based on actual phase data
        # This ensures accuracy and prevents false "100% complete" reports
        
        # Try to parse JSON from response, but use pre-calculated scores as ground truth
        parsed_result = None
        try:
            json_match = re.search(r'\{.*\}', response.response, re.DOTALL)
            if json_match:
                parsed_result = json.loads(json_match.group())
                # Override score with calculated score to ensure accuracy
                if parsed_result:
                    parsed_result["score"] = total_score
                    parsed_result["completed_phases"] = completed_phases
                    parsed_result["total_phases"] = total_phases
                    parsed_result["phase_scores"] = phase_scores
                    parsed_result["missing_sections"] = missing_sections
                    parsed_result["status"] = "ready" if total_score >= 100 else "needs_attention"
                    parsed_result["summary"] = f"PRD completeness: {total_score}% ({completed_phases}/{total_phases} phases completed). {'Ready for export' if total_score >= 100 else f'Missing {len(missing_phases) if missing_phases else 0} phase(s). Complete all phases for 100% completion.'}"
                    return parsed_result
        except:
            pass
        
        # If parsing failed, return pre-calculated results (most accurate)
        return {
            "status": "ready" if total_score >= 100 else "needs_attention",
            "score": total_score,
            "completed_phases": completed_phases,
            "total_phases": total_phases,
            "missing_sections": missing_sections,
            "phase_scores": phase_scores,
            "summary": f"PRD completeness: {total_score}% ({completed_phases}/{total_phases} phases completed). {'Ready for export - all phases completed' if total_score >= 100 else f'Missing {len(missing_phases) if missing_phases else 0} phase(s): {", ".join([p.get("phase_name", "Unknown") for p in (missing_phases or [])])}. Complete all phases for 100% completion.'}"
        }

    async def generate_comprehensive_prd(
        self,
        product_id: str,
        product_info: Dict[str, Any],
        phase_data: List[Dict[str, Any]],
        conversation_history: List[Dict[str, Any]],
        knowledge_base: List[Dict[str, Any]],
        design_mockups: Optional[List[Dict[str, Any]]] = None,
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
                design_mockups=design_mockups,
                context=context
            )
            context = context or {}
            context["review_result"] = review_result
        
        response = await self.export_prd(
            product_id=product_id,
            phase_submissions=phase_data,
            conversation_history=conversation_history,
            knowledge_articles=knowledge_base,
            context={**(context or {}), "product_info": product_info, "override_missing": override_missing, "design_mockups": design_mockups or []}
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
        
        # Format design mockups if available
        design_mockups = context.get("design_mockups", []) if context else []
        design_mockups_text = ""
        if design_mockups:
            design_mockups_text = "\n**Design Prototypes:**\n"
            for mockup in design_mockups:
                provider = mockup.get('provider', 'unknown').upper()
                status = mockup.get('project_status', 'unknown')
                project_url = mockup.get('project_url', '')
                thumbnail_url = mockup.get('thumbnail_url') or mockup.get('image_url', '')
                prompt = mockup.get('prompt', '')
                design_mockups_text += f"""
- **{provider} Prototype:**
  - Status: {status}
  - Prototype URL: {project_url}
  - Thumbnail: {thumbnail_url if thumbnail_url else 'N/A'}
  - Prompt Used: {prompt[:200] if prompt else 'N/A'}...
"""
        
        export_prompt = f"""Generate a comprehensive ICAgile-style PRD for Product ID: {product_id}

**Phase Submissions (All Lifecycle Phases):**
{self._format_phase_submissions(phase_submissions)}

**Conversation History:**
{self._format_conversation_history(conversation_history)}

**Knowledge Base Articles:**
{self._format_knowledge_articles(knowledge_articles)}
{design_mockups_text}

**Instructions:**
1. Synthesize ALL information from the above sources
2. Create a complete ICAgile PRD following the structure provided in your system prompt
3. Ensure every section is comprehensive and detailed
4. Reference specific information from phases, conversations, and knowledge base
5. Include design prototypes section with clickable links to prototypes
6. Make it actionable for engineering teams
7. Follow ICAgile standards strictly"""

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
    
    def _format_all_phases_for_review(self, all_phases: List[Dict[str, Any]], phase_scores: List[Dict[str, Any]]) -> str:
        """Format all lifecycle phases for review prompt."""
        if not all_phases:
            return "No lifecycle phases defined."
        
        # Create a map of phase scores for quick lookup
        scores_map = {ps.get("phase_id"): ps for ps in phase_scores}
        
        formatted = []
        for phase in sorted(all_phases, key=lambda x: x.get("phase_order", 999)):
            phase_id = phase.get("phase_id", "")
            phase_name = phase.get("phase_name", "Unknown Phase")
            phase_order = phase.get("phase_order", 999)
            has_submission = phase.get("has_submission", False)
            
            score_info = scores_map.get(phase_id, {})
            score = score_info.get("score", 0)
            status = score_info.get("status", "missing")
            
            status_icon = "✅" if status == "complete" else "⚠️" if status == "incomplete" else "❌"
            formatted.append(f"{status_icon} Phase {phase_order}: {phase_name} - Score: {score}% ({status})")
        
        return '\n'.join(formatted)
    
    def _format_missing_phases(self, missing_phases: List[Dict[str, Any]]) -> str:
        """Format missing phases for review prompt."""
        if not missing_phases:
            return "No missing phases - all phases have submissions."
        
        formatted = []
        for phase in sorted(missing_phases, key=lambda x: x.get("phase_order", 999)):
            phase_name = phase.get("phase_name", "Unknown Phase")
            phase_order = phase.get("phase_order", 999)
            description = phase.get("description", "")
            formatted.append(f"❌ Phase {phase_order}: {phase_name} - {description}")
        
        return '\n'.join(formatted)
