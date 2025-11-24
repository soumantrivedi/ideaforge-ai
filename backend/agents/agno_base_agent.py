"""
Extensible Agno Framework Base Agent
Provides a consistent pattern for all agents using Agno framework
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime
from uuid import UUID
import structlog

try:
    from agno import Agent
    from agno.models.openai import OpenAIChat
    from agno.models.anthropic import Claude
    from agno.models.google import Gemini
    from agno.knowledge.knowledge import Knowledge
    from agno.vectordb.pgvector import PgVector, SearchType
    from agno.embedder.openai import OpenAIEmbedder
    # Try alternative import paths for embedders
    try:
        from agno.knowledge.embedder.openai import OpenAIEmbedder as KBOpenAIEmbedder
        from agno.knowledge.embedder.anthropic import AnthropicEmbedder
        from agno.knowledge.embedder.google import GoogleEmbedder
    except ImportError:
        # Fallback to main embedder module
        from agno.embedder.openai import OpenAIEmbedder as KBOpenAIEmbedder
        AnthropicEmbedder = None
        GoogleEmbedder = None
    AGNO_AVAILABLE = True
except ImportError as e:
    AGNO_AVAILABLE = False
    structlog.get_logger().warning("agno_framework_not_available", error=str(e))

from backend.models.schemas import AgentMessage, AgentResponse, AgentInteraction
from backend.services.provider_registry import provider_registry
from backend.config import settings

if TYPE_CHECKING:
    from backend.agents.agno_coordinator_agent import AgnoCoordinatorAgent

logger = structlog.get_logger()


class AgnoBaseAgent(ABC):
    """
    Extensible base agent using Agno framework.
    Provides consistent pattern for all agents with optional RAG support.
    """
    
    def __init__(
        self,
        name: str,
        role: str,
        system_prompt: str,
        enable_rag: bool = False,
        rag_table_name: Optional[str] = None,
        tools: Optional[List[Any]] = None,
        capabilities: Optional[List[str]] = None
    ):
        """
        Initialize Agno-based agent.
        
        Args:
            name: Agent name
            role: Agent role/type
            system_prompt: System instructions for the agent
            enable_rag: Enable RAG (Retrieval-Augmented Generation)
            rag_table_name: Custom table name for RAG knowledge base
            tools: List of Agno tools to attach
            capabilities: List of agent capabilities for routing
        """
        if not AGNO_AVAILABLE:
            raise ImportError("Agno framework is not available. Install with: pip install agno")
        
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.capabilities = capabilities or []
        self.logger = logger.bind(agent=name)
        self.interactions: List[AgentInteraction] = []
        self.coordinator: Optional['AgnoCoordinatorAgent'] = None
        
        # Get model based on provider registry
        model = self._get_agno_model()
        
        # Setup RAG knowledge base if enabled
        knowledge_base = None
        if enable_rag:
            knowledge_base = self._create_knowledge_base(rag_table_name or f"{role}_knowledge")
        
        # Create Agno agent
        self.agno_agent = Agent(
            name=name,
            model=model,
            instructions=system_prompt,
            knowledge_base=knowledge_base,
            tools=tools or [],
            markdown=True,
            show_tool_calls=True,
        )
        
        self.logger.info("agno_agent_initialized", agent=name, role=role, rag_enabled=enable_rag)
    
    def _get_agno_model(self):
        """Get appropriate Agno model based on provider registry."""
        if provider_registry.has_openai_key():
            return OpenAIChat(id=settings.agent_model_primary)
        elif provider_registry.has_claude_key():
            return Claude(id=settings.agent_model_secondary)
        elif provider_registry.has_gemini_key():
            return Gemini(id=settings.agent_model_tertiary)
        else:
            raise ValueError("No AI provider configured. Please configure at least one provider.")
    
    def _create_knowledge_base(self, table_name: str) -> Optional[Knowledge]:
        """Create knowledge base with pgvector for RAG."""
        try:
            # Get embedder based on available provider
            embedder = None
            if provider_registry.has_openai_key():
                try:
                    embedder = KBOpenAIEmbedder() if 'KBOpenAIEmbedder' in globals() else OpenAIEmbedder()
                except:
                    embedder = OpenAIEmbedder()
            elif provider_registry.has_claude_key() and AnthropicEmbedder:
                embedder = AnthropicEmbedder()
            elif provider_registry.has_gemini_key() and GoogleEmbedder:
                embedder = GoogleEmbedder()
            else:
                # Fallback to OpenAI embedder if available
                if provider_registry.has_openai_key():
                    embedder = OpenAIEmbedder()
                else:
                    self.logger.warning("no_embedder_available", message="RAG enabled but no embedder available")
                    return None
            
            # Create pgvector database connection
            vector_db = PgVector(
                table_name=table_name,
                db_url=settings.database_url,
                search_type=SearchType.similarity,
            )
            
            # Create knowledge base
            knowledge = Knowledge(
                vector_db=vector_db,
                embedder=embedder,
                num_documents=5,  # Return top 5 relevant documents
            )
            
            self.logger.info("rag_knowledge_base_created", table_name=table_name)
            return knowledge
            
        except Exception as e:
            self.logger.error("failed_to_create_knowledge_base", error=str(e))
            return None
    
    async def process(
        self,
        messages: List[AgentMessage],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """
        Process messages using Agno agent.
        
        Args:
            messages: List of agent messages
            context: Optional context dictionary
            
        Returns:
            AgentResponse with agent's response
        """
        try:
            # Convert messages to query string
            query = self._format_messages_to_query(messages, context)
            
            # Run Agno agent
            response = self.agno_agent.run(query)
            
            # Extract response content
            response_content = response.content if hasattr(response, 'content') else str(response)
            
            # Extract metadata
            metadata = {
                "has_context": context is not None,
                "message_count": len(messages),
                "model": str(self.agno_agent.model) if hasattr(self.agno_agent, 'model') else None,
            }
            
            # Add tool calls if available
            if hasattr(response, 'tool_calls') and response.tool_calls:
                metadata["tool_calls"] = [str(tc) for tc in response.tool_calls]
            
            return AgentResponse(
                agent_type=self.role,
                response=response_content,
                metadata=metadata,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            self.logger.error("agno_agent_error", error=str(e), agent=self.name)
            raise
    
    def _format_messages_to_query(self, messages: List[AgentMessage], context: Optional[Dict[str, Any]]) -> str:
        """Convert AgentMessage list to query string for Agno."""
        query_parts = []
        
        # Add conversation history
        for msg in messages:
            role_prefix = "User" if msg.role == "user" else "Assistant"
            query_parts.append(f"{role_prefix}: {msg.content}")
        
        # Add context if provided
        if context:
            context_str = "\n\n## Additional Context:\n"
            for key, value in context.items():
                if isinstance(value, (dict, list)):
                    import json
                    value = json.dumps(value, indent=2)
                context_str += f"- {key}: {value}\n"
            query_parts.append(context_str)
        
        return "\n".join(query_parts)
    
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
    
    def set_coordinator(self, coordinator: 'AgnoCoordinatorAgent'):
        """Set the coordinator for agent-to-agent communication."""
        self.coordinator = coordinator
    
    async def log_activity(
        self,
        user_id: UUID,
        product_id: Optional[UUID],
        action: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log agent activity."""
        self.logger.info(
            "agent_activity",
            user_id=str(user_id),
            product_id=str(product_id) if product_id else None,
            agent=self.name,
            action=action,
            metadata=metadata,
            timestamp=datetime.utcnow().isoformat()
        )
    
    def add_to_knowledge_base(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add content to knowledge base (if RAG is enabled)."""
        if hasattr(self.agno_agent, 'knowledge_base') and self.agno_agent.knowledge_base:
            try:
                self.agno_agent.knowledge_base.load(content=content, metadata=metadata or {})
                self.logger.info("content_added_to_knowledge_base", agent=self.name)
            except Exception as e:
                self.logger.error("failed_to_add_to_knowledge_base", error=str(e))
        else:
            self.logger.warning("knowledge_base_not_available", agent=self.name)

