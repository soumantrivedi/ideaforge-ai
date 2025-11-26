"""
Enhanced Agno Coordinator with Heavy Contextualization
Ensures agents coordinate and share context before responding
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
from backend.agents.agno_summary_agent import AgnoSummaryAgent
from backend.agents.agno_scoring_agent import AgnoScoringAgent
from backend.agents.agno_validation_agent import AgnoValidationAgent
from backend.agents.agno_export_agent import AgnoExportAgent
from backend.agents.agno_v0_agent import AgnoV0Agent
from backend.agents.agno_lovable_agent import AgnoLovableAgent
from backend.agents.rag_agent import RAGAgent
from backend.models.schemas import AgentMessage, AgentResponse, AgentInteraction, AgentCapability
from backend.services.provider_registry import provider_registry
from backend.config import settings

logger = structlog.get_logger()


class AgnoEnhancedCoordinator:
    """
    Enhanced Coordinator with heavy contextualization.
    Agents coordinate and share context before providing full responses.
    """
    
    def __init__(self, enable_rag: bool = True):
        """Initialize Enhanced Coordinator with all agents."""
        if not AGNO_AVAILABLE:
            raise ImportError("Agno framework is not available. Install with: pip install agno")
        
        # Initialize all agents
        self.research_agent = AgnoResearchAgent(enable_rag=enable_rag)
        self.analysis_agent = AgnoAnalysisAgent(enable_rag=enable_rag)
        self.ideation_agent = AgnoIdeationAgent(enable_rag=enable_rag)
        self.prd_agent = AgnoPRDAuthoringAgent(enable_rag=enable_rag)
        self.summary_agent = AgnoSummaryAgent(enable_rag=enable_rag)
        self.scoring_agent = AgnoScoringAgent(enable_rag=enable_rag)
        self.validation_agent = AgnoValidationAgent(enable_rag=enable_rag)
        self.export_agent = AgnoExportAgent(enable_rag=enable_rag)
        self.v0_agent = AgnoV0Agent(enable_rag=enable_rag)
        self.lovable_agent = AgnoLovableAgent(enable_rag=enable_rag)
        self.rag_agent = RAGAgent()
        
        # Register all agents
        self.agents: Dict[str, AgnoBaseAgent] = {
            "research": self.research_agent,
            "analysis": self.analysis_agent,
            "ideation": self.ideation_agent,
            "prd_authoring": self.prd_agent,
            "summary": self.summary_agent,
            "scoring": self.scoring_agent,
            "validation": self.validation_agent,
            "export": self.export_agent,
            "v0": self.v0_agent,
            "lovable": self.lovable_agent,
            "rag": self.rag_agent,
        }
        
        # Set coordinator reference
        for agent in self.agents.values():
            agent.set_coordinator(self)
        
        # Create enhanced teams with heavy coordination
        self._create_enhanced_teams()
        
        self.logger = logger.bind(component="enhanced_coordinator")
        self.interaction_history: List[AgentInteraction] = []
        self.shared_context: Dict[str, Any] = {
            "conversation_history": [],  # All chatbot messages
            "ideation_content": [],  # Extracted ideation from conversations
            "product_context": {},  # Product-specific context
            "phase_context": {},  # Lifecycle phase context
            "user_inputs": []  # All user inputs from chatbot
        }
    
    def _get_agno_model(self):
        """Get appropriate Agno model.
        Priority: ChatGPT 5.1 (primary) > Gemini 3.0 Pro (tertiary) > Claude 4 Sonnet (secondary)
        Prefers ChatGPT 5.1 for best reasoning, falls back to Gemini 3.0 Pro if OpenAI not available.
        """
        # Prefer ChatGPT 5.1 for best reasoning capabilities
        if provider_registry.has_openai_key():
            return OpenAIChat(id=settings.agent_model_primary)  # gpt-5.1
        # Fall back to Gemini 3.0 Pro if OpenAI not available
        elif provider_registry.has_gemini_key():
            return Gemini(id=settings.agent_model_tertiary)  # gemini-3.0-pro
        # Last resort: Claude 4 Sonnet
        elif provider_registry.has_claude_key():
            return Claude(id=settings.agent_model_secondary)
        else:
            raise ValueError("No AI provider configured")
    
    def _create_enhanced_teams(self):
        """Create enhanced coordination logic.
        Note: Agno Agent doesn't support 'team' parameter directly.
        We use agent consultation via route_agent_consultation instead.
        """
        # Agno doesn't support team parameter, so we'll use agent consultation
        # The coordination happens via process_with_context which uses
        # route_agent_consultation to coordinate agents
        pass
    
    async def process_with_context(
        self,
        query: str,
        product_id: Optional[str] = None,
        session_ids: Optional[List[str]] = None,
        user_context: Optional[Dict[str, Any]] = None,
        coordination_mode: str = "enhanced_collaborative",
        db: Optional[Any] = None
    ) -> AgentResponse:
        """
        Process query with heavy contextualization from multiple sources.
        Automatically loads conversation history into shared context.
        
        Args:
            query: User query
            product_id: Product ID for context
            session_ids: List of session IDs to include in context
            user_context: Additional user context
            coordination_mode: Coordination mode to use
            db: Database session for loading conversation history
        """
        try:
            # Build comprehensive context (includes loading conversation history)
            context = await self._build_comprehensive_context(
                product_id=product_id,
                session_ids=session_ids,
                user_context=user_context,
                db=db
            )
            
            # Enhance query with context
            enhanced_query = self._enhance_query_with_context(query, context)
            
            # Process with enhanced coordination using agent consultation
            # Start with RAG agent for context
            rag_response = await self.rag_agent.process(
                [AgentMessage(role="user", content=enhanced_query, timestamp=datetime.utcnow())],
                context
            )
            
            # Then research agent
            research_query = f"{enhanced_query}\n\nKnowledge Base Context:\n{rag_response.response}"
            research_response = await self.research_agent.process(
                [AgentMessage(role="user", content=research_query, timestamp=datetime.utcnow())],
                context
            )
            
            # Then analysis agent
            analysis_query = f"{enhanced_query}\n\nResearch Context:\n{research_response.response}"
            analysis_response = await self.analysis_agent.process(
                [AgentMessage(role="user", content=analysis_query, timestamp=datetime.utcnow())],
                context
            )
            
            # Then ideation agent
            ideation_query = f"{enhanced_query}\n\nAnalysis Context:\n{analysis_response.response}"
            ideation_response = await self.ideation_agent.process(
                [AgentMessage(role="user", content=ideation_query, timestamp=datetime.utcnow())],
                context
            )
            
            # Finally PRD agent with all context
            prd_query = f"{enhanced_query}\n\nFull Context:\nKnowledge: {rag_response.response}\nResearch: {research_response.response}\nAnalysis: {analysis_response.response}\nIdeation: {ideation_response.response}"
            prd_response = await self.prd_agent.process(
                [AgentMessage(role="user", content=prd_query, timestamp=datetime.utcnow())],
                context
            )
            
            # Use PRD response as final response (most comprehensive)
            final_response = prd_response.response
            
            # Update shared context with latest interaction
            self.shared_context.update({
                "last_query": query,
                "last_response": final_response,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Add current query/response to conversation history in shared context
            if "conversation_history" not in self.shared_context:
                self.shared_context["conversation_history"] = []
            
            self.shared_context["conversation_history"].append({
                "role": "user",
                "content": query,
                "timestamp": datetime.utcnow().isoformat()
            })
            self.shared_context["conversation_history"].append({
                "role": "assistant",
                "content": final_response,
                "agent_name": "multi_agent_enhanced",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Update ideation content if query contains ideation
            if any(keyword in query.lower() for keyword in ["idea", "ideation", "concept", "feature", "requirement"]):
                if "ideation_content" not in self.shared_context:
                    self.shared_context["ideation_content"] = []
                self.shared_context["ideation_content"].append(query)
            
            return AgentResponse(
                agent_type="multi_agent_enhanced",
                response=final_response,
                metadata={
                    "mode": coordination_mode,
                    "context_sources": list(context.keys()),
                    "session_ids": session_ids or [],
                    "product_id": product_id,
                    "team_members": list(self.agents.keys())
                },
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            self.logger.error("enhanced_processing_error", error=str(e))
            raise
    
    async def load_conversation_history(
        self,
        product_id: Optional[str] = None,
        session_ids: Optional[List[str]] = None,
        db: Optional[Any] = None
    ):
        """Load conversation history from database and store in shared context."""
        if not db or not product_id:
            return
        
        try:
            from sqlalchemy import text
            
            # Load conversation history for the product
            conv_query = text("""
                SELECT ch.message_type, ch.content, ch.agent_name, ch.agent_role, ch.created_at
                FROM conversation_history ch
                WHERE ch.product_id = :product_id
                ORDER BY ch.created_at ASC
            """)
            conv_result = await db.execute(conv_query, {"product_id": str(product_id)})
            conv_rows = conv_result.fetchall()
            
            conversation_history = [
                {
                    "role": row[0],
                    "content": row[1],
                    "agent_name": row[2],
                    "agent_role": row[3],
                    "timestamp": row[4].isoformat() if row[4] else None
                }
                for row in conv_rows
            ]
            
            # Store in shared context
            self.shared_context["conversation_history"] = conversation_history
            
            # Extract ideation and relevant content
            ideation_content = self._extract_ideation_from_history(conversation_history)
            self.shared_context["ideation_content"] = ideation_content
            
            # Extract user inputs
            user_inputs = [
                msg["content"] for msg in conversation_history
                if msg.get("role") in ["user", "human"]
            ]
            self.shared_context["user_inputs"] = user_inputs
            
            # Store product context
            self.shared_context["product_context"]["product_id"] = product_id
            self.shared_context["product_context"]["conversation_count"] = len(conversation_history)
            
            self.logger.info(
                "conversation_history_loaded_to_shared_context",
                product_id=str(product_id),
                message_count=len(conversation_history),
                ideation_snippets=len(ideation_content)
            )
            
        except Exception as e:
            self.logger.warning("failed_to_load_conversation_history", error=str(e))
    
    def _extract_ideation_from_history(self, conversation_history: List[Dict[str, Any]]) -> List[str]:
        """Extract ideation and relevant content from conversation history."""
        ideation_keywords = [
            "idea", "ideation", "concept", "product vision", "feature", "requirement",
            "user need", "problem", "solution", "goal", "objective", "purpose",
            "market", "research", "analysis", "strategy", "design", "architecture"
        ]
        
        ideation_messages = []
        for msg in conversation_history:
            content = msg.get("content", "").lower()
            role = msg.get("role", "")
            
            # Extract user messages that contain ideation keywords
            if role in ["user", "human"] and any(keyword in content for keyword in ideation_keywords):
                ideation_messages.append(msg.get("content", ""))
            
            # Also extract agent responses that might contain synthesized ideation
            elif role in ["assistant", "agent"] and any(keyword in content for keyword in ideation_keywords):
                # Only include if it's a synthesis or summary
                if any(word in content.lower() for word in ["based on", "considering", "synthesizing", "summary"]):
                    ideation_messages.append(msg.get("content", ""))
        
        return ideation_messages
    
    async def _build_comprehensive_context(
        self,
        product_id: Optional[str] = None,
        session_ids: Optional[List[str]] = None,
        user_context: Optional[Dict[str, Any]] = None,
        db: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Build comprehensive context from multiple sources."""
        # Load conversation history if product_id is available and not already loaded
        if product_id and db:
            # Check if we need to reload (product_id changed or no history loaded)
            current_product_id = self.shared_context.get("product_context", {}).get("product_id")
            if current_product_id != str(product_id) or not self.shared_context.get("conversation_history"):
                await self.load_conversation_history(product_id=product_id, session_ids=session_ids, db=db)
        
        context = {
            "shared_context": self.shared_context.copy(),
            "user_context": user_context or {}
        }
        
        # Add product context if available
        if product_id:
            context["product_id"] = product_id
        
        # Add session context if available
        if session_ids:
            context["session_ids"] = session_ids
        
        # Include conversation history and ideation in context
        if self.shared_context.get("conversation_history"):
            context["conversation_history"] = self.shared_context["conversation_history"]
            context["ideation_from_chat"] = "\n\n".join(self.shared_context.get("ideation_content", []))
            context["user_inputs"] = self.shared_context.get("user_inputs", [])
        
        # Retrieve knowledge from RAG
        if session_ids or product_id:
            try:
                rag_query = f"Product: {product_id}, Sessions: {', '.join(session_ids) if session_ids else 'N/A'}"
                knowledge_results = await self.rag_agent.search_knowledge(rag_query, top_k=10)
                context["knowledge_base"] = knowledge_results
            except Exception as e:
                self.logger.warning("rag_context_retrieval_failed", error=str(e))
        
        return context
    
    def _enhance_query_with_context(self, query: str, context: Dict[str, Any]) -> str:
        """Enhance query with comprehensive context including conversation history."""
        import json
        
        enhanced = f"""User Query: {query}

COMPREHENSIVE CONTEXT:
"""
        
        if context.get("product_id"):
            enhanced += f"\nProduct ID: {context['product_id']}\n"
        
        if context.get("session_ids"):
            enhanced += f"\nRelevant Sessions: {', '.join(context['session_ids'])}\n"
            enhanced += "Note: Include insights from these sessions in your response.\n"
        
        # Include conversation history and ideation from chatbot
        if context.get("conversation_history"):
            enhanced += "\n=== CONVERSATION HISTORY (Multi-Agent Memory) ===\n"
            enhanced += "All previous chatbot interactions for this product:\n"
            for msg in context["conversation_history"][-20:]:  # Last 20 messages
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                agent_name = msg.get("agent_name", "")
                if content:
                    agent_label = f" ({agent_name})" if agent_name else ""
                    enhanced += f"\n{role.upper()}{agent_label}: {content[:500]}\n"
            enhanced += "\n"
        
        if context.get("ideation_from_chat"):
            enhanced += "\n=== IDEATION FROM CHATBOT ===\n"
            enhanced += "Relevant ideation and product concepts from previous conversations:\n"
            enhanced += context["ideation_from_chat"][:2000] + "\n\n"
        
        if context.get("user_inputs"):
            enhanced += "\n=== USER INPUTS SUMMARY ===\n"
            enhanced += f"Total user inputs: {len(context['user_inputs'])}\n"
            enhanced += "Recent user inputs:\n"
            for user_input in context["user_inputs"][-5:]:  # Last 5 user inputs
                enhanced += f"- {user_input[:200]}\n"
            enhanced += "\n"
        
        if context.get("knowledge_base"):
            enhanced += "\n=== RELEVANT KNOWLEDGE FROM KNOWLEDGE BASE ===\n"
            for kb_item in context["knowledge_base"][:5]:  # Top 5
                enhanced += f"- {kb_item.get('content', '')[:200]}...\n"
        
        if context.get("shared_context"):
            shared = context["shared_context"]
            if shared.get("last_query") or shared.get("last_response"):
                enhanced += "\n=== PREVIOUS INTERACTIONS ===\n"
                if shared.get("last_query"):
                    enhanced += f"Last Query: {shared['last_query'][:200]}\n"
                if shared.get("last_response"):
                    enhanced += f"Last Response: {shared['last_response'][:200]}\n"
        
        if context.get("user_context"):
            enhanced += "\n=== ADDITIONAL USER CONTEXT ===\n"
            enhanced += json.dumps(context["user_context"], indent=2) + "\n"
        
        enhanced += """
INSTRUCTIONS:
- Use ALL provided context in your response, especially conversation history and ideation
- Reference specific information from chatbot conversations
- Synthesize ideation from previous conversations with current query
- Show how different pieces of information were synthesized
- Provide a comprehensive, heavily contextualized answer
- Coordinate with other agents to ensure complete coverage
- If user provided ideation externally via chatbot, incorporate it into your response
"""
        
        return enhanced
    
    async def route_agent_consultation(
        self,
        from_agent: str,
        to_agent: str,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentInteraction:
        """Route consultation with shared context."""
        # Enhance context with shared context
        enhanced_context = {**(context or {}), **self.shared_context}
        
        if to_agent not in self.agents:
            raise ValueError(f"Unknown agent type: {to_agent}")
        
        target_agent = self.agents[to_agent]
        
        consultation_message = AgentMessage(
            role="user",
            content=f"[Consultation from {from_agent}]: {query}\n\nShared Context: {self.shared_context}",
            timestamp=datetime.utcnow()
        )
        
        response = await target_agent.process([consultation_message], context=enhanced_context)
        
        # Build comprehensive metadata
        interaction_metadata = {
            "shared_context_used": True,
            "system_context": str(enhanced_context) if enhanced_context else None,
            "system_prompt": target_agent.system_prompt if hasattr(target_agent, 'system_prompt') else None,
            "rag_context": enhanced_context.get("rag_context") if enhanced_context else None,
            "user_prompt": query,
        }
        
        # Add response metadata if available
        if response.metadata:
            interaction_metadata.update(response.metadata)
        
        interaction = AgentInteraction(
            from_agent=from_agent,
            to_agent=to_agent,
            query=query,
            response=response.response,
            metadata=interaction_metadata
        )
        
        self.interaction_history.append(interaction)
        self.shared_context[f"{from_agent}_to_{to_agent}"] = response.response
        
        return interaction
    
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
    
    def get_interaction_history(self) -> List[AgentInteraction]:
        """Get all agent interactions."""
        return self.interaction_history.copy()
    
    def get_shared_context(self) -> Dict[str, Any]:
        """Get shared context."""
        return self.shared_context.copy()
    
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
        """Determine which supporting agents should be consulted.
        ALWAYS includes RAG agent for knowledge base context.
        """
        query_lower = query.lower()
        supporting = []
        
        # ALWAYS include RAG agent first (unless it's the primary agent)
        if primary_agent != "rag":
            supporting.append("rag")
        
        # Keywords that suggest multi-agent collaboration
        if any(kw in query_lower for kw in ["research", "market", "competitive", "trend"]):
            if primary_agent != "research":
                supporting.append("research")
        
        if any(kw in query_lower for kw in ["analyze", "swot", "feasibility", "risk"]):
            if primary_agent != "analysis":
                supporting.append("analysis")
        
        # RAG is already added above, so we don't need to add it again here
        
        return supporting
    
    async def route_query(
        self,
        query: str,
        coordination_mode: str = "enhanced_collaborative",
        primary_agent: Optional[str] = None,
        supporting_agents: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        db: Optional[Any] = None
    ) -> AgentResponse:
        """
        Route query to appropriate team or agent.
        Compatible with AgnoAgenticOrchestrator interface.
        """
        try:
            # Use process_with_context for enhanced coordination
            if coordination_mode == "enhanced_collaborative":
                product_id = context.get("product_id") if context else None
                session_ids = context.get("session_ids") if context else None
                user_context = {k: v for k, v in (context or {}).items() if k not in ["product_id", "session_ids"]}
                
                return await self.process_with_context(
                    query=query,
                    product_id=product_id,
                    session_ids=session_ids,
                    user_context=user_context,
                    coordination_mode=coordination_mode,
                    db=db
                )
            elif coordination_mode == "collaborative":
                # Handle collaborative mode similar to AgnoCoordinatorAgent
                if not primary_agent:
                    primary_agent, confidence = self.determine_primary_agent(query)
                    self.logger.info("auto_routed", primary_agent=primary_agent, confidence=confidence)
                
                # Get primary agent
                if primary_agent not in self.agents:
                    raise ValueError(f"Primary agent '{primary_agent}' not found")
                
                primary = self.agents[primary_agent]
                
                # Get supporting agents
                if not supporting_agents:
                    supporting_agents = self.determine_supporting_agents(query, primary_agent)
                
                # ALWAYS ensure RAG agent is included in supporting agents
                if "rag" not in supporting_agents and primary_agent != "rag":
                    supporting_agents.insert(0, "rag")  # Add RAG as first supporting agent
                    self.logger.info("rag_agent_added", message="RAG agent automatically added to supporting agents")
                
                # Consult supporting agents first, starting with RAG for knowledge base context
                supporting_responses = []
                rag_context = ""
                
                # Always consult RAG first if available
                if "rag" in supporting_agents and "rag" in self.agents:
                    rag_interaction = await self.route_agent_consultation(
                        from_agent=primary_agent,
                        to_agent="rag",
                        query=f"Retrieve relevant knowledge from the knowledge base for: '{query}'",
                        context=context
                    )
                    rag_context = rag_interaction.response
                    supporting_responses.append(rag_interaction)
                    self.logger.info("rag_consulted_first", message="RAG agent consulted first for knowledge base context")
                
                # Then consult other supporting agents with RAG context
                for support_agent_name in supporting_agents:
                    if support_agent_name in self.agents and support_agent_name != "rag":
                        enhanced_query = f"Based on the query: '{query}'"
                        if rag_context:
                            enhanced_query += f"\n\nKnowledge Base Context:\n{rag_context}"
                        interaction = await self.route_agent_consultation(
                            from_agent=primary_agent,
                            to_agent=support_agent_name,
                            query=enhanced_query,
                            context=context
                        )
                        supporting_responses.append(interaction)
                
                # Build enhanced query with supporting agent insights
                # Prioritize RAG context
                enhanced_query = query
                if supporting_responses:
                    enhanced_query += "\n\nSupporting Agent Insights (Prioritizing Knowledge Base):\n"
                    # Put RAG response first if available
                    rag_response = None
                    for resp in supporting_responses:
                        if hasattr(resp, 'to_agent') and resp.to_agent == "rag":
                            rag_response = resp
                            break
                    
                    if rag_response:
                        enhanced_query += f"\n[RAG Knowledge Base]: {rag_response.response}\n"
                    
                    for interaction in supporting_responses:
                        if not (hasattr(interaction, 'to_agent') and interaction.to_agent == "rag"):
                            agent_name = interaction.to_agent if hasattr(interaction, 'to_agent') else "agent"
                            response_text = interaction.response if hasattr(interaction, 'response') else str(interaction)
                            enhanced_query += f"\n[{agent_name}]: {response_text}\n"
                
                if context:
                    import json
                    enhanced_query += f"\n\nContext: {json.dumps(context, indent=2)}"
                
                # Process with primary agent
                messages = [AgentMessage(role="user", content=enhanced_query, timestamp=datetime.utcnow())]
                response = await primary.process(messages, context)
                
                return AgentResponse(
                    agent_type="multi_agent",
                    response=response.response,
                    metadata={
                        "mode": "collaborative",
                        "primary_agent": primary_agent,
                        "supporting_agents": supporting_agents or [],
                    },
                    timestamp=datetime.utcnow()
                )
            else:
                # For other modes (sequential, parallel), fall back to enhanced collaborative
                self.logger.warning("unsupported_coordination_mode", mode=coordination_mode, message="Falling back to enhanced_collaborative")
                product_id = context.get("product_id") if context else None
                session_ids = context.get("session_ids") if context else None
                user_context = {k: v for k, v in (context or {}).items() if k not in ["product_id", "session_ids"]}
                
                return await self.process_with_context(
                    query=query,
                    product_id=product_id,
                    session_ids=session_ids,
                    user_context=user_context,
                    coordination_mode="enhanced_collaborative",
                    db=db
                )
        except Exception as e:
            self.logger.error("route_query_error", error=str(e), coordination_mode=coordination_mode)
            raise

