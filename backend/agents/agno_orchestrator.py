"""
Agno-based Orchestrator
Manages agent workflows using Agno framework
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
import structlog

from backend.agents.agno_coordinator_agent import AgnoCoordinatorAgent
from backend.agents.agno_enhanced_coordinator import AgnoEnhancedCoordinator
from backend.agents.agno_prd_authoring_agent import AgnoPRDAuthoringAgent
from backend.agents.agno_ideation_agent import AgnoIdeationAgent
from backend.agents.agno_summary_agent import AgnoSummaryAgent
from backend.agents.agno_scoring_agent import AgnoScoringAgent
from backend.agents.rag_agent import RAGAgent
from backend.models.schemas import AgentMessage, AgentResponse, MultiAgentRequest, MultiAgentResponse, AgentInteraction

logger = structlog.get_logger()


class AgnoAgenticOrchestrator:
    """Orchestrator using Agno framework for agent management."""
    
    def __init__(self, enable_rag: bool = True, use_enhanced: bool = True):
        """Initialize orchestrator with Agno coordinator and agents."""
        if use_enhanced:
            self.coordinator = AgnoEnhancedCoordinator(enable_rag=enable_rag)
        else:
            self.coordinator = AgnoCoordinatorAgent(enable_rag=enable_rag)
        
        self.agents: Dict[str, Any] = {
            "prd_authoring": AgnoPRDAuthoringAgent(enable_rag=enable_rag),
            "ideation": AgnoIdeationAgent(enable_rag=enable_rag),
            "summary": AgnoSummaryAgent(enable_rag=enable_rag),
            "scoring": AgnoScoringAgent(enable_rag=enable_rag),
            "rag": RAGAgent(),  # RAG agent always has RAG enabled
        }
        self.logger = logger.bind(component="agno_orchestrator")
    
    async def route_request(
        self,
        user_id: UUID,
        product_id: Optional[UUID],
        agent_type: str,
        messages: List[AgentMessage],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """Route request to appropriate agent."""
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
            # Add product context if available
            enhanced_context = context or {}
            if product_id:
                enhanced_context["product_id"] = str(product_id)
            
            response = await agent.process(messages, enhanced_context)
            
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
    
    async def process_multi_agent_request(
        self,
        user_id: UUID,
        request: MultiAgentRequest
    ) -> MultiAgentResponse:
        """Process a multi-agent coordination request using Agno teams."""
        self.logger.info(
            "multi_agent_request",
            user_id=str(user_id),
            coordination_mode=request.coordination_mode,
            primary_agent=request.primary_agent,
            supporting_agents=request.supporting_agents
        )
        
        try:
            # Add user and product context
            enhanced_context = request.context or {}
            enhanced_context["user_id"] = str(user_id)
            if hasattr(request, 'product_id') and request.product_id:
                enhanced_context["product_id"] = str(request.product_id)
            
            response = await self.coordinator.route_query(
                query=request.query,
                coordination_mode=request.coordination_mode,
                primary_agent=request.primary_agent,
                supporting_agents=request.supporting_agents,
                context=enhanced_context
            )
            
            # Get interaction history
            interactions = self.coordinator.get_interaction_history()
            
            metadata = dict(response.metadata or {})
            metadata.update({
                "supporting_agents": request.supporting_agents,
                "user_id": str(user_id)
            })
            
            return MultiAgentResponse(
                primary_agent=request.primary_agent or response.agent_type,
                response=response.response,
                agent_interactions=interactions[-10:],  # Last 10 interactions
                coordination_mode=request.coordination_mode,
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error("multi_agent_error", error=str(e), user_id=str(user_id))
            raise
    
    def get_available_agents(self) -> List[Dict[str, str]]:
        """Get all available agents."""
        agents = [
            {
                "type": agent_type,
                "name": agent.name,
                "role": agent.role
            }
            for agent_type, agent in self.agents.items()
        ]
        
        # Add coordinator agents
        coordinator_agents = [
            {
                "type": agent_type,
                "name": agent.name,
                "role": agent.role
            }
            for agent_type, agent in self.coordinator.agents.items()
        ]
        
        return agents + coordinator_agents
    
    def get_agent_capabilities(self) -> List[Dict[str, Any]]:
        """Get capabilities of all agents."""
        capabilities = self.coordinator.get_agent_capabilities()
        return [cap.dict() for cap in capabilities]

