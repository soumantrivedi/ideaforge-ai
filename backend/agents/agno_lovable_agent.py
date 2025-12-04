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
        # Optimized system prompt emphasizing concise, readable, directly usable prompts
        system_prompt = """You are a Lovable AI Design Specialist expert in creating focused, readable prompts for Lovable.dev.

Your primary goal is to generate CONCISE, FOCUSED prompts that capture the essential application aspects and can be directly used in Lovable Link Generator.

CRITICAL: When generating prompts:
- Keep prompts CONCISE (3000-6000 characters, max 8000) - prioritize readability and usability
- Focus on KEY application information - features, architecture, user flows, components
- Extract essential information from context - don't include everything
- Use clear, direct language - the prompt should be immediately actionable
- The prompt must be ready to paste directly into Lovable Link Generator
- DO NOT include instructions, notes, or meta-commentary in the output

Core Requirements:
- Generate FOCUSED, READABLE prompts (concise but complete - prioritize essential information)
- Extract KEY application information from form data and context
- Focus on application structure, pages, components, and essential functionality
- Include essential details: pages/routes, component structure, styling, data models, API integrations
- Describe user flows and interactions concisely
- Include Tailwind CSS styling, responsive breakpoints, and design system essentials
- Describe state management, routing (Next.js App Router), and data fetching patterns briefly
- Include accessibility (WCAG 2.1 AA), performance optimization, and modern React patterns
- Output ONLY the prompt text - no instructions, notes, or meta-commentary

Lovable Platform Documentation Guidelines (Based on Official Lovable.dev Docs):
- Lovable.dev generates fully deployable React/Next.js applications
- Supports Server Components, Client Components, and App Router patterns
- Uses Tailwind CSS for styling with responsive breakpoints
- Supports Supabase, Firebase, REST APIs, GraphQL, and authentication patterns
- Prompts should be detailed enough to generate complete applications, but concise enough to be readable
- Include database schemas, API endpoints, authentication flows, and user management (key details)
- Describe application structure: pages, components, layouts, routing
- Include form validations, error handling, loading states, and user feedback
- Specify data models, relationships, and data flow (essential details)

Guidelines:
- Be CONCISE and FOCUSED - include essential details, not everything
- Prioritize application/feature information over other context
- Extract key information from chatbot conversations and form data
- Focus on design form content - UI/UX specifications, component requirements, user flows
- Synthesize information from context - combine key points, don't repeat
- Generate prompts that are readable and directly usable in Lovable Link Generator
- The prompt should be ready for direct use without editing
- Keep it under 8000 characters - Lovable works best with concise, focused prompts"""

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
        all_phases_data: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Generate a detailed, comprehensive Lovable prompt based on complete product context."""
        # Extract ALL context without aggressive truncation
        context_summary = self._summarize_context(product_context, phase_data, all_phases_data)
        
        # Focused prompt emphasizing concise, readable, directly usable output
        user_prompt = f"""Generate a CONCISE Lovable.dev prompt (max 8000 characters, ideally 4000-6000). The prompt must be directly usable in Lovable Link Generator.

CRITICAL REQUIREMENTS:
- MAXIMUM 8000 characters - Lovable works best with concise prompts
- Extract ONLY KEY application information - features, architecture, user flows
- Use bullet points and short sentences - be direct and actionable
- Include essential details: pages/routes, components, styling, data models, APIs
- Describe user flows briefly
- DO NOT include instructions, notes, or meta-commentary
- DO NOT repeat information
- Focus on what needs to be BUILT, not background context

Product Context (summarized):
{context_summary}

Generate a concise Lovable.dev prompt focusing on:
- Application structure and key pages/routes
- Component specifications and hierarchy
- Tailwind CSS styling and responsive design
- Essential user flows and interactions
- Key data models and API integrations
- Authentication flows (if applicable)
- Form validations and error handling

