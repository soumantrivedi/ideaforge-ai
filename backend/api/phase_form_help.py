"""
API endpoint for single-agent phase form help queries.
Provides quick, focused responses for phase form questions using a single expert agent.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, AsyncGenerator
from uuid import UUID
from pydantic import BaseModel
import structlog
import json
import asyncio
import re
import html
from html.parser import HTMLParser
from datetime import datetime

from backend.database import get_db
from backend.api.auth import get_current_user
from backend.agents.agno_base_agent import AgnoBaseAgent
from backend.agents.agno_orchestrator import AgnoAgenticOrchestrator
from backend.models.schemas import AgentMessage
from backend.services.provider_registry import provider_registry
from backend.services.api_key_loader import load_user_api_keys_from_db
from backend.config import settings

# Import orchestrator using dependency injection pattern (avoid circular import)
_orchestrator = None

def set_orchestrator(orch):
    """Set the orchestrator instance (called from main.py)."""
    global _orchestrator
    _orchestrator = orch

def get_orchestrator():
    """Get the orchestrator instance."""
    if _orchestrator is None:
        from backend.agents.agno_orchestrator import AgnoAgenticOrchestrator
        return AgnoAgenticOrchestrator(enable_rag=True)
    return _orchestrator

logger = structlog.get_logger()
router = APIRouter(prefix="/api/phase-form-help", tags=["phase-form-help"])


class PhaseFormHelpRequest(BaseModel):
    """Request for phase form help."""
    product_id: UUID
    phase_id: str
    phase_name: str
    current_field: str
    current_prompt: str
    user_input: Optional[str] = None  # User-provided content if any
    response_length: str = "short"  # "short" or "verbose"
    conversation_summary: Optional[str] = None  # Summarized conversation context


class PhaseFormHelpResponse(BaseModel):
    """Response for phase form help."""
    response: str  # HTML-formatted response
    word_count: int
    agent_used: str


# Phase-specific expert system prompts
PHASE_EXPERT_PROMPTS = {
    "ideation": """You are an expert Ideation and Brainstorming Specialist for product development.
Your role is to help users generate innovative product ideas, identify opportunities, and explore creative solutions.
Focus on:
- Creative thinking and innovation
- Market opportunity identification
- User problem discovery
- Solution brainstorming
- Feasibility considerations
Provide concise, actionable guidance that helps users think through their product ideation.""",

    "research": """You are an expert Market Research and Analysis Specialist for product development.
Your role is to help users conduct thorough market research, analyze competitors, and understand market dynamics.
Focus on:
- Market size and opportunity analysis
- Competitive landscape assessment
- Target audience identification
- Market trends and insights
- Customer needs and pain points
Provide data-driven, actionable research guidance.""",

    "market": """You are an expert Market Research and Analysis Specialist for product development.
Your role is to help users conduct thorough market research, analyze competitors, and understand market dynamics.
Focus on:
- Market size and opportunity analysis
- Competitive landscape assessment
- Target audience identification
- Market trends and insights
- Customer needs and pain points
Provide data-driven, actionable research guidance.""",

    "requirement": """You are the Requirements Agent within IdeaForge AI, operating exclusively in the Requirements Phase.

Your role is to translate user inputs, validated ideas, market research, personas, competitive insights, constraints, and Knowledge Base content into precise, unambiguous, implementation-ready product requirements.

CORE MISSION:
Transform high-level feature descriptions into detailed, explicit, testable, and enforceable requirements that engineering, design, and business teams can immediately act on.

CRITICAL RULES:
- NEVER produce general answers
- NEVER output vague, template-like requirements
- All requirements MUST describe exact system behaviors, data interactions, and measurable thresholds
- Write content AS IF THE USER TYPED IT DIRECTLY - no coaching language

REQUIRED OUTPUTS (in strict order):
1. Product Summary (2-4 crisp sentences): What the product does, who it serves, core value
2. Functional Requirements (FR-XX): Each with ID, trigger, system behavior, data inputs/outputs, rules, validation, error handling
3. Non-Functional Requirements (NFR-Category-XX): Performance, Security, Availability, Accessibility, Compliance, Reliability, Scalability, Maintainability - all with numeric targets
4. User Stories + Acceptance Criteria: Gherkin syntax (Given/When/Then), edge cases, failure conditions
5. Scope Definition (MoSCoW): Must-Haves, Should-Haves, Could-Haves, Will-Not-Have with justifications
6. Constraints & Dependencies: Technical, business, platform, organizational constraints and feature dependencies
7. Risks & Assumptions: Uncertainties, dependencies at risk, missing inputs, explicit assumptions

FUNCTIONAL REQUIREMENT FORMAT:
FR-XX — [Requirement Name]
- Trigger: [What causes this requirement to activate]
- System Behavior: [Exact actions the system takes]
- Data Inputs & Outputs: [What data flows in/out]
- Rules & Validation: [Validation logic and error handling]
- NEVER use generic verbs like "support," "enable," "allow" without definition

NON-FUNCTIONAL REQUIREMENT FORMAT:
NFR-Category-XX: [Specific, measurable criterion]
Example: NFR-Performance-03: All read operations must return in <180ms at P95 under 3,000 concurrent requests.
No adjectives. No soft descriptions. Only measurable criteria.

