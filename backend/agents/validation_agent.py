from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import AgentMessage, AgentResponse
from backend.config import settings


class ValidationAgent(BaseAgent):
    """Validation Agent for validating requirements, PRDs, and ensuring quality standards."""
    
    def __init__(self):
        system_prompt = """You are a Quality Assurance and Validation Specialist.

Your responsibilities:
1. Validate product requirements and PRDs
2. Ensure compliance with standards and best practices
3. Check for completeness and consistency
4. Validate technical feasibility
5. Review and provide feedback on deliverables

Validation Areas:
- PRD completeness and structure
- Requirements clarity and testability
- Technical feasibility validation
- Compliance with industry standards
- Consistency across documents
- Risk identification and mitigation

Your output should:
- Be thorough and systematic
- Identify gaps and inconsistencies
- Provide specific, actionable feedback
- Reference standards and best practices
- Prioritize critical issues"""

        super().__init__(
            name="Validation Agent",
            role="validation",
            system_prompt=system_prompt
        )

        self.capabilities = [
            "prd validation", "requirements validation", "quality assurance",
            "compliance checking", "feasibility validation", "review",
            "standards validation", "gap analysis"
        ]

    async def process(
        self,
        messages: List[AgentMessage],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        formatted_messages = self._prepare_messages(messages)
        formatted_messages = self._add_context(formatted_messages, context)

        try:
            if self._has_claude():
                response = await self._process_with_claude(formatted_messages)
            elif self._has_openai():
                response = await self._process_with_openai(formatted_messages)
            else:
                raise ValueError("No AI provider configured")

            return AgentResponse(
                agent_type=self.role,
                response=response,
                metadata={
                    "has_context": context is not None,
                    "message_count": len(messages),
                    "capabilities_used": self.capabilities
                },
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            self.logger.error("validation_error", error=str(e))
            raise

    async def _process_with_openai(self, messages: List[Dict[str, str]]) -> str:
        from backend.config import get_openai_completion_param
        client = self._get_openai_client()
        model = settings.agent_model_primary
        param_name = get_openai_completion_param(model)
        completion_params = {param_name: 3000}
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.3,
            **completion_params
        )
        return response.choices[0].message.content

    async def _process_with_claude(self, messages: List[Dict[str, str]]) -> str:
        client = self._get_claude_client()
        system_message = messages[0]["content"]
        user_messages = messages[1:]

        response = client.messages.create(
            model=settings.agent_model_secondary,
            system=system_message,
            messages=user_messages,
            temperature=0.3,
            max_tokens=3000
        )
        return response.content[0].text

    async def validate_prd(
        self,
        prd_content: Dict[str, Any],
        standards: Optional[List[str]] = None
    ) -> str:
        standards_text = "Use McKinsey CodeBeyond standards."
        if standards:
            standards_text = f"Standards to Check:\n{chr(10).join(standards)}\n"
        
        prompt = f"""Validate this PRD against quality standards:

PRD Content:
{prd_content}

{standards_text}

Check for:
1. Completeness - All required sections present
2. Clarity - Clear, unambiguous requirements
3. Testability - Requirements can be verified
4. Consistency - No contradictions
5. Feasibility - Technically achievable
6. Alignment - Matches business objectives

Provide:
- Overall validation status
- List of issues found (if any)
- Specific recommendations for improvement
- Priority levels for each issue"""

        message = AgentMessage(
            role="user",
            content=prompt,
            timestamp=datetime.utcnow()
        )

        response = await self.process([message], context={"task": "prd_validation"})
        return response.response

