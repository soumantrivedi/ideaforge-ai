from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
import structlog

from backend.agents.base_agent import BaseAgent
from backend.agents.prd_authoring_agent import PRDAuthoringAgent
from backend.agents.ideation_agent import IdeationAgent
from backend.agents.jira_agent import JiraAgent
from backend.models.schemas import AgentMessage, AgentResponse

logger = structlog.get_logger()


class AgenticOrchestrator:
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {
            "prd_authoring": PRDAuthoringAgent(),
            "ideation": IdeationAgent(),
            "jira_integration": JiraAgent(),
        }
        self.logger = logger.bind(component="orchestrator")

    async def route_request(
        self,
        user_id: UUID,
        product_id: Optional[UUID],
        agent_type: str,
        messages: List[AgentMessage],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        if agent_type not in self.agents:
            available = ", ".join(self.agents.keys())
            raise ValueError(f"Unknown agent type: {agent_type}. Available: {available}")

        agent = self.agents[agent_type]

        self.logger.info(
            "routing_request",
            user_id=str(user_id),
            product_id=str(product_id) if product_id else None,
            agent_type=agent_type,
            message_count=len(messages)
        )

        try:
            response = await agent.process(messages, context)

            await agent.log_activity(
                user_id=user_id,
                product_id=product_id,
                action="process_request",
                metadata={
                    "message_count": len(messages),
                    "has_context": context is not None
                }
            )

            return response

        except Exception as e:
            self.logger.error(
                "agent_error",
                agent_type=agent_type,
                error=str(e),
                user_id=str(user_id)
            )
            raise

    async def collaborative_workflow(
        self,
        user_id: UUID,
        product_id: UUID,
        workflow_type: str,
        initial_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if workflow_type == "idea_to_jira":
            return await self._idea_to_jira_workflow(
                user_id, product_id, initial_input, context
            )
        elif workflow_type == "prd_to_jira":
            return await self._prd_to_jira_workflow(
                user_id, product_id, initial_input, context
            )
        else:
            raise ValueError(f"Unknown workflow type: {workflow_type}")

    async def _idea_to_jira_workflow(
        self,
        user_id: UUID,
        product_id: UUID,
        initial_idea: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        results = {}

        message = AgentMessage(
            role="user",
            content=f"Generate feature ideas based on: {initial_idea}",
            timestamp=datetime.utcnow()
        )

        ideation_response = await self.route_request(
            user_id=user_id,
            product_id=product_id,
            agent_type="ideation",
            messages=[message],
            context=context
        )
        results["ideation"] = ideation_response.response

        prd_message = AgentMessage(
            role="user",
            content=f"Create a PRD for these features:\n\n{ideation_response.response}",
            timestamp=datetime.utcnow()
        )

        prd_response = await self.route_request(
            user_id=user_id,
            product_id=product_id,
            agent_type="prd_authoring",
            messages=[prd_message],
            context=context
        )
        results["prd"] = prd_response.response

        jira_message = AgentMessage(
            role="user",
            content=f"Convert this PRD to Jira structure:\n\n{prd_response.response}",
            timestamp=datetime.utcnow()
        )

        jira_response = await self.route_request(
            user_id=user_id,
            product_id=product_id,
            agent_type="jira_integration",
            messages=[jira_message],
            context=context
        )
        results["jira"] = jira_response.response

        return results

    async def _prd_to_jira_workflow(
        self,
        user_id: UUID,
        product_id: UUID,
        prd_content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        results = {}

        jira_message = AgentMessage(
            role="user",
            content=f"Convert this PRD to Jira epics and stories:\n\n{prd_content}",
            timestamp=datetime.utcnow()
        )

        jira_response = await self.route_request(
            user_id=user_id,
            product_id=product_id,
            agent_type="jira_integration",
            messages=[jira_message],
            context=context
        )
        results["jira"] = jira_response.response

        return results

    def get_available_agents(self) -> List[Dict[str, str]]:
        return [
            {
                "type": agent_type,
                "name": agent.name,
                "role": agent.role
            }
            for agent_type, agent in self.agents.items()
        ]
