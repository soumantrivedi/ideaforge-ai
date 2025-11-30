"""Natural Language Understanding service for interpreting user intent and preventing unnecessary AI calls."""
from typing import Dict, Optional, Tuple
import re
import structlog

logger = structlog.get_logger()


class NaturalLanguageUnderstanding:
    """Service for understanding user intent from natural language responses."""
    
    # Negative responses that indicate user doesn't want AI assistance
    NEGATIVE_PATTERNS = [
        r'\bno\b',
        r'\bnot\s+(required|needed|necessary|wanted|desired)\b',
        r'\bdon\'?t\s+(need|want|require)\b',
        r'\bno\s+thanks?\b',
        r'\bnot\s+now\b',
        r'\bskip\b',
        r'\bcancel\b',
        r'\bnever\s+mind\b',
        r'\bignore\b',
        r'\bnot\s+interested\b',
        r'\bdecline\b',
        r'\brefuse\b',
    ]
    
    # Positive responses that indicate user wants AI assistance
    POSITIVE_PATTERNS = [
        r'\byes\b',
        r'\byeah\b',
        r'\byep\b',
        r'\bsure\b',
        r'\bok\b',
        r'\bokay\b',
        r'\bplease\b',
        r'\bgo\s+ahead\b',
        r'\bproceed\b',
        r'\bcontinue\b',
        r'\bdo\s+it\b',
        r'\bgenerate\b',
        r'\bcreate\b',
        r'\bmake\b',
    ]
    
    # Question patterns that require AI response
    QUESTION_PATTERNS = [
        r'\?',
        r'\bwhat\b',
        r'\bhow\b',
        r'\bwhy\b',
        r'\bwhen\b',
        r'\bwhere\b',
        r'\bwho\b',
        r'\bwhich\b',
        r'\bcan\s+you\b',
        r'\bcould\s+you\b',
        r'\bwould\s+you\b',
        r'\bwill\s+you\b',
        r'\btell\s+me\b',
        r'\bexplain\b',
        r'\bdescribe\b',
        r'\bshow\s+me\b',
    ]
    
    # Information request patterns
    INFO_REQUEST_PATTERNS = [
        r'\bhelp\b',
        r'\binformation\b',
        r'\bdetails?\b',
        r'\bmore\b',
        r'\bexplain\b',
        r'\bclarify\b',
        r'\bunderstand\b',
    ]
    
    def __init__(self):
        """Initialize NLU service."""
        self.negative_regex = re.compile('|'.join(self.NEGATIVE_PATTERNS), re.IGNORECASE)
        self.positive_regex = re.compile('|'.join(self.POSITIVE_PATTERNS), re.IGNORECASE)
        self.question_regex = re.compile('|'.join(self.QUESTION_PATTERNS), re.IGNORECASE)
        self.info_request_regex = re.compile('|'.join(self.INFO_REQUEST_PATTERNS), re.IGNORECASE)
    
    def extract_previous_question(self, conversation_history: Optional[list] = None, context: Optional[Dict] = None) -> Optional[str]:
        """
        Extract the most recent assistant question from conversation history.
        
        Args:
            conversation_history: List of conversation messages
            context: Optional context dictionary that may contain message_history
        
        Returns:
            The most recent assistant question/request, or None
        """
        messages = conversation_history or []
        
        # Also check context for message_history
        if context and not messages:
            messages = context.get("message_history", [])
        
        # Look for the most recent assistant message that is a question
        for msg in reversed(messages):
            if isinstance(msg, dict):
                role = msg.get("role", "")
                content = msg.get("content", "")
            else:
                # Handle AgentMessage objects
                role = getattr(msg, "role", "")
                content = getattr(msg, "content", "")
            
            if role in ["assistant", "agent"] and content:
                content_lower = content.lower()
                # Check if it's a question (contains question mark or question words)
                if "?" in content or any(qw in content_lower for qw in ["do you want", "would you like", "should i", "can i", "shall i"]):
                    return content
        
        return None
    
    def analyze_intent(self, user_input: str, agent_question: Optional[str] = None, context: Optional[Dict] = None) -> Dict[str, any]:
        """
        Analyze user input to determine intent.
        
        Args:
            user_input: User's text input
            agent_question: Optional question/request from agent that prompted this response
            context: Optional context dictionary with conversation history
        
        Returns:
            Dict with:
                - should_proceed: bool - Whether to proceed with AI call
                - intent: str - Detected intent (negative, positive, question, info_request, neutral)
                - confidence: float - Confidence score (0.0-1.0)
                - reason: str - Explanation of decision
                - suggested_response: Optional[str] - Suggested response if should_proceed is False
        """
        if not user_input or not user_input.strip():
            return {
                "should_proceed": False,
                "intent": "empty",
                "confidence": 1.0,
                "reason": "Empty input",
                "suggested_response": None
            }
        
        user_input_lower = user_input.lower().strip()
        
        # Extract previous question from context if not provided
        if not agent_question and context:
            agent_question = self.extract_previous_question(context=context)
        
        # Check for negative responses (high priority)
        negative_match = self.negative_regex.search(user_input_lower)
        if negative_match:
            # If agent asked a question and user said no, don't proceed
            if agent_question:
                # Generate helpful next steps based on context
                suggested_response = self._generate_helpful_response_for_negative(context)
                return {
                    "should_proceed": False,
                    "intent": "negative",
                    "confidence": 0.95,
                    "reason": f"User declined: '{negative_match.group()}'",
                    "suggested_response": suggested_response
                }
            # Even without explicit question, if it's a clear "no", check if it's a standalone rejection
            if len(user_input_lower.split()) <= 3:  # Short response like "no", "no thanks"
                suggested_response = self._generate_helpful_response_for_negative(context)
                return {
                    "should_proceed": False,
                    "intent": "negative",
                    "confidence": 0.85,
                    "reason": f"User declined: '{negative_match.group()}'",
                    "suggested_response": suggested_response
                }
        
        # Check for questions (always proceed)
        question_match = self.question_regex.search(user_input_lower)
        if question_match:
            return {
                "should_proceed": True,
                "intent": "question",
                "confidence": 0.95,
                "reason": "User asked a question",
                "suggested_response": None
            }
        
        # Check for information requests (proceed)
        info_match = self.info_request_regex.search(user_input_lower)
        if info_match:
            return {
                "should_proceed": True,
                "intent": "info_request",
                "confidence": 0.85,
                "reason": "User requested information",
                "suggested_response": None
            }
        
        # Check for positive responses
        positive_match = self.positive_regex.search(user_input_lower)
        if positive_match:
            return {
                "should_proceed": True,
                "intent": "positive",
                "confidence": 0.8,
                "reason": f"User confirmed: '{positive_match.group()}'",
                "suggested_response": None
            }
        
        # If agent asked a question and user response is ambiguous, check length
        if agent_question:
            # Short responses to questions are likely negative
            if len(user_input_lower.split()) <= 3:
                # Check if it's a clear negative
                if negative_match:
                    suggested_response = self._generate_helpful_response_for_negative(context)
                    return {
                        "should_proceed": False,
                        "intent": "negative",
                        "confidence": 0.8,
                        "reason": "Short negative response to agent question",
                        "suggested_response": suggested_response
                    }
                # Otherwise, treat as neutral and proceed (user might be providing context)
                return {
                    "should_proceed": True,
                    "intent": "neutral",
                    "confidence": 0.5,
                    "reason": "Ambiguous response, proceeding to avoid blocking valid requests",
                    "suggested_response": None
                }
        
        # Default: proceed if input is substantial (likely a real request)
        if len(user_input_lower.split()) > 3:
            return {
                "should_proceed": True,
                "intent": "neutral",
                "confidence": 0.6,
                "reason": "Substantial input, likely a request",
                "suggested_response": None
            }
        
        # Very short input without clear intent - don't proceed
        return {
            "should_proceed": False,
            "intent": "ambiguous",
            "confidence": 0.4,
            "reason": "Input too short and ambiguous",
            "suggested_response": self._generate_helpful_response_for_negative(context)
        }
    
    def _generate_helpful_response_for_negative(self, context: Optional[Dict] = None) -> str:
        """
        Generate a helpful response when user says no/declines.
        Provides context-aware next steps instead of a full agent response.
        """
        # Check if user is in a specific phase
        phase_name = None
        if context:
            phase_name = context.get("phase_name")
            product_id = context.get("product_id")
        
        if phase_name:
            # User is in a specific phase - provide phase-specific guidance
            response_parts = [
                f"Got it! You're working on the **{phase_name}** phase.",
                "",
                "**What would you like to do next?**",
                "",
                f"• **Continue with {phase_name}** - Fill out the remaining questions in this phase",
                "• **Move to Next Phase** - Proceed to the next lifecycle phase",
                "• **Ask a Question** - Ask me anything about your product or this phase",
                "• **Review Progress** - Check what you've completed so far",
                "• **Export Your Work** - Download your progress as a document",
                "",
                "Just let me know what you'd like to work on! 🚀"
            ]
        else:
            # General helpful guidance
            response_parts = [
                "No problem! Here are some things you can do:",
                "",
                "**Product Lifecycle Phases:**",
                "• Click on any phase (Ideation, Market Research, Requirements, etc.) to get step-by-step guidance",
                "",
                "**Chat & Questions:**",
                "• Ask me anything about your product, market, or requirements",
                "• Get help with specific questions in any phase",
                "",
                "**Review & Export:**",
                "• Check your progress in the 'My Progress' section",
                "• Export your work using the 'Export PRD' button",
                "",
                "What would you like to work on next? 💡"
            ]
        
        return "\n".join(response_parts)
    
    def should_make_ai_call(
        self,
        user_input: str,
        agent_question: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Determine if an AI call should be made based on user input.
        
        Args:
            user_input: User's text input
            agent_question: Optional question from agent
            context: Optional context dictionary
        
        Returns:
            Tuple of (should_proceed: bool, reason: str, suggested_response: Optional[str])
        """
        analysis = self.analyze_intent(user_input, agent_question, context)
        
        logger.info(
            "nlu_analysis",
            user_input=user_input[:50],
            intent=analysis["intent"],
            should_proceed=analysis["should_proceed"],
            confidence=analysis["confidence"],
            reason=analysis["reason"]
        )
        
        return analysis["should_proceed"], analysis["reason"], analysis.get("suggested_response")


# Global NLU instance
_nlu_instance: Optional[NaturalLanguageUnderstanding] = None


def get_nlu() -> NaturalLanguageUnderstanding:
    """Get or create global NLU instance."""
    global _nlu_instance
    if _nlu_instance is None:
        _nlu_instance = NaturalLanguageUnderstanding()
    return _nlu_instance

