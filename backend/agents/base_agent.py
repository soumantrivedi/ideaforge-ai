from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
import structlog

from backend.models.schemas import AgentMessage, AgentResponse

logger = structlog.get_logger()


class BaseAgent(ABC):
    def __init__(self, name: str, role: str, system_prompt: str):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.logger = logger.bind(agent=name)

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
