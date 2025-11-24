from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
import structlog

from backend.agents.base_agent import BaseAgent
from backend.agents.research_agent import ResearchAgent
from backend.agents.analysis_agent import AnalysisAgent
from backend.agents.validation_agent import ValidationAgent
from backend.agents.strategy_agent import StrategyAgent
from backend.agents.ideation_agent import IdeationAgent
from backend.agents.prd_authoring_agent import PRDAuthoringAgent
from backend.agents.jira_agent import JiraAgent
from backend.agents.v0_agent import V0Agent
from backend.agents.lovable_agent import LovableAgent
from backend.models.schemas import AgentMessage, AgentResponse, AgentInteraction, AgentCapability

logger = structlog.get_logger()


class CoordinatorAgent:
    """Coordinator Agent that routes queries and orchestrates multi-agent workflows."""
    
    def __init__(self):
        """Initialize Coordinator Agent with all specialized agents."""
        # Initialize all agents
        self.research_agent = ResearchAgent()
        self.analysis_agent = AnalysisAgent()
        self.validation_agent = ValidationAgent()
        self.strategy_agent = StrategyAgent()
        self.ideation_agent = IdeationAgent()
        self.prd_agent = PRDAuthoringAgent()
        self.jira_agent = JiraAgent()
        self.v0_agent = V0Agent()
        self.lovable_agent = LovableAgent()
        
        # Register all agents
        self.agents: Dict[str, BaseAgent] = {
            "research": self.research_agent,
            "analysis": self.analysis_agent,
            "validation": self.validation_agent,
            "strategy": self.strategy_agent,
            "ideation": self.ideation_agent,
            "prd_authoring": self.prd_agent,
            "jira_integration": self.jira_agent,
            "v0_design": self.v0_agent,
            "lovable_design": self.lovable_agent,
        }
        
        # Set coordinator reference for agent-to-agent communication
        for agent in self.agents.values():
            agent.set_coordinator(self)
        
        self.logger = logger.bind(component="coordinator")
        self.interaction_history: List[AgentInteraction] = []
    
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
        """Determine the best agent to handle a query.
        
        Returns:
            Tuple of (agent_type, confidence_score)
        """
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
        
        if any(kw in query_lower for kw in ["validate", "check", "review", "quality"]):
            if primary_agent != "validation":
                supporting.append("validation")
        
        if any(kw in query_lower for kw in ["strategy", "roadmap", "gtm", "plan"]):
            if primary_agent != "strategy":
                supporting.append("strategy")
        
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
    
    async def process_sequential(
        self,
        query: str,
        agents: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> List[AgentResponse]:
        """Process query sequentially through multiple agents."""
        responses = []
        previous_response = None
        
        for agent_type in agents:
            if agent_type not in self.agents:
                continue
            
            agent = self.agents[agent_type]
            
            # Build message with previous agent's response as context
            if previous_response:
                message_content = f"{query}\n\nPrevious agent's response:\n{previous_response.response}"
            else:
                message_content = query
            
            message = AgentMessage(
                role="user",
                content=message_content,
                timestamp=datetime.utcnow()
            )
            
            response = await agent.process([message], context=context)
            responses.append(response)
            previous_response = response
        
        return responses
    
    async def process_parallel(
        self,
        query: str,
        agents: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> List[AgentResponse]:
        """Process query in parallel across multiple agents."""
        import asyncio
        
        async def process_agent(agent_type: str) -> AgentResponse:
            if agent_type not in self.agents:
                return None
            
            agent = self.agents[agent_type]
            message = AgentMessage(
                role="user",
                content=query,
                timestamp=datetime.utcnow()
            )
            
            return await agent.process([message], context=context)
        
        tasks = [process_agent(agent_type) for agent_type in agents]
        responses = await asyncio.gather(*tasks)
        
        return [r for r in responses if r is not None]
    
    async def process_collaborative(
        self,
        query: str,
        primary_agent: str,
        supporting_agents: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """Process query collaboratively with primary agent consulting supporting agents."""
        if primary_agent not in self.agents:
            raise ValueError(f"Unknown primary agent: {primary_agent}")
        
        primary = self.agents[primary_agent]
        supporting = supporting_agents or []
        
        # Primary agent can consult supporting agents
        consultation_context = {}
        for supporting_agent in supporting:
            if supporting_agent in self.agents:
                try:
                    consultation = await self.route_agent_consultation(
                        from_agent=primary_agent,
                        to_agent=supporting_agent,
                        query=query,
                        context=context
                    )
                    consultation_context[supporting_agent] = consultation.response
                except Exception as e:
                    self.logger.error("consultation_error", error=str(e), supporting_agent=supporting_agent)
        
        # Add consultation results to context
        enhanced_context = {**(context or {}), "consultations": consultation_context}
        
        # Process with primary agent
        message = AgentMessage(
            role="user",
            content=query,
            timestamp=datetime.utcnow()
        )
        
        response = await primary.process([message], context=enhanced_context)
        
        return response
    
    async def process_debate(
        self,
        query: str,
        agents: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """Process query through debate mode with multiple agents."""
        if len(agents) < 2:
            raise ValueError("Debate mode requires at least 2 agents")
        
        # Round 1: Initial positions
        round1_responses = await self.process_parallel(query, agents, context)
        
        # Round 2: Responses to other agents
        round2_prompts = []
        for i, response in enumerate(round1_responses):
            other_responses = [r.response for j, r in enumerate(round1_responses) if j != i]
            debate_prompt = f"""Original Query: {query}

Your initial response:
{response.response}

Other agents' responses:
{chr(10).join(f"Agent {j+1}: {resp}" for j, resp in enumerate(other_responses))}

Please:
1. Review other agents' perspectives
2. Refine or defend your position
3. Identify areas of agreement or disagreement
4. Provide a final synthesis"""
            
            round2_prompts.append(debate_prompt)
        
        # Get round 2 responses
        round2_responses = []
        for i, agent_type in enumerate(agents):
            if agent_type in self.agents:
                agent = self.agents[agent_type]
                message = AgentMessage(
                    role="user",
                    content=round2_prompts[i],
                    timestamp=datetime.utcnow()
                )
                response = await agent.process([message], context=context)
                round2_responses.append(response)
        
        # Final synthesis (use analysis agent for synthesis)
        synthesis_prompt = f"""Original Query: {query}

Agent Positions (Round 1):
{chr(10).join(f"{agents[i]}: {r.response[:500]}..." for i, r in enumerate(round1_responses))}

Agent Refinements (Round 2):
{chr(10).join(f"{agents[i]}: {r.response[:500]}..." for i, r in enumerate(round2_responses))}

Please provide a comprehensive synthesis that:
1. Summarizes all perspectives
2. Identifies key agreements and disagreements
3. Provides a balanced, well-reasoned conclusion
4. Highlights actionable recommendations"""
        
        synthesis_message = AgentMessage(
            role="user",
            content=synthesis_prompt,
            timestamp=datetime.utcnow()
        )
        
        synthesis_response = await self.analysis_agent.process([synthesis_message], context=context)
        
        return synthesis_response
    
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
            responses = await self.process_sequential(query, agents, context)
            return responses[-1] if responses else AgentResponse(
                agent_type="coordinator",
                response="No agents available",
                timestamp=datetime.utcnow()
            )
        
        elif coordination_mode == "parallel":
            agents = [primary_agent] + (supporting_agents or [])
            responses = await self.process_parallel(query, agents, context)
            # Combine parallel responses
            combined = "\n\n".join([f"**{r.agent_type}**:\n{r.response}" for r in responses])
            return AgentResponse(
                agent_type="multi_agent",
                response=combined,
                metadata={"mode": "parallel", "agents": agents},
                timestamp=datetime.utcnow()
            )
        
        elif coordination_mode == "collaborative":
            return await self.process_collaborative(
                query, primary_agent, supporting_agents, context
            )
        
        elif coordination_mode == "debate":
            agents = [primary_agent] + (supporting_agents or [])
            return await self.process_debate(query, agents, context)
        
        else:
            raise ValueError(f"Unknown coordination mode: {coordination_mode}")
    
    def get_interaction_history(self) -> List[AgentInteraction]:
        """Get all agent interactions."""
        return self.interaction_history.copy()

