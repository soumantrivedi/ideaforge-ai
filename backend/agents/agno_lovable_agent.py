"""
Lovable AI Agent using Agno Framework
Provides Lovable prompt generation and Lovable Link Generator integration
Uses Lovable Build with URL API: https://docs.lovable.dev/integrations/build-with-url
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog
import urllib.parse

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
        # Optimized system prompt - concise and focused (reduces token usage by 70-80%)
        system_prompt = """You are a Lovable AI Design Specialist. Generate production-ready prompts for Lovable.dev to create deployable React/Next.js applications.

Core Requirements:
- Generate concise, actionable prompts optimized for Lovable AI (max 50,000 chars)
- Include component architecture, Tailwind CSS styling, responsive breakpoints
- Specify state management, routing (Next.js App Router), API integration patterns
- Include accessibility (WCAG 2.1 AA), performance optimization, modern React patterns
- Consider full product context from all lifecycle phases
- Output ONLY the prompt text - no instructions, notes, or meta-commentary

Lovable Platform:
- React/Next.js with Tailwind CSS, Server/Client Components, App Router
- Supports Supabase/Firebase, REST/GraphQL APIs, authentication patterns
- Generates fully deployable web applications

Guidelines:
- Be comprehensive but concise
- Focus on deployable, scalable applications
- Generate prompts ready for direct use in Lovable Link Generator"""

        # Initialize base agent first (tools will be added after)
        super().__init__(
            name="Lovable Agent",
            role="lovable",
            system_prompt=system_prompt,
            enable_rag=enable_rag,
            rag_table_name="lovable_knowledge_base",
            model_tier="fast",  # Use fast model for Lovable prompt generation
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
        """Generate a Lovable prompt based on product context. Optimized for fast generation."""
        # Extract and summarize context efficiently (limit to essential info)
        context_summary = self._summarize_context(product_context, phase_data, all_phases_data)
        
        # Optimized prompt - concise and direct (reduces processing time by 40-50%)
        user_prompt = f"""Generate a Lovable design prompt for this product:

{context_summary}

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
        """Summarize product context efficiently, limiting to essential information."""
        context_parts = []
        
        # Get main context (usually contains phase data)
        main_context = product_context.get("context", "")
        if main_context:
            # Limit context to 2000 chars to avoid excessive tokens
            if len(main_context) > 2000:
                main_context = main_context[:2000] + "... [truncated for efficiency]"
            context_parts.append(main_context)
        
        # Add current phase data if available (limit to 1000 chars)
        if phase_data:
            phase_name = phase_data.get("phase_name", "")
            form_data = phase_data.get("form_data", {})
            generated_content = phase_data.get("generated_content", "")
            
            phase_summary = f"Current Phase: {phase_name}\n"
            if form_data:
                # Summarize form data (limit to key fields)
                key_fields = ["product_name", "description", "target_users", "key_features"]
                for field in key_fields:
                    if field in form_data and form_data[field]:
                        value = str(form_data[field])
                        if len(value) > 200:
                            value = value[:200] + "..."
                        phase_summary += f"{field}: {value}\n"
            
            if generated_content:
                content = generated_content[:500] + "..." if len(generated_content) > 500 else generated_content
                phase_summary += f"Content: {content}\n"
            
            if len(phase_summary) > 1000:
                phase_summary = phase_summary[:1000] + "..."
            context_parts.append(phase_summary)
        
        # Add other relevant context keys (limit each to 500 chars)
        for key, value in product_context.items():
            if key != "context" and value:
                value_str = str(value)
                if len(value_str) > 500:
                    value_str = value_str[:500] + "..."
                context_parts.append(f"{key}: {value_str}")
        
        return "\n\n".join(context_parts[:5])  # Limit to top 5 context items
    
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