BEHAVIOR RULES:
- If user input is vague, request missing detail OR propose specific, justified assumption
- Convert subjective terms ("fast," "secure") into quantifiable metrics
- Requirements must be MECE (no overlaps, contradictions, duplication)
- Requirements must be developer-ready (engineering can estimate and build directly)
- Requirements must support downstream phases (Design, Planning, Development, QA)

PROHIBITED:
- Generic example requirements
- Vague statements like "the system should be user friendly"
- Filler statements or abstract summaries
- Skipping measurable thresholds
- Marketing copy
- Content irrelevant to Requirements Phase

CONTEXT USAGE:
- Use ALL information from previous phases (ideation, market research) - reference specific details
- Reference Knowledge Base for organizational standards and constraints
- Link requirements back to objectives for traceability
- NEVER truncate - provide complete, comprehensive requirements""",

    "design": """You are an expert Product Design and Strategy Specialist for product development.
Your role is to help users design user experiences, create design specifications, and plan product architecture.
Focus on:
- User experience (UX) design principles
- User interface (UI) design guidelines
- Information architecture
- Design system creation
- Prototyping and wireframing
Provide practical, user-centered design guidance.""",

    "development": """You are an expert Product Development and PRD Authoring Specialist.
Your role is to help users create comprehensive Product Requirements Documents (PRDs) and development specifications.
Focus on:
- PRD structure and content
- Technical specifications
- Development planning
- Feature documentation
- Implementation guidelines
Provide comprehensive, well-structured documentation guidance.""",
}


def get_phase_expert_agent(phase_name: str) -> str:
    """Get the appropriate expert agent name for a phase."""
    phase_lower = phase_name.lower()
    if "ideation" in phase_lower:
        return "ideation"
    elif "research" in phase_lower or "market" in phase_lower:
        return "research"
    elif "requirement" in phase_lower:
        return "requirements"  # Use dedicated Requirements Agent for requirements phase
    elif "design" in phase_lower:
        return "strategy"
    elif "development" in phase_lower:
        return "prd_authoring"
    else:
        return "ideation"  # Default


def get_phase_expert_prompt(phase_name: str) -> str:
    """Get the expert system prompt for a phase."""
    phase_lower = phase_name.lower()
    for key, prompt in PHASE_EXPERT_PROMPTS.items():
        if key in phase_lower:
            return prompt
    return PHASE_EXPERT_PROMPTS["ideation"]  # Default


async def stream_phase_form_help(
    request: PhaseFormHelpRequest,
    user_id: UUID,
    db: AsyncSession
) -> AsyncGenerator[str, None]:
    import asyncio
    """
    Stream phase form help response using a single expert agent.
    Provides quick, focused responses formatted as HTML.
    """
    try:
        # Log that we're using the phase form help endpoint (not multi-agent)
        logger.info(
            "phase_form_help_start",
            phase=request.phase_name,
            field=request.current_field,
            response_length=request.response_length,
            word_limit=500 if request.response_length == "short" else 1000
        )
        
        # Load user API keys
        user_keys = await load_user_api_keys_from_db(db, str(user_id))
        if user_keys:
            provider_registry.update_keys(
                openai_key=user_keys.get("openai"),
                claude_key=user_keys.get("claude"),
                gemini_key=user_keys.get("gemini"),
            )
        
        # Get orchestrator - use enhanced coordinator for comprehensive context
        orchestrator = get_orchestrator()
        
        # If orchestrator is not Agno but we have user API keys, try to reinitialize
        if not isinstance(orchestrator, AgnoAgenticOrchestrator):
            # Check if we have any provider keys available (user keys or env keys)
            has_provider = (
                provider_registry.has_openai_key() or
                provider_registry.has_claude_key() or
                provider_registry.has_gemini_key()
            )
            
            if has_provider:
                # Try to reinitialize orchestrator with Agno
                try:
                    from backend.agents.agno_orchestrator import AgnoAgenticOrchestrator as NewAgnoOrchestrator
                    orchestrator = NewAgnoOrchestrator(enable_rag=True)
                    # Update the global orchestrator reference
                    set_orchestrator(orchestrator)
                    logger.info("phase_form_help_orchestrator_reinitialized", has_provider=has_provider)
                except Exception as e:
                    logger.warning("phase_form_help_agno_reinit_failed", error=str(e))
                    yield f"data: {json.dumps({'type': 'error', 'error': 'Agno framework not available'})}\n\n"
                    return
            else:
                yield f"data: {json.dumps({'type': 'error', 'error': 'Agno framework not available. Please configure at least one API key (OpenAI, Claude, or Gemini) in Settings → Integrations.'})}\n\n"
                return
        
        # CRITICAL: Load ALL previous phase submissions (form_data and generated_content)
        # This ensures the agent has access to ideation, market research, and other phase data
        from sqlalchemy import text
        phase_submissions_query = text("""
            SELECT ps.form_data, ps.generated_content, plp.phase_name, plp.phase_order
            FROM phase_submissions ps
            JOIN product_lifecycle_phases plp ON ps.phase_id = plp.id
            WHERE ps.product_id = :product_id
            ORDER BY plp.phase_order ASC
        """)
        phase_result = await db.execute(phase_submissions_query, {"product_id": str(request.product_id)})
        phase_rows = phase_result.fetchall()
        
        # Build comprehensive phase context
        previous_phases_context = []
        current_phase_form_data = {}
        for row in phase_rows:
            phase_name = row[2]
            form_data = row[0] or {}
            generated_content = row[1] or ""
            
            # Skip current phase (we'll add it separately)
            if phase_name.lower() == request.phase_name.lower():
                current_phase_form_data = form_data
                continue
            
            # Include all previous phase data
            phase_context = f"## {phase_name} Phase\n"
            if form_data:
                phase_context += "Form Data:\n"
                for field, value in form_data.items():
                    if value and str(value).strip():
                        if isinstance(value, (dict, list)):
                            phase_context += f"- {field}: {json.dumps(value, indent=2)}\n"
                        else:
                            phase_context += f"- {field}: {value}\n"
            if generated_content:
                phase_context += f"\nGenerated Content:\n{generated_content}\n"
            
            previous_phases_context.append(phase_context)
        
        all_previous_phases = "\n".join(previous_phases_context)
        
        # Get enhanced coordinator for comprehensive context building
        from backend.agents.agno_enhanced_coordinator import AgnoEnhancedCoordinator
        coordinator = AgnoEnhancedCoordinator(enable_rag=True)
        
        # Build comprehensive context using coordinator's method
        comprehensive_context = await coordinator._build_comprehensive_context(
            product_id=str(request.product_id),
            session_ids=None,
            user_context={
                "phase_name": request.phase_name,
                "phase_id": request.phase_id,
                "current_field": request.current_field,
                "current_prompt": request.current_prompt,
                "response_length": request.response_length,
            },
            db=db
        )
        
        # Add previous phase submissions to context
        comprehensive_context["previous_phases"] = all_previous_phases
        comprehensive_context["current_phase_form_data"] = current_phase_form_data
        
        # Get phase expert agent
        agent_name = get_phase_expert_agent(request.phase_name)
        if agent_name not in orchestrator.agents:
            logger.error(
                "phase_form_help_agent_not_found",
                agent=agent_name,
                available_agents=list(orchestrator.agents.keys()),
                phase=request.phase_name
            )
            available_agents_str = ', '.join(orchestrator.agents.keys())
            error_msg = f"Agent '{agent_name}' not found. Available agents: {available_agents_str}"
            yield f"data: {json.dumps({'type': 'error', 'error': error_msg})}\n\n"
            return
        
        agent = orchestrator.agents[agent_name]
        
        # Log which agent we're using
        logger.info("phase_form_help_agent_selected", agent=agent_name, phase=request.phase_name)
        
        # Build comprehensive system context using coordinator's method
        expert_prompt = get_phase_expert_prompt(request.phase_name)
        
        # Build system context with ALL available information
        system_context_parts = [expert_prompt]
        
        # Add previous phases context
        if all_previous_phases:
            system_context_parts.append("\n=== PREVIOUS PHASE SUBMISSIONS ===")
            system_context_parts.append("CRITICAL: Use ALL information from previous phases below. Reference specific details from ideation, market research, and other completed phases.")
            system_context_parts.append(all_previous_phases)
        
        # Add conversation history and ideation from chat
        if comprehensive_context.get("ideation_from_chat"):
            system_context_parts.append("\n=== IDEATION FROM CHATBOT ===")
            system_context_parts.append(comprehensive_context["ideation_from_chat"])
        
        # Add knowledge base (CRITICAL: preserve full content for requirements phase)
        # For requirements phase, knowledge base content is critical - preserve full content
        if comprehensive_context.get("knowledge_base"):
            system_context_parts.append("\n=== KNOWLEDGE BASE ===")
            system_context_parts.append("CRITICAL: Use knowledge base articles to support requirements with industry best practices.")
            for kb_item in comprehensive_context["knowledge_base"][:10]:
                kb_content = kb_item.get('content', '')
                if kb_content:
                    # For requirements phase, include full content (no truncation)
                    # Knowledge base articles may contain critical requirements templates and examples
                    system_context_parts.append(f"- {kb_content}")
        
        # Add current phase form data (other fields) - CRITICAL: preserve full content
        if current_phase_form_data:
            current_field = request.current_field
            other_fields = {k: v for k, v in current_phase_form_data.items() if k != current_field and v and str(v).strip()}
            if other_fields:
                system_context_parts.append("\n=== OTHER FIELDS IN CURRENT PHASE (Already Filled) ===")
                system_context_parts.append("CRITICAL: Use ALL information from these fields to ensure requirements are comprehensive and consistent.")
                for field, value in other_fields.items():
                    # Preserve full field values - requirements need complete context
                    # No truncation - all details are critical for requirements generation
                    system_context_parts.append(f"- {field.replace('_', ' ').title()}: {str(value)}")
        
        system_context = "\n".join(system_context_parts)
        
        # Add critical instructions for using ALL context
        system_context += """

