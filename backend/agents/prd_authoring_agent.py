from typing import List, Dict, Any, Optional
from datetime import datetime
import openai
from anthropic import Anthropic

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import AgentMessage, AgentResponse
from backend.config import settings


class PRDAuthoringAgent(BaseAgent):
    def __init__(self):
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
            system_prompt=system_prompt
        )

        self.openai_client = openai.OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self.claude_client = Anthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None

    async def process(
        self,
        messages: List[AgentMessage],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        formatted_messages = self._prepare_messages(messages)
        formatted_messages = self._add_context(formatted_messages, context)

        try:
            if self.openai_client:
                response = await self._process_with_openai(formatted_messages)
            elif self.claude_client:
                response = await self._process_with_claude(formatted_messages)
            else:
                raise ValueError("No AI provider configured")

            return AgentResponse(
                agent_type=self.role,
                response=response,
                metadata={
                    "has_context": context is not None,
                    "message_count": len(messages)
                },
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            self.logger.error("prd_authoring_error", error=str(e))
            raise

    async def _process_with_openai(self, messages: List[Dict[str, str]]) -> str:
        response = self.openai_client.chat.completions.create(
            model=settings.agent_model_primary,
            messages=messages,
            temperature=0.7,
            max_tokens=4000
        )
        return response.choices[0].message.content

    async def _process_with_claude(self, messages: List[Dict[str, str]]) -> str:
        system_message = messages[0]["content"]
        user_messages = messages[1:]

        response = self.claude_client.messages.create(
            model=settings.agent_model_secondary,
            system=system_message,
            messages=user_messages,
            temperature=0.7,
            max_tokens=4000
        )
        return response.content[0].text

    async def generate_prd_section(
        self,
        section: str,
        product_info: Dict[str, Any],
        existing_content: Optional[str] = None
    ) -> str:
        prompt = f"""Generate the '{section}' section for a PRD.

Product Information:
{product_info}

{f"Existing Content to Build Upon:\n{existing_content}\n" if existing_content else ""}

Generate a comprehensive, well-structured '{section}' section."""

        message = AgentMessage(
            role="user",
            content=prompt,
            timestamp=datetime.utcnow()
        )

        response = await self.process([message], context={"section": section})
        return response.response
