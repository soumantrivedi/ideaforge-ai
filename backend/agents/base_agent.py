from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime
from uuid import UUID
import structlog

from backend.models.schemas import AgentMessage, AgentResponse, AgentInteraction
from backend.services.provider_registry import provider_registry

if TYPE_CHECKING:
    from backend.agents.coordinator_agent import CoordinatorAgent

logger = structlog.get_logger()


class BaseAgent(ABC):
    def __init__(self, name: str, role: str, system_prompt: str):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.logger = logger.bind(agent=name)
        self.interactions: List[AgentInteraction] = []
        self.capabilities: List[str] = []
        self.coordinator: Optional['CoordinatorAgent'] = None

    @abstractmethod
    async def process(
        self,
        messages: List[AgentMessage],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        pass

    def _prepare_messages(self, messages: List[AgentMessage]) -> List[Dict[str, str]]:
        formatted_messages = [{"role": "system", "content": self.system_prompt}]

        for msg in messages:
            formatted_messages.append({
                "role": msg.role,
                "content": msg.content
            })

        return formatted_messages

    def _add_context(
        self,
        messages: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        if not context:
            return messages

        context_str = "\n\n## Additional Context:\n"
        for key, value in context.items():
            context_str += f"- {key}: {value}\n"

        messages[0]["content"] += context_str
        return messages

    async def consult_agent(
        self,
        target_agent_type: str,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Consult another agent for specialized expertise."""
        if not self.coordinator:
            raise ValueError("Coordinator not set. Cannot consult other agents.")

        interaction = await self.coordinator.route_agent_consultation(
            from_agent=self.role,
            to_agent=target_agent_type,
            query=query,
            context=context
        )

        self.interactions.append(interaction)
        return interaction.response

    def can_handle(self, query: str) -> bool:
        """Determine if this agent can handle the query."""
        query_lower = query.lower()
        for capability in self.capabilities:
            if capability.lower() in query_lower:
                return True
        return False

    def get_confidence(self, query: str) -> float:
        """Get confidence score for handling a query (0.0 to 1.0)."""
        if not self.capabilities:
            return 0.5

        query_lower = query.lower()
        matches = sum(1 for cap in self.capabilities if cap.lower() in query_lower)
        return min(1.0, matches / len(self.capabilities) + 0.3)

    def get_interactions(self) -> List[AgentInteraction]:
        """Get all agent-to-agent interactions."""
        return self.interactions.copy()

    def set_coordinator(self, coordinator: 'CoordinatorAgent'):
        """Set the coordinator for agent-to-agent communication."""
        self.coordinator = coordinator

    def _get_openai_client(self):
        client = provider_registry.get_openai_client()
        if not client:
            raise ValueError("OpenAI provider is not configured")
        return client

    def _get_claude_client(self):
        client = provider_registry.get_claude_client()
        if not client:
            raise ValueError("Anthropic Claude provider is not configured")
        return client

    def _has_openai(self) -> bool:
        return provider_registry.has_openai_key()

    def _has_claude(self) -> bool:
        return provider_registry.has_claude_key()

    async def log_activity(
        self,
        user_id: UUID,
        product_id: Optional[UUID],
        action: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.logger.info(
            "agent_activity",
            user_id=str(user_id),
            product_id=str(product_id) if product_id else None,
            agent=self.name,
            action=action,
            metadata=metadata,
            timestamp=datetime.utcnow().isoformat()
        )