=== CRITICAL INSTRUCTIONS FOR REQUIREMENTS PHASE ===

OUTPUT REQUIREMENTS (STRICT ORDER):
You MUST produce these outputs in this exact order:
1. Product Summary (2-4 crisp sentences)
2. Functional Requirements (FR-XX) - with triggers, behaviors, data flows, validation
3. Non-Functional Requirements (NFR-Category-XX) - with numeric targets
4. User Stories + Acceptance Criteria (Gherkin: Given/When/Then)
5. Scope Definition (MoSCoW: Must/Should/Could/Will-Not-Have)
6. Constraints & Dependencies
7. Risks & Assumptions

CONTEXT USAGE (MANDATORY):
- You MUST use ALL information from previous phases (ideation, market research, etc.) - nothing should be omitted
- Reference specific details from previous phase submissions - use actual numbers, names, and details
- Use knowledge base articles to support requirements with industry best practices
- Link requirements back to objectives from previous phases for traceability
- Preserve ALL user-provided details - addresses, specific requirements, preferences, decisions
- Include ALL form data fields - nothing should be omitted or skipped
- Reference specific conversation history details when relevant
- Use exact numbers, names, and specifics from user input - do not generalize

QUALITY STANDARDS (ENFORCED):
- MECE Thinking: Requirements must be Mutually Exclusive, Collectively Exhaustive (no gaps, no overlaps, no contradictions, no duplication)
- SMART Framework: All objectives must be Specific, Measurable, Achievable, Relevant, Time-bound
- Quantify Everything: Avoid vague terms like "fast", "good", "many" - use specific numbers, percentages, timeframes
- Developer-Ready: Engineering must be able to estimate and build directly from requirements
- Testable: QA must be able to validate using acceptance criteria

