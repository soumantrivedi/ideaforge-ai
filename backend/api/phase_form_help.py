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

    "requirement": """You are an expert Requirements Analysis Specialist for product development.
Your role is to help users define clear, actionable product requirements and specifications.
Focus on:
- Functional requirements definition
- Non-functional requirements (performance, security, scalability)
- User story creation
- Acceptance criteria
- Requirement prioritization
Provide clear, structured requirements guidance.""",

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
        return "analysis"
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
        
        # Get orchestrator
        orchestrator = get_orchestrator()
        if not isinstance(orchestrator, AgnoAgenticOrchestrator):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agno framework not available"
            )
        
        # Get phase expert agent
        agent_name = get_phase_expert_agent(request.phase_name)
        if agent_name not in orchestrator.agents:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent '{agent_name}' not found"
            )
        
        agent = orchestrator.agents[agent_name]
        
        # Log which agent we're using
        logger.info("phase_form_help_agent_selected", agent=agent_name, phase=request.phase_name)
        
        # Build system context (expert prompt + brief conversation summary)
        expert_prompt = get_phase_expert_prompt(request.phase_name)
        
        # Build minimal system context - just expert role + brief summary
        system_context = expert_prompt
        if request.conversation_summary:
            # Limit summary to 100 chars max (very brief)
            brief_summary = request.conversation_summary[:100] + "..." if len(request.conversation_summary) > 100 else request.conversation_summary
            system_context += f"\n\nContext: {brief_summary}"
        
        # Add instructions for plain text response (NO HTML, NO word limits)
        if request.response_length == "short":
            response_style = "concise and direct"
            response_guidance = "Provide a brief, focused answer that directly addresses the question. Be clear and to the point."
        else:
            response_style = "detailed and thorough"
            response_guidance = "Provide a comprehensive answer that includes: key points, context, relevant considerations, and practical guidance. Be thorough but focused - aim for 3-5 paragraphs with clear structure. Include examples or specific details where helpful, but avoid unnecessary repetition or rambling."
        
        system_context += f"\n\nCRITICAL REQUIREMENTS:\n- Return PLAIN TEXT only (NO HTML, NO markdown formatting)\n- Be {response_style}\n- {response_guidance}\n- Use natural language, no formatting codes\n- Write as if speaking directly to the user\n- Structure your response clearly with logical flow"
        
        # Build user prompt - KEEP IT MINIMAL
        # Just the question, nothing else
        if request.user_input and request.user_input.strip():
            # If user provided input, use it but keep it very short (100 chars max)
            user_prompt = f"User input: {request.user_input[:100]}\n\nQuestion: {request.current_prompt}"
        else:
            user_prompt = f"Question: {request.current_prompt}"
        
        # Add plain text reminder with mode-specific guidance
        if request.response_length == "verbose":
            user_prompt += f"\n\nProvide a detailed, comprehensive answer in plain text (no HTML, no markdown). Include context, key considerations, and practical guidance. Aim for thoroughness while staying focused and relevant."
        else:
            user_prompt += f"\n\nProvide a clear, concise answer in plain text (no HTML, no markdown)."
        
        # Temporarily switch to fast model if short mode
        original_model = None
        if request.response_length == "short" and hasattr(agent, 'agno_agent') and agent.agno_agent:
            from agno.models.openai import OpenAIChat
            from agno.models.anthropic import Claude
            from agno.models.google import Gemini
            
            original_model = agent.agno_agent.model
            fast_model = None
            
            if provider_registry.has_openai_key():
                fast_model = OpenAIChat(id="gpt-4o-mini", api_key=provider_registry.get_openai_key())
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
            
            # Process with agent (SINGLE AGENT - not multi-agent)
            logger.info("phase_form_help_processing", agent=agent_name, query_length=len(user_prompt))
            response = await agent.process(messages, {
                "phase_name": request.phase_name,
                "current_field": request.current_field,
                "response_length": request.response_length,
            })
            
            response_text = response.response if hasattr(response, 'response') else str(response)
            
            # Log initial response length
            initial_word_count = len(response_text.split())
            logger.info(
                "phase_form_help_response_received",
                agent=agent_name,
                initial_words=initial_word_count,
                response_length=request.response_length
            )
            
            # Extract plain text from response (handles HTML, markdown, or plain text)
            # The agent might return HTML documents, markdown, or plain text
            plain_text = extract_plain_text(response_text)
            
            # Count final words for logging
            word_count = len(plain_text.split())
            
            # Stream the plain text response in chunks for smooth streaming
            chunk_size = 50  # Characters per chunk
            for i in range(0, len(plain_text), chunk_size):
                chunk = plain_text[i:i+chunk_size]
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk, 'word_count': word_count})}\n\n"
                await asyncio.sleep(0.01)  # Small delay for smooth streaming
            
            yield f"data: {json.dumps({'type': 'complete', 'content': plain_text, 'word_count': word_count, 'agent': agent_name})}\n\n"
            
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
        }
    )

