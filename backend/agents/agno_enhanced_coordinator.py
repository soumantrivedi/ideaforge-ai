"""
Enhanced Agno Coordinator with Heavy Contextualization
Ensures agents coordinate and share context before responding
"""
from typing import List, Dict, Any, Optional, AsyncGenerator
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
from backend.agents.agno_strategy_agent import AgnoStrategyAgent
from backend.agents.agno_validation_agent import AgnoValidationAgent
from backend.agents.agno_export_agent import AgnoExportAgent
from backend.agents.agno_v0_agent import AgnoV0Agent
from backend.agents.agno_lovable_agent import AgnoLovableAgent
from backend.agents.agno_atlassian_agent import AgnoAtlassianAgent
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
        # CRITICAL: Enable RAG for all lifecycle agents to ensure knowledge base is used across all phases
        self.research_agent = AgnoResearchAgent(enable_rag=True)  # Always enable RAG for research
        self.analysis_agent = AgnoAnalysisAgent(enable_rag=True)  # Always enable RAG for analysis
        self.ideation_agent = AgnoIdeationAgent(enable_rag=True)  # Always enable RAG for ideation
        self.prd_agent = AgnoPRDAuthoringAgent(enable_rag=True)  # Always enable RAG for PRD authoring
        self.summary_agent = AgnoSummaryAgent(enable_rag=enable_rag)
        self.scoring_agent = AgnoScoringAgent(enable_rag=enable_rag)
        self.strategy_agent = AgnoStrategyAgent(enable_rag=enable_rag)
        self.validation_agent = AgnoValidationAgent(enable_rag=True)  # Always enable RAG for validation/review
        self.export_agent = AgnoExportAgent(enable_rag=True)  # Always enable RAG for export
        self.v0_agent = AgnoV0Agent(enable_rag=enable_rag)
        self.lovable_agent = AgnoLovableAgent(enable_rag=enable_rag)
        self.atlassian_agent = AgnoAtlassianAgent(enable_rag=enable_rag)
        self.rag_agent = RAGAgent()
        
        # Register all agents
        self.agents: Dict[str, AgnoBaseAgent] = {
            "research": self.research_agent,
            "analysis": self.analysis_agent,
            "ideation": self.ideation_agent,
            "prd_authoring": self.prd_agent,
            "summary": self.summary_agent,
            "scoring": self.scoring_agent,
            "strategy": self.strategy_agent,
            "validation": self.validation_agent,
            "export": self.export_agent,
            "v0": self.v0_agent,
            "lovable": self.lovable_agent,
            "atlassian_mcp": self.atlassian_agent,
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
    
    def _get_agno_model(self, model_tier: str = "standard"):
        """Get appropriate Agno model based on provider registry and tier.
        
        Model Tiers:
        - fast: gpt-5.1-chat-latest, claude-3-haiku, gemini-1.5-flash
        - standard: gpt-5.1, claude-3.5-sonnet, gemini-1.5-pro (for coordinators)
        - premium: gpt-5.1, claude-4-sonnet, gemini-3.0-pro
        """
        api_key = None
        
        if model_tier == "fast":
            if provider_registry.has_openai_key():
                api_key = provider_registry.get_openai_key()
                if api_key:
                    # GPT-5.1 models require max_completion_tokens instead of max_tokens
                    # Use fast model from settings (env.kind), fallback to agent_model_primary
                    fast_model_id = getattr(settings, "agent_model_fast", None) or getattr(settings, "agent_model_primary", "gpt-5.1")
                    return OpenAIChat(id=fast_model_id, api_key=api_key, max_completion_tokens=2000)
            elif provider_registry.has_gemini_key():
                api_key = provider_registry.get_gemini_key()
                if api_key:
                    return Gemini(id="gemini-1.5-flash", api_key=api_key)
            elif provider_registry.has_claude_key():
                api_key = provider_registry.get_claude_key()
                if api_key:
                    return Claude(id="claude-3-haiku-20240307", api_key=api_key)
        elif model_tier == "standard":
            if provider_registry.has_openai_key():
                api_key = provider_registry.get_openai_key()
                if api_key:
                    # GPT-5.1 models require max_completion_tokens instead of max_tokens
                    return OpenAIChat(id="gpt-5.1", api_key=api_key, max_completion_tokens=4000)
            elif provider_registry.has_gemini_key():
                api_key = provider_registry.get_gemini_key()
                if api_key:
                    return Gemini(id="gemini-1.5-pro", api_key=api_key)
            elif provider_registry.has_claude_key():
                api_key = provider_registry.get_claude_key()
                if api_key:
                    return Claude(id="claude-3-5-sonnet-20241022", api_key=api_key)
        elif model_tier == "premium":
            if provider_registry.has_openai_key():
                api_key = provider_registry.get_openai_key()
                if api_key:
                    model_id = settings.agent_model_primary
                    # GPT-5.1 models require max_completion_tokens instead of max_tokens
                    if 'gpt-5.1' in model_id.lower() or 'gpt-5' in model_id.lower():
                        return OpenAIChat(id=model_id, api_key=api_key, max_completion_tokens=4000)
                    else:
                        return OpenAIChat(id=model_id, api_key=api_key)
            elif provider_registry.has_gemini_key():
                api_key = provider_registry.get_gemini_key()
                if api_key:
                    return Gemini(id=settings.agent_model_tertiary, api_key=api_key)
            elif provider_registry.has_claude_key():
                api_key = provider_registry.get_claude_key()
                if api_key:
                    return Claude(id=settings.agent_model_secondary, api_key=api_key)
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
            
            # Determine primary agent based on phase and query content
            primary_agent, confidence = self.determine_primary_agent(enhanced_query, context)
            self.logger.info(
                "process_with_context_agent_selection",
                primary_agent=primary_agent,
                confidence=confidence,
                phase_name=context.get("phase_name") if context else None
            )
            
            # Process with enhanced coordination using agent consultation
            # Start with RAG agent for context (must be first as others depend on it)
            rag_response = await self.rag_agent.process(
                [AgentMessage(role="user", content=enhanced_query, timestamp=datetime.utcnow())],
                context
            )
            
            # Determine which agents to run based on phase and primary agent selection
            # Only run phase-appropriate agents, not all agents for every query
            import asyncio
            shared_context_msg = f"{enhanced_query}\n\nKnowledge Base Context:\n{rag_response.response}"
            shared_message = [AgentMessage(role="user", content=shared_context_msg, timestamp=datetime.utcnow())]
            
            # Get supporting agents based on phase and query
            supporting_agents = self.determine_supporting_agents(enhanced_query, primary_agent, context)
            
            # Build list of agents to run in parallel (only phase-appropriate ones)
            agents_to_run = []
            agent_tasks = {}
            
            # Always include primary agent
            if primary_agent in self.agents:
                agents_to_run.append(primary_agent)
                agent_tasks[primary_agent] = self.agents[primary_agent].process(shared_message, context)
            
            # Add supporting agents that are phase-appropriate
            for agent_name in supporting_agents:
                if agent_name in self.agents and agent_name not in agents_to_run:
                    agents_to_run.append(agent_name)
                    agent_tasks[agent_name] = self.agents[agent_name].process(shared_message, context)
            
            self.logger.info(
                "process_with_context_agents_selected",
                primary_agent=primary_agent,
                supporting_agents=supporting_agents,
                agents_to_run=agents_to_run,
                phase_name=context.get("phase_name") if context else None
            )
            
            # Run selected agents in parallel
            if agent_tasks:
                agent_responses = await asyncio.gather(
                    *agent_tasks.values(),
                    return_exceptions=True
                )
                
                # Map responses back to agent names
                agent_results = {}
                for i, agent_name in enumerate(agents_to_run):
                    response = agent_responses[i]
                    if isinstance(response, Exception):
                        self.logger.error(f"{agent_name}_agent_failed", error=str(response))
                        agent_results[agent_name] = AgentResponse(
                            agent_type=agent_name,
                            response=f"{agent_name} agent failed",
                            timestamp=datetime.utcnow()
                        )
                    else:
                        agent_results[agent_name] = response
            else:
                # Fallback: if no agents selected, use primary agent only
                if primary_agent in self.agents:
                    agent_results = {primary_agent: await self.agents[primary_agent].process(shared_message, context)}
                else:
                    # Ultimate fallback: use research agent
                    agent_results = {"research": await self.research_agent.process(shared_message, context)}
            
            # Build context string from agent responses
            context_parts = [f"Knowledge: {rag_response.response}"]
            for agent_name, response in agent_results.items():
                context_parts.append(f"{agent_name.capitalize()}: {response.response if hasattr(response, 'response') else str(response)}")
            
            # Use primary agent's response as final response, enhanced with other agents' context
            primary_response = agent_results.get(primary_agent)
            if primary_response:
                if hasattr(primary_response, 'response'):
                    final_response = primary_response.response
                else:
                    final_response = str(primary_response)
            else:
                # Fallback to first available response
                first_response = list(agent_results.values())[0]
                final_response = first_response.response if hasattr(first_response, 'response') else str(first_response)
            
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
            # Also include as message_history for NLU extraction
            context["message_history"] = self.shared_context["conversation_history"]
        
        # Retrieve knowledge from RAG - CRITICAL: Filter by product_id to get only relevant documents
        if session_ids or product_id:
            try:
                rag_query = f"Product: {product_id}, Sessions: {', '.join(session_ids) if session_ids else 'N/A'}"
                # Pass product_id as filter to ensure only documents for this product are retrieved
                filters = {}
                if product_id:
                    filters["product_id"] = str(product_id)
                knowledge_results = await self.rag_agent.search_knowledge(rag_query, top_k=10, filters=filters)
                context["knowledge_base"] = knowledge_results
                self.logger.info("rag_knowledge_retrieved",
                               product_id=product_id,
                               results_count=len(knowledge_results),
                               filters=filters)
            except Exception as e:
                self.logger.warning("rag_context_retrieval_failed", error=str(e), product_id=product_id)
        
        return context
    
    def _build_system_content(self, context: Dict[str, Any]) -> str:
        """Build system content from context - separate from user prompt for better structure."""
        import json
        
        system_parts = []
        
        # Product context
        if context.get("product_id"):
            system_parts.append(f"Product ID: {context['product_id']}")
        
        if context.get("phase_id"):
            system_parts.append(f"Phase ID: {context['phase_id']}")
        
        if context.get("phase_name"):
            system_parts.append(f"Phase: {context['phase_name']}")
        
        # Section-specific context (for phase forms)
        if context.get("current_field"):
            field_name = ' '.join([w.capitalize() for w in str(context['current_field']).split('_')])
            system_parts.append(f"Current Section/Field: {field_name}")
        
        if context.get("section_name"):
            system_parts.append(f"Section Name: {context['section_name']}")
        
        if context.get("current_prompt"):
            system_parts.append(f"Section Question: {context['current_prompt']}")
        
        if context.get("session_ids"):
            system_parts.append(f"Relevant Sessions: {', '.join(context['session_ids'])}")
        
        # Conversation history - structured for system context (Option E: increased limits)
        if context.get("conversation_history"):
            system_parts.append("\n=== CONVERSATION HISTORY ===")
            for msg in context["conversation_history"][-20:]:  # Last 20 messages (increased from 15 - Option E)
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                agent_name = msg.get("agent_name", "")
                if content:
                    agent_label = f" ({agent_name})" if agent_name else ""
                    system_parts.append(f"{role.upper()}{agent_label}: {content[:600]}")  # Increased from 400 - Option E
        
        # Ideation from chat (Option E: increased limit)
        if context.get("ideation_from_chat"):
            system_parts.append("\n=== IDEATION FROM CHATBOT ===")
            system_parts.append(context["ideation_from_chat"][:2500])  # Increased from 1500 - Option E
        
        # Previous phase submissions (CRITICAL: Include ALL previous phase data)
        if context.get("previous_phases"):
            system_parts.append("\n=== PREVIOUS PHASE SUBMISSIONS ===")
            system_parts.append("CRITICAL: Use ALL information from previous phases. Reference specific details from ideation, market research, and other completed phases.")
            system_parts.append(context["previous_phases"])
        
        # Form data context (exclude current field to avoid duplication) (Option E: increased limit)
        if context.get("form_data"):
            current_field = context.get("current_field")
            form_data_filtered = {k: v for k, v in context["form_data"].items() if k != current_field and v and str(v).strip()}
            if form_data_filtered:
                system_parts.append("\n=== OTHER FORM FIELDS (Already Filled) ===")
                form_summary = "\n".join([f"{k.replace('_', ' ').title()}: {str(v)[:500]}" for k, v in form_data_filtered.items()])  # Increased from 200 - Option E
                system_parts.append(form_summary)
        
        # Knowledge base (Option E: increased limit)
        if context.get("knowledge_base"):
            system_parts.append("\n=== KNOWLEDGE BASE ===")
            for kb_item in context["knowledge_base"][:10]:  # Increased from 5 - Option E
                kb_content = kb_item.get('content', '')[:500]  # Increased from 300 - Option E
                system_parts.append(f"- {kb_content}")
        
        # Shared context
        if context.get("shared_context"):
            shared = context["shared_context"]
            if shared.get("last_query") or shared.get("last_response"):
                system_parts.append("\n=== PREVIOUS INTERACTIONS ===")
                if shared.get("last_query"):
                    system_parts.append(f"Last Query: {shared['last_query'][:150]}")
                if shared.get("last_response"):
                    system_parts.append(f"Last Response: {shared['last_response'][:150]}")
        
        return "\n".join(system_parts)
    
    def _enhance_query_with_context(self, query: str, context: Dict[str, Any]) -> str:
        """Enhance query with context - optimized structure using system/user prompt separation.
        
        Instead of putting everything in user prompt, we structure it as:
        - System Content: Context, history, knowledge base
        - User Prompt: Clean, focused query
        
        This allows the AI to better understand context vs. the actual request.
        """
        # Build system content separately
        system_content = self._build_system_content(context)
        
        # Clean user query - just the actual request
        user_query = query.strip()
        
        # Structure the enhanced query with clear separation
        enhanced = f"""SYSTEM CONTEXT:
{system_content}

USER REQUEST:
{user_query}

INSTRUCTIONS:
- Use the SYSTEM CONTEXT above to inform your response
- Focus on the USER REQUEST as the primary task
- Synthesize information from conversation history, knowledge base, AND previous phase submissions
- Reference specific details from previous phases (ideation, market research, etc.) when relevant
- Provide data-driven, specific responses - NOT generic guidance
- Write content AS IF THE USER TYPED IT DIRECTLY - do not use coaching language
- DO NOT say "Since the earlier context only states..." or "Because your previous question was..."
- Instead, directly use the information: "Based on your ideation phase, the problem is X, therefore..."
- Be crisp, specific, and use actual information from previous phases
"""
        
        return enhanced
    
    async def route_agent_consultation(
        self,
        from_agent: str,
        to_agent: str,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentInteraction:
        """Route consultation with shared context. Ensures agent-to-agent interactions are focused and useful."""
        # Enhance context with shared context
        enhanced_context = {**(context or {}), **self.shared_context}
        
        if to_agent not in self.agents:
            raise ValueError(f"Unknown agent type: {to_agent}")
        
        target_agent = self.agents[to_agent]
        
        # Build structured consultation message for better agent-to-agent communication
        # Extract relevant context for the consultation
        relevant_context_parts = []
        
        # Include product context if available
        if enhanced_context.get("product_id"):
            relevant_context_parts.append(f"Product ID: {enhanced_context['product_id']}")
        
        # Include phase context if available
        if enhanced_context.get("phase_name"):
            relevant_context_parts.append(f"Current Phase: {enhanced_context['phase_name']}")
        
        # Include form data if available (for requirements/research)
        if enhanced_context.get("form_data"):
            form_summary = "\n".join([f"- {k}: {str(v)[:200]}" for k, v in list(enhanced_context["form_data"].items())[:5]])
            if form_summary:
                relevant_context_parts.append(f"Form Data:\n{form_summary}")
        
        # Include conversation history summary if available
        if enhanced_context.get("conversation_history"):
            recent_messages = enhanced_context["conversation_history"][-3:]  # Last 3 messages
            conv_summary = "\n".join([f"- {msg.get('role', 'user')}: {msg.get('content', '')[:200]}" for msg in recent_messages])
            if conv_summary:
                relevant_context_parts.append(f"Recent Conversation:\n{conv_summary}")
        
        # Build structured consultation message
        context_section = f"\n\nRelevant Context:\n" + "\n".join(relevant_context_parts) if relevant_context_parts else ""
        
        consultation_message = AgentMessage(
            role="user",
            content=f"[Agent Consultation Request from {from_agent}]\n\nQuery: {query}{context_section}\n\nPlease provide a focused, actionable response that directly addresses the consultation query. Be concise but thorough.",
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
    
    def determine_primary_agent(self, query: str, context: Optional[Dict[str, Any]] = None) -> tuple[str, float]:
        """
        Intelligently determine the best agent to handle a query based on:
        1. Phase context (if user is in a specific phase)
        2. Query content and keywords
        3. Agent capabilities
        
        CRITICAL: Only selects agents relevant to the current phase and query content.
        """
        query_lower = query.lower()
        best_agent = None
        best_confidence = 0.0
        
        # Phase-to-agent mapping for intelligent routing
        phase_agent_mapping = {
            "ideation": "ideation",
            "market research": "research",
            "market_research": "research",
            "requirements": "prd_authoring",
            "requirements phase": "prd_authoring",
            "design": "prd_authoring",  # Design phase may need PRD content
            "strategy": "strategy",
            "analysis": "analysis",
            "validation": "validation",
            "review": "validation",
        }
        
        # Check phase context first - this is the most reliable indicator
        phase_name = None
        if context:
            phase_name = context.get("phase_name", "").lower() if context.get("phase_name") else None
        
        # If user is in a specific phase, prioritize agents for that phase
        phase_agent = None
        if phase_name:
            # Direct match
            if phase_name in phase_agent_mapping:
                phase_agent = phase_agent_mapping[phase_name]
            else:
                # Partial match (e.g., "Market Research Phase" -> "research")
                for phase_key, agent_type in phase_agent_mapping.items():
                    if phase_key in phase_name or phase_name in phase_key:
                        phase_agent = agent_type
                        break
        
        # Query-based agent detection with phase awareness
        # Phase-specific keywords that override general keyword matching
        phase_specific_keywords = {
            "ideation": ["ideation", "idea", "brainstorm", "concept", "innovation", "problem statement", "what problem"],
            "research": ["market research", "competitive analysis", "trend", "market trend", "competitor", "industry analysis", "user research"],
            "prd_authoring": ["requirement", "prd", "user story", "acceptance criteria", "functional requirement", "non-functional", "specification"],
            "strategy": ["strategy", "roadmap", "go-to-market", "gtm", "business model", "positioning"],
            "analysis": ["analyze", "analysis", "swot", "feasibility", "risk analysis", "gap analysis"],
            "validation": ["validate", "validation", "review", "quality check", "verify"],
        }
        
        # Score agents based on query content and phase context
        agent_scores = {}
        for agent_type, agent in self.agents.items():
            if agent_type == "rag":  # Skip RAG as primary agent
                continue
            
            score = 0.0
            
            # Phase context boost (high priority)
            if phase_agent == agent_type:
                score += 0.5  # Strong boost for phase-matched agent
            
            # Query keyword matching
            agent_confidence = agent.get_confidence(query)
            score += agent_confidence * 0.4
            
            # Phase-specific keyword matching
            if agent_type in phase_specific_keywords:
                keywords = phase_specific_keywords[agent_type]
                matches = sum(1 for kw in keywords if kw in query_lower)
                if matches > 0:
                    score += (matches / len(keywords)) * 0.3
            
            # Negative scoring: if query explicitly mentions a different phase, reduce score
            if phase_name:
                for other_phase, other_agent in phase_agent_mapping.items():
                    if other_agent != agent_type and other_phase in phase_name:
                        # If we're in a different phase, reduce score for this agent
                        score *= 0.3
            
            agent_scores[agent_type] = score
        
        # Find best agent
        if agent_scores:
            best_agent = max(agent_scores.items(), key=lambda x: x[1])[0]
            best_confidence = agent_scores[best_agent]
        
        # Only default to ideation if:
        # 1. No phase context is available AND
        # 2. Confidence is very low AND
        # 3. Query doesn't explicitly mention other phases
        if best_confidence < 0.3 and not phase_name:
            # Check if query mentions other phases
            mentions_research = any(kw in query_lower for kw in ["research", "market", "competitive", "trend", "market trend", "industry", "competitor"])
            mentions_requirements = any(kw in query_lower for kw in ["requirement", "prd", "specification", "user story", "acceptance criteria", "functional requirement"])
            mentions_design = any(kw in query_lower for kw in ["design", "mockup", "ui", "ux", "wireframe", "prototype"])
            mentions_strategy = any(kw in query_lower for kw in ["strategy", "roadmap", "gtm", "go-to-market", "business model", "positioning"])
            mentions_ideation = any(kw in query_lower for kw in ["ideation", "brainstorm", "idea generation", "innovation", "problem statement", "what problem"])
            
            if mentions_research:
                best_agent = "research"
                best_confidence = 0.6
            elif mentions_requirements:
                best_agent = "prd_authoring"
                best_confidence = 0.6
            elif mentions_design:
                best_agent = "prd_authoring"
                best_confidence = 0.6
            elif mentions_strategy:
                best_agent = "strategy"
                best_confidence = 0.6
            elif mentions_ideation:
                # Only use ideation if query explicitly mentions ideation keywords
                best_agent = "ideation"
                best_confidence = 0.6
            else:
                # Last resort: default to research (safer than ideation for ambiguous queries)
                # Only use ideation if query is very vague and has no phase context AND mentions ideation
                best_agent = "research"  # Changed from ideation to research as safer default
                best_confidence = 0.4
        
        self.logger.info(
            "primary_agent_determined",
            agent=best_agent,
            confidence=best_confidence,
            phase_name=phase_name,
            phase_agent=phase_agent,
            query_preview=query[:100]
        )
        
        return best_agent, best_confidence
    
    def determine_supporting_agents(
        self, 
        query: str, 
        primary_agent: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Intelligently determine which supporting agents should be consulted.
        
        CRITICAL: Only includes agents that are relevant to:
        1. The current phase context
        2. The query content
        3. The primary agent's needs
        
        Does NOT automatically include ideation/research/analysis for all queries.
        """
        query_lower = query.lower()
        supporting = []
        
        # Get phase context
        phase_name = None
        if context:
            phase_name = context.get("phase_name", "").lower() if context.get("phase_name") else None
        
        # Phase-to-agent mapping
        phase_agent_mapping = {
            "ideation": "ideation",
            "market research": "research",
            "market_research": "research",
            "requirements": "prd_authoring",
            "requirements phase": "prd_authoring",
            "design": "prd_authoring",
            "strategy": "strategy",
            "analysis": "analysis",
            "validation": "validation",
            "review": "validation",
        }
        
        # RAG agent: Only include if there's actual knowledge base content or documents
        # Check if RAG has knowledge (will be checked later in stream_route_query)
        # For now, include RAG but it will be skipped if no knowledge is available
        if primary_agent != "rag":
            supporting.append("rag")
        
        # Phase-aware agent selection
        # Only add supporting agents if they're relevant to the current phase or query
        
        # Research agent: Only for market research phase or explicit research queries
        should_include_research = False
        if phase_name and ("research" in phase_name or "market" in phase_name):
            should_include_research = True
        elif any(kw in query_lower for kw in ["market research", "competitive analysis", "trend analysis", "industry analysis"]):
            should_include_research = True
        
        if should_include_research and primary_agent != "research":
            supporting.append("research")
        
        # Analysis agent: Only for analysis phase or explicit analysis queries
        should_include_analysis = False
        if phase_name and "analysis" in phase_name:
            should_include_analysis = True
        elif any(kw in query_lower for kw in ["swot", "feasibility analysis", "risk analysis", "gap analysis", "strategic analysis"]):
            should_include_analysis = True
        
        if should_include_analysis and primary_agent != "analysis":
            supporting.append("analysis")
        
        # Ideation agent: Only for ideation phase or explicit ideation queries
        # CRITICAL: Do NOT include ideation for market research or requirements phases
        should_include_ideation = False
        if phase_name and "ideation" in phase_name:
            should_include_ideation = True
        elif any(kw in query_lower for kw in ["ideation", "brainstorm", "idea generation", "innovation", "problem statement"]) and not phase_name:
            # Only include if NOT in a different phase
            should_include_ideation = True
        
        # Explicitly exclude ideation for non-ideation phases
        if phase_name and "ideation" not in phase_name and "research" in phase_name:
            should_include_ideation = False
        if phase_name and "ideation" not in phase_name and "requirement" in phase_name:
            should_include_ideation = False
        
        if should_include_ideation and primary_agent != "ideation":
            supporting.append("ideation")
        
        # Strategy agent: Only for strategy phase or explicit strategy queries
        should_include_strategy = False
        if phase_name and "strategy" in phase_name:
            should_include_strategy = True
        elif any(kw in query_lower for kw in ["strategy", "roadmap", "go-to-market", "gtm", "business model", "positioning"]):
            should_include_strategy = True
        
        if should_include_strategy and primary_agent != "strategy":
            supporting.append("strategy")
        
        # Validation agent: Only for validation/review phase or explicit validation queries
        should_include_validation = False
        if phase_name and ("validation" in phase_name or "review" in phase_name):
            should_include_validation = True
        elif any(kw in query_lower for kw in ["validate", "validation", "review", "quality check", "verify"]):
            should_include_validation = True
        
        if should_include_validation and primary_agent != "validation":
            supporting.append("validation")
        
        # PRD Authoring agent: Only for requirements phase or explicit PRD queries
        should_include_prd = False
        if phase_name and ("requirement" in phase_name or "prd" in phase_name):
            should_include_prd = True
        elif any(kw in query_lower for kw in ["prd", "product requirements", "requirements document", "specification", "user story"]):
            should_include_prd = True
        
        if should_include_prd and primary_agent != "prd_authoring":
            supporting.append("prd_authoring")
        
        # Atlassian agent: Only for explicit Confluence/Jira operations
        if any(kw in query_lower for kw in ["confluence", "jira", "atlassian", "publish", "page", "space", "documentation"]):
            if primary_agent != "atlassian_mcp":
                supporting.append("atlassian_mcp")
        
        # Export agent: Only for explicit export/document generation
        if any(kw in query_lower for kw in ["export", "generate document", "publish document", "download prd"]):
            if primary_agent != "export":
                supporting.append("export")
        
        # V0 agent: For UI/code generation requests
        if any(kw in query_lower for kw in ["v0", "generate code", "create ui", "build interface", "design ui", "ui design", "generate prompt for v0", "submit to v0", "use v0"]):
            if primary_agent != "v0":
                supporting.append("v0")
        
        self.logger.info(
            "supporting_agents_determined",
            primary_agent=primary_agent,
            supporting_agents=supporting,
            phase_name=phase_name,
            query_preview=query[:100]
        )
        
        return supporting
    
    async def stream_route_query(
        self,
        query: str,
        coordination_mode: str = "enhanced_collaborative",
        primary_agent: Optional[str] = None,
        supporting_agents: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        db: Optional[Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream route query with real-time events.
        Yields events as agents process the query.
        """
        import asyncio
        
        # Track accumulated response and interactions for error recovery
        accumulated_response = ""
        interactions = []
        
        try:
            # Intelligent pre-processing: Check user intent before invoking agents
            from backend.services.natural_language_understanding import get_nlu
            nlu = get_nlu()
            
            # Build context first to extract conversation history
            enhanced_context = await self._build_comprehensive_context(
                product_id=context.get("product_id") if context else None,
                session_ids=context.get("session_ids") if context else None,
                user_context=context,
                db=db
            )
            
            # Check if user intent suggests we should proceed with full agent processing
            should_proceed, reason, suggested_response = nlu.should_make_ai_call(
                user_input=query,
                agent_question=None,  # Will be extracted from context
                context=enhanced_context
            )
            
            if not should_proceed:
                # User said no or doesn't want full processing - provide helpful response
                self.logger.info("nlu_blocked_streaming", query=query[:50], reason=reason)
                
                if suggested_response:
                    response_text = suggested_response
                else:
                    # Default helpful guidance
                    phase_name = enhanced_context.get("phase_name") if enhanced_context else None
                    if phase_name:
                        response_text = f"Got it! You're working on the **{phase_name}** phase. What would you like to do next?\n\n• Continue with {phase_name}\n• Move to next phase\n• Ask a question\n• Review progress"
                    else:
                        response_text = "No problem! What would you like to work on next?\n\n• Select a Product Lifecycle Phase\n• Ask a question\n• View your progress\n• Export your work"
                
                # Stream the helpful response
                chunk_size = 5
                for i in range(0, len(response_text), chunk_size):
                    chunk = response_text[i:i+chunk_size]
                    yield {
                        "type": "agent_chunk",
                        "agent": "coordinator",
                        "chunk": chunk,
                        "progress": 0.5 + (0.4 * (i / len(response_text))),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await asyncio.sleep(0.01)
                
                yield {
                    "type": "agent_complete",
                    "agent": "coordinator",
                    "response": response_text,
                    "metadata": {
                        "system_context": "NLU detected user declined or ambiguous intent",
                        "system_prompt": "Helpful guidance provider",
                        "user_prompt": query,
                        "rag_context": "Not applicable - no agent processing",
                        "nlu_blocked": True,
                        "reason": reason
                    },
                    "progress": 0.9,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                yield {
                    "type": "complete",
                    "response": response_text,
                    "interactions": [],
                    "metadata": {
                        "mode": "nlu_guided",
                        "primary_agent": "coordinator",
                        "nlu_blocked": True,
                        "reason": reason,
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "progress": 1.0,
                    "timestamp": datetime.utcnow().isoformat()
                }
                return  # Exit early - no agent processing needed
            
            # Check if this is a phase form help request with fast mode
            is_phase_form_help = context and context.get("current_field")
            use_fast_model = context and context.get("use_fast_model", False)
            skip_rag = context and context.get("skip_rag", False)
            single_agent_mode = context and context.get("single_agent_mode", False)
            
            # Check if user is in a specific phase - restrict content to that phase only
            current_phase_name = context.get("phase_name") if context else None
            is_phase_specific = current_phase_name is not None
            # Check if user explicitly asked for full PRD
            query_lower = query.lower()
            user_wants_full_prd = any(phrase in query_lower for phrase in [
                "full prd", "complete prd", "entire prd", "generate prd", "create prd",
                "full document", "complete document", "entire document",
                "all phases", "all lifecycle phases", "complete product requirements"
            ])
            use_chatbot_context_only = context and context.get("use_chatbot_context_only", False)
            response_length = context.get("response_length", "verbose") if context else "verbose"
            
            # Enhance query with context and add concise mode instruction for chat
            enhanced_query = query
            
            # For phase form help with chatbot context only, use minimal context
            if is_phase_form_help and use_chatbot_context_only:
                # Only use chatbot conversation history (already in query)
                if enhanced_context.get("ideation_from_chat"):
                    enhanced_query = f"{query}\n\n[Chatbot context]:\n{enhanced_context['ideation_from_chat'][:500]}"  # Reduced to 500 chars
            elif enhanced_context.get("ideation_from_chat"):
                enhanced_query = f"{query}\n\n[Context from previous conversations]:\n{enhanced_context['ideation_from_chat'][:1000]}"
            
            # Add instructions based on context type
            if is_phase_form_help:
                # Phase form help - enforce strict word limits for inline help
                if response_length == "short":
                    concise_instruction = "\n\nCRITICAL: Maximum 500 words. Be concise and direct. Answer ONLY the specific question asked. Do NOT generate full PRD sections or other content. Stay within word limit."
                else:
                    concise_instruction = "\n\nCRITICAL: Maximum 1000 words. Be detailed but focused. Answer ONLY the specific question asked. Do NOT generate full PRD sections or other content. Stay within word limit."
                enhanced_query = enhanced_query + concise_instruction
            elif is_phase_specific and not user_wants_full_prd:
                # User is in a specific phase - only generate content for that phase
                phase_instruction = f"\n\nCRITICAL: The user is currently working on the {current_phase_name} phase. Generate content ONLY for the {current_phase_name} phase. Do NOT generate content for other phases (Market Research, Requirements, Design, etc.) unless the user explicitly asks for them. Focus your response on {current_phase_name} phase content only."
                enhanced_query = enhanced_query + phase_instruction
                # For phase-specific queries, provide comprehensive but focused response
                quality_instruction = "\n\nIMPORTANT: Provide a comprehensive, intelligent response with all relevant details. Use the agent army to gather insights from all relevant agents. Be thorough and include actionable insights. Quality over brevity - ensure the response is complete and useful."
                enhanced_query = enhanced_query + quality_instruction
            else:
                # Regular chat response - CONVERSATIONAL MODE
                # Check if user wants to perform analysis or just chat
                query_lower = query.lower()
                wants_analysis = any(phrase in query_lower for phrase in [
                    "perform analysis", "do analysis", "run analysis", "analyze", "analysis",
                    "generate prd", "create prd", "build prd", "complete analysis"
                ])
                is_confirmation = any(phrase in query_lower for phrase in [
                    "yes", "proceed", "go ahead", "continue", "ok", "okay", "sure", "confirm"
                ])
                
                if wants_analysis or is_confirmation:
                    # User wants analysis - provide comprehensive response using agent army
                    quality_instruction = "\n\nIMPORTANT: The user wants to perform analysis. Use the agent army to provide a comprehensive, intelligent, and detailed analysis. Include all relevant context, insights, and actionable information. Quality and completeness are priorities - ensure the response is thorough, well-reasoned, and useful. Leverage all available agents and knowledge to provide the best possible analysis."
                    enhanced_query = enhanced_query + quality_instruction
                else:
                    # Conversational mode - be friendly, ask questions, keep responses shorter
                    # Check if user wants v0 agent integration
                    wants_v0 = any(phrase in query_lower for phrase in [
                        "v0", "generate code", "create ui", "build interface", "design ui", "ui design",
                        "generate prompt for v0", "submit to v0", "use v0"
                    ])
                    
                    if wants_v0:
                        # User wants v0 agent - guide them through prompt generation
                        v0_instruction = """\n\nV0 AGENT INTEGRATION MODE:
- The user wants to use the v0 agent to generate UI/code
- First, help them build a comprehensive prompt by asking clarifying questions about:
  * What type of application/interface they want
  * Key features and functionality
  * Design preferences (if any)
  * Target users
- Once you have enough information, use the v0 agent to generate the prompt
- Ask the user if they want to submit the prompt to v0
- Keep responses conversational and helpful
- Format with clear paragraphs and bullet points"""
                        enhanced_query = enhanced_query + v0_instruction
                    else:
                        conversational_instruction = """\n\nCONVERSATIONAL MODE - CRITICAL INSTRUCTIONS:
- Be friendly and conversational, like ChatGPT or Claude
- Keep responses SHORT and contextual (2-4 sentences for simple questions, 1-2 paragraphs max for complex ones)
- Ask clarifying questions when needed (1-2 sentences)
- Build understanding through conversation - don't overwhelm with information
- Only provide comprehensive analysis when user explicitly asks or confirms
- If user mentions an idea or product, compliment them and ask 1-2 follow-up questions
- Guide the user step-by-step through their product lifecycle phase
- Use bullet points for lists, but keep them concise
- Be helpful and supportive, not overwhelming
- If user says "help me with idea" or similar, ask: "That's a great start! Can you tell me a bit more about [specific aspect]?" 
- Build context gradually through conversation
- When user has provided enough information, ask: "Would you like me to perform a comprehensive analysis now?"
- Only then use the full agent army for analysis
- Format responses with clear paragraphs and bullet points where helpful
- Make it feel like a natural conversation, not a Q&A session
- Remember: Forms are just to collect information - the real analysis happens in the chatbot when user confirms"""
                        enhanced_query = enhanced_query + conversational_instruction
            
            # Skip RAG if requested (for fast phase form help)
            if skip_rag:
                # Create empty RAG response immediately
                from backend.models.schemas import AgentResponse
                rag_response = AgentResponse(
                    agent_type="rag",
                    response="RAG skipped for fast response mode.",
                    metadata={"skipped": True, "reason": "fast_mode"},
                    timestamp=datetime.utcnow()
                )
                yield {
                    "type": "agent_complete",
                    "agent": "rag",
                    "response": "RAG skipped for fast response.",
                    "progress": 0.1,
                    "timestamp": datetime.utcnow().isoformat(),
                    "metadata": {
                        "system_context": "RAG skipped",
                        "system_prompt": "RAG skipped for fast mode",
                        "user_prompt": enhanced_query[:500],
                        "rag_context": "RAG skipped",
                    }
                }
            # Start with RAG agent - optimized for speed
            # Only run RAG if there's actual knowledge base content or attached documents
            elif not skip_rag:
                has_knowledge_base = enhanced_context.get("product_id") is not None
                has_attached_docs = enhanced_context.get("attached_documents") or enhanced_context.get("file_attachments")
                
                # Check if RAG agent actually has knowledge base available
                # CRITICAL: Filter by product_id when checking for knowledge
                rag_has_knowledge = False
                if hasattr(self.rag_agent, 'agno_agent') and self.rag_agent.agno_agent:
                    if hasattr(self.rag_agent.agno_agent, 'knowledge') and self.rag_agent.agno_agent.knowledge:
                        # Try a quick search to see if there's any content for this product
                        try:
                            # Pass product_id as filter to check for product-specific knowledge
                            test_filters = {}
                            if enhanced_context.get("product_id"):
                                test_filters["product_id"] = str(enhanced_context.get("product_id"))
                            test_results = await self.rag_agent.search_knowledge(enhanced_query[:50], top_k=1, filters=test_filters)
                            rag_has_knowledge = len(test_results) > 0
                        except:
                            rag_has_knowledge = False
                
                # Skip RAG completely if no knowledge base, no documents, and no actual knowledge content
                if not has_knowledge_base and not has_attached_docs and not rag_has_knowledge:
                    skip_metadata = {
                        "system_context": "No RAG context available",
                        "system_prompt": "Skipped RAG - no documents or knowledge base",
                        "user_prompt": enhanced_query,  # No truncation
                        "rag_context": "No RAG context retrieved",
                        "skipped": True,
                        "reason": "no_documents_or_kb"
                    }
                    yield {
                        "type": "agent_complete",
                        "agent": "rag",
                        "response": "No knowledge base content available. Skipping RAG agent.",
                        "progress": 0.2,
                        "timestamp": datetime.utcnow().isoformat(),
                        "metadata": skip_metadata
                    }
                    # CRITICAL: Also yield interaction event for skipped RAG so it's tracked
                    yield {
                        "type": "interaction",
                        "from_agent": "coordinator",
                        "to_agent": "rag",
                        "query": enhanced_query,  # No truncation
                        "response": "No knowledge base content available. Skipping RAG agent.",
                        "metadata": skip_metadata,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    # Add to interactions list
                    interactions.append({
                        "from_agent": "coordinator",
                        "to_agent": "rag",
                        "query": enhanced_query,  # No truncation
                        "response": "No knowledge base content available. Skipping RAG agent.",
                        "metadata": skip_metadata,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    # Create empty RAG response object
                    from backend.models.schemas import AgentResponse
                    rag_response = AgentResponse(
                        agent_type="rag",
                        response="No knowledge base content available.",
                        metadata={"skipped": True, "reason": "no_documents_or_kb"},
                        timestamp=datetime.utcnow()
                    )
                else:
                    # RAG has knowledge - process it
                    yield {
                        "type": "agent_start",
                        "agent": "rag",
                        "query": enhanced_query,
                        "progress": 0.1,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    # Optimize RAG: limit search results and add reasonable timeout
                    # Increased timeout to 60 seconds to allow for:
                    # - Lazy knowledge base creation (with retries)
                    # - Vector database connection establishment
                    # - Vector search operations (fast, but may need to search through many documents)
                    # - Document retrieval and processing
                    # - Handling cases with 10+ documents in knowledge base
                    # Note: RAG search itself is fast (vector similarity search), but processing
                    # multiple retrieved documents and generating embeddings can take time
                    try:
                        rag_response = await asyncio.wait_for(
                            self.rag_agent.process(
                                [AgentMessage(role="user", content=enhanced_query, timestamp=datetime.utcnow())],
                                enhanced_context
                            ),
                            timeout=60.0  # 60 second timeout for RAG (increased from 30s to handle 10+ documents)
                        )
                    except asyncio.TimeoutError as e:
                        error_msg = "RAG agent timed out after 60 seconds. Proceeding without RAG context."
                        self.logger.warning("rag_agent_timeout", query=enhanced_query[:100], error=error_msg)
                        from backend.models.schemas import AgentResponse
                        rag_response = AgentResponse(
                            agent_type="rag",
                            response=error_msg,
                            metadata={"timeout": True, "error": error_msg, "error_type": "TimeoutError"},
                            timestamp=datetime.utcnow()
                        )
                    except Exception as e:
                        error_type = type(e).__name__
                        error_msg = str(e) if str(e) else f"{error_type} occurred"
                        if not error_msg or error_msg == "":
                            error_msg = f"RAG agent encountered {error_type}. Proceeding without RAG context."
                        else:
                            error_msg = f"RAG agent error: {error_msg}. Proceeding without RAG context."
                        self.logger.error("rag_agent_error", error=error_msg, error_type=error_type)
                        from backend.models.schemas import AgentResponse
                        rag_response = AgentResponse(
                            agent_type="rag",
                            response=error_msg,
                            metadata={"error": error_msg, "error_type": error_type},
                            timestamp=datetime.utcnow()
                        )
            
            # Build system context for RAG agent
            system_context_str = self._build_system_content(enhanced_context) if enhanced_context else "Not available"
            rag_metadata = {
                "system_context": system_context_str if system_context_str != "Not available" else "Not available",  # Remove truncation
                "system_prompt": self.rag_agent.system_prompt if hasattr(self.rag_agent, 'system_prompt') else "Not available",  # Remove truncation
                "user_prompt": enhanced_query,  # Remove truncation
                "rag_context": rag_response.response if rag_response and rag_response.response else "No RAG context retrieved",  # Remove truncation
            }
            if rag_response and rag_response.metadata:
                rag_metadata.update(rag_response.metadata)
            
            yield {
                "type": "agent_complete",
                "agent": "rag",
                "response": rag_response.response if rag_response and rag_response.response else "No RAG context retrieved",  # No truncation - full response
                "progress": 0.2,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": rag_metadata
            }
            
            # CRITICAL: Also yield an interaction event for RAG so it's tracked in interactions list
            # This ensures RAG usage is visible in test verification and metadata
            yield {
                "type": "interaction",
                "from_agent": "coordinator",
                "to_agent": "rag",
                "query": enhanced_query,  # No truncation
                "response": rag_response.response if rag_response and rag_response.response else "No RAG context retrieved",  # No truncation
                "metadata": rag_metadata,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Also add to interactions list for final response
            interactions.append({
                "from_agent": "coordinator",
                "to_agent": "rag",
                "query": enhanced_query,  # No truncation
                "response": rag_response.response if rag_response and rag_response.response else "No RAG context retrieved",  # No truncation
                "metadata": rag_metadata,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Skip supporting agents if single_agent_mode is enabled (for fast phase form help)
            if single_agent_mode:
                # Skip all supporting agents, go directly to primary agent
                supporting_agents_list = []
                tasks = {}
                full_supporting_response = ""
                # Skip RAG context in query for single agent mode
                if skip_rag:
                    # RAG already skipped above, proceed directly to primary agent
                    pass
            else:
                # Run supporting agents in parallel (only if not in single agent mode)
                # Respect user-specified supporting agents, or auto-determine if not specified
                if supporting_agents:
                    # User specified agents - use them (but exclude RAG if it was skipped)
                    supporting_agents_list = [a for a in supporting_agents if a != "rag" or (rag_response and rag_response.metadata and not rag_response.metadata.get("skipped"))]
                else:
                    # Auto-determine based on query, primary agent, and phase context
                    # CRITICAL: Pass context to determine_supporting_agents for phase-aware selection
                    if not primary_agent:
                        # Determine primary agent with context
                        primary_agent, confidence = self.determine_primary_agent(enhanced_query, enhanced_context)
                        self.logger.info(
                            "auto_determined_primary_agent",
                            primary_agent=primary_agent,
                            confidence=confidence,
                            phase_name=enhanced_context.get("phase_name") if enhanced_context else None
                        )
                    
                    # Use determined primary agent, don't fallback to ideation if we have phase context
                    # Only fallback to ideation if no phase context and low confidence
                    if not primary_agent:
                        phase_name = enhanced_context.get("phase_name") if enhanced_context else None
                        if phase_name:
                            # If we have phase context but no primary agent, determine again with stricter criteria
                            primary_agent, confidence = self.determine_primary_agent(enhanced_query, enhanced_context)
                            if not primary_agent or confidence < 0.3:
                                # Map phase to agent directly
                                phase_lower = phase_name.lower()
                                if "research" in phase_lower or "market" in phase_lower:
                                    primary_agent = "research"
                                elif "requirement" in phase_lower or "prd" in phase_lower:
                                    primary_agent = "prd_authoring"
                                elif "design" in phase_lower:
                                    primary_agent = "prd_authoring"
                                elif "strategy" in phase_lower or "gtm" in phase_lower or "go-to-market" in phase_lower:
                                    primary_agent = "strategy"
                                elif "ideation" in phase_lower:
                                    primary_agent = "ideation"
                                else:
                                    primary_agent = "research"  # Default to research for unknown phases
                        else:
                            # No phase context - only then fallback to ideation
                            primary_agent = "ideation"
                    
                    supporting_agents_list = self.determine_supporting_agents(
                        enhanced_query, 
                        primary_agent,
                        enhanced_context  # Pass context for phase-aware selection
                    )
                    # Remove RAG from auto-determined list if it was skipped
                    if rag_response and rag_response.metadata and rag_response.metadata.get("skipped"):
                        supporting_agents_list = [a for a in supporting_agents_list if a != "rag"]
                
                # Build shared context message with RAG context only if available
                # CRITICAL: Include full RAG context without truncation for comprehensive reference
                if rag_response and rag_response.response and not (rag_response.metadata and rag_response.metadata.get("skipped")):
                    # Include full RAG context - no truncation to ensure all knowledge is available
                    shared_context_msg = f"{enhanced_query}\n\nKnowledge Base Context (Reference these documents when relevant):\n{rag_response.response}\n\nIMPORTANT: Use knowledge base context to provide specific, actionable insights. Reference specific documents when relevant. Write content AS IF THE USER TYPED IT DIRECTLY - do not use coaching language."
                else:
                    shared_context_msg = f"{enhanced_query}\n\nIMPORTANT: Provide specific, actionable insights. Write content AS IF THE USER TYPED IT DIRECTLY - do not use coaching language."
                
                shared_message = [AgentMessage(role="user", content=shared_context_msg, timestamp=datetime.utcnow())]
                
                # Start all agents (but mark as internal so frontend doesn't show them)
                tasks = {}
                for agent_name in supporting_agents_list:
                    if agent_name in self.agents and agent_name != "rag":  # Skip RAG if already processed
                        yield {
                            "type": "agent_start",
                            "agent": agent_name,
                            "query": shared_context_msg[:200],
                            "progress": 0.3,
                            "timestamp": datetime.utcnow().isoformat(),
                            "internal": True  # Mark as internal - don't show to user
                        }
                        tasks[agent_name] = self.agents[agent_name].process(shared_message, enhanced_context)
            
            # Process supporting agents silently - don't stream their responses to user
            # Only store them for primary agent synthesis
            for agent_name, task in tasks.items():
                try:
                    response = await task
                    if hasattr(response, 'response'):
                        full_response = response.response
                        
                        # Build comprehensive metadata for transparency (stored but not shown)
                        agent_instance = self.agents[agent_name]
                        system_context_str = self._build_system_content(enhanced_context) if enhanced_context else "Not available"
                        comprehensive_metadata = {
                            "system_context": system_context_str if system_context_str != "Not available" else "Not available",
                            "system_prompt": agent_instance.system_prompt if hasattr(agent_instance, 'system_prompt') else "Not available",
                            "user_prompt": shared_context_msg,
                            "rag_context": rag_response.response if rag_response and rag_response.response else "No RAG context retrieved",
                        }
                        # Merge with response metadata if available
                        if hasattr(response, 'metadata') and response.metadata:
                            comprehensive_metadata.update(response.metadata)
                        
                        # Create AgentInteraction for supporting agents to track usage and metadata
                        from backend.models.schemas import AgentInteraction
                        supporting_interaction = AgentInteraction(
                            from_agent="coordinator",
                            to_agent=agent_name,
                            query=shared_context_msg,  # No truncation
                            response=full_response,  # No truncation - store full response
                            metadata=comprehensive_metadata,
                            timestamp=datetime.utcnow()
                        )
                        self.interaction_history.append(supporting_interaction)
                        interactions.append({
                            "from_agent": "coordinator",
                            "to_agent": agent_name,
                            "query": shared_context_msg,  # No truncation
                            "response": full_response,  # No truncation - store full response
                            "metadata": comprehensive_metadata,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        
                        # Yield agent_complete with internal flag - frontend will filter this out
                        yield {
                            "type": "agent_complete",
                            "agent": agent_name,
                            "response": full_response,
                            "metadata": comprehensive_metadata,
                            "progress": 0.5 + (0.2 * (list(tasks.keys()).index(agent_name) / len(tasks))),
                            "timestamp": datetime.utcnow().isoformat(),
                            "internal": True  # Mark as internal - don't show to user
                        }
                except Exception as e:
                    self.logger.error(f"{agent_name}_agent_failed", error=str(e))
                    yield {
                        "type": "error",
                        "agent": agent_name,
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat(),
                        "internal": True  # Mark as internal
                    }
            
            # Final primary agent - determine intelligently if not provided
            if not primary_agent:
                primary, _ = self.determine_primary_agent(enhanced_query, enhanced_context)
            else:
                primary = primary_agent
            if primary in self.agents:
                yield {
                    "type": "agent_start",
                    "agent": primary,
                    "query": enhanced_query[:200],
                    "progress": 0.2 if single_agent_mode else 0.8,  # Faster progress if single agent
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Add word limit instruction if this is a phase form help request
                is_phase_form_help = context and context.get("current_field")
                response_length = context.get("response_length", "verbose") if context else "verbose"
                
                word_limit_instruction = ""
                if is_phase_form_help:
                    if response_length == "short":
                        word_limit_instruction = "\n\nCRITICAL WORD LIMIT: Maximum 500 words. Be concise and direct. Answer ONLY the specific question. Do NOT generate full PRD sections."
                    else:
                        word_limit_instruction = "\n\nCRITICAL WORD LIMIT: Maximum 1000 words. Be detailed but focused. Answer ONLY the specific question. Do NOT generate full PRD sections."
                elif is_phase_specific and not user_wants_full_prd:
                    # Add phase-specific restriction to primary agent query
                    word_limit_instruction = f"\n\nCRITICAL: The user is currently working on the {current_phase_name} phase. Generate content ONLY for the {current_phase_name} phase. Do NOT generate content for other phases (Market Research, Requirements, Design, etc.) unless explicitly requested. Focus your response on {current_phase_name} phase content only."
                elif is_phase_specific and not user_wants_full_prd:
                    # Add phase-specific restriction to primary agent query
                    word_limit_instruction = f"\n\nCRITICAL: The user is currently working on the {current_phase_name} phase. Generate content ONLY for the {current_phase_name} phase. Do NOT generate content for other phases (Market Research, Requirements, Design, etc.) unless explicitly requested. Focus your response on {current_phase_name} phase content only."
                
                # For single agent mode, use simplified query (no supporting agent context, no RAG context)
                if single_agent_mode:
                    prd_query = f"{enhanced_query}{word_limit_instruction}"
                else:
                    # Build comprehensive summary query for primary agent
                    # Collect all supporting agent responses from completed tasks
                    supporting_insights = []
                    supporting_responses = {}  # Store responses as they complete
                    
                    # Build query with proper summarization instructions
                    prd_query = f"{enhanced_query}{word_limit_instruction}\n\n"
                    
                    # Add RAG context if available - include full context without truncation
                    if rag_response and rag_response.response and not (rag_response.metadata and rag_response.metadata.get("skipped")):
                        prd_query += f"Knowledge Base Context (Reference these documents when relevant):\n{rag_response.response}\n\n"
                    
                    # Add supporting agent insights (will be populated from interactions list)
                    # CRITICAL: Include full responses without truncation for comprehensive synthesis
                    if interactions:
                        prd_query += "Supporting Agent Insights (synthesize these into your response):\n"
                        for interaction in interactions:
                            agent_name = interaction.get("to_agent")
                            if agent_name and agent_name in supporting_agents_list:
                                response_text = interaction.get("response", "")  # No truncation - include full response
                                if response_text:
                                    prd_query += f"[{agent_name.title()}]: {response_text}\n"
                        prd_query += "\n\n"
                    
                    # Add comprehensive synthesis instruction with emphasis on direct content generation
                    if interactions or (rag_response and rag_response.response and not (rag_response.metadata and rag_response.metadata.get("skipped"))):
                        prd_query += "\nCRITICAL INSTRUCTIONS:\n"
                        prd_query += "- Write content AS IF THE USER TYPED IT DIRECTLY - do not use coaching language\n"
                        prd_query += "- DO NOT say 'When you define the problem...' or 'The goal is to create...'\n"
                        prd_query += "- Instead, write the actual content: 'The problem we are solving is...' or 'Our product vision is...'\n"
                        prd_query += "- Reference knowledge base articles when relevant to support your content\n"
                        prd_query += "- Synthesize ALL information from phases, conversations, and knowledge base\n"
                        prd_query += "- Your response should be the actual PRD content, not instructions on how to write it\n\n"
                        if is_phase_specific and not user_wants_full_prd:
                            prd_query += f"CRITICAL: Synthesize the above insights into a comprehensive, intelligent response for the {current_phase_name} phase ONLY. Include all relevant details and actionable insights. Do NOT generate content for other phases. Structure your response with clear headings relevant to {current_phase_name} phase only. Quality and completeness are priorities.\n"
                        else:
                            # For regular chat queries, emphasize comprehensive, quality responses
                            # CRITICAL: Only structure response with headings for agents that were actually invoked
                            agent_headings = []
                            if any(i.get("to_agent") == "ideation" for i in interactions):
                                agent_headings.append("- ## Ideation Insights")
                            if any(i.get("to_agent") == "research" for i in interactions):
                                agent_headings.append("- ## Research Findings")
                            if any(i.get("to_agent") == "analysis" for i in interactions):
                                agent_headings.append("- ## Analysis & Recommendations")
                            if any(i.get("to_agent") == "strategy" for i in interactions):
                                agent_headings.append("- ## Strategy & Recommendations")
                            if any(i.get("to_agent") == "prd_authoring" for i in interactions):
                                agent_headings.append("- ## Requirements & Specifications")
                            
                            if agent_headings:
                                prd_query += "CRITICAL: Synthesize the above insights into a comprehensive, intelligent, and detailed response. Include all relevant context, insights, and actionable information. Quality and completeness are priorities - ensure the response is thorough, well-reasoned, and useful. Structure your response with clear headings:\n"
                                prd_query += "\n".join(agent_headings) + "\n"
                                prd_query += "- ## Summary & Next Steps\n"
                            else:
                                prd_query += "CRITICAL: Synthesize the above insights into a comprehensive, intelligent, and detailed response. Include all relevant context, insights, and actionable information. Quality and completeness are priorities - ensure the response is thorough, well-reasoned, and useful.\n"
                            prd_query += "\nProvide a comprehensive response that leverages all available insights.\n"
                
                # Determine model tier based on query type
                # Use fast model for phase form help, standard for regular chat queries (quality priority)
                original_model = None
                should_use_fast_model = use_fast_model and is_phase_form_help
                
                # For regular chat queries, use standard tier for better quality
                if not should_use_fast_model and hasattr(self.agents[primary], 'agno_agent') and self.agents[primary].agno_agent:
                    # Check current model tier - if it's fast, upgrade to standard for quality
                    current_model = self.agents[primary].agno_agent.model
                    current_model_id = getattr(current_model, 'id', '') if current_model else ''
                    
                    # If using fast model (gpt-5.1-chat-latest, haiku, flash), upgrade to standard
                    is_fast_model = any(fast_id in current_model_id.lower() for fast_id in [
                        'gpt-5.1-chat-latest', 'haiku', 'flash'
                    ])
                    
                    if is_fast_model:
                        # Temporarily switch to standard model for better quality
                        original_model = current_model
                        from backend.services.provider_registry import provider_registry
                        
                        standard_model = None
                        if provider_registry.has_openai_key():
                            # Use GPT-5.1 (standard tier) for quality responses
                            standard_model = OpenAIChat(id="gpt-5.1", api_key=provider_registry.get_openai_key(), max_completion_tokens=4000)
                        elif provider_registry.has_claude_key():
                            standard_model = Claude(id="claude-3.5-sonnet-20241022", api_key=provider_registry.get_claude_key())
                        elif provider_registry.has_gemini_key():
                            standard_model = Gemini(id="gemini-1.5-pro", api_key=provider_registry.get_gemini_key())
                        
                        if standard_model:
                            self.agents[primary].agno_agent.model = standard_model
                            self.logger.info("upgraded_to_standard_model", agent=primary, model=standard_model.id if hasattr(standard_model, 'id') else str(type(standard_model)), reason="quality_priority_for_chat")
                
                # Force fast model if requested (for phase form help only)
                if should_use_fast_model and hasattr(self.agents[primary], 'agno_agent') and self.agents[primary].agno_agent:
                    # Temporarily switch to fast model
                    original_model = self.agents[primary].agno_agent.model
                    from backend.services.provider_registry import provider_registry
                    
                    fast_model = None
                    if provider_registry.has_openai_key():
                        # GPT-5.1 models require max_completion_tokens instead of max_tokens
                        # Use fast model from settings (env.kind), fallback to agent_model_primary
                        fast_model_id = getattr(settings, "agent_model_fast", None) or getattr(settings, "agent_model_primary", "gpt-5.1")
                        fast_model = OpenAIChat(id=fast_model_id, api_key=provider_registry.get_openai_key(), max_completion_tokens=2000)
                    elif provider_registry.has_gemini_key():
                        fast_model = Gemini(id="gemini-1.5-flash", api_key=provider_registry.get_gemini_key())
                    elif provider_registry.has_claude_key():
                        fast_model = Claude(id="claude-3-haiku-20240307", api_key=provider_registry.get_claude_key())
                    
                    if fast_model:
                        self.agents[primary].agno_agent.model = fast_model
                        self.logger.info("switched_to_fast_model", agent=primary, model=fast_model.id if hasattr(fast_model, 'id') else str(type(fast_model)))
                
                try:
                    prd_response = await self.agents[primary].process(
                        [AgentMessage(role="user", content=prd_query, timestamp=datetime.utcnow())],
                        enhanced_context
                    )
                finally:
                    # Restore original model if we switched to fast model
                    if original_model:
                        self.agents[primary].agno_agent.model = original_model
                        self.logger.info("restored_original_model", agent=primary)
                
                # CRITICAL: Do NOT truncate responses - store full response asynchronously
                # Responses are saved to database asynchronously, so no truncation needed
                full_prd = prd_response.response
                # Note: response_length parameter is still respected for model generation,
                # but we don't truncate the final response - it's stored in full
                if is_phase_form_help and full_prd:
                    word_count = len(full_prd.split())
                    self.logger.info("response_generated", agent=primary, word_count=word_count, response_length=response_length)
                    # No truncation - full response is preserved and stored asynchronously
                
                # Stream PRD response
                chunk_size = 50
                for i in range(0, len(full_prd), chunk_size):
                    chunk = full_prd[i:i+chunk_size]
                    yield {
                        "type": "agent_chunk",
                        "agent": primary,
                        "chunk": chunk,
                        "progress": 0.85 + (0.1 * (i / len(full_prd))),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await asyncio.sleep(0.01)
                
                # Build comprehensive metadata for PRD agent
                prd_agent_instance = self.agents[primary]
                # Build system context as readable string
                system_context_str = self._build_system_content(enhanced_context) if enhanced_context else "Not available"
                prd_comprehensive_metadata = {
                    "system_context": system_context_str if system_context_str != "Not available" else "Not available",  # No truncation
                    "system_prompt": prd_agent_instance.system_prompt if hasattr(prd_agent_instance, 'system_prompt') else "Not available",  # No truncation
                    "user_prompt": prd_query,  # No truncation
                    "rag_context": rag_response.response if rag_response and rag_response.response else "No RAG context retrieved",  # No truncation
                }
                # Merge with response metadata if available (includes performance metrics)
                if hasattr(prd_response, 'metadata') and prd_response.metadata:
                    prd_comprehensive_metadata.update(prd_response.metadata)
                
                # Ensure performance metrics are included from agent response
                if hasattr(prd_response, 'metadata') and prd_response.metadata:
                    # Extract metrics from response metadata if not already present
                    if 'processing_time' not in prd_comprehensive_metadata and 'processing_time' in prd_response.metadata:
                        prd_comprehensive_metadata['processing_time'] = prd_response.metadata['processing_time']
                    if 'tokens' not in prd_comprehensive_metadata and 'tokens' in prd_response.metadata:
                        prd_comprehensive_metadata['tokens'] = prd_response.metadata['tokens']
                    if 'cache_hit' not in prd_comprehensive_metadata and 'cache_hit' in prd_response.metadata:
                        prd_comprehensive_metadata['cache_hit'] = prd_response.metadata['cache_hit']
                
                # Create AgentInteraction for PRD agent to track usage and metadata
                from backend.models.schemas import AgentInteraction
                # CRITICAL: Store full responses without truncation - responses are saved asynchronously
                prd_interaction = AgentInteraction(
                    from_agent="coordinator",
                    to_agent=primary,
                    query=prd_query,  # No truncation - store full query
                    response=full_prd,  # No truncation - store full response asynchronously
                    metadata=prd_comprehensive_metadata,
                    timestamp=datetime.utcnow()
                )
                self.interaction_history.append(prd_interaction)
                interactions.append({
                    "from_agent": "coordinator",
                    "to_agent": primary,
                    "query": prd_query,  # No truncation
                    "response": full_prd,  # No truncation - will be saved asynchronously
                    "metadata": prd_comprehensive_metadata,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Accumulate final response
                accumulated_response = full_prd
                
                yield {
                    "type": "agent_complete",
                    "agent": primary,
                    "response": full_prd,
                    "metadata": prd_comprehensive_metadata,
                    "progress": 0.95,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Also yield an interaction event for the PRD agent
                yield {
                    "type": "interaction",
                    "from_agent": "coordinator",
                    "to_agent": primary,
                    "query": prd_query,  # No truncation
                    "response": full_prd,  # No truncation - will be saved asynchronously
                    "metadata": prd_comprehensive_metadata,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Final completion
                # Get interaction history (convert to dict format) - include PRD interaction
                interaction_dicts = []
                for interaction in self.interaction_history[-10:]:
                    if hasattr(interaction, 'dict'):
                        interaction_dicts.append(interaction.dict())
                    elif hasattr(interaction, '__dict__'):
                        interaction_dicts.append({
                            "from_agent": getattr(interaction, 'from_agent', ''),
                            "to_agent": getattr(interaction, 'to_agent', ''),
                            "query": getattr(interaction, 'query', ''),
                            "response": getattr(interaction, 'response', ''),
                            "timestamp": getattr(interaction, 'timestamp', datetime.utcnow()).isoformat() if hasattr(getattr(interaction, 'timestamp', None), 'isoformat') else str(getattr(interaction, 'timestamp', datetime.utcnow())),
                            "metadata": getattr(interaction, 'metadata', {}) or {}
                        })
                    else:
                        interaction_dicts.append(interaction)
                
                # Ensure PRD interaction is included
                prd_interaction_dict = {
                    "from_agent": "coordinator",
                    "to_agent": primary,
                    "query": prd_query,  # No truncation
                    "response": full_prd,  # No truncation - will be saved asynchronously
                    "metadata": prd_comprehensive_metadata,
                    "timestamp": datetime.utcnow().isoformat()
                }
                # Add if not already in list
                if not any(i.get("to_agent") == primary and i.get("from_agent") == "coordinator" for i in interaction_dicts):
                    interaction_dicts.append(prd_interaction_dict)
                
                yield {
                    "type": "complete",
                    "response": full_prd,
                    "interactions": interaction_dicts,
                    "metadata": {
                        "mode": coordination_mode,
                        "primary_agent": primary,
                        "supporting_agents": supporting_agents_list,
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "progress": 1.0,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                yield {
                    "type": "error",
                    "error": f"Primary agent {primary} not found",
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        except asyncio.TimeoutError as e:
            error_type = "TimeoutError"
            error_message = "Request timed out. This may happen if the AI service is slow or overloaded. Please try again."
            self.logger.error("streaming_route_query_timeout", error=error_message, traceback=traceback.format_exc())
            yield {
                "type": "error",
                "error": error_message,
                "error_type": error_type,
                "timestamp": datetime.utcnow().isoformat()
            }
            # Yield partial results if available
            if accumulated_response:
                yield {
                    "type": "complete",
                    "response": accumulated_response,
                    "interactions": interactions,
                    "metadata": {"error": error_message, "error_type": error_type, "partial": True},
                    "timestamp": datetime.utcnow().isoformat()
                }
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            # Get detailed error information
            error_type = type(e).__name__
            error_message = str(e) if str(e) else ""
            error_repr = repr(e) if repr(e) else ""
            
            # Build descriptive error message
            if error_type == "TimeoutError":
                final_error_message = "Request timed out. This may happen if the AI service is slow or overloaded. Please try again."
            elif error_message and error_message != "":
                final_error_message = f"{error_type}: {error_message}"
            elif error_repr and error_repr != "":
                final_error_message = f"{error_type}: {error_repr}"
            else:
                final_error_message = f"{error_type} occurred during streaming. Please try again."
            
            self.logger.error(
                "streaming_route_query_error",
                error=final_error_message,
                error_type=error_type,
                error_message=error_message,
                error_repr=error_repr,
                traceback=error_trace
            )
            
            yield {
                "type": "error",
                "error": final_error_message,
                "error_type": error_type,
                "timestamp": datetime.utcnow().isoformat()
            }
            # Also yield a complete event with partial results if available
            if accumulated_response:
                yield {
                    "type": "complete",
                    "response": accumulated_response,
                    "interactions": interactions,
                    "metadata": {"error": final_error_message, "error_type": error_type, "partial": True},
                    "timestamp": datetime.utcnow().isoformat()
                }
    
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
                # Build context if available
                enhanced_context = {}
                if context:
                    try:
                        enhanced_context = await self._build_comprehensive_context(
                            product_id=context.get("product_id"),
                            session_ids=context.get("session_ids"),
                            user_context=context,
                            db=db
                        )
                    except:
                        enhanced_context = context or {}
                
                if not primary_agent:
                    primary_agent, confidence = self.determine_primary_agent(query, enhanced_context)
                    self.logger.info("auto_routed", primary_agent=primary_agent, confidence=confidence, phase_name=enhanced_context.get("phase_name"))
                
                # Get primary agent
                if primary_agent not in self.agents:
                    raise ValueError(f"Primary agent '{primary_agent}' not found")
                
                primary = self.agents[primary_agent]
                
                # Get supporting agents with phase context
                if not supporting_agents:
                    supporting_agents = self.determine_supporting_agents(query, primary_agent, enhanced_context)
                
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

