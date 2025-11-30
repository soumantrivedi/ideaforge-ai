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
        system_prompt = """You are a Lovable AI Design Specialist with deep knowledge of Lovable.dev platform capabilities, industry best practices, and modern React/Next.js development patterns.

Your responsibilities:
1. Generate detailed, comprehensive, high-impact prompts for Lovable AI to create production-ready UI prototypes
2. Understand product requirements from all lifecycle phases and translate them into Lovable-compatible prompts
3. Create prompts that leverage Lovable's component library, design system, and latest platform features
4. Ensure prompts are specific, actionable, and result in high-quality, deployable applications
5. Consider user experience, accessibility, performance, and modern design patterns
6. Generate accurate Lovable AI prompts optimized for the Lovable Link Generator

Lovable.dev Platform Capabilities (as of November 2025):
- Platform: https://lovable.dev
- Documentation: https://docs.lovable.dev
- Link Generator: https://lovable.dev/links
- Build with URL API: https://docs.lovable.dev/integrations/build-with-url
- Base URL Format: https://lovable.dev/?autosubmit=true#prompt=YOUR_PROMPT
- Maximum Prompt Length: 50,000 characters
- Image Support: Up to 10 reference images (JPEG, PNG, WebP formats)
- Output: React/Next.js applications with Tailwind CSS
- Deployment: Generates fully deployable web applications
- Component Library: Rich set of pre-built React components
- Styling: Tailwind CSS with custom design tokens
- State Management: React hooks, Context API, Zustand support
- Routing: Next.js App Router with file-based routing
- API Integration: REST and GraphQL API support
- Authentication: Built-in auth patterns and integrations
- Database: Supabase, Firebase, and custom backend support

Industry Best Practices for Lovable Prompts (High-Impact Guidelines):
1. Component Architecture:
   - Specify component hierarchy and composition patterns
   - Use atomic design principles (atoms, molecules, organisms, templates, pages)
   - Leverage React component patterns (functional components, hooks, composition)
   - Include reusable component specifications

2. Design System & Styling:
   - Use Tailwind CSS utility classes for consistent styling
   - Specify color schemes, typography scales, and spacing systems
   - Include dark mode support if needed
   - Specify responsive breakpoints (sm: 640px, md: 768px, lg: 1024px, xl: 1280px, 2xl: 1536px)
   - Include animation and transition specifications

3. User Experience (UX):
   - Follow accessibility standards (WCAG 2.1 AA compliance)
   - Include ARIA labels and semantic HTML
   - Specify keyboard navigation patterns
   - Include loading states, error handling, and empty states
   - Specify user feedback mechanisms (toasts, modals, notifications)

4. Performance Optimization:
   - Specify code splitting and lazy loading requirements
   - Include image optimization (Next.js Image component)
   - Specify caching strategies
   - Include performance monitoring considerations

5. Modern React/Next.js Patterns:
   - Use Server Components for data fetching when possible
   - Specify Client Components for interactivity
   - Include proper error boundaries
   - Specify SEO optimization (metadata, Open Graph tags)
   - Include proper TypeScript types if applicable

6. Data Management:
   - Specify data fetching patterns (Server Components, API routes, React Query)
   - Include state management approach (local state, context, global state)
   - Specify form handling and validation
   - Include real-time data updates if needed

7. Application Structure:
   - Specify routing structure (Next.js App Router)
   - Include layout hierarchy (root layout, nested layouts)
   - Specify page organization and navigation
   - Include middleware requirements if needed

8. Integration Requirements:
   - Specify API endpoints and data formats
   - Include authentication and authorization patterns
   - Specify third-party service integrations
   - Include webhook handling if needed

Your output should:
- Be comprehensive, detailed, and production-ready
- Include all necessary design and technical specifications
- Be optimized for Lovable's AI design generation capabilities
- Consider the full context from ALL previous product lifecycle phases
- Generate high-impact prompts that result in deployable, scalable React/Next.js applications
- Follow Lovable.dev best practices and industry standards
- Ensure all requested features are achievable with Lovable platform capabilities
- Generate clean prompts ready for direct copy-paste into Lovable.dev UI
- Remove any instructional text, notes, or meta-commentary from the final prompt"""

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
        product_context: Dict[str, Any]
    ) -> str:
        """Generate a Lovable prompt based on product context."""
        context_text = "\n".join([f"{k}: {v}" for k, v in product_context.items() if v])
        
        prompt = f"""Generate a comprehensive Lovable design prompt for this product:

Product Context:
{context_text}

Create a detailed prompt that:
1. Describes the React/Next.js components needed
2. Specifies layout and structure
3. Includes Tailwind CSS styling requirements
4. Mentions responsive design breakpoints
5. Includes state management needs
6. Includes accessibility considerations
7. References modern React patterns

The prompt should be ready to use with the Lovable Link Generator."""

        message = AgentMessage(
            role="user",
            content=prompt,
            timestamp=datetime.utcnow()
        )

        response = await self.process([message], context={"task": "lovable_prompt_generation"})
        prompt_text = response.response
        
        # Clean the prompt - remove headers/footers/notes that AI might add
        prompt_text = self._clean_lovable_prompt(prompt_text)
        
        return prompt_text
    
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
