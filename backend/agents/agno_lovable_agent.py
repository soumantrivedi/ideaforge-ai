"""
Lovable AI Agent using Agno Framework
Provides Lovable prompt generation and Lovable Link Generator integration
Uses Lovable Build with URL API: https://docs.lovable.dev/integrations/build-with-url
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog
import urllib.parse
import json

from backend.agents.agno_base_agent import AgnoBaseAgent
from backend.models.schemas import AgentMessage, AgentResponse
from backend.config import settings
from backend.services.provider_registry import provider_registry

logger = structlog.get_logger()

try:
    from agno.tools import tool
    AGNO_TOOLS_AVAILABLE = True
except ImportError:
    AGNO_TOOLS_AVAILABLE = False
    logger.warning("agno_tools_not_available", message="Agno tools not available")


class AgnoLovableAgent(AgnoBaseAgent):
    """Lovable AI Design Agent using Agno framework with Lovable Link Generator."""
    
    def __init__(self, enable_rag: bool = False):
        # Optimized system prompt based on v0-prompt-guidance.txt approach for faster, focused generation
        system_prompt = """You are an assistant whose ONLY job is to generate a single, high-quality prompt for Lovable.dev to build a complete, deployable application.

You receive two inputs:
1) A structured UX requirements form filled by the user (PRIMARY source of truth)
2) A chatbot conversation history between the user and an assistant (used to enrich and clarify)

Your goal:
- Combine both inputs into ONE clear, objective, and concise Lovable prompt that Lovable.dev can use to generate an accurate, production-ready application
- The UX form is the primary source of truth; the chat is used to enrich and clarify it
- Preserve all critical facts, numbers, constraints, and edge cases that are relevant for the application

General rules:
- Be concise. Avoid long explanations or repetition
- Be neutral and objective. Do not invent requirements not supported by the inputs
- Ignore small talk and irrelevant parts of the conversation
- If there are conflicts, prefer the latest and most explicit user instructions
- Never mention the existence of "forms", "chat history", or "inputs" in the final prompt. Speak as if it is a single coherent specification
- Keep the total length reasonably short but complete enough for a developer to understand what to build

Processing steps (internal to you):
1) Read and interpret the UX form:
   - Extract: product goal, target users, platforms, main flows, key screens, navigation, accessibility needs, branding/tone, tech constraints, database needs, API requirements, authentication patterns
2) Summarise the chatbot conversation:
   - Capture ONLY useful application/build details such as:
     - Clarifications or changes to requirements
     - Examples and scenarios the user cares about
     - Important data fields, numbers, limits, and rules
     - Edge cases and error states
     - Preferences about architecture, tech stack, and implementation
   - Ignore greetings, meta talk, or irrelevant topics
3) Merge both into a single coherent specification:
   - Remove duplicates
   - Resolve contradictions in favour of the most recent clear user intent
   - Keep all important facts and constraints

Your OUTPUT:
- A single Lovable prompt written as an implementation brief
- Do NOT explain your reasoning
- Do NOT include any headings about "summary of chat" or "UX form"
- Talk directly about the application, as if briefing a full-stack developer

Recommended structure of the Lovable prompt:
1) Application overview - What the application is, who it is for, and the main problem it solves
2) Target users and context - Who will use it, in what environment, and on which devices/platforms
3) Key user flows & use cases - Main tasks users must be able to do, with important variations and edge cases
4) Application structure - Pages, routes, components, layouts, navigation structure
5) Data models and API - Database schemas, data structures, API endpoints, authentication flows
6) Technical requirements - Tech stack preferences, state management, routing patterns, performance needs
7) Visual & UX style - Tone and branding, accessibility requirements, specific UX preferences
8) Success criteria - What a "good" application should definitely include