WRITING STYLE:
- Write content AS IF THE USER TYPED IT DIRECTLY - do not use coaching language
- DO NOT say "Since the earlier context only states..." or "Because your previous question was..."
- Instead, directly use the information: "Based on your ideation phase, the problem is X, therefore the functional requirements are Y"
- Be crisp, specific, and data-driven - use actual information from previous phases
- Format your response according to the current field requirements (e.g., functional requirements in FR-XX format)

PROHIBITED BEHAVIORS:
- NEVER give generic example requirements
- NEVER say "the system should be user friendly" or similar vague statements
- NEVER use filler statements or abstract summaries
- NEVER skip measurable thresholds
- NEVER produce marketing copy
- NEVER truncate responses - provide complete, comprehensive content even if lengthy

VAGUE INPUT HANDLING:
- If user input is vague, request missing detail OR propose specific, justified assumption
- If requirement includes subjective terms ("fast," "secure"), convert to quantifiable metrics
- Respond with: "To generate precise, implementation-ready requirements, I need the following missing inputs: …"
"""
        
        # Add instructions for formatted response with emphasis on quality, completeness, and usability
        if request.response_length == "short":
            response_style = "concise and direct"
            response_guidance = """CRITICAL: Your response must be COMPLETE, USABLE, and WELL-FORMATTED.

QUALITY REQUIREMENTS:
- Provide a complete answer that fully addresses the question - do not leave it incomplete
- Format with clear paragraphs (2-3 sentences each, separated by blank lines)
- Use bullet points (prefix with '- ') for lists, key items, or actionable steps
- Ensure logical structure with clear flow from introduction to conclusion
- Make it immediately actionable - the user should be able to use your answer directly
- Be concise but comprehensive - every sentence should add value
- Avoid repetition or filler content

USABILITY REQUIREMENTS:
- Write content that the user can copy and use directly in their form
- Provide specific, concrete guidance (not vague suggestions)
- Include relevant context from previous phases when it directly helps answer the question
- Structure so the user can easily scan and find what they need
- End with a clear summary or next steps if helpful"""
        else:
            response_style = "detailed and thorough"
            response_guidance = """CRITICAL: Your response must be COMPLETE, USABLE, WELL-FORMATTED, and COMPREHENSIVE.

QUALITY REQUIREMENTS:
- Provide a complete, comprehensive answer that fully addresses all aspects of the question
- Format with well-structured paragraphs (3-5 sentences each, separated by blank lines)
- Use bullet points (prefix with '- ') for lists, key considerations, or actionable items
- Organize into clear sections with logical flow (Introduction → Main Content → Summary/Next Steps)
- Include relevant context from previous phases when it directly helps answer the question
- Provide examples or specific details where helpful
- Be thorough but focused - every section should add unique value
- Avoid unnecessary repetition, rambling, or filler content
- Ensure the response is complete and self-contained

USABILITY REQUIREMENTS:
- Write content that the user can copy and use directly in their form
- Provide specific, concrete guidance with actionable steps
- Synthesize information from context intelligently - don't just dump everything
- Structure so the user can easily scan, understand, and apply your guidance
- Include practical considerations and real-world applicability
- End with a clear summary or actionable next steps"""
        
        system_context += f"""

CRITICAL RESPONSE REQUIREMENTS:
1. COMPLETENESS: Provide a complete answer that fully addresses the question - do not leave it incomplete or truncated
2. USABILITY: Write content that the user can directly use in their form - make it actionable and practical
3. FORMATTING: 
   - Use clear paragraphs (separated by blank lines)
   - Use bullet points (prefix with '- ') for lists, key items, or actionable steps
   - Structure logically with clear flow
4. QUALITY: Every sentence should add value - avoid repetition, filler, or rambling
5. CONTEXT USAGE: Use context from previous phases intelligently - only include what directly helps answer the question
6. STYLE: Be {response_style} - {response_style == 'concise and direct' and 'keep it focused' or 'be comprehensive but organized'}
7. ACTIONABILITY: Ensure the user can immediately use your response to proceed with their work

