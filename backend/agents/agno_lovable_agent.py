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

CRITICAL: You MUST use ALL available information from:
- ALL chatbot conversation history and context
- ALL design form content and fields
- ALL product lifecycle phase data (Ideation, Strategy, Research, PRD, Design, etc.)
- ALL generated content from previous phases
- ALL form data fields - do not skip any fields, include everything

Core Requirements:
- Generate DETAILED, COMPREHENSIVE prompts (not concise - include all relevant information)
- Include ALL form data, product context, and requirements from all lifecycle phases
- Extract and use ALL information from chatbot conversations - every detail matters
- Include ALL design form fields and their values - nothing should be omitted
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
- Extract and include ALL information from chatbot conversations - user discussions, requirements, preferences
- Include ALL design form content - every field, every value, every specification
- Include context from ALL lifecycle phases (Ideation, Strategy, Research, PRD, Design, etc.)
- Synthesize information from chatbot content AND form content - combine everything
- Generate prompts that are detailed enough to create complete, deployable applications
- The prompt should be ready for direct use in Lovable Link Generator without additional editing
- If chatbot content mentions features, requirements, or preferences, include them in the prompt
- If design form has specific styling, layout, or component requirements, include them all"""

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
        
        # Detailed prompt emphasizing comprehensive output with ALL chatbot and form content
        user_prompt = f"""Generate a DETAILED, COMPREHENSIVE Lovable.dev prompt for this application. Include ALL relevant information from the context below.

CRITICAL REQUIREMENTS:
- Extract and use ALL information from chatbot conversations - every discussion, requirement, preference mentioned
- Include ALL design form fields and their values - nothing should be omitted or skipped
- Synthesize information from BOTH chatbot content AND form content - combine everything
- Include ALL form data fields, product details, features, and requirements
- Describe the complete application architecture, features, and user flows in detail using ALL available information
- Include all component specifications, pages, routing, API integrations, and data models
- Make the prompt EXTENSIVE and DETAILED - not concise
- The prompt should be comprehensive enough to generate a complete, deployable application
- If chatbot mentions specific features, styling, or requirements, they MUST be included
- If design form has any field values, they MUST all be incorporated

