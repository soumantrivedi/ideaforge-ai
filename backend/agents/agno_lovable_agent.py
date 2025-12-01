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
        # Enhanced system prompt emphasizing detailed, comprehensive prompts
        system_prompt = """You are a Lovable AI Design Specialist expert in creating detailed, comprehensive prompts for Lovable.dev.

Your primary goal is to generate EXTENSIVE, DETAILED prompts that capture ALL aspects of the application based on the complete context provided.

Core Requirements:
- Generate DETAILED, COMPREHENSIVE prompts (not concise - include all relevant information)
- Include ALL form data, product context, and requirements from all lifecycle phases
- Describe complete application architecture, component structure, and data flow
- Specify ALL features, user flows, API integrations, and authentication patterns
- Include detailed Tailwind CSS styling, responsive breakpoints, and design system
- Describe state management, routing (Next.js App Router), and data fetching patterns
- Include accessibility (WCAG 2.1 AA), performance optimization, and modern React patterns
- Output ONLY the prompt text - no instructions, notes, or meta-commentary

Lovable Platform Documentation Guidelines (Based on Official Lovable.dev Docs):
- Lovable.dev generates fully deployable React/Next.js applications
- Supports Server Components, Client Components, and App Router patterns
- Uses Tailwind CSS for styling with responsive breakpoints
- Supports Supabase, Firebase, REST APIs, GraphQL, and authentication patterns
- Prompts should be detailed enough to generate complete, production-ready applications
- Include database schemas, API endpoints, authentication flows, and user management
- Describe complete application structure: pages, components, layouts, routing
- Include form validations, error handling, loading states, and user feedback
- Specify data models, relationships, and data flow throughout the application

Guidelines:
- Be EXTENSIVE and COMPREHENSIVE - include ALL relevant details from the product context
- Use ALL form data fields, not just key fields - every detail matters
- Include context from ALL lifecycle phases (Ideation, Strategy, Research, PRD, Design, etc.)
- Generate prompts that are detailed enough to create complete, deployable applications
- The prompt should be ready for direct use in Lovable Link Generator without additional editing"""

        # Initialize base agent first (tools will be added after)
        super().__init__(
            name="Lovable Agent",
            role="lovable",
            system_prompt=system_prompt,
            enable_rag=enable_rag,
            rag_table_name="lovable_knowledge_base",
            model_tier="standard",  # Use standard model for better quality, detailed prompts
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
        
        # Detailed prompt emphasizing comprehensive output
        user_prompt = f"""Generate a DETAILED, COMPREHENSIVE Lovable.dev prompt for this application. Include ALL relevant information from the context below.

IMPORTANT: 
- Include ALL form data fields, product details, features, and requirements
- Describe the complete application architecture, features, and user flows in detail
- Include all component specifications, pages, routing, API integrations, and data models
- Make the prompt EXTENSIVE and DETAILED - not concise
- The prompt should be comprehensive enough to generate a complete, deployable application

Product Context:
{context_summary}

Generate a detailed Lovable.dev prompt that captures ALL aspects of this application. Include:
- Complete application architecture and structure
- All pages, routes, and navigation structure
- Detailed component specifications with props and state
- Full styling details (Tailwind CSS classes, responsive breakpoints, design system)
- Complete user flows and interactions
- Database schema and data models
- API endpoints and data fetching patterns
- Authentication and user management flows
- Form validations, error handling, and user feedback
- State management patterns (React hooks, context, state)
- Accessibility features (WCAG 2.1 AA compliance)
- Performance optimizations and best practices

Output ONLY the prompt text - no instructions, notes, or explanations. The prompt should be ready to use directly in Lovable Link Generator."""

        message = AgentMessage(
            role="user",
            content=user_prompt,
            timestamp=datetime.utcnow()
        )

        # Use fast model tier (already set in __init__)
        response = await self.process([message], context={"task": "lovable_prompt_generation"})
        prompt_text = response.response
        
        # Clean the prompt - remove headers/footers/notes that AI might add
        prompt_text = self._clean_lovable_prompt(prompt_text)
        
        return prompt_text
    
    def _summarize_context(
        self,
        product_context: Dict[str, Any],
        phase_data: Optional[Dict[str, Any]] = None,
        all_phases_data: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Extract ALL product context without aggressive truncation - include everything."""
        context_parts = []
        
        # Get main context (usually contains phase data) - include ALL of it
        main_context = product_context.get("context", "")
        if main_context:
            # Include full context - don't truncate
            context_parts.append(f"Product Context:\n{main_context}")
        
        # Add ALL phase data if available - include EVERYTHING
        if all_phases_data:
            context_parts.append("\n=== ALL PRODUCT LIFECYCLE PHASES ===\n")
            for phase_item in all_phases_data:
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
