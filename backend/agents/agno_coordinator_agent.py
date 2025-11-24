"""
Agno Coordinator Agent using Agno Teams
Manages multi-agent coordination using Agno's team functionality
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog

try:
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat
    from agno.models.anthropic import Claude
    from agno.models.google import Gemini
    AGNO_AVAILABLE = True
except ImportError as e:
    AGNO_AVAILABLE = False
    import structlog
    structlog.get_logger().warning("agno_framework_not_available", error=str(e))

from backend.agents.agno_base_agent import AgnoBaseAgent
from backend.agents.agno_prd_authoring_agent import AgnoPRDAuthoringAgent
from backend.agents.agno_ideation_agent import AgnoIdeationAgent
from backend.agents.agno_research_agent import AgnoResearchAgent
from backend.agents.agno_analysis_agent import AgnoAnalysisAgent
from backend.agents.rag_agent import RAGAgent
from backend.models.schemas import AgentMessage, AgentResponse, AgentInteraction, AgentCapability
from backend.services.provider_registry import provider_registry
from backend.config import settings

logger = structlog.get_logger()


class AgnoCoordinatorAgent:
    """Coordinator Agent using Agno Teams for multi-agent orchestration."""
    
    def __init__(self, enable_rag: bool = True):
        """Initialize Coordinator Agent with all specialized agents using Agno."""
        if not AGNO_AVAILABLE:
            raise ImportError("Agno framework is not available. Install with: pip install agno")
        
        # Initialize all agents with Agno
        self.research_agent = AgnoResearchAgent(enable_rag=enable_rag)
        self.analysis_agent = AgnoAnalysisAgent(enable_rag=enable_rag)
        self.ideation_agent = AgnoIdeationAgent(enable_rag=enable_rag)
        self.prd_agent = AgnoPRDAuthoringAgent(enable_rag=enable_rag)
        self.rag_agent = RAGAgent()  # RAG agent always has RAG enabled
        
        # Register all agents
        self.agents: Dict[str, AgnoBaseAgent] = {
            "research": self.research_agent,
            "analysis": self.analysis_agent,
            "ideation": self.ideation_agent,
            "prd_authoring": self.prd_agent,
            "rag": self.rag_agent,
        }
        
        # Set coordinator reference for agent-to-agent communication
        for agent in self.agents.values():
            agent.set_coordinator(self)
        
        # Create Agno teams for different coordination modes
        self._create_agno_teams()
        
        self.logger = logger.bind(component="agno_coordinator")
        self.interaction_history: List[AgentInteraction] = []
    
    def _get_agno_model(self):
        """Get appropriate Agno model based on provider registry."""
        if provider_registry.has_openai_key():
            return OpenAIChat(id=settings.agent_model_primary)
        elif provider_registry.has_claude_key():
            return Claude(id=settings.agent_model_secondary)
        elif provider_registry.has_gemini_key():
            return Gemini(id=settings.agent_model_tertiary)
        else:
            raise ValueError("No AI provider configured")
    
    def _create_agno_teams(self):
        """Create Agno teams for different coordination modes."""
        model = self._get_agno_model()
        
        # Collaborative team: Primary agent consults supporting agents
        self.collaborative_team = Agent(
            name="Collaborative Product Team",
            model=model,
            team=[
                self.research_agent.agno_agent,
                self.analysis_agent.agno_agent,
                self.prd_agent.agno_agent,
                self.rag_agent.agno_agent,
            ],
            instructions=[
                "You coordinate a team of specialized agents to answer user queries.",
                "When a user asks about product requirements:",
                "1. First, have the research agent gather market and competitive information",
                "2. Then, have the analysis agent perform strategic analysis",
                "3. Use the RAG agent to retrieve relevant knowledge from the knowledge base",
                "4. Finally, have the PRD agent create a comprehensive PRD based on all gathered information",
                "5. Synthesize the final response combining all insights"
            ],
            show_tool_calls=True,
            markdown=True
        )
        
        # Sequential team: Agents work one after another
        self.sequential_team = Agent(
            name="Sequential Product Team",
            model=model,
            team=[
                self.research_agent.agno_agent,
                self.analysis_agent.agno_agent,
                self.prd_agent.agno_agent,
            ],
            instructions=[
                "Agents work sequentially, each building on the previous agent's output.",
                "1. Research agent gathers information",
                "2. Analysis agent analyzes the research",
                "3. PRD agent creates PRD based on analysis"
            ],
            show_tool_calls=True,
            markdown=True
        )
        
        # Parallel team: All agents respond simultaneously
        self.parallel_team = Agent(
            name="Parallel Product Team",
            model=model,
            team=[
                self.research_agent.agno_agent,
                self.analysis_agent.agno_agent,
                self.ideation_agent.agno_agent,
                self.prd_agent.agno_agent,
            ],
            instructions=[
                "All agents respond to the query simultaneously.",
                "Each agent provides their perspective independently.",
                "Synthesize all responses into a comprehensive answer."
            ],
            show_tool_calls=True,
            markdown=True
        )
    
    def get_agent_capabilities(self) -> List[AgentCapability]:
        """Get capabilities of all agents."""
        capabilities = []
        for agent_type, agent in self.agents.items():
            capabilities.append(AgentCapability(
                agent_type=agent_type,
                capabilities=agent.capabilities,
                description=agent.system_prompt[:200] + "..." if len(agent.system_prompt) > 200 else agent.system_prompt
            ))
        return capabilities
    
    def determine_primary_agent(self, query: str) -> tuple[str, float]:
        """Determine the best agent to handle a query."""
        query_lower = query.lower()
        best_agent = None
        best_confidence = 0.0
        
        for agent_type, agent in self.agents.items():
            confidence = agent.get_confidence(query)
            if confidence > best_confidence:
                best_confidence = confidence
                best_agent = agent_type
        
        # Default to ideation if no clear match
        if best_confidence < 0.3:
            best_agent = "ideation"
            best_confidence = 0.5
        
        return best_agent, best_confidence
    
    def determine_supporting_agents(self, query: str, primary_agent: str) -> List[str]:
        """Determine which supporting agents should be consulted."""
        query_lower = query.lower()
        supporting = []
        
        # Keywords that suggest multi-agent collaboration
        if any(kw in query_lower for kw in ["research", "market", "competitive", "trend"]):
            if primary_agent != "research":
                supporting.append("research")
        
        if any(kw in query_lower for kw in ["analyze", "swot", "feasibility", "risk"]):
            if primary_agent != "analysis":
                supporting.append("analysis")
        
        if any(kw in query_lower for kw in ["knowledge", "document", "search", "retrieve"]):
            if primary_agent != "rag":
                supporting.append("rag")
        
        return supporting
    
    async def route_agent_consultation(
        self,
        from_agent: str,
        to_agent: str,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentInteraction:
        """Route a consultation request from one agent to another."""
        if to_agent not in self.agents:
            raise ValueError(f"Unknown agent type: {to_agent}")
        
        target_agent = self.agents[to_agent]
        
        # Create consultation message
        consultation_message = AgentMessage(
            role="user",
            content=f"[Consultation from {from_agent}]: {query}",
            timestamp=datetime.utcnow()
        )
        
        # Process with target agent
        response = await target_agent.process([consultation_message], context=context)
        
        # Create interaction record
        interaction = AgentInteraction(
            from_agent=from_agent,
            to_agent=to_agent,
            query=query,
            response=response.response,
            metadata=response.metadata
        )
        
        self.interaction_history.append(interaction)
        self.logger.info(
            "agent_consultation",
            from_agent=from_agent,
            to_agent=to_agent,
            query_length=len(query)
        )
        
        return interaction
    
    async def process_collaborative(
        self,
        query: str,
        primary_agent: str,
        supporting_agents: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """Process query collaboratively using Agno team."""
        try:
            # Use Agno collaborative team
            enhanced_query = query
            if context:
                import json
                enhanced_query += f"\n\nContext: {json.dumps(context, indent=2)}"
            
            import asyncio
            response = await asyncio.to_thread(self.collaborative_team.run, enhanced_query)
            
            return AgentResponse(
                agent_type="multi_agent",
                response=response.content if hasattr(response, 'content') else str(response),
                metadata={
                    "mode": "collaborative",
                    "primary_agent": primary_agent,
                    "supporting_agents": supporting_agents or [],
                    "team_members": [agent.name for agent in self.collaborative_team.team]
                },
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            self.logger.error("collaborative_processing_error", error=str(e))
            raise
    
    async def process_sequential(
        self,
        query: str,
        agents: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """Process query sequentially using Agno team."""
        try:
            enhanced_query = query
            if context:
                import json
                enhanced_query += f"\n\nContext: {json.dumps(context, indent=2)}"
            
            import asyncio
            response = await asyncio.to_thread(self.sequential_team.run, enhanced_query)
            
            return AgentResponse(
                agent_type="multi_agent",
                response=response.content if hasattr(response, 'content') else str(response),
                metadata={"mode": "sequential", "agents": agents},
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            self.logger.error("sequential_processing_error", error=str(e))
            raise
    
    async def process_parallel(
        self,
        query: str,
        agents: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """Process query in parallel using Agno team."""
        try:
            enhanced_query = query
            if context:
                import json
                enhanced_query += f"\n\nContext: {json.dumps(context, indent=2)}"
            
            import asyncio
            response = await asyncio.to_thread(self.parallel_team.run, enhanced_query)
            
            return AgentResponse(
                agent_type="multi_agent",
                response=response.content if hasattr(response, 'content') else str(response),
                metadata={"mode": "parallel", "agents": agents},
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            self.logger.error("parallel_processing_error", error=str(e))
            raise
    
    async def route_query(
        self,
        query: str,
        coordination_mode: str = "collaborative",
        primary_agent: Optional[str] = None,
        supporting_agents: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """Route a query based on coordination mode."""
        # Auto-determine agents if not specified
        if not primary_agent:
            primary_agent, confidence = self.determine_primary_agent(query)
            self.logger.info("auto_routed", primary_agent=primary_agent, confidence=confidence)
        
        if coordination_mode == "sequential":
            agents = [primary_agent] + (supporting_agents or [])
            return await self.process_sequential(query, agents, context)
        
        elif coordination_mode == "parallel":
            agents = [primary_agent] + (supporting_agents or [])
            return await self.process_parallel(query, agents, context)
        
        elif coordination_mode == "collaborative":
            return await self.process_collaborative(query, primary_agent, supporting_agents, context)
        
        else:
            raise ValueError(f"Unknown coordination mode: {coordination_mode}")
    
    def get_interaction_history(self) -> List[AgentInteraction]:
        """Get all agent interactions."""
        return self.interaction_history.copy()