Product Context (includes ALL chatbot conversations, form data, and generated content):
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

        # Temporarily disable tools during prompt generation to prevent accidental submission
        # Store original tools
        original_tools = None
        if hasattr(self.agno_agent, 'tools') and self.agno_agent.tools:
            original_tools = self.agno_agent.tools.copy()
            # Clear tools to prevent tool invocation during prompt generation
            self.agno_agent.tools = []
        
        try:
            # Use fast model tier (already set in __init__)
            # Context explicitly indicates this is prompt generation only, not submission
            # When tools are disabled, try to call model directly for better response extraction
            response = await self.process([message], context={"task": "lovable_prompt_generation", "disable_tools": True})
            prompt_text = response.response
            
            # Get the raw Agno response from metadata if available (always try this first)
            raw_agno_response = None
            if response.metadata and "_agno_raw_response" in response.metadata:
                raw_agno_response = response.metadata["_agno_raw_response"]
            
            # CRITICAL: If prompt_text is empty, too short, or is a RunOutput string, try extraction
            # Don't just check for RunOutput - also check if content is missing/empty
            needs_extraction = False
            if not prompt_text or not isinstance(prompt_text, str):
                needs_extraction = True
            elif len(prompt_text.strip()) < 50:
                needs_extraction = True
            elif "RunOutput" in prompt_text or "run_id=" in prompt_text:
                needs_extraction = True
            
            if needs_extraction:
                # Strategy 0: Try to extract from raw Agno response in metadata first (MOST RELIABLE)
                if raw_agno_response:
                    try:
                        # Check messages array in raw response - this is the most reliable source
                        if hasattr(raw_agno_response, "messages") and raw_agno_response.messages:
                            for msg in reversed(raw_agno_response.messages):
                                if hasattr(msg, "role") and msg.role == "assistant":
                                    # Try content first (most common)
                                    if hasattr(msg, "content") and msg.content:
                                        content = msg.content
                                        if isinstance(content, str) and content.strip() and "RunOutput" not in content and len(content.strip()) > 50:
                                            prompt_text = content.strip()
                                            logger.info("lovable_prompt_extracted_from_raw_response_metadata", 
                                                      extracted_length=len(prompt_text))
                                            break
                                    # Try reasoning_content if content is empty
                                    elif hasattr(msg, "reasoning_content") and msg.reasoning_content:
                                        reasoning = msg.reasoning_content
                                        if isinstance(reasoning, str) and reasoning.strip() and "RunOutput" not in reasoning and len(reasoning.strip()) > 50:
                                            prompt_text = reasoning.strip()
                                            logger.info("lovable_prompt_extracted_from_raw_reasoning", 
                                                      extracted_length=len(prompt_text))
                                            break
                                    # Try text attribute
                                    elif hasattr(msg, "text") and msg.text:
                                        text = msg.text
                                        if isinstance(text, str) and text.strip() and "RunOutput" not in text and len(text.strip()) > 50:
                                            prompt_text = text.strip()
                                            logger.info("lovable_prompt_extracted_from_raw_text", 
                                                      extracted_length=len(prompt_text))
                                            break
                        # Also check raw response content directly
                        if (not prompt_text or len(prompt_text.strip()) < 50) and hasattr(raw_agno_response, "content") and raw_agno_response.content:
                            content = raw_agno_response.content
                            if isinstance(content, str) and content.strip() and "RunOutput" not in content and len(content.strip()) > 50:
                                prompt_text = content.strip()
                                logger.info("lovable_prompt_extracted_from_raw_response_content", 
                                          extracted_length=len(prompt_text))
                    except Exception as raw_extract_error:
                        logger.warning("lovable_prompt_raw_response_extraction_failed", 
                                     error=str(raw_extract_error),
                                     error_type=type(raw_extract_error).__name__)
                
                # Continue with existing extraction strategies if still not found
                # Try multiple extraction strategies
                if (not prompt_text or len(prompt_text.strip()) < 50) and hasattr(self, 'agno_agent') and self.agno_agent:
                    try:
                        # Strategy 1: Check if response object itself has content (not just response.response)
                        if hasattr(response, 'content') and response.content:
                            if isinstance(response.content, str) and response.content.strip() and "RunOutput" not in response.content:
                                prompt_text = response.content
                                logger.info("lovable_prompt_extracted_from_response_content", 
                                          extracted_length=len(prompt_text))
                            elif not isinstance(response.content, str):
                                # Try to get string representation
                                content_str = str(response.content)
                                if "RunOutput" not in content_str and len(content_str) > 50:
                                    prompt_text = content_str
                                    logger.info("lovable_prompt_extracted_from_response_content_str", 
                                              extracted_length=len(prompt_text))
                        
                        # Strategy 2: Get the last run from the agent
                        if ("RunOutput" in prompt_text or "run_id=" in prompt_text) and hasattr(self.agno_agent, 'last_run') and self.agno_agent.last_run:
                            last_run = self.agno_agent.last_run
                            
                            # Check last_run.content directly
                            if hasattr(last_run, 'content') and last_run.content:
                                if isinstance(last_run.content, str) and last_run.content.strip() and "RunOutput" not in last_run.content:
                                    prompt_text = last_run.content
                                    logger.info("lovable_prompt_extracted_from_last_run_content", 
                                              extracted_length=len(prompt_text))
                            
                            # Strategy 3: Check model_provider_data for actual model response
                            if ("RunOutput" in prompt_text or "run_id=" in prompt_text) and hasattr(last_run, 'model_provider_data') and last_run.model_provider_data:
                                try:
                                    # Try to extract from model provider data
                                    model_data = last_run.model_provider_data
                                    if isinstance(model_data, dict):
                                        # Check common response fields
                                        for field in ['content', 'text', 'message', 'choices', 'response']:
                                            if field in model_data:
                                                field_value = model_data[field]
                                                if isinstance(field_value, str) and field_value.strip() and "RunOutput" not in field_value and len(field_value) > 50:
                                                    prompt_text = field_value
                                                    logger.info("lovable_prompt_extracted_from_model_provider_data", 
                                                              field=field, extracted_length=len(prompt_text))
                                                    break
                                        # Check nested choices[0].message.content (OpenAI format)
                                        if "RunOutput" in prompt_text and 'choices' in model_data and isinstance(model_data['choices'], list) and len(model_data['choices']) > 0:
                                            choice = model_data['choices'][0]
                                            if isinstance(choice, dict) and 'message' in choice:
                                                msg = choice['message']
                                                if isinstance(msg, dict) and 'content' in msg:
                                                    content = msg['content']
                                                    if isinstance(content, str) and content.strip() and "RunOutput" not in content and len(content) > 50:
                                                        prompt_text = content
                                                        logger.info("lovable_prompt_extracted_from_model_choices", 
                                                                  extracted_length=len(prompt_text))
                                except Exception as model_data_error:
                                    logger.warning("lovable_prompt_model_data_extraction_failed", 
                                                 error=str(model_data_error))
                            
                            # Strategy 4: Check messages array for assistant message with content
                            if ("RunOutput" in prompt_text or "run_id=" in prompt_text) and hasattr(last_run, 'messages') and last_run.messages:
                                # Find the last assistant message with actual content
                                for msg in reversed(last_run.messages):
                                    if hasattr(msg, 'role') and msg.role == 'assistant':
                                        # Try content first
                                        if hasattr(msg, 'content') and msg.content:
                                            content = msg.content
                                            if isinstance(content, str) and content.strip():
                                                # Make sure it's not the RunOutput string representation
                                                if "RunOutput" not in content and "run_id=" not in content and len(content) > 50:
                                                    prompt_text = content
                                                    logger.info("lovable_prompt_extracted_from_messages", 
                                                              extracted_length=len(prompt_text),
                                                              content_preview=prompt_text[:100])
                                                    break
                                        # Try reasoning_content if content is empty
                                        elif hasattr(msg, 'reasoning_content') and msg.reasoning_content:
                                            reasoning = msg.reasoning_content
                                            if isinstance(reasoning, str) and reasoning.strip() and "RunOutput" not in reasoning and len(reasoning) > 50:
                                                prompt_text = reasoning
                                                logger.info("lovable_prompt_extracted_from_reasoning", 
                                                          extracted_length=len(prompt_text))
                                                break
                                        # Try text attribute
                                        elif hasattr(msg, 'text') and msg.text:
                                            text = msg.text
                                            if isinstance(text, str) and text.strip() and "RunOutput" not in text and len(text) > 50:
                                                prompt_text = text
                                                logger.info("lovable_prompt_extracted_from_text", 
                                                          extracted_length=len(prompt_text))
                                                break
                                        
                                        # Strategy 5: If message has model_provider_data, check it
                                        if ("RunOutput" in prompt_text or "run_id=" in prompt_text) and hasattr(msg, 'provider_data') and msg.provider_data:
                                            try:
                                                provider_data = msg.provider_data
                                                if isinstance(provider_data, dict):
                                                    for field in ['content', 'text', 'message']:
                                                        if field in provider_data:
                                                            field_value = provider_data[field]
                                                            if isinstance(field_value, str) and field_value.strip() and "RunOutput" not in field_value and len(field_value) > 50:
                                                                prompt_text = field_value
                                                                logger.info("lovable_prompt_extracted_from_msg_provider_data", 
                                                                          field=field, extracted_length=len(prompt_text))
                                                                break
                                            except Exception as msg_data_error:
                                                logger.warning("lovable_prompt_msg_provider_data_extraction_failed", 
                                                             error=str(msg_data_error))
                                        
                                        # Try string representation
                                        elif isinstance(msg, str):
                                            if "RunOutput" not in msg and len(msg) > 50:
                                                prompt_text = msg
                                                logger.info("lovable_prompt_extracted_from_msg_str", 
                                                          extracted_length=len(prompt_text))
                                                break
                    except Exception as run_extract_error:
                        logger.warning("lovable_prompt_run_extraction_failed", 
                                     error=str(run_extract_error),
                                     error_type=type(run_extract_error).__name__)
                        # If extraction fails, we'll try to clean what we have
            
            # Clean the prompt - remove headers/footers/notes that AI might add
            prompt_text = self._clean_lovable_prompt(prompt_text)
            
            # Final validation: ensure we have actual prompt text, not RunOutput representation
            if isinstance(prompt_text, str) and ("RunOutput" in prompt_text or len(prompt_text) < 50):
                logger.error("lovable_prompt_extraction_failed", 
                           prompt_preview=prompt_text[:200],
                           prompt_length=len(prompt_text))
                # Return a helpful error message instead of the RunOutput string
                return "Error: Could not extract Lovable prompt from agent response. Please try again or contact support."
            
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