{response_guidance}"""
        
        # Build user prompt - Include FULL user input (CRITICAL: preserve all details)
        # Include the complete user input to preserve critical details like addresses, requirements, etc.
        # NEVER truncate user input - all details are critical for requirements generation
        if request.user_input and request.user_input.strip():
            # Include FULL user input (no truncation) - preserve all user details
            user_prompt = f"""User input for {request.current_field}:
{request.user_input}

Question: {request.current_prompt}

CRITICAL: Use ALL details from the user input above. Preserve specific numbers, names, addresses, requirements, preferences, and any other details exactly as provided. Do not generalize or omit any information."""
        else:
            user_prompt = f"Question: {request.current_prompt}"
        
        # Add quality and usability instructions
        if request.response_length == "verbose":
            user_prompt += f"""

RESPONSE REQUIREMENTS:
- Provide a COMPLETE, comprehensive answer that fully addresses the question
- Format with clear paragraphs (separated by blank lines) and bullet points (prefix with '- ')
- Use context from previous phases intelligently - only include what directly helps answer the question
- Make it USABLE - write content the user can copy and use directly in their form
- Be thorough but organized - avoid repetition or rambling
- Structure logically: Introduction → Main Content → Summary/Next Steps
- Ensure every section adds unique value
- Stop when you've provided a complete, comprehensive answer - do not continue generating beyond what's needed"""
        else:
            user_prompt += f"""