Important:
- Focus on relevance and clarity. Short is better, as long as all critical details are present
- Capture and retain key numeric values and factual details whenever they influence implementation
- Output ONLY the final Lovable prompt text. No comments, explanations, or meta-instructions
- Lovable.dev generates fully deployable React/Next.js applications with Tailwind CSS, supports Supabase/Firebase, REST APIs, GraphQL"""

        # Initialize base agent first (tools will be added after)
        super().__init__(
            name="Lovable Agent",
            role="lovable",
            system_prompt=system_prompt,
            enable_rag=enable_rag,
            rag_table_name="lovable_knowledge_base",
            model_tier="fast",  # Use fast model to avoid timeout issues
            tools=[],  # Tools will be added after initialization
            capabilities=[
                "lovable prompt generation",
                "lovable link generation",
                "lovable integration",
                "ui prototype generation",
                "react application generation",
                "next.js development"
            ]
        )
        
        # Add tools after initialization
        if AGNO_TOOLS_AVAILABLE:
            created_tools = [
                self._generate_lovable_link_tool(),
            ]
            # Add tools to the agent
            if hasattr(self.agno_agent, 'tools') and self.agno_agent.tools is not None:
                valid_tools = [t for t in created_tools if t is not None]
                if valid_tools:
                    self.agno_agent.tools.extend(valid_tools)
    
    def _generate_lovable_link_tool(self):
        """Create Agno tool for Lovable link generation."""
        if not AGNO_TOOLS_AVAILABLE:
            return None
        
        @tool
        def generate_lovable_link(prompt: str, image_urls: Optional[List[str]] = None) -> str:
            """
            Generate a Lovable AI shareable link using the Build with URL API.
            
            Args:
                prompt: The design prompt (up to 50,000 characters)
                image_urls: Optional list of image URLs (up to 10, JPEG/PNG/WebP)
            
            Returns:
                Lovable shareable link URL
            """
            try:
                # Base URL for Lovable Build with URL
                base_url = "https://lovable.dev/?autosubmit=true#"
                
                # URL encode the prompt
                encoded_prompt = urllib.parse.quote(prompt)
                
                # Build URL with prompt
                url = f"{base_url}prompt={encoded_prompt}"
                
                # Add image URLs if provided
                if image_urls and len(image_urls) > 0:
                    # Limit to 10 images as per Lovable API
                    image_urls = image_urls[:10]
                    for img_url in image_urls:
                        encoded_img = urllib.parse.quote(img_url)
                        url += f"&images={encoded_img}"
                
                return f"Lovable link generated successfully!\nLink: {url}\n\nThis link will automatically open Lovable and start building your app when clicked."
            except Exception as e:
                logger.error("lovable_link_generation_error", error=str(e))
                return f"Error generating Lovable link: {str(e)}"
    
    async def generate_lovable_prompt(
        self,
        product_context: Dict[str, Any],
        phase_data: Optional[Dict[str, Any]] = None,
        all_phases_data: Optional[List[Dict[str, Any]]] = None,
        conversation_summary: Optional[str] = None,
        design_form_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a detailed, comprehensive Lovable prompt based on complete product context."""
        # Extract and optimize context - focus on relevant application/build details only
        context_summary = self._summarize_context(product_context, phase_data, all_phases_data)
        
        # Optimized user prompt for faster processing - concise and focused
        user_prompt = f"""Generate a single, high-quality Lovable prompt by combining the UX form data (primary source) with relevant chatbot conversation details (enrichment).

UX Form Data (Primary Source of Truth):
{self._extract_design_form_summary(design_form_data) if design_form_data else "No design form data provided"}

Product Context from All Phases:
{context_summary}

Chatbot Conversation Summary (Use only relevant application/build details):
{conversation_summary if conversation_summary else "No conversation history"}

Instructions:
- Combine UX form (primary) and chatbot (enrichment) into ONE clear, concise Lovable prompt
- Ignore small talk and irrelevant conversation parts
- Preserve all critical facts, numbers, constraints, and edge cases
- If conflicts exist, prefer the latest and most explicit user instructions
- Never mention "forms", "chat history", or "inputs" in the final prompt
- Follow the recommended structure: Application overview → Target users → Key flows → Application structure → Data models/API → Technical requirements → Visual style → Success criteria
- Be concise but complete - focus on relevance and clarity
- Output ONLY the final Lovable prompt text - no explanations or meta-instructions"""

        message = AgentMessage(
            role="user",
            content=user_prompt,
            timestamp=datetime.utcnow()
        )

        # Temporarily disable tools during prompt generation to prevent accidental submission
        # Store original tools
        original_tools = None
        if hasattr(self.agno_agent, 'tools') and self.agno_agent.tools:
            original_tools = self.agno_agent.tools.copy()
            # Clear tools to prevent tool invocation during prompt generation
            self.agno_agent.tools = []
        
        try:
            # Build context with conversation summary and design form data for system context
            process_context = {
                "task": "lovable_prompt_generation",
                "disable_tools": True
            }
            
            # Add conversation history summary to context (will be included in system prompt)
            if conversation_summary:
                process_context["conversation_history"] = [
                    {"role": "user", "content": msg.split(": ", 1)[1] if ": " in msg else msg}
                    for msg in conversation_summary.split("\n") if msg.strip()
                ]
            
            # Add design form data to context (will be included in system prompt)
            if design_form_data:
                process_context["form_data"] = design_form_data
            
            # Use fast model tier (already set in __init__)
            # Context explicitly indicates this is prompt generation only, not submission
            # The conversation_history and form_data in context will be included in enhanced system prompt
            response = await self.process([message], context=process_context)
            prompt_text = response.response
            
            # Clean the prompt - remove headers/footers/notes that AI might add
            prompt_text = self._clean_lovable_prompt(prompt_text)
            
            return prompt_text
        finally:
            # Restore original tools after prompt generation
            if original_tools is not None:
                self.agno_agent.tools = original_tools
    
    def _summarize_context(
        self,
        product_context: Dict[str, Any],
        phase_data: Optional[Dict[str, Any]] = None,
        all_phases_data: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Extract ALL product context without aggressive truncation - include everything."""
        context_parts = []
        
        # Ensure product_context is a dict, not a list
        if not isinstance(product_context, dict):
            logger.warning("product_context_not_dict_lovable", 
                         product_context_type=type(product_context).__name__,
                         product_context_value=str(product_context)[:200])
            # Convert list to dict or use empty dict
            if isinstance(product_context, list):
                product_context = {"context": "\n".join([str(item) for item in product_context if item])}
            else:
                product_context = {"context": str(product_context)}
        
        # Get main context (usually contains phase data) - include ALL of it
        main_context = product_context.get("context", "")
        if main_context:
            # Include full context - don't truncate
            context_parts.append(f"Product Context:\n{main_context}")
        
        # Add ALL phase data if available - include EVERYTHING
        if all_phases_data:
            context_parts.append("\n=== ALL PRODUCT LIFECYCLE PHASES ===\n")
            for phase_item in all_phases_data:
                # Ensure phase_item is a dict, not a list
                if not isinstance(phase_item, dict):
                    logger.warning("phase_item_not_dict", 
                                 phase_item_type=type(phase_item).__name__,
                                 phase_item_value=str(phase_item)[:100])
                    continue  # Skip invalid phase items
                
                phase_name = phase_item.get("phase_name", "")
                form_data = phase_item.get("form_data", {})
                generated_content = phase_item.get("generated_content", "")
                
                phase_summary = f"\n--- {phase_name} Phase ---\n"
                
                # Include ALL form data fields, not just key fields
                if form_data:
                    phase_summary += "Form Data:\n"
                    for field, value in form_data.items():
                        if value:  # Only include non-empty fields
                            if isinstance(value, (dict, list)):
                                phase_summary += f"  {field}: {json.dumps(value, indent=2)}\n"
                            else:
                                phase_summary += f"  {field}: {value}\n"
                
                # Include full generated content
                if generated_content:
                    phase_summary += f"\nGenerated Content:\n{generated_content}\n"
                
                context_parts.append(phase_summary)
        
        # Add current phase data with full details if available
        if phase_data:
            # Ensure phase_data is a dict, not a list
            if not isinstance(phase_data, dict):
                logger.warning("phase_data_not_dict", 
                             phase_data_type=type(phase_data).__name__)
                phase_data = {}  # Use empty dict to avoid errors
            
            phase_name = phase_data.get("phase_name", "")
            form_data = phase_data.get("form_data", {})
            generated_content = phase_data.get("generated_content", "")
            
            phase_summary = f"\n=== CURRENT PHASE: {phase_name} ===\n"
            
            # Include ALL form data fields
            if form_data:
                phase_summary += "Form Data (Complete):\n"
                for field, value in form_data.items():
                    if value:
                        if isinstance(value, (dict, list)):
                            phase_summary += f"  {field}: {json.dumps(value, indent=2)}\n"
                        else:
                            phase_summary += f"  {field}: {value}\n"
            
            # Include full generated content
            if generated_content:
                phase_summary += f"\nGenerated Content:\n{generated_content}\n"
            
            context_parts.append(phase_summary)
        
        # Add ALL other context keys with full content
        for key, value in product_context.items():
            if key != "context" and value:
                if isinstance(value, dict):
                    formatted_dict = "\n".join([f"  {k}: {v}" for k, v in value.items() if v])
                    context_parts.append(f"{key}:\n{formatted_dict}")
                elif isinstance(value, list):
                    formatted_list = "\n".join([f"  - {item}" for item in value if item])
                    context_parts.append(f"{key}:\n{formatted_list}")
                else:
                    context_parts.append(f"{key}: {value}")
        
        return "\n\n".join(context_parts)  # Include ALL context items
    
    def _extract_design_form_summary(self, design_form_data: Dict[str, Any]) -> str:
        """Extract and format design form data in a concise, focused way for prompt generation."""
        if not design_form_data:
            return ""
        
        summary_parts = []
        for field, value in design_form_data.items():
            if value and str(value).strip():
                # Format value concisely
                if isinstance(value, (dict, list)):
                    import json
                    formatted = json.dumps(value, indent=2)
                    # Truncate very long JSON to keep it concise
                    if len(formatted) > 500:
                        formatted = formatted[:500] + "... (truncated)"
                    summary_parts.append(f"{field}: {formatted}")
                else:
                    value_str = str(value)
                    # Truncate very long values to keep it concise
                    if len(value_str) > 300:
                        value_str = value_str[:300] + "... (truncated)"
                    summary_parts.append(f"{field}: {value_str}")
        
        return "\n".join(summary_parts) if summary_parts else ""
    
    def _clean_lovable_prompt(self, prompt: str) -> str:
        """
        Clean Lovable prompt by removing instructional headers/footers and notes.
        Removes text like "Notes:", "This prompt follows Lovable guidelines", etc.
        """
        if not prompt:
            return prompt
        
        lines = prompt.split('\n')
        cleaned_lines = []
        skip_until_content = True
        in_notes_section = False
        
        # Patterns that indicate we should skip lines
        skip_patterns = [
            "below is a lovable.dev prompt",
            "here is a prompt",
            "lovable.dev prompt:",
            "prompt for lovable.dev:",
            "you can use this prompt",
            "copy this prompt",
            "notes:",
            "note:",
            "instructions:",
            "this prompt follows",
            "lovable guidelines:",
            "if you want",
            "tell me and i will",
            "encoded version",
            "url-encoded",
            "autosubmit",
        ]
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Check for notes section start
            if "notes:" in line_lower or "note:" in line_lower:
                in_notes_section = True
                continue
            
            # Skip everything in notes section
            if in_notes_section:
                # Check if we've exited notes section (new major section)
                if line_lower and (line_lower.startswith("#") or len(line_lower) > 50):
                    if not any(note_word in line_lower for note_word in ["note", "instruction", "guideline", "follow"]):
                        in_notes_section = False
                else:
                    continue
            
            # Skip empty lines at the start
            if skip_until_content and not line_lower:
                continue
            
            # Check if this line matches a skip pattern
            should_skip = any(pattern in line_lower for pattern in skip_patterns)
            
            if should_skip:
                skip_until_content = True
                continue
            
            # If we find actual content, start including lines
            if line_lower and not should_skip:
                skip_until_content = False
                cleaned_lines.append(line)
            elif not skip_until_content:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip() or prompt
    
    def generate_lovable_link(
        self,
        lovable_prompt: str,
        image_urls: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate a Lovable shareable link using the Build with URL API.
        Based on: https://docs.lovable.dev/integrations/build-with-url
        
        Args:
            lovable_prompt: The design prompt (up to 50,000 characters)
            image_urls: Optional list of publicly accessible image URLs (up to 10)
        
        Returns:
            Dictionary with project_url and metadata
        """
        try:
            # Base URL for Lovable Build with URL
            base_url = "https://lovable.dev/?autosubmit=true#"
            
            # URL encode the prompt
            encoded_prompt = urllib.parse.quote(lovable_prompt)
            
            # Build URL with prompt
            project_url = f"{base_url}prompt={encoded_prompt}"
            
            # Add image URLs if provided
            if image_urls and len(image_urls) > 0:
                # Limit to 10 images as per Lovable API
                image_urls = image_urls[:10]
                for img_url in image_urls:
                    encoded_img = urllib.parse.quote(img_url)
                    project_url += f"&images={encoded_img}"
            
            logger.info("lovable_link_generated", 
                       prompt_length=len(lovable_prompt),
                       num_images=len(image_urls) if image_urls else 0)
            
            return {
                "project_url": project_url,
                "prompt": lovable_prompt,
                "image_urls": image_urls or [],
                "metadata": {
                    "api_version": "build-with-url",
                    "link_type": "shareable",
                    "auto_submit": True,
                    "num_images": len(image_urls) if image_urls else 0,
                    "prompt_length": len(lovable_prompt)
                }
            }
        except Exception as e:
            logger.error("lovable_link_generation_error", error=str(e))
            raise ValueError(f"Error generating Lovable link: {str(e)}")
