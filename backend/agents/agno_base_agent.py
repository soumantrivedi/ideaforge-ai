"""
Extensible Agno Framework Base Agent
Provides a consistent pattern for all agents using Agno framework
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, TYPE_CHECKING, Union
from datetime import datetime
from uuid import UUID
import structlog

try:
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat
    from agno.models.anthropic import Claude
    from agno.models.google import Gemini
    from agno.knowledge.knowledge import Knowledge
    from agno.vectordb.pgvector import PgVector, SearchType
    # Embedders are in agno.knowledge.embedder
    try:
        from agno.knowledge.embedder.openai import OpenAIEmbedder
        from agno.knowledge.embedder.anthropic import AnthropicEmbedder
        from agno.knowledge.embedder.google import GoogleEmbedder
        KBOpenAIEmbedder = OpenAIEmbedder
    except ImportError as e:
        # If embedders are not available, set to None
        OpenAIEmbedder = None
        KBOpenAIEmbedder = None
        AnthropicEmbedder = None
        GoogleEmbedder = None
        structlog.get_logger().warning("agno_embedders_not_available", error=str(e))
    AGNO_AVAILABLE = True
except ImportError as e:
    AGNO_AVAILABLE = False
    structlog.get_logger().warning("agno_framework_not_available", error=str(e))

from backend.models.schemas import AgentMessage, AgentResponse, AgentInteraction
from backend.services.provider_registry import provider_registry
from backend.config import settings

if TYPE_CHECKING:
    from backend.agents.agno_coordinator_agent import AgnoCoordinatorAgent
    from backend.agents.agno_enhanced_coordinator import AgnoEnhancedCoordinator

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
        self.enable_rag = enable_rag
        self.rag_table_name = rag_table_name or f"{role}_knowledge"
        self.capabilities = capabilities or []
        self.logger = logger.bind(agent=name)
        self.interactions: List[AgentInteraction] = []
        self.coordinator: Optional[Union['AgnoCoordinatorAgent', 'AgnoEnhancedCoordinator']] = None
        
        # Get model based on provider registry
        model = self._get_agno_model()
        
        # If no model is available, defer agent creation until a provider is configured
        if model is None:
            self.agno_agent = None
            self.logger.warning("agno_agent_deferred", agent=name, reason="no_provider_configured")
        else:
            # Setup RAG knowledge base if enabled
            knowledge = None
            if enable_rag:
                knowledge = self._create_knowledge_base(self.rag_table_name)
            
            # Create Agno agent (use 'knowledge' parameter, not 'knowledge_base')
            self.agno_agent = Agent(
                name=name,
                model=model,
                instructions=system_prompt,
                knowledge=knowledge,  # Agno uses 'knowledge' parameter
                tools=tools or [],
                markdown=True,
                # Note: show_tool_calls is not a valid parameter for Agno Agent
            )
            
            self.logger.info("agno_agent_initialized", agent=name, role=role, rag_enabled=enable_rag)
    
    def _get_agno_model(self):
        """Get appropriate Agno model based on provider registry.
        Priority: GPT-5.1 (primary) > Gemini 3.0 Pro (tertiary) > Claude 4 Sonnet (secondary)
        Prefers GPT-5.1 for best reasoning, falls back to Gemini 3.0 Pro if OpenAI not available.
        """
        # Prefer GPT-5.1 for best reasoning capabilities
        if provider_registry.has_openai_key():
            api_key = provider_registry.get_openai_key()
            if api_key:
                return OpenAIChat(id=settings.agent_model_primary, api_key=api_key)  # gpt-5.1 or gpt-5
        # Fall back to Gemini 3.0 Pro if OpenAI not available
        elif provider_registry.has_gemini_key():
            api_key = provider_registry.get_gemini_key()
            if api_key:
                return Gemini(id=settings.agent_model_tertiary, api_key=api_key)  # gemini-3.0-pro
        # Last resort: Claude 4 Sonnet
        elif provider_registry.has_claude_key():
            api_key = provider_registry.get_claude_key()
            if api_key:
                return Claude(id=settings.agent_model_secondary, api_key=api_key)
        # Return None instead of raising - allows lazy initialization
        # The agent will fail when actually used, not during initialization
        return None
    
    def _ensure_agent_initialized(self):
        """Ensure agent is initialized with a model. Reinitialize if needed."""
        if self.agno_agent is None:
            model = self._get_agno_model()
            if model is None:
                raise ValueError("No AI provider configured. Please configure at least one provider (OpenAI, Claude, or Gemini) before using this agent.")
            
            # Setup RAG knowledge base if enabled
            knowledge = None
            if self.enable_rag:
                knowledge = self._create_knowledge_base(self.rag_table_name)
            
            # Create Agno agent
            self.agno_agent = Agent(
                name=self.name,
                model=model,
                instructions=self.system_prompt,
                knowledge=knowledge,
                tools=[],
                markdown=True,
            )
            
            self.logger.info("agno_agent_initialized_lazy", agent=self.name, role=self.role)
    
    def _create_knowledge_base(self, table_name: str) -> Optional[Any]:
        """Create knowledge base with pgvector for RAG."""
        if not AGNO_AVAILABLE:
            return None
        try:
            # Get embedder based on available provider
            embedder = None
            if provider_registry.has_openai_key() and OpenAIEmbedder:
                try:
                    api_key = provider_registry.get_openai_key()
                    # OpenAIEmbedder may need api_key parameter
                    try:
                        embedder = OpenAIEmbedder(api_key=api_key)
                    except TypeError:
                        # If api_key parameter not accepted, try without it (may use env var)
                        embedder = OpenAIEmbedder()
                except Exception as e:
                    self.logger.warning("openai_embedder_init_failed", error=str(e))
            elif provider_registry.has_claude_key() and AnthropicEmbedder:
                try:
                    api_key = provider_registry.get_claude_key()
                    try:
                        embedder = AnthropicEmbedder(api_key=api_key)
                    except TypeError:
                        embedder = AnthropicEmbedder()
                except Exception as e:
                    self.logger.warning("anthropic_embedder_init_failed", error=str(e))
            elif provider_registry.has_gemini_key() and GoogleEmbedder:
                try:
                    api_key = provider_registry.get_gemini_key()
                    try:
                        embedder = GoogleEmbedder(api_key=api_key)
                    except TypeError:
                        embedder = GoogleEmbedder()
                except Exception as e:
                    self.logger.warning("google_embedder_init_failed", error=str(e))
            
            if not embedder:
                self.logger.warning("no_embedder_available", message="RAG enabled but no embedder available")
                return None
            
            # Create pgvector database connection
            vector_db = PgVector(
                table_name=table_name,
                db_url=settings.database_url,
                search_type=SearchType.similarity,
            )
            
            # Create knowledge base
            from agno.knowledge.knowledge import Knowledge
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
    
    def _update_model_api_key(self):
        """Update the model's API key from provider registry if available.
        Recreates the model if necessary to ensure API key is properly set.
        """
        try:
            if self.agno_agent is None or not hasattr(self.agno_agent, 'model') or not self.agno_agent.model:
                return
            
            # Get the current model type and ID
            current_model = self.agno_agent.model
            model_id = None
            if hasattr(current_model, 'id'):
                model_id = current_model.id
            elif hasattr(current_model, 'model'):
                model_id = current_model.model
            
            # Determine which provider to use and get API key
            new_model = None
            if provider_registry.has_openai_key():
                api_key = provider_registry.get_openai_key()
                if api_key:
                    new_model = OpenAIChat(
                        id=model_id or settings.agent_model_primary,
                        api_key=api_key
                    )
            elif provider_registry.has_claude_key():
                api_key = provider_registry.get_claude_key()
                if api_key:
                    new_model = Claude(
                        id=model_id or settings.agent_model_secondary,
                        api_key=api_key
                    )
            elif provider_registry.has_gemini_key():
                api_key = provider_registry.get_gemini_key()
                if api_key:
                    new_model = Gemini(
                        id=model_id or settings.agent_model_tertiary,
                        api_key=api_key
                    )
            
            # Update the agent's model if we created a new one
            if new_model:
                self.agno_agent.model = new_model
                self.logger.debug("model_api_key_updated", agent=self.name, provider=type(new_model).__name__)
        except Exception as e:
            self.logger.warning("failed_to_update_model_api_key", error=str(e))
    
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
        # Ensure agent is initialized before processing
        self._ensure_agent_initialized()
        try:
            # Update model API key from provider registry before processing
            # This ensures user-specific keys are used
            self._update_model_api_key()
            
            # Convert messages to query string
            query = self._format_messages_to_query(messages, context)
            
            # Run Agno agent (run is synchronous, wrap in asyncio for async context)
            import asyncio
            response = await asyncio.to_thread(self.agno_agent.run, query)
            
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
    
    def set_coordinator(self, coordinator: Union['AgnoCoordinatorAgent', 'AgnoEnhancedCoordinator']):
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
        if self.agno_agent is not None and hasattr(self.agno_agent, 'knowledge') and self.agno_agent.knowledge:
            try:
                self.agno_agent.knowledge.load(content=content, metadata=metadata or {})
                self.logger.info("content_added_to_knowledge_base", agent=self.name)
            except Exception as e:
                self.logger.error("failed_to_add_to_knowledge_base", error=str(e))
        else:
            self.logger.warning("knowledge_base_not_available", agent=self.name)