RESPONSE REQUIREMENTS:
- Provide a COMPLETE, concise answer that fully addresses the question
- Format with clear paragraphs (separated by blank lines) and bullet points (prefix with '- ') where appropriate
- Use context from previous phases when it directly helps answer the question
- Make it USABLE - write content the user can copy and use directly in their form
- Be focused and well-structured - every sentence should add value
- Stop when you've answered the question completely - do not continue beyond what's needed"""
        
        # Temporarily switch to fast model if short mode
        original_model = None
        if request.response_length == "short" and hasattr(agent, 'agno_agent') and agent.agno_agent:
            from agno.models.openai import OpenAIChat
            from agno.models.anthropic import Claude
            from agno.models.google import Gemini
            from backend.models.ai_gateway_model import AIGatewayModel
            
            original_model = agent.agno_agent.model
            fast_model = None
            
            # Check AI Gateway first if enabled
            if provider_registry.has_ai_gateway():
                gateway_client = provider_registry.get_ai_gateway_client()
                if gateway_client:
                    # Use AI Gateway fast model from settings, fallback to agent_model_primary
                    fast_model_id = getattr(settings, "ai_gateway_fast_model", None) or getattr(settings, "agent_model_primary", "gpt-5.1")
                    try:
                        fast_model = AIGatewayModel(
                            id=fast_model_id,
                            client=gateway_client,
                            max_completion_tokens=2000,
                        )
                    except Exception as e:
                        logger.warning("ai_gateway_fast_model_creation_failed", error=str(e))
                        # Fall through to other providers
            
            # Only use direct providers if AI Gateway is not enabled or failed
            if fast_model is None:
                if provider_registry.has_openai_key():
                    # GPT-5.1 models require max_completion_tokens instead of max_tokens
                    api_key = provider_registry.get_openai_key()
                    base_url = getattr(settings, "ai_gateway_openai_base_url", None)
                    # Don't use AI Gateway URLs with direct API keys
                    if not (base_url and "ai-gateway" in base_url):
                        # Use AGENT_MODEL_FAST from settings (env.kind), fallback to agent_model_primary
                        fast_model_id = getattr(settings, "agent_model_fast", None) or getattr(settings, "agent_model_primary", "gpt-5.1")
                        fast_model = OpenAIChat(id=fast_model_id, api_key=api_key, max_completion_tokens=2000)
                elif provider_registry.has_gemini_key():
                    fast_model = Gemini(id="gemini-1.5-flash", api_key=provider_registry.get_gemini_key())
                elif provider_registry.has_claude_key():
                    fast_model = Claude(id="claude-3-haiku-20240307", api_key=provider_registry.get_claude_key())
            
            if fast_model:
                agent.agno_agent.model = fast_model
                logger.info("switched_to_fast_model", agent=agent_name, model=fast_model.id if hasattr(fast_model, 'id') else str(type(fast_model)))
        
        try:
            # Update agent's system prompt temporarily with expert context
            original_system_prompt = agent.system_prompt if hasattr(agent, 'system_prompt') else None
            if hasattr(agent, 'system_prompt'):
                agent.system_prompt = system_context
            if hasattr(agent, 'agno_agent') and agent.agno_agent:
                # Update Agno agent instructions
                agent.agno_agent.instructions = system_context
            
            # Create messages
            messages = [
                AgentMessage(
                    role="user",
                    content=user_prompt,
                    timestamp=datetime.utcnow()
                )
            ]
            
            # Process with agent using comprehensive context
            # Use the comprehensive context built above which includes:
            # - Previous phase submissions (ideation, market research, etc.)
            # - Conversation history
            # - Knowledge base
            # - Current phase form data
            context = comprehensive_context.copy()
            context.update({
                "phase_name": request.phase_name,
                "phase_id": request.phase_id,
                "current_field": request.current_field,
                "current_prompt": request.current_prompt,
                "response_length": request.response_length,
            })
            
            # Add current field's user input to form_data (CRITICAL: preserve all details)
            # Include FULL user input - never truncate as all details are critical
            if request.user_input and request.user_input.strip():
                if "form_data" not in context:
                    context["form_data"] = {}
                # Preserve complete user input - all details matter for requirements
                context["form_data"][request.current_field] = request.user_input
                # Also add to context as separate field for emphasis
                context["current_field_user_input"] = request.user_input
            
            # Merge with current phase form data
            if current_phase_form_data:
                if "form_data" not in context:
                    context["form_data"] = {}
                context["form_data"].update(current_phase_form_data)
            
            logger.info(
                "phase_form_help_processing",
                agent=agent_name,
                query_length=len(user_prompt),
                has_form_data=bool(context.get("form_data")),
                previous_phases_count=len(previous_phases_context),
                has_knowledge_base=bool(comprehensive_context.get("knowledge_base")),
                has_conversation_history=bool(comprehensive_context.get("conversation_history"))
            )
            
            # Process with agent - wrap in try-except to catch any processing errors
            # Add timeout protection to prevent infinite loops (60 seconds max)
            try:
                response = await asyncio.wait_for(
                    agent.process(messages, context),
                    timeout=60.0  # 60 second timeout for phase form help
                )
            except asyncio.TimeoutError:
                logger.error("phase_form_help_timeout",
                           agent=agent_name,
                           timeout_seconds=60)
                yield f"data: {json.dumps({'type': 'error', 'error': 'Agent processing timed out. Please try again with a shorter question or use short mode.'})}\n\n"
                return
            except Exception as process_error:
                logger.error(
                    "phase_form_help_agent_process_error",
                    error=str(process_error),
                    error_type=type(process_error).__name__,
                    agent=agent_name,
                    exc_info=True
                )
                yield f"data: {json.dumps({'type': 'error', 'error': f'Agent processing failed: {str(process_error)}'})}\n\n"
                return
            
            if not response:
                logger.error("phase_form_help_empty_response", agent=agent_name)
                yield f"data: {json.dumps({'type': 'error', 'error': 'Agent returned empty response'})}\n\n"
                return
            
            # Extract response text - try multiple attributes (enhanced extraction like base_agent)
            response_text = None
            
            # Try different ways to extract content from Agno response
            if hasattr(response, "response"):
                content = response.response
                if content:
                    if isinstance(content, str):
                        response_text = content
                    elif isinstance(content, list) and len(content) > 0:
                        # Handle Anthropic-style response with content array
                        if hasattr(content[0], "text"):
                            response_text = content[0].text
                        elif isinstance(content[0], str):
                            response_text = content[0]
                        else:
                            response_text = str(content[0])
                    else:
                        response_text = str(content) if content else ""
            
            # Try .content attribute
            if not response_text and hasattr(response, "content") and response.content:
                content = response.content
                if isinstance(content, str):
                    response_text = content
                elif isinstance(content, list) and len(content) > 0:
                    if hasattr(content[0], "text"):
                        response_text = content[0].text
                    elif isinstance(content[0], str):
                        response_text = content[0]
                    else:
                        response_text = str(content[0])
                else:
                    response_text = str(content) if content else ""
            
            # Try .text attribute
            if not response_text and hasattr(response, "text") and response.text:
                response_text = response.text
            
            # Try .message attribute
            if not response_text and hasattr(response, "message"):
                message = response.message
                if message:
                    if hasattr(message, "content") and message.content:
                        response_text = message.content
                    elif isinstance(message, str):
                        response_text = message
                    else:
                        response_text = str(message)
            
            # Try .messages attribute (RunOutput-style response)
            if not response_text and hasattr(response, "messages") and response.messages:
                # Find the last assistant message
                for msg in reversed(response.messages):
                    if hasattr(msg, "role") and msg.role == "assistant":
                        if hasattr(msg, "content") and msg.content:
                            if isinstance(msg.content, str) and msg.content.strip():
                                response_text = msg.content
                                break
                        elif isinstance(msg, str):
                            response_text = msg
                            break
            
            # Fallback to string conversion
            if not response_text:
                response_text = str(response)
            
            # Check if response_text is a RunOutput string representation
            if isinstance(response_text, str) and ("RunOutput" in response_text or "run_id=" in response_text):
                # Try to extract from the underlying agno agent's last run
                if hasattr(agent, 'agno_agent') and agent.agno_agent:
                    try:
                        if hasattr(agent.agno_agent, 'last_run') and agent.agno_agent.last_run:
                            last_run = agent.agno_agent.last_run
                            if hasattr(last_run, 'messages') and last_run.messages:
                                # Find the last assistant message with actual content
                                for msg in reversed(last_run.messages):
                                    if hasattr(msg, 'role') and msg.role == 'assistant':
                                        content = None
                                        if hasattr(msg, 'content'):
                                            content = msg.content
                                        elif hasattr(msg, 'text'):
                                            content = msg.text
                                        elif isinstance(msg, str):
                                            content = msg
                                        
                                        if content:
                                            if isinstance(content, str) and content.strip():
                                                if "RunOutput" not in content and "run_id=" not in content and len(content) > 50:
                                                    response_text = content
                                                    logger.info("phase_form_help_extracted_from_messages", 
                                                              agent=agent_name,
                                                              extracted_length=len(response_text))
                                                    break
                    except Exception as extract_error:
                        logger.warning("phase_form_help_run_extraction_failed", 
                                     error=str(extract_error),
                                     agent=agent_name)
            
            # Log response structure for debugging
            logger.info(
                "phase_form_help_response_structure",
                agent=agent_name,
                has_response_attr=hasattr(response, 'response'),
                has_content_attr=hasattr(response, 'content'),
                has_text_attr=hasattr(response, 'text'),
                response_type=type(response).__name__,
                response_text_length=len(response_text) if response_text else 0,
                response_text_preview=response_text[:100] if response_text else None,
                is_runoutput_string="RunOutput" in str(response_text)[:200] if response_text else False
            )
            
            if not response_text or not response_text.strip():
                logger.error(
                    "phase_form_help_empty_response_text",
                    agent=agent_name,
                    response_type=type(response).__name__,
                    response_attrs=[attr for attr in dir(response) if not attr.startswith("_")],
                    response_str=str(response)[:200]
                )
                yield f"data: {json.dumps({'type': 'error', 'error': 'Agent returned empty response text'})}\n\n"
                return
            
            # Check if still a RunOutput string after extraction
            if isinstance(response_text, str) and ("RunOutput" in response_text or len(response_text) < 50):
                logger.error("phase_form_help_runoutput_extraction_failed",
                           agent=agent_name,
                           response_preview=response_text[:200],
                           response_length=len(response_text))
                yield f"data: {json.dumps({'type': 'error', 'error': 'Could not extract response from agent. Please try again.'})}\n\n"
                return
            
            # Log initial response length
            initial_word_count = len(response_text.split())
            initial_char_count = len(response_text)
            logger.info(
                "phase_form_help_response_received",
                agent=agent_name,
                initial_words=initial_word_count,
                initial_chars=initial_char_count,
                response_length=request.response_length
            )
            
            # Extract plain text from response (handles HTML, markdown, or plain text)
            # The agent might return HTML documents, markdown, or plain text
            plain_text = extract_plain_text(response_text)
            
            # Apply hard character limits to prevent excessive generation
            # Short mode: max 2000 characters, Verbose mode: max 8000 characters
            MAX_CHARS_SHORT = 2000
            MAX_CHARS_VERBOSE = 8000
            
            def truncate_at_complete_thought(text: str, max_chars: int) -> str:
                """Truncate text at a complete sentence or paragraph boundary to maintain usability."""
                if len(text) <= max_chars:
                    return text
                
                # Try to find a good truncation point
                truncated = text[:max_chars]
                
                # First, try to find the end of a paragraph (double newline)
                last_paragraph = truncated.rfind('\n\n')
                if last_paragraph > max_chars * 0.8:  # If we can find a paragraph break in the last 20%
                    return text[:last_paragraph] + "\n\n[Response truncated - content exceeded length limit]"
                
                # Second, try to find the end of a sentence (period, exclamation, question mark followed by space)
                sentence_endings = ['. ', '.\n', '! ', '!\n', '? ', '?\n']
                last_sentence = -1
                for ending in sentence_endings:
                    pos = truncated.rfind(ending)
                    if pos > max_chars * 0.8 and pos > last_sentence:
                        last_sentence = pos + len(ending)
                
                if last_sentence > 0:
                    return text[:last_sentence] + "\n\n[Response truncated - content exceeded length limit]"
                
                # Third, try to find a word boundary
                last_space = truncated.rfind(' ')
                if last_space > max_chars * 0.9:  # If we can find a space in the last 10%
                    return text[:last_space] + "\n\n[Response truncated - content exceeded length limit]"
                
                # Last resort: truncate at character boundary
                return truncated + "\n\n[Response truncated - content exceeded length limit]"
            
            if request.response_length == "short":
                if len(plain_text) > MAX_CHARS_SHORT:
                    logger.warning("phase_form_help_response_truncated",
                                 agent=agent_name,
                                 original_length=len(plain_text),
                                 truncated_to=MAX_CHARS_SHORT,
                                 mode="short")
                    plain_text = truncate_at_complete_thought(plain_text, MAX_CHARS_SHORT)
            else:  # verbose mode
                if len(plain_text) > MAX_CHARS_VERBOSE:
                    logger.warning("phase_form_help_response_truncated",
                                 agent=agent_name,
                                 original_length=len(plain_text),
                                 truncated_to=MAX_CHARS_VERBOSE,
                                 mode="verbose")
                    plain_text = truncate_at_complete_thought(plain_text, MAX_CHARS_VERBOSE)
            
            # Count final words for logging
            word_count = len(plain_text.split())
            
            # Stream the plain text response in chunks for smooth streaming
            chunk_size = 50  # Characters per chunk
            try:
                for i in range(0, len(plain_text), chunk_size):
                    chunk = plain_text[i:i+chunk_size]
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk, 'word_count': word_count})}\n\n"
                    await asyncio.sleep(0.01)  # Small delay for smooth streaming
                
                yield f"data: {json.dumps({'type': 'complete', 'content': plain_text, 'word_count': word_count, 'agent': agent_name})}\n\n"
            except Exception as stream_error:
                logger.error("phase_form_help_streaming_error", error=str(stream_error), agent=agent_name)
                yield f"data: {json.dumps({'type': 'error', 'error': f'Streaming error: {str(stream_error)}'})}\n\n"
            
            # Restore original system prompt
            if original_system_prompt and hasattr(agent, 'system_prompt'):
                agent.system_prompt = original_system_prompt
            
        finally:
            # Restore original model
            if original_model:
                agent.agno_agent.model = original_model
                logger.info("restored_original_model", agent=agent_name)
                
    except Exception as e:
        logger.error("phase_form_help_error", error=str(e), phase=request.phase_name)
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"


def extract_plain_text(content: str) -> str:
    """Extract plain text from HTML, markdown, or plain text content."""
    # First, check if it's HTML (contains HTML tags)
    if re.search(r'<[^>]+>', content):
        # It's HTML - extract text content
        class HTMLTextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text = []
                self.in_script = False
                self.in_style = False
            
            def handle_starttag(self, tag, attrs):
                if tag.lower() in ['script', 'style']:
                    self.in_script = tag.lower() == 'script'
                    self.in_style = tag.lower() == 'style'
            
            def handle_endtag(self, tag):
                if tag.lower() in ['script', 'style']:
                    self.in_script = False
                    self.in_style = False
                elif tag.lower() in ['p', 'div', 'li', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    self.text.append('\n')
            
            def handle_data(self, data):
                if not self.in_script and not self.in_style:
                    self.text.append(data)
        
        try:
            parser = HTMLTextExtractor()
            parser.feed(content)
            text = ''.join(parser.text)
            # Decode HTML entities
            text = html.unescape(text)
        except Exception as e:
            logger.warning("html_parsing_failed", error=str(e))
            # Fallback: use regex to remove HTML tags
            text = re.sub(r'<[^>]+>', '', content)
            # Decode HTML entities
            text = html.unescape(text)
    else:
        # It's markdown or plain text - strip markdown formatting
        text = content
        
        # Remove headers (keep text)
        text = re.sub(r'^#+\s+(.*)$', r'\1', text, flags=re.MULTILINE)
        
        # Remove bold/italic (keep text)
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        
        # Remove code blocks (keep text)
        text = re.sub(r'```[\w]*\n(.*?)```', r'\1', text, flags=re.DOTALL)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        
        # Remove links (keep text)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        # Remove list markers (keep text, add newlines)
        text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    
    # Clean up extra whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces to single space
    text = text.strip()
    
    return text


def markdown_to_html(markdown: str) -> str:
    """Convert markdown to HTML with proper formatting for textarea display."""
    import html as html_escape
    html = markdown
    
    # Escape HTML first to prevent XSS
    html = html_escape.escape(html)
    
    # Headers (with styling classes)
    html = re.sub(r'^### (.*)$', r'<h3 class="text-xl font-semibold mt-4 mb-2">\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*)$', r'<h2 class="text-2xl font-semibold mt-6 mb-3">\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.*)$', r'<h1 class="text-3xl font-bold mt-8 mb-4">\1</h1>', html, flags=re.MULTILINE)
    
    # Bold
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong class="font-semibold">\1</strong>', html)
    
    # Italic
    html = re.sub(r'\*(.*?)\*', r'<em class="italic">\1</em>', html)
    
    # Lists (unordered)
    html = re.sub(r'^\* (.*)$', r'<li class="ml-4 mb-1">\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'^- (.*)$', r'<li class="ml-4 mb-1">\1</li>', html, flags=re.MULTILINE)
    
    # Lists (ordered)
    html = re.sub(r'^\d+\. (.*)$', r'<li class="ml-4 mb-1">\1</li>', html, flags=re.MULTILINE)
    
    # Wrap consecutive list items in ul/ol
    html = re.sub(r'(<li class="ml-4 mb-1">.*?</li>\n?)+', lambda m: f'<ul class="list-disc my-3">{m.group(0)}</ul>', html, flags=re.DOTALL)
    
    # Code blocks (with styling)
    html = re.sub(r'```(\w+)?\n(.*?)```', r'<pre class="bg-gray-100 p-3 rounded my-2 overflow-x-auto"><code class="text-sm">\2</code></pre>', html, flags=re.DOTALL)
    
    # Inline code
    html = re.sub(r'`([^`]+)`', r'<code class="bg-gray-100 px-1 rounded text-sm">\1</code>', html)
    
    # Links
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" class="text-blue-600 underline" target="_blank">\1</a>', html)
    
    # Paragraphs (with styling)
    lines = html.split('\n')
    html_lines = []
    for line in lines:
        trimmed = line.strip()
        if trimmed and not trimmed.startswith('<'):
            html_lines.append(f'<p class="mb-3 leading-relaxed">\1</p>')
        else:
            html_lines.append(line)
    html = '\n'.join(html_lines)
    
    # Paragraphs: wrap standalone text lines (not already wrapped in HTML tags)
    lines = html.split('\n')
    html_lines = []
    for line in lines:
        trimmed = line.strip()
        if trimmed and not trimmed.startswith('<') and not trimmed.startswith('&'):
            html_lines.append(f'<p class="mb-3 leading-relaxed">{trimmed}</p>')
        else:
            html_lines.append(line)
    html = '\n'.join(html_lines)
    
    return html


@router.post("/stream")
async def stream_phase_form_help_endpoint(
    request: PhaseFormHelpRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Stream phase form help response."""
    user_id = UUID(str(current_user["id"]))
    return StreamingResponse(
        stream_phase_form_help(request, user_id, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Accel-Charset": "utf-8",
            # Force HTTP/1.1 for streaming to avoid HTTP/2 protocol errors
            "Upgrade": "",
        }
    )

