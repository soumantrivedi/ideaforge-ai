"""
Summary Agent using Agno Framework
Creates comprehensive summaries from multiple chat sessions and conversations
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.agents.agno_base_agent import AgnoBaseAgent
from backend.models.schemas import AgentMessage, AgentResponse


class AgnoSummaryAgent(AgnoBaseAgent):
    """Summary Agent for creating comprehensive summaries from conversations."""
    
    def __init__(self, enable_rag: bool = True):
        system_prompt = """You are a Summary and Documentation Specialist.

Your responsibilities:
1. Create comprehensive summaries from multiple conversation sessions
2. Synthesize information from various sources and participants
3. Identify key themes, decisions, and action items
4. Extract important context and requirements
5. Organize information in a structured, easy-to-understand format

Summary Structure:
- Executive Summary: High-level overview
- Key Themes: Main topics discussed
- Decisions Made: Important decisions and rationale
- Requirements Identified: Functional and non-functional requirements
- Action Items: Tasks and next steps
- Open Questions: Unresolved items
- Context: Important background information
- Participants: Key contributors and their inputs

Your summaries should:
- Be comprehensive yet concise
- Preserve important context and nuance
- Highlight critical decisions and requirements
- Identify patterns and themes across sessions
- Be actionable and clear
- Maintain chronological flow when relevant"""

        super().__init__(
            name="Summary Agent",
            role="summary",
            system_prompt=system_prompt,
            enable_rag=enable_rag,
            rag_table_name="summary_knowledge_base",
            capabilities=[
                "summary",
                "synthesis",
                "documentation",
                "conversation summary",
                "session summary",
                "meeting notes",
                "requirements extraction"
            ]
        )
    
    async def create_session_summary(
        self,
        session_id: str,
        messages: List[Dict[str, Any]],
        participants: Optional[List[str]] = None
    ) -> str:
        """Create a summary from a single session."""
        context = {
            "session_id": session_id,
            "participants": participants or [],
            "message_count": len(messages)
        }
        
        # Format messages for summary
        conversation_text = self._format_conversation(messages)
        
        prompt = f"""Create a comprehensive summary of this conversation session:

Session ID: {session_id}
Participants: {', '.join(participants) if participants else 'Multiple users'}

Conversation:
{conversation_text}

Provide a structured summary following the standard format."""

        message = AgentMessage(
            role="user",
            content=prompt,
            timestamp=datetime.utcnow()
        )

        response = await self.process([message], context=context)
        return response.response
    
    async def create_multi_session_summary(
        self,
        sessions: List[Dict[str, Any]],
        product_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a comprehensive summary from multiple sessions."""
        context = {
            "session_count": len(sessions),
            "product_context": product_context or {}
        }
        
        # Combine all sessions
        all_conversations = []
        for session in sessions:
            session_text = f"\n\n=== Session: {session.get('session_id', 'Unknown')} ===\n"
            session_text += f"Participants: {', '.join(session.get('participants', []))}\n"
            session_text += self._format_conversation(session.get('messages', []))
            all_conversations.append(session_text)
        
        combined_text = "\n".join(all_conversations)
        
        product_context_text = ""
        if product_context:
            product_context_text = f"\n\nProduct Context:\n{product_context}\n"
        
        prompt = f"""Create a comprehensive summary from multiple conversation sessions:

{product_context_text}

Sessions ({len(sessions)} total):
{combined_text}

Provide a unified summary that:
1. Identifies common themes across all sessions
2. Highlights key decisions and requirements
3. Shows evolution of ideas and requirements
4. Consolidates action items and next steps
5. Identifies any conflicts or inconsistencies
6. Provides a complete picture of the product vision"""

        message = AgentMessage(
            role="user",
            content=prompt,
            timestamp=datetime.utcnow()
        )

        response = await self.process([message], context=context)
        return response.response
    
    def _format_conversation(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages for summary generation."""
        formatted = []
        for msg in messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', '')
            agent_name = msg.get('agent_name', '')
            
            prefix = f"[{role}]"
            if agent_name:
                prefix += f" {agent_name}"
            if timestamp:
                prefix += f" ({timestamp})"
            
            formatted.append(f"{prefix}: {content}")
        
        return "\n".join(formatted)

