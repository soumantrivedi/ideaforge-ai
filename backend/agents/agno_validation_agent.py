"""
Validation Agent using Agno Framework
Validates responses, PRDs, and ensures quality standards
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.agents.agno_base_agent import AgnoBaseAgent
from backend.models.schemas import AgentMessage, AgentResponse


class AgnoValidationAgent(AgnoBaseAgent):
    """Validation Agent using Agno framework with optional RAG support."""
    
    def __init__(self, enable_rag: bool = False):
        system_prompt = """You are a Quality Assurance and Validation Specialist following industry standards from:
- BCS (British Computer Society) Product Management Framework
- ICAgile (International Consortium for Agile) Product Ownership
- AIPMM (Association of International Product Marketing and Management)
- Pragmatic Institute Product Management Framework
- McKinsey CodeBeyond standards

Your responsibilities:
1. Validate product requirements and responses for completeness
2. Ensure compliance with standards and best practices
3. Check for clarity, testability, and consistency
4. Validate technical feasibility
5. Review and provide actionable feedback on deliverables
6. Assess quality against user-submitted form data

Validation Areas:
- Response completeness and structure
- Requirements clarity and testability
- Technical feasibility validation
- Compliance with industry standards (ICAgile, AIPMM, BCS, Pragmatic Institute)
- Consistency across documents and responses
- Risk identification and mitigation
- Alignment with user-submitted form data

Your output format should be:
1. **Validation Status**: PASS / NEEDS_REFINEMENT / FAIL
2. **Completeness Score**: 0-100
3. **Issues Found**: List of specific issues with severity (critical/warning/info)
4. **Recommendations**: Specific, actionable recommendations for improvement
5. **User Satisfaction Assessment**: Whether the response adequately addresses the user's form data

Be thorough but constructive. Focus on making responses actionable and aligned with user needs."""

        super().__init__(
            name="Validation Agent",
            model_tier="fast",  # Use fast model for validation
            role="validation",
            system_prompt=system_prompt,
            enable_rag=enable_rag,
            capabilities=[
                "response validation",
                "prd validation",
                "requirements validation",
                "quality assurance",
                "compliance checking",
                "feasibility validation",
                "standards validation",
                "gap analysis",
                "user satisfaction assessment"
            ]
        )

    async def validate_response(
        self,
        response_content: str,
        form_data: Dict[str, Any],
        phase_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Validate a generated response against form data and standards.
        
        Args:
            response_content: The generated response to validate
            form_data: User-submitted form data to validate against
            phase_name: Name of the phase being validated
            context: Additional context for validation
        """
        validation_prompt = f"""Validate the following generated response for the "{phase_name}" phase:

**Generated Response:**
{response_content}

**User-Submitted Form Data:**
{self._format_form_data(form_data)}

**Validation Criteria:**
1. Does the response adequately address all fields in the form data?
2. Is the response complete and comprehensive?
3. Does it follow industry standards (ICAgile, AIPMM, BCS, Pragmatic Institute)?
4. Is the response clear, actionable, and testable?
5. Are there any gaps or inconsistencies?
6. Would a user find this response satisfactory for their needs?

Provide your validation in this format:

**Validation Status**: [PASS / NEEDS_REFINEMENT / FAIL]

**Completeness Score**: [0-100]

**Issues Found**:
- [Severity: critical/warning/info] [Issue description] - [Suggestion]

**Recommendations**:
- [Specific recommendation 1]
- [Specific recommendation 2]

**User Satisfaction Assessment**: [Assessment of whether response meets user needs based on form data]

**Refinement Suggestions**: [If NEEDS_REFINEMENT, provide specific suggestions for improvement]"""

        messages = [
            AgentMessage(
                role="user",
                content=validation_prompt,
                timestamp=datetime.utcnow()
            )
        ]

        enhanced_context = {
            **(context or {}),
            "task": "response_validation",
            "phase_name": phase_name,
            "form_data": form_data
        }

        return await self.process(messages, enhanced_context)

    def _format_form_data(self, form_data: Dict[str, Any]) -> str:
        """Format form data for display in validation prompt."""
        formatted = []
        for key, value in form_data.items():
            if value and str(value).strip():
                field_name = key.replace('_', ' ').title()
                formatted.append(f"- **{field_name}**: {value}")
        return '\n'.join(formatted) if formatted else "No form data provided"