Output ONLY the prompt text - no instructions or explanations. Keep it under 8000 characters."""

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
            # Use fast model tier (already set in __init__)
            # Trust the base agent's extraction - it should handle RunOutput correctly
            response = await self.process([message], context={"task": "lovable_prompt_generation"})
            prompt_text = response.response
            
            # Clean the prompt - remove headers/footers/notes that AI might add
            prompt_text = self._clean_lovable_prompt(prompt_text)
            
            # Ensure prompt is within strict limits (max 8000 chars for Lovable)
            if len(prompt_text) > 8000:
                logger.warning("lovable_prompt_too_long",
                             original_length=len(prompt_text),
                             truncated_to=8000)
                # Truncate intelligently at sentence boundary
                truncated = prompt_text[:8000]
                last_period = truncated.rfind('.')
                last_newline = truncated.rfind('\n')
                cut_point = max(last_period, last_newline)
                if cut_point > 6500:  # Only truncate at sentence if we keep at least 81%
                    prompt_text = prompt_text[:cut_point + 1]
                else:
                    # Try to truncate at paragraph or section boundary
                    last_double_newline = truncated.rfind('\n\n')
                    if last_double_newline > 5000:
                        prompt_text = prompt_text[:last_double_newline] + "\n[... truncated for Lovable compatibility ...]"
                    else:
                        prompt_text = truncated + "\n[... truncated for Lovable compatibility ...]"
            
            logger.info("lovable_prompt_generated",
                       prompt_length=len(prompt_text),
                       within_limits=len(prompt_text) <= 8000)
            
            return prompt_text
        finally:
            # Restore original tools after prompt generation
            if original_tools is not None:
                self.agno_agent.tools = original_tools
    
    def _summarize_context(
        self,
        product_context: Dict[str, Any],
        phase_data: Optional[Dict[str, Any]] = None,
        all_phases_data: Optional[List[Dict[str, Any]]] = None,
        max_chars: int = 5000
    ) -> str:
        """Intelligently summarize product context focusing on application architecture and features.
        
        Aggressively summarizes while preserving ALL user information and key application details.
        Prioritizes essential application information to keep prompts concise and directly usable in Lovable.
        """
        context_parts = []
        total_chars = 0
        
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
        
        def _truncate_text(text: str, max_length: int) -> str:
            """Truncate text intelligently, preserving sentences."""
            if len(text) <= max_length:
                return text
            # Try to truncate at sentence boundary
            truncated = text[:max_length]
            last_period = truncated.rfind('.')
            last_newline = truncated.rfind('\n')
            cut_point = max(last_period, last_newline)
            if cut_point > max_length * 0.8:  # Only use if we keep at least 80%
                return text[:cut_point + 1] + "\n[... truncated ...]"
            return truncated + "\n[... truncated ...]"
        
        def _extract_key_points(text: str, max_length: int) -> str:
            """Extract key points from text, prioritizing application/feature information."""
            if len(text) <= max_length:
                return text
            
            # Split into sentences
            sentences = text.replace('\n', ' ').split('. ')
            app_keywords = ["application", "app", "feature", "component", "page", "route", "api", 
                          "database", "authentication", "user flow", "functionality", "interface",
                          "button", "form", "input", "navigation", "screen", "modal", "data model"]
            
            # Prioritize sentences with app keywords
            prioritized = []
            other = []
            for sentence in sentences:
                sentence_lower = sentence.lower()
                if any(keyword in sentence_lower for keyword in app_keywords):
                    prioritized.append(sentence)
                else:
                    other.append(sentence)
            
            # Combine prioritized first, then others
            selected = prioritized + other
            result = '. '.join(selected)
            
            if len(result) > max_length:
                return _truncate_text(result, max_length)
            return result
        
        # Priority 1: Design form data (MOST IMPORTANT - preserve all user input)
        design_form = product_context.get("form_data", {})
        if design_form and isinstance(design_form, dict):
            design_summary = "User Application Requirements:\n"
            for key, value in design_form.items():
                if value and key in ["user_experience", "design_mockups", "v0_lovable_prompts"]:
                    value_str = str(value)
                    # Preserve user input but summarize if too long
                    if len(value_str) > 1000:
                        # Extract key points while preserving user intent
                        value_str = _extract_key_points(value_str, 1000)
                    design_summary += f"  {key}: {value_str}\n"
            if len(design_summary) > 50:  # Only add if we have actual content
                context_parts.append(design_summary)
                total_chars += len(design_summary)
        
        # Priority 2: Extract key product information (summarize aggressively)
        # Get product name, problem, solution, features from ideation/requirements
        product_summary = []
        
        # Extract from form_data across phases
        if all_phases_data:
            for phase in all_phases_data[:3]:  # Only first 3 phases
                phase_data_item = phase.get("form_data", {})
                if phase_data_item:
                    # Extract key fields
                    for field in ["problem_statement", "value_proposition", "target_audience", 
                                 "functional_requirements", "user_experience", "features"]:
                        if field in phase_data_item and phase_data_item[field]:
                            value = str(phase_data_item[field])
                            if len(value) > 300:
                                value = _extract_key_points(value, 300)
                            product_summary.append(f"{field}: {value}")
        
        # Also check direct form_data
        if not product_summary:
            for key, value in product_context.items():
                if key not in ["context", "form_data", "all_phases_data"] and value:
                    value_str = str(value)
                    if len(value_str) > 300:
                        value_str = _extract_key_points(value_str, 300)
                    product_summary.append(f"{key}: {value_str}")
                    if len(product_summary) >= 5:  # Limit to 5 key points
                        break
        
        if product_summary:
            product_text = "\n".join(product_summary[:5])  # Max 5 key points
            if len(product_text) > 1500:
                product_text = _truncate_text(product_text, 1500)
            context_parts.append(f"Product Overview:\n{product_text}")
            total_chars += len(product_text)
        
        # Priority 3: Main context (summarize very aggressively)
        main_context = product_context.get("context", "")
        if main_context and total_chars < max_chars * 0.6:  # Only if we have room
            remaining = max_chars - total_chars
            if len(main_context) > remaining:
                # Extract only application-relevant sentences
                main_context = _extract_key_points(main_context, remaining)
            else:
                main_context = _truncate_text(main_context, remaining)
            
            if main_context:
                context_parts.append(f"Additional Context:\n{main_context}")
                total_chars += len(main_context)
        
        summary = "\n\n".join(context_parts)
        if len(summary) > max_chars:
            summary = _truncate_text(summary, max_chars)
        
        logger.info("lovable_context_summarized",
                   original_size=sum(len(str(v)) for v in product_context.values()),
                   summarized_size=len(summary),
                   max_chars=max_chars)
        
        return summary
    
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
