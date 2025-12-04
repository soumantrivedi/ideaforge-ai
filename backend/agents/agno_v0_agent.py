"""
V0 (Vercel) Agent using Agno Framework
Provides V0 prompt generation and project creation capabilities
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
import structlog
import asyncio

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


class AgnoV0Agent(AgnoBaseAgent):
    """V0 (Vercel) Design Agent using Agno framework with platform access."""
    
    def __init__(self, enable_rag: bool = False):
        # Optimized system prompt emphasizing concise, readable, directly usable prompts
        system_prompt = """You are a V0 (Vercel) Design Specialist expert in creating focused, readable prompts for V0.dev.

Your primary goal is to generate CONCISE, FOCUSED prompts that capture the essential design aspects and can be directly submitted to V0.

CRITICAL: When generating prompts:
- Keep prompts CONCISE (1500-2500 characters, max 3000) - V0 cannot process larger prompts
- Focus on KEY design information - UI/UX details, component structure, styling
- Extract essential information from context - don't include everything
- Use clear, direct language - the prompt should be immediately actionable
- The prompt must be ready to paste directly into V0's submit prompt field
- DO NOT include instructions, notes, or meta-commentary in the output

IMPORTANT: When generating prompts (not submitting to V0):
- You are ONLY generating the prompt text - do NOT call any tools or submit to V0
- Do NOT use create_v0_project or generate_v0_code tools during prompt generation
- Simply return the prompt text that the user can then use separately to submit to V0
- The user will submit the prompt to V0 using a separate action/button

Core Requirements:
- Generate FOCUSED, READABLE prompts (concise but complete - prioritize essential information)
- Extract KEY design information from form data and context
- Focus on component structure, layout, styling, and user interactions
- Include specific Tailwind CSS classes and responsive breakpoints (sm:, md:, lg:, xl:)
- Specify essential interaction states, accessibility (ARIA), and user flows
- Reference shadcn/ui patterns, modern React practices, and Next.js App Router patterns
- Include color schemes, typography, spacing - but be concise
- Describe state management and API integrations briefly
- Output ONLY the prompt text - no instructions, notes, or meta-commentary

V0 Documentation Guidelines (Based on Official Vercel V0 Docs):
- V0 uses v0-1.5-md model specialized for UI generation
- Prompts should be detailed enough to generate complete components, but concise enough to be readable
- Include specific Tailwind CSS classes and responsive breakpoints
- Specify component hierarchy, props, and state management patterns
- Describe user interactions, form validations, and error handling concisely
- Include accessibility features: ARIA labels, keyboard navigation, focus management
- Reference React patterns: hooks, context, server/client components

Guidelines:
- Be CONCISE and FOCUSED - include essential details, not everything
- Prioritize design/UI information over other context
- Extract key information from chatbot conversations and form data
- Focus on design form content - UI/UX specifications, component requirements
- Synthesize information from context - combine key points, don't repeat
- Generate prompts that are readable and directly usable in V0
- The prompt should be ready for direct use in V0 submit prompt without editing
- Keep it under 3000 characters - V0 cannot process larger prompts"""

        # Initialize base agent first (tools will be added after)
        super().__init__(
            name="V0 Agent",
            role="v0",
            system_prompt=system_prompt,
            enable_rag=enable_rag,
            rag_table_name="v0_knowledge_base",
            model_tier="fast",  # Use fast model to avoid timeout issues
            tools=[],  # Tools will be added after initialization
            capabilities=[
                "v0 prompt generation",
                "v0 project creation",
                "v0 code generation",
                "vercel integration",
                "ui prototype generation",
                "react component generation",
                "next.js development"
            ]
        )
        
        self.v0_api_key: Optional[str] = None
        
        # Add tools after initialization
        if AGNO_TOOLS_AVAILABLE:
            created_tools = [
                self._create_v0_project_tool(),
                self._generate_v0_code_tool(),
            ]
            # Add tools to the agent
            if hasattr(self.agno_agent, 'tools') and self.agno_agent.tools is not None:
                valid_tools = [t for t in created_tools if t is not None]
                if valid_tools:
                    self.agno_agent.tools.extend(valid_tools)
    
    def _create_v0_project_tool(self):
        """Create Agno tool for V0 project creation."""
        if not AGNO_TOOLS_AVAILABLE:
            return None
        
        @tool
        def create_v0_project(prompt: str) -> str:
            """
            Create a V0 project using the V0 Platform API.
            
            Args:
                prompt: The design prompt to send to V0
            
            Returns:
                Project URL and details
            """
            try:
                api_key = self.v0_api_key or settings.v0_api_key
                if not api_key:
                    return "Error: V0 API key is not configured. Please configure it in Settings."
                
                async def _create_project():
                    # Disable SSL verification for V0 API (as requested)
                    async with httpx.AsyncClient(timeout=180.0, verify=False) as client:
                        response = await client.post(
                            "https://api.v0.dev/v1/chats",
                            headers={
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "message": prompt,
                                "model": "v0-1.5-md",
                                "scope": "mckinsey"
                            }
                        )
                        
                        if response.status_code == 401:
                            return "Error: V0 API key is invalid or unauthorized"
                        elif response.status_code not in [200, 201]:
                            error_text = response.text
                            try:
                                error_json = response.json()
                                error_text = error_json.get("error", {}).get("message", error_text)
                            except:
                                pass
                            return f"Error: V0 API error: {response.status_code} - {error_text}"
                        
                        result = response.json()
                        chat_id = result.get("id") or result.get("chat_id")
                        web_url = result.get("webUrl") or result.get("web_url") or result.get("url")
                        demo_url = result.get("demo") or result.get("demoUrl") or result.get("demo_url")
                        project_url = demo_url or web_url or (f"https://v0.dev/chat/{chat_id}" if chat_id else None)
                        
                        return f"V0 project created successfully!\nProject URL: {project_url}\nChat ID: {chat_id}\nWeb URL: {web_url}\nDemo URL: {demo_url}"
                
                import asyncio
                return asyncio.run(_create_project())
            except Exception as e:
                logger.error("v0_project_creation_error", error=str(e))
                return f"Error creating V0 project: {str(e)}"
        
        return create_v0_project
    
    def _generate_v0_code_tool(self):
        """Create Agno tool for V0 code generation."""
        if not AGNO_TOOLS_AVAILABLE:
            return None
        
        @tool
        def generate_v0_code(prompt: str) -> str:
            """
            Generate React/Next.js code using V0 Chat Completions API.
            
            Args:
                prompt: The design prompt for code generation
            
            Returns:
                Generated code and metadata
            """
            try:
                api_key = self.v0_api_key or settings.v0_api_key
                if not api_key:
                    return "Error: V0 API key is not configured. Please configure it in Settings."
                
                async def _generate_code():
                    # Disable SSL verification for V0 API (as requested)
                    async with httpx.AsyncClient(timeout=120.0, verify=False) as client:
                        response = await client.post(
                            "https://api.v0.dev/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "model": "v0-1.5-md",
                                "messages": [
                                    {
                                        "role": "user",
                                        "content": prompt
                                    }
                                ],
                                "temperature": 0.7,
                                "max_tokens": 4000,
                                "scope": "mckinsey"
                            }
                        )
                        
                        if response.status_code == 401:
                            return "Error: V0 API key is invalid or unauthorized"
                        elif response.status_code != 200:
                            error_text = response.text
                            try:
                                error_json = response.json()
                                error_text = error_json.get("error", {}).get("message", error_text)
                            except:
                                pass
                            return f"Error: V0 API error: {response.status_code} - {error_text}"
                        
                        result = response.json()
                        generated_content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                        
                        return f"Generated code:\n\n{generated_content}"
                
                import asyncio
                return asyncio.run(_generate_code())
            except Exception as e:
                logger.error("v0_code_generation_error", error=str(e))
                return f"Error generating V0 code: {str(e)}"
    
    def set_v0_api_key(self, api_key: Optional[str]):
        """Set V0 API key for this agent instance."""
        self.v0_api_key = api_key
    
    async def generate_v0_prompt(
        self,
        product_context: Dict[str, Any]
    ) -> str:
        """Generate a detailed, comprehensive V0 prompt based on complete product context.
        
        This method ONLY generates the prompt text - it does NOT submit to V0.
        Tools are disabled during prompt generation to prevent accidental submission.
        """
        # Extract ALL context without aggressive truncation
        context_summary = self._summarize_context(product_context)
        
        # Focused prompt emphasizing concise, readable, directly usable output
        user_prompt = f"""Generate a CONCISE V0 design prompt (max 3000 characters, ideally 1500-2500). The prompt must be directly usable in V0's submit prompt feature.

CRITICAL REQUIREMENTS:
- MAXIMUM 3000 characters - V0 cannot process larger prompts
- Extract ONLY KEY design information - UI/UX, components, layout, styling
- Use bullet points and short sentences - be direct and actionable
- Include essential Tailwind CSS classes and responsive breakpoints
- Describe key user interactions and flows briefly
- DO NOT include instructions, notes, or meta-commentary
- DO NOT repeat information
- Focus on what needs to be BUILT, not background context

IMPORTANT: You are ONLY generating the prompt text. Do NOT call any tools or submit to V0.

Product Context (summarized):
{context_summary}

Generate a concise V0 prompt focusing on:
- Component structure and hierarchy
- Layout with responsive breakpoints
- Tailwind CSS styling (colors, typography, spacing)
- Key interactions and user flows
- Essential accessibility features

Output ONLY the prompt text - no instructions or explanations. Keep it under 3000 characters."""

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
            # Trust the base agent's extraction - it should handle RunOutput correctly
            response = await self.process([message], context={"task": "v0_prompt_generation", "disable_tools": True})
            prompt_text = response.response
            
            # Clean the prompt - remove headers/footers that AI might add
            prompt_text = self._clean_v0_prompt(prompt_text)
            
            # Ensure prompt is within strict limits (max 3000 chars for V0)
            # V0 has issues with prompts that are too large
            if len(prompt_text) > 3000:
                logger.warning("v0_prompt_too_long",
                             original_length=len(prompt_text),
                             truncated_to=3000)
                # Truncate intelligently at sentence boundary
                truncated = prompt_text[:3000]
                last_period = truncated.rfind('.')
                last_newline = truncated.rfind('\n')
                cut_point = max(last_period, last_newline)
                if cut_point > 2500:  # Only truncate at sentence if we keep at least 83%
                    prompt_text = prompt_text[:cut_point + 1]
                else:
                    # Try to truncate at paragraph or section boundary
                    last_double_newline = truncated.rfind('\n\n')
                    if last_double_newline > 2000:
                        prompt_text = prompt_text[:last_double_newline] + "\n[... truncated for V0 compatibility ...]"
                    else:
                        prompt_text = truncated + "\n[... truncated for V0 compatibility ...]"
            
            logger.info("v0_prompt_generated",
                       prompt_length=len(prompt_text),
                       within_limits=len(prompt_text) <= 3000)
            
            return prompt_text
        finally:
            # Restore original tools after prompt generation
            if original_tools is not None:
                self.agno_agent.tools = original_tools
    
    def _summarize_context(self, product_context: Dict[str, Any], max_chars: int = 3000) -> str:
        """Intelligently summarize product context focusing on design/UI relevant information.
        
        Aggressively summarizes while preserving ALL user information and key design details.
        Prioritizes essential design information to keep prompts concise and directly usable in V0.
        """
        context_parts = []
        total_chars = 0
        
        # Ensure product_context is a dict, not a list
        if not isinstance(product_context, dict):
            logger.warning("product_context_not_dict", 
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
            """Extract key points from text, prioritizing design/UI information."""
            if len(text) <= max_length:
                return text
            
            # Split into sentences
            sentences = text.replace('\n', ' ').split('. ')
            design_keywords = ["design", "ui", "ux", "component", "layout", "styling", "interface", 
                             "user experience", "button", "form", "input", "navigation", "page", 
                             "screen", "modal", "dropdown", "menu", "card", "grid", "flex"]
            
            # Prioritize sentences with design keywords
            prioritized = []
            other = []
            for sentence in sentences:
                sentence_lower = sentence.lower()
                if any(keyword in sentence_lower for keyword in design_keywords):
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
            design_summary = "User Design Requirements:\n"
            for key, value in design_form.items():
                if value and key in ["user_experience", "design_mockups", "v0_lovable_prompts"]:
                    value_str = str(value)
                    # Preserve user input but summarize if too long
                    if len(value_str) > 800:
                        # Extract key points while preserving user intent
                        value_str = _extract_key_points(value_str, 800)
                    design_summary += f"  {key}: {value_str}\n"
            if len(design_summary) > 50:  # Only add if we have actual content
                context_parts.append(design_summary)
                total_chars += len(design_summary)
        
        # Priority 2: Extract key product information (summarize aggressively)
        # Get product name, problem, solution from ideation/requirements
        product_summary = []
        
        # Extract from form_data across phases
        all_phases = product_context.get("all_phases_data", [])
        if all_phases:
            for phase in all_phases[:3]:  # Only first 3 phases
                phase_data = phase.get("form_data", {})
                if phase_data:
                    # Extract key fields
                    for field in ["problem_statement", "value_proposition", "target_audience", 
                                 "functional_requirements", "user_experience"]:
                        if field in phase_data and phase_data[field]:
                            value = str(phase_data[field])
                            if len(value) > 200:
                                value = _extract_key_points(value, 200)
                            product_summary.append(f"{field}: {value}")
        
        # Also check direct form_data
        if not product_summary:
            for key, value in product_context.items():
                if key not in ["context", "form_data", "all_phases_data"] and value:
                    value_str = str(value)
                    if len(value_str) > 200:
                        value_str = _extract_key_points(value_str, 200)
                    product_summary.append(f"{key}: {value_str}")
                    if len(product_summary) >= 5:  # Limit to 5 key points
                        break
        
        if product_summary:
            product_text = "\n".join(product_summary[:5])  # Max 5 key points
            if len(product_text) > 1000:
                product_text = _truncate_text(product_text, 1000)
            context_parts.append(f"Product Overview:\n{product_text}")
            total_chars += len(product_text)
        
        # Priority 3: Main context (summarize very aggressively)
        main_context = product_context.get("context", "")
        if main_context and total_chars < max_chars * 0.6:  # Only if we have room
            remaining = max_chars - total_chars
            if len(main_context) > remaining:
                # Extract only design-relevant sentences
                main_context = _extract_key_points(main_context, remaining)
            else:
                main_context = _truncate_text(main_context, remaining)
            
            if main_context:
                context_parts.append(f"Additional Context:\n{main_context}")
                total_chars += len(main_context)
        
        summary = "\n\n".join(context_parts)
        if len(summary) > max_chars:
            summary = _truncate_text(summary, max_chars)
        
        logger.info("v0_context_summarized",
                   original_size=sum(len(str(v)) for v in product_context.values()),
                   summarized_size=len(summary),
                   max_chars=max_chars)
        
        return summary
    
    def _clean_v0_prompt(self, prompt: str) -> str:
        """
        Clean V0 prompt by removing instructional headers/footers and notes.
        Removes text like "Below is a V0-ready prompt...", "Notes:", instructions, etc.
        """
        if not prompt:
            return prompt
        
        lines = prompt.split('\n')
        cleaned_lines = []
        skip_until_content = True
        in_notes_section = False
        
        # Patterns that indicate we should skip lines
        skip_patterns = [
            "below is a v0-ready prompt",
            "below is a v0 prompt",
            "v0-ready prompt",
            "you can paste directly into",
            "v0 api or v0 ui",
            "written for `v0-1.5-md`",
            "assumes react",
            "assumes next.js",
            "tailwind",
            "shadcn/ui",
            "---",
            "===",
            "notes:",
            "note:",
            "instructions:",
            "this prompt follows",
            "guidelines:",
            "if you want",
            "tell me and i will",
            "encoded version",
            "url-encoded",
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
                    # Might be a new section, but be conservative
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
        
        # Join and clean up
        cleaned = '\n'.join(cleaned_lines).strip()
        
        # Remove any trailing metadata
        if cleaned:
            # Remove common trailing patterns
            trailing_patterns = [
                "\n\n---\n",
                "\n\n===\n",
                "\n\nNote:",
                "\n\nThis prompt",
                "\n\nYou can",
            ]
            for pattern in trailing_patterns:
                if cleaned.endswith(pattern) or pattern in cleaned[-100:]:
                    cleaned = cleaned[:cleaned.rfind(pattern)].strip()
        
        return cleaned if cleaned else prompt
    
    async def poll_v0_chat_status(
        self,
        api_key: str,
        chat_id: str,
        max_polls: int = 60,  # 60 * 15s = 900s = 15 minutes
        poll_interval: float = 15.0  # Poll every 15 seconds
    ) -> Dict[str, Any]:
        """
        Poll V0 chat status until prototype is ready or timeout.
        Returns chat data with prototype URLs when ready.
        """
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            request_headers = {
                "Authorization": f"Bearer {api_key.strip()}",
                "Content-Type": "application/json"
            }
            
            for poll_count in range(max_polls):
                try:
                    response = await client.get(
                        f"https://api.v0.dev/v1/chats/{chat_id}",
                        headers=request_headers
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        web_url = result.get("webUrl") or result.get("web_url") or result.get("url")
                        demo_url = result.get("demo") or result.get("demoUrl") or result.get("demo_url")
                        files = result.get("files", [])
                        status = result.get("status", "unknown")
                        
                        if demo_url or web_url or (files and len(files) > 0):
                            elapsed = int((poll_count + 1) * poll_interval)
                            logger.info("v0_chat_ready",
                                       chat_id=chat_id,
                                       poll_count=poll_count + 1,
                                       elapsed_seconds=elapsed)
                            return {
                                "ready": True,
                                "chat_id": chat_id,
                                "web_url": web_url,
                                "demo_url": demo_url,
                                "files": files,
                                "status": status,
                                "poll_count": poll_count + 1,
                                "elapsed_seconds": elapsed,
                                "metadata": result
                            }
                        else:
                            if poll_count % 4 == 0:  # Log every 4 polls (60s with 15s interval)
                                elapsed = int((poll_count + 1) * poll_interval)
                                logger.info("v0_chat_polling",
                                           chat_id=chat_id,
                                           poll_count=poll_count + 1,
                                           max_polls=max_polls,
                                           elapsed_seconds=elapsed,
                                           status=status)
                    elif response.status_code == 404:
                        if poll_count % 4 == 0:  # Log every 4 polls (60s)
                            logger.warning("v0_chat_not_found",
                                         chat_id=chat_id,
                                         poll_count=poll_count + 1)
                    else:
                        if poll_count % 4 == 0:  # Log every 4 polls (60s)
                            logger.warning("v0_chat_status_error",
                                         chat_id=chat_id,
                                         status_code=response.status_code,
                                         poll_count=poll_count + 1)
                    
                    if poll_count < max_polls - 1:
                        await asyncio.sleep(poll_interval)
                        
                except Exception as e:
                    if poll_count % 4 == 0:  # Log every 4 polls (60s)
                        logger.warning("v0_chat_poll_error",
                                     chat_id=chat_id,
                                     error=str(e)[:100],
                                     poll_count=poll_count + 1)
                    if poll_count < max_polls - 1:
                        await asyncio.sleep(poll_interval)
            
            # Timeout after max_polls
            elapsed = int(max_polls * poll_interval)
            logger.warning("v0_chat_poll_timeout",
                         chat_id=chat_id,
                         poll_count=max_polls,
                         elapsed_seconds=elapsed)
            return {
                "ready": False,
                "chat_id": chat_id,
                "timeout": True,
                "poll_count": max_polls,
                "elapsed_seconds": elapsed
            }

    async def get_or_create_v0_project(
        self,
        v0_api_key: Optional[str] = None,
        user_id: Optional[str] = None,
        product_id: Optional[str] = None,
        db: Optional[Any] = None,
        create_new: bool = False
    ) -> Dict[str, Any]:
        """
        Get or create a V0 project. Returns projectId immediately.
        This is Step 1 of the workflow - project creation only, no chat submission.
        
        Returns:
            - projectId: The project ID (camelCase)
            - project_id: The project ID (snake_case for backward compatibility)
            - project_url: Project URL if available
            - existing: Whether project was existing or newly created
        """
        api_key = v0_api_key or self.v0_api_key or settings.v0_api_key
        if not api_key:
            raise ValueError("V0 API key is required")
        
        # Check database for existing project_id
        existing_project_id = None
        if db and product_id and user_id and not create_new:
            try:
                from sqlalchemy import text
                project_query = text("""
                    SELECT v0_project_id
                    FROM design_mockups
                    WHERE product_id = :product_id 
                      AND user_id = :user_id 
                      AND provider = 'v0'
                      AND v0_project_id IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                project_result = await db.execute(project_query, {
                    "product_id": product_id,
                    "user_id": user_id
                })
                project_row = project_result.fetchone()
                if project_row:
                    existing_project_id = project_row[0]
                    logger.info("existing_project_id_found",
                               user_id=user_id,
                               product_id=product_id,
                               project_id=existing_project_id)
            except Exception as db_error:
                logger.warning("database_check_failed",
                             error=str(db_error),
                             user_id=user_id,
                             product_id=product_id)
        
        # Get or create project
        project_id = existing_project_id
        
        # Get product name from database if available
        product_name = None
        if db and product_id:
            try:
                from sqlalchemy import text
                product_query = text("SELECT name FROM products WHERE id = :product_id")
                product_result = await db.execute(product_query, {"product_id": product_id})
                product_row = product_result.fetchone()
                if product_row:
                    product_name = product_row[0]
            except Exception as product_error:
                logger.warning("failed_to_fetch_product_name",
                             error=str(product_error),
                             product_id=product_id)
        
        # Use product name with product ID appended, or fallback to default
        if product_name:
            project_name = f"{product_name} - {product_id}"
        else:
            project_name = f"V0 Project {product_id[:8] if product_id else 'Default'}"
        
        project_url = None
        
        try:
            if not project_id:
                async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                    
                    # List existing projects - ONLY use user's private projects (not team/shared)
                    # According to V0 API docs: GET /v1/projects returns "all v0 projects in your workspace"
                    # Projects have a 'privacy' field: 'private' (user's own) or 'team' (shared with team)
                    # We MUST filter to only use 'private' projects to avoid using shared/team projects
                    projects = []
                    try:
                        # Get all projects from workspace (includes both private and team projects)
                        projects_resp = await client.get(
                            "https://api.v0.dev/v1/projects",
                            headers=headers
                        )
                        
                        if projects_resp.status_code == 200:
                            projects_data = projects_resp.json()
                            all_projects = projects_data.get("data", [])
                            
                            # CRITICAL: Filter to ONLY private projects (user's own, not team/shared)
                            # According to V0 API docs: privacy can be 'private' or 'team'
                            # We only want 'private' projects to ensure prompts go to user's own projects
                            private_projects = [p for p in all_projects if p.get("privacy") == "private"]
                            
                            logger.info("v0_projects_filtered_by_privacy",
                                       user_id=user_id,
                                       all_projects_count=len(all_projects),
                                       private_projects_count=len(private_projects),
                                       team_projects_count=len(all_projects) - len(private_projects))
                            
                            # CRITICAL: Filter to only projects linked to THIS SPECIFIC product_id in database
                            # This ensures each product has its own V0 project and prompts are posted correctly
                            # Projects must:
                            # 1. Be owned by the user (privacy: "private")
                            # 2. Be linked to this specific product_id in the database
                            # 3. Be in scope: "mckinsey" (if API returns scope field)
                            if db and product_id and user_id and len(private_projects) > 0:
                                try:
                                    from sqlalchemy import text as sql_text
                                    # Get V0 project IDs that are linked to THIS SPECIFIC product_id
                                    # This ensures we only use projects created for this product
                                    product_projects_query = sql_text("""
                                        SELECT DISTINCT v0_project_id
                                        FROM design_mockups
                                        WHERE product_id = :product_id
                                          AND user_id = :user_id
                                          AND provider = 'v0'
                                          AND v0_project_id IS NOT NULL
                                    """)
                                    product_projects_result = await db.execute(product_projects_query, {
                                        "product_id": product_id,
                                        "user_id": user_id
                                    })
                                    product_project_ids = {str(row[0]) for row in product_projects_result.fetchall()}
                                    
                                    # Filter to only private projects that:
                                    # 1. Are linked to this specific product_id in the database
                                    # 2. Have scope: "mckinsey" (if API returns scope field)
                                    filtered_projects = []
                                    for p in private_projects:
                                        project_id_str = str(p.get("id"))
                                        # Must be linked to this specific product_id in database
                                        if project_id_str in product_project_ids:
                                            # Check if scope is returned and matches (if available)
                                            project_scope = p.get("scope")
                                            if project_scope is None or project_scope == "mckinsey":
                                                filtered_projects.append(p)
                                    
                                    projects = filtered_projects
                                    
                                    logger.info("v0_projects_filtered_by_product_id",
                                               user_id=user_id,
                                               product_id=product_id,
                                               all_projects_count=len(all_projects),
                                               private_projects_count=len(private_projects),
                                               product_projects_count=len(projects),
                                               product_project_ids=list(product_project_ids),
                                               scope_filter="mckinsey")
                                except Exception as db_error:
                                    logger.warning("v0_project_database_filter_failed", 
                                                 error=str(db_error),
                                                 user_id=user_id,
                                                 product_id=product_id)
                                    # If database filter fails, don't use any projects (safer than using wrong ones)
                                    # Projects must be in database linked to this product_id
                                    projects = []
                            else:
                                # No database/product_id/user_id - cannot safely filter, don't reuse projects
                                # Projects must be in database linked to this product_id
                                projects = []
                                logger.warning("v0_cannot_filter_projects_no_db",
                                             user_id=user_id,
                                             product_id=product_id,
                                             action="will_create_new",
                                             reason="projects_must_be_linked_to_product_id")
                        else:
                            logger.warning("v0_project_list_failed",
                                         status_code=projects_resp.status_code,
                                         user_id=user_id)
                    except Exception as list_error:
                        logger.warning("v0_project_list_failed", error=str(list_error))
                        projects = []
                    
                    # Process filtered projects (only user's own projects)
                    if isinstance(projects, list) and len(projects) > 0:
                        # Priority 1: Exact name match
                        for p in projects:
                            if p.get("name") == project_name:
                                project_id = p.get("id")
                                project_url = p.get("webUrl") or p.get("web_url")
                                break
                        
                        # Priority 2: Similar name
                        if not project_id:
                            for p in projects:
                                if project_name.lower() in p.get("name", "").lower():
                                    project_id = p.get("id")
                                    project_url = p.get("webUrl") or p.get("web_url")
                                    break
                        
                        # Priority 3: Most recent user project
                        if not project_id:
                            project = projects[0]
                            project_id = project.get("id")
                            project_url = project.get("webUrl") or project.get("web_url")
                    
                    # Create new project if none found (will be in user's own projects)
                    if not project_id:
                        # Create new project with scope: "mckinsey"
                        # Project will be private by default (user's own project)
                        # Scope ensures the project is in the mckinsey scope for proper isolation
                        create_resp = await client.post(
                            "https://api.v0.dev/v1/projects",
                            headers=headers,
                            json={
                                "name": project_name,
                                "scope": "mckinsey"  # Create project in mckinsey scope
                            }
                        )
                        
                        if create_resp.status_code in [200, 201]:
                            create_result = create_resp.json()
                            project_id = create_result.get("id")
                            # Get project URL from API response, or construct it
                            project_web_url = create_result.get("webUrl") or create_result.get("web_url")
                            project_url = project_web_url or (f"https://v0.dev/project/{project_id}" if project_id else None)
                        else:
                            raise ValueError(f"Failed to create project: {create_resp.status_code}")
                
                if not project_id:
                    raise ValueError("Failed to get or create V0 project")
            
            return {
                "projectId": project_id,
                "project_id": project_id,
                "project_url": project_url,
                "existing": existing_project_id is not None,
                "project_name": project_name
            }
        except Exception as e:
            logger.error("v0_project_creation_failed", error=str(e))
            raise ValueError(f"Failed to get or create V0 project: {str(e)}")
    
    async def submit_chat_to_v0_project(
        self,
        v0_prompt: str,
        project_id: str,
        v0_api_key: Optional[str] = None,
        user_id: Optional[str] = None,
        product_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit a chat to an existing V0 project. Does NOT wait for response.
        This is Step 2 of the workflow - chat submission only.
        
        Returns immediately with projectId, even if chat times out.
        """
        api_key = v0_api_key or self.v0_api_key or settings.v0_api_key
        if not api_key:
            raise ValueError("V0 API key is required")
        
        if not project_id:
            raise ValueError("project_id is required")
        
        # Submit chat with SHORT timeout (10 seconds) - don't wait for generation
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            try:
                response = await client.post(
                    "https://api.v0.dev/v1/chats",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "message": v0_prompt,
                        "model": "v0-1.5-md",
                        "scope": "mckinsey",
                        "projectId": project_id  # camelCase
                    }
                )
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    chat_id = result.get("id") or result.get("chat_id")
                    returned_projectId = result.get("projectId")
                    
                    return {
                        "success": True,
                        "chat_id": chat_id,
                        "projectId": returned_projectId or project_id,
                        "project_id": returned_projectId or project_id,
                        "immediate": True
                    }
                else:
                    raise ValueError(f"Failed to submit chat: {response.status_code}")
                    
            except httpx.TimeoutException:
                # Timeout is EXPECTED - return immediately with projectId
                logger.info("v0_chat_submission_timeout",
                           user_id=user_id,
                           product_id=product_id,
                           projectId=project_id,
                           note="Timeout expected - chat submitted in background")
                return {
                    "success": True,
                    "chat_id": None,  # Will be found via project polling
                    "projectId": project_id,
                    "project_id": project_id,
                    "immediate": False,
                    "note": "Chat submitted but timed out - will appear in project later"
                }
            except Exception as e:
                logger.error("v0_chat_submission_failed", error=str(e))
                raise ValueError(f"Failed to submit chat: {str(e)}")

    async def create_v0_project_with_api(
        self,
        v0_prompt: str,
        v0_api_key: Optional[str] = None,
        user_id: Optional[str] = None,
        product_id: Optional[str] = None,
        db: Optional[Any] = None,  # Database session for duplicate prevention
        create_new: bool = False,  # If False, reuse existing; if True, create new
        timeout_seconds: int = 600  # 10 minutes default, can be up to 900 (15 minutes)
    ) -> Dict[str, Any]:
        """
        Create a V0 project using the V0 Platform API with duplicate prevention and async polling.
        
        Features:
        - Checks for existing prototype (unless create_new=True)
        - Creates project with scope=mckinsey
        - Polls for completion with configurable timeout (10-15 minutes)
        - Returns chat_id, project_id, and status information
        """
        # Priority: passed parameter > instance variable > global settings
        api_key = v0_api_key
        key_source = "parameter"
        
        if not api_key:
            api_key = self.v0_api_key
            key_source = "instance"
        
        if not api_key:
            api_key = settings.v0_api_key
            key_source = "global_settings"
        
        if not api_key:
            raise ValueError("V0 API key is not configured. Please configure it in Settings.")
        
        # Step 1: Check for existing project_id in database (unless create_new=True)
        # If project_id exists, we'll submit new chat to same project (not create new project)
        existing_project_id = None
        if db and product_id and user_id and not create_new:
            try:
                from sqlalchemy import text
                project_query = text("""
                    SELECT v0_project_id
                    FROM design_mockups
                    WHERE product_id = :product_id 
                      AND user_id = :user_id 
                      AND provider = 'v0'
                      AND v0_project_id IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                
                project_result = await db.execute(project_query, {
                    "product_id": product_id,
                    "user_id": user_id
                })
                project_row = project_result.fetchone()
                
                if project_row:
                    existing_project_id = project_row[0]
                    logger.info("existing_project_id_found",
                               user_id=user_id,
                               product_id=product_id,
                               project_id=existing_project_id,
                               note="Will submit new chat to existing project")
            except Exception as db_error:
                logger.warning("database_check_failed",
                             error=str(db_error),
                             user_id=user_id,
                             product_id=product_id)
                # Continue with project creation if database check fails
        
        # Log key usage (without logging the actual key)
        logger.info("v0_api_key_usage",
                   user_id=user_id,
                   key_source=key_source,
                   key_length=len(api_key) if api_key else 0,
                   has_instance_key=bool(self.v0_api_key),
                   has_global_key=bool(settings.v0_api_key),
                   create_new=create_new)
        
        # Step 2: Get or create project (IMMEDIATE - < 1 second)
        # This MUST happen BEFORE submitting chat - matches test workflow
        project_id = existing_project_id
        
        # Get product name from database if available
        product_name = None
        if db and product_id:
            try:
                from sqlalchemy import text
                product_query = text("SELECT name FROM products WHERE id = :product_id")
                product_result = await db.execute(product_query, {"product_id": product_id})
                product_row = product_result.fetchone()
                if product_row:
                    product_name = product_row[0]
            except Exception as product_error:
                logger.warning("failed_to_fetch_product_name",
                             error=str(product_error),
                             product_id=product_id)
        
        # Use product name with product ID appended, or fallback to default
        if product_name:
            project_name = f"{product_name} - {product_id}"
        else:
            project_name = f"V0 Project {product_id[:8] if product_id else 'Default'}"
        
        project_url = None
        
        try:
            # If no existing project_id, get or create one using the same logic as test workflow
            if not project_id:
                async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                    
                    # Step 1: List existing projects - ONLY use user's private projects (not team/shared)
                    # According to V0 API docs: GET /v1/projects returns "all v0 projects in your workspace"
                    # Projects have a 'privacy' field: 'private' (user's own) or 'team' (shared with team)
                    # We MUST filter to only use 'private' projects to avoid using shared/team projects
                    projects = []
                    try:
                        # Get all projects from workspace (includes both private and team projects)
                        projects_resp = await client.get(
                            "https://api.v0.dev/v1/projects",
                            headers=headers
                        )
                        
                        if projects_resp.status_code == 200:
                            projects_data = projects_resp.json()
                            all_projects = projects_data.get("data", [])
                            
                            # CRITICAL: Filter to ONLY private projects (user's own, not team/shared)
                            # According to V0 API docs: privacy can be 'private' or 'team'
                            # We only want 'private' projects to ensure prompts go to user's own projects
                            private_projects = [p for p in all_projects if p.get("privacy") == "private"]
                            
                            logger.info("v0_projects_filtered_by_privacy",
                                       user_id=user_id,
                                       product_id=product_id,
                                       all_projects_count=len(all_projects),
                                       private_projects_count=len(private_projects),
                                       team_projects_count=len(all_projects) - len(private_projects))
                            
                            # CRITICAL: Filter to only projects linked to THIS SPECIFIC product_id in database
                            # This ensures each product has its own V0 project and prompts are posted correctly
                            # Projects must:
                            # 1. Be owned by the user (privacy: "private")
                            # 2. Be linked to this specific product_id in the database
                            # 3. Be in scope: "mckinsey" (if API returns scope field)
                            if db and product_id and user_id and len(private_projects) > 0:
                                try:
                                    from sqlalchemy import text as sql_text
                                    # Get V0 project IDs that are linked to THIS SPECIFIC product_id
                                    # This ensures we only use projects created for this product
                                    product_projects_query = sql_text("""
                                        SELECT DISTINCT v0_project_id
                                        FROM design_mockups
                                        WHERE product_id = :product_id
                                          AND user_id = :user_id
                                          AND provider = 'v0'
                                          AND v0_project_id IS NOT NULL
                                    """)
                                    product_projects_result = await db.execute(product_projects_query, {
                                        "product_id": product_id,
                                        "user_id": user_id
                                    })
                                    product_project_ids = {str(row[0]) for row in product_projects_result.fetchall()}
                                    
                                    # Filter to only private projects that:
                                    # 1. Are linked to this specific product_id in the database
                                    # 2. Have scope: "mckinsey" (if API returns scope field)
                                    filtered_projects = []
                                    for p in private_projects:
                                        project_id_str = str(p.get("id"))
                                        # Must be linked to this specific product_id in database
                                        if project_id_str in product_project_ids:
                                            # Check if scope is returned and matches (if available)
                                            project_scope = p.get("scope")
                                            if project_scope is None or project_scope == "mckinsey":
                                                filtered_projects.append(p)
                                    
                                    projects = filtered_projects
                                    
                                    logger.info("v0_projects_filtered_by_product_id",
                                               user_id=user_id,
                                               product_id=product_id,
                                               all_projects_count=len(all_projects),
                                               private_projects_count=len(private_projects),
                                               product_projects_count=len(projects),
                                               product_project_ids=list(product_project_ids),
                                               scope_filter="mckinsey")
                                except Exception as db_filter_error:
                                    logger.warning("v0_project_database_filter_failed",
                                                 error=str(db_filter_error),
                                                 user_id=user_id,
                                                 product_id=product_id,
                                                 fallback="no_projects")
                                    # If database filter fails, don't use any projects (safer than using wrong ones)
                                    # Projects must be in database linked to this product_id
                                    projects = []
                            else:
                                # No database/product_id/user_id - cannot safely filter, don't reuse projects
                                # Projects must be in database linked to this product_id
                                projects = []
                                logger.warning("v0_cannot_filter_projects_no_db",
                                             user_id=user_id,
                                             product_id=product_id,
                                             action="will_create_new",
                                             reason="projects_must_be_linked_to_product_id")
                        else:
                            logger.warning("v0_project_list_failed",
                                         status_code=projects_resp.status_code,
                                         user_id=user_id,
                                         product_id=product_id)
                    except Exception as list_error:
                        logger.warning("v0_project_list_failed",
                                     error=str(list_error),
                                     user_id=user_id,
                                     product_id=product_id)
                    
                    # Now process filtered projects (only user's own projects)
                    if isinstance(projects, list) and len(projects) > 0:
                        logger.info("v0_user_projects_found",
                                   user_id=user_id,
                                   product_id=product_id,
                                   count=len(projects))
                        
                        # Priority 1: Look for project with exact matching name
                        for p in projects:
                            if p.get("name") == project_name:
                                project_id = p.get("id")
                                # Get project URL from API response, or construct it
                                project_web_url = p.get("webUrl") or p.get("web_url")
                                project_url = project_web_url or (f"https://v0.dev/project/{project_id}" if project_id else None)
                                logger.info("v0_project_found_exact_name",
                                           user_id=user_id,
                                           product_id=product_id,
                                           project_id=project_id,
                                           name=project_name)
                                break
                        
                        # Priority 2: Look for projects containing the name
                        if not project_id:
                            for p in projects:
                                if project_name.lower() in p.get("name", "").lower():
                                    project_id = p.get("id")
                                    # Get project URL from API response, or construct it
                                    project_web_url = p.get("webUrl") or p.get("web_url")
                                    project_url = project_web_url or (f"https://v0.dev/project/{project_id}" if project_id else None)
                                    logger.info("v0_project_found_similar_name",
                                               user_id=user_id,
                                               product_id=product_id,
                                               project_id=project_id,
                                               name=p.get("name"))
                                    break
                        
                        # Priority 3: Use the most recent user project (first in list)
                        if not project_id:
                            project = projects[0]
                            project_id = project.get("id")
                            # Get project URL from API response, or construct it
                            project_web_url = project.get("webUrl") or project.get("web_url")
                            project_url = project_web_url or (f"https://v0.dev/project/{project_id}" if project_id else None)
                            logger.info("v0_project_reusing_most_recent_user_project",
                                       user_id=user_id,
                                       product_id=product_id,
                                       project_id=project_id,
                                       name=project.get("name", "Unnamed"))
                    
                    # Step 2: Create new project ONLY if NO projects exist at all
                    if not project_id:
                        logger.info("v0_creating_new_project",
                                   user_id=user_id,
                                   product_id=product_id,
                                   name=project_name)
                        # Create new project with scope: "mckinsey"
                        # Project will be private by default (user's own project)
                        # Scope ensures the project is in the mckinsey scope for proper isolation
                        create_resp = await client.post(
                            "https://api.v0.dev/v1/projects",
                            headers=headers,
                            json={
                                "name": project_name,
                                "scope": "mckinsey"  # Create project in mckinsey scope
                            }
                        )
                        
                        if create_resp.status_code in [200, 201]:
                            create_result = create_resp.json()
                            project_id = create_result.get("id")
                            # Get project URL from API response, or construct it
                            project_web_url = create_result.get("webUrl") or create_result.get("web_url")
                            project_url = project_web_url or (f"https://v0.dev/project/{project_id}" if project_id else None)
                            logger.info("v0_project_created",
                                       user_id=user_id,
                                       product_id=product_id,
                                       project_id=project_id,
                                       project_url=project_url)
                        else:
                            error_text = create_resp.text[:200] if create_resp.text else "No error text"
                            logger.error("v0_project_creation_failed",
                                       user_id=user_id,
                                       product_id=product_id,
                                       status_code=create_resp.status_code,
                                       error=error_text)
                            raise ValueError(f"Failed to create V0 project: {create_resp.status_code} - {error_text}")
                
                if not project_id:
                    raise ValueError("Failed to get or create V0 project - no project_id returned")
            else:
                logger.info("v0_using_existing_project_id",
                           user_id=user_id,
                           product_id=product_id,
                           project_id=project_id)
        
        except Exception as project_error:
            logger.error("project_creation_failed",
                         error=str(project_error),
                         user_id=user_id,
                         product_id=product_id,
                         error_type=type(project_error).__name__)
            raise ValueError(f"Failed to get or create V0 project: {str(project_error)}")
        
        # Step 3: Submit chat to project with SHORT timeout (returns immediately)
        # Use projectId (camelCase) parameter to associate with project
        # This happens AFTER project is created/retrieved (matches test workflow)
        if not project_id:
            raise ValueError("Cannot submit chat: project_id is required but was not created/retrieved")
        
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:  # Short timeout
            try:
                # Log the request
                logger.info("v0_api_request",
                           user_id=user_id,
                           endpoint="https://api.v0.dev/v1/chats",
                           prompt_length=len(v0_prompt) if v0_prompt else 0,
                           project_id=project_id,
                           key_source=key_source)
                
                # Submit chat with projectId parameter (camelCase)
                chat_payload = {
                    "message": v0_prompt,
                    "model": "v0-1.5-md",
                    "scope": "mckinsey"
                }
                
                if project_id:
                    chat_payload["projectId"] = project_id  # camelCase - correct format
                
                response = await client.post(
                    "https://api.v0.dev/v1/chats",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json=chat_payload
                )
                
                # Log response status
                logger.info("v0_api_response",
                           user_id=user_id,
                           status_code=response.status_code,
                           key_source=key_source)
                
                if response.status_code == 401:
                    logger.error("v0_api_auth_failed",
                               user_id=user_id,
                               status_code=401,
                               key_source=key_source,
                               response_text=response.text[:200] if response.text else "No response text")
                    raise ValueError("V0 API key is invalid or unauthorized. Please check your API key in Settings.")
                elif response.status_code == 402:
                    # Parse error response to get detailed message
                    error_text = response.text
                    error_detail = ""
                    try:
                        error_json = response.json()
                        error_detail = error_json.get("detail", error_json.get("error", {}).get("message", error_text))
                        if isinstance(error_detail, dict):
                            error_detail = error_detail.get("message", str(error_detail))
                    except:
                        error_detail = error_text
                    
                    logger.error("v0_api_credits_exhausted",
                               user_id=user_id,
                               status_code=402,
                               key_source=key_source,
                               key_prefix=api_key[:8] + "..." if api_key and len(api_key) > 8 else "N/A",
                               response_text=error_detail[:500] if error_detail else "No response text")
                    
                    # Check if it's actually a credit issue or another 402 error
                    if "out of credits" in error_detail.lower() or "credits" in error_detail.lower():
                        raise ValueError(f"V0 API error: You are out of credits. Add more or enable Auto-topup at https://v0.app/chat/settings/billing. Please check your V0 account credits at https://v0.app/chat/settings/billing. Error details: {error_detail}")
                    else:
                        # 402 might be for other reasons (rate limit, etc.)
                        raise ValueError(f"V0 API error: {response.status_code} - {error_detail}")
                elif response.status_code != 200 and response.status_code != 201:
                    logger.error("v0_api_error",
                               user_id=user_id,
                               status_code=response.status_code,
                               key_source=key_source,
                               response_text=response.text[:200] if response.text else "No response text")
                    error_text = response.text
                    try:
                        error_json = response.json()
                        error_text = error_json.get("error", {}).get("message", error_text)
                    except:
                        pass
                    raise ValueError(f"V0 API error: {response.status_code} - {error_text}")
                
                # Parse response
                try:
                    result = response.json()
                except Exception as json_error:
                    logger.error("v0_api_json_parse_error",
                               user_id=user_id,
                               error=str(json_error),
                               response_text=response.text[:500])
                    raise ValueError(f"V0 API returned invalid JSON. Response: {response.text[:200]}")
                
                chat_id = result.get("id") or result.get("chat_id")
                returned_project_id = result.get("projectId")  # camelCase in response
                
                # Use returned project_id if available, otherwise use the one we created/got
                final_project_id = returned_project_id or project_id
                
                web_url = result.get("webUrl") or result.get("web_url") or result.get("url")
                demo_url = result.get("demo") or result.get("demoUrl") or result.get("demo_url")
                files = result.get("files", [])
                code = "\n\n".join([f.get("content", "") for f in files if f.get("content")])
                
                if not chat_id:
                    logger.error("v0_api_no_chat_id",
                               user_id=user_id,
                               response_keys=list(result.keys()) if isinstance(result, dict) else "not_dict")
                    raise ValueError("No chat_id returned from V0 API. Response may be incomplete.")
                
                # If chat was created in different project, try to assign it
                if returned_project_id and returned_project_id != project_id and project_id:
                    try:
                        assign_resp = await client.patch(
                            f"https://api.v0.dev/v1/chats/{chat_id}",
                            headers={
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json"
                            },
                            json={"projectId": project_id}
                        )
                        if assign_resp.status_code in [200, 201, 204]:
                            final_project_id = project_id
                            logger.info("v0_chat_assigned_to_project",
                                       chat_id=chat_id,
                                       project_id=project_id)
                    except:
                        pass  # Assignment failed, use returned project_id
                
                logger.info("v0_chat_created",
                           chat_id=chat_id,
                           user_id=user_id,
                           product_id=product_id,
                           project_id=final_project_id,
                           has_demo=bool(demo_url),
                           has_web_url=bool(web_url),
                           num_files=len(files))
                
                # Return IMMEDIATELY with project_id - no waiting for generation
                # project_url should be the project page URL, not the chat/prototype URL
                # Construct project URL: https://v0.dev/project/{project_id}
                project_page_url = f"https://v0.dev/project/{final_project_id}" if final_project_id else None
                initial_status = "completed" if (demo_url or web_url or files) else "in_progress"
                project_name_result = result.get("name") or f"V0 Project {final_project_id[:8] if final_project_id else 'N/A'}"
                
                return {
                    "chat_id": chat_id,
                    "projectId": final_project_id,  # Use projectId (camelCase) to match V0 API format
                    "project_id": final_project_id,  # Keep for backward compatibility
                    "project_url": project_page_url,  # Project page URL, not chat/prototype URL
                    "web_url": web_url,  # Prototype web URL (if available)
                    "demo_url": demo_url,  # Prototype demo URL (if available)
                    "project_name": project_name_result,
                    "code": code,
                    "files": files,
                    "prompt": v0_prompt,
                    "image_url": None,
                    "thumbnail_url": None,
                    "project_status": initial_status,
                    "is_existing": False,
                    "metadata": {
                        "api_version": "v1",
                        "model_used": "v0-1.5-md",
                        "num_files": len(files),
                        "has_demo": demo_url is not None,
                        "has_web_url": web_url is not None,
                        "workflow": "project_based_immediate",
                        "key_source": key_source
                    }
                }
                
            except httpx.TimeoutException as timeout_error:
                # Timeout is EXPECTED - V0 API generates in background
                # Return immediately with project_id - user can check status later
                # CRITICAL: project_id MUST be set at this point (created in Step 2)
                # Construct project page URL
                project_page_url = f"https://v0.dev/project/{project_id}" if project_id else None
                if not project_id:
                    logger.error("v0_timeout_without_project_id",
                               user_id=user_id,
                               product_id=product_id,
                               error="Project creation failed but timeout occurred - this should not happen")
                    raise ValueError("V0 project creation failed. Cannot submit chat without project_id.")
                
                logger.info("v0_chat_submission_timeout",
                           user_id=user_id,
                           product_id=product_id,
                           projectId=project_id,
                           note="Timeout expected - chat is being generated in background, projectId is available")
                
                # Return immediately with projectId - chat will appear in project
                # Construct project page URL
                project_page_url = f"https://v0.dev/project/{project_id}" if project_id else None
                return {
                    "chat_id": None,  # Will be found via project polling
                    "projectId": project_id,  # Use projectId (camelCase) - MUST be set (created in Step 2)
                    "project_id": project_id,  # Keep for backward compatibility
                    "project_url": project_page_url,  # Project page URL, not chat URL
                    "web_url": None,
                    "demo_url": None,
                    "project_name": project_name,
                    "code": None,
                    "files": [],
                    "prompt": v0_prompt,
                    "image_url": None,
                    "thumbnail_url": None,
                    "project_status": "in_progress",
                    "is_existing": False,
                    "metadata": {
                        "api_version": "v1",
                        "model_used": "v0-1.5-md",
                        "workflow": "project_based_timeout",
                        "key_source": key_source,
                        "note": "Chat submitted but timed out - check status later via projectId"
                    }
                }
            except httpx.RequestError as e:
                error_msg = str(e) if str(e) else f"{type(e).__name__}: Unable to connect to V0 API"
                logger.error("v0_api_connection_error",
                           user_id=user_id,
                           error=error_msg,
                           error_type=type(e).__name__)
                raise ValueError(f"V0 API connection error: {error_msg}")
            except httpx.HTTPStatusError as e:
                error_msg = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
                logger.error("v0_api_http_error",
                           user_id=user_id,
                           status_code=e.response.status_code if e.response else None,
                           error=error_msg)
                raise ValueError(f"V0 API HTTP error: {error_msg}")
            except ValueError:
                # Re-raise ValueError as-is (these are our custom errors)
                raise
            except Exception as e:
                logger.error("v0_project_creation_error", 
                           error=str(e), 
                           error_type=type(e).__name__,
                           api_key_length=len(api_key) if api_key else 0)
                raise ValueError(f"V0 API error: {str(e)}")
    
    async def check_v0_project_status(
        self,
        project_id: str,
        v0_api_key: Optional[str] = None,
        user_id: Optional[str] = None,
        product_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check status of V0 project by getting latest chat and checking its status.
        This is used for the "Check Status" button - can be called multiple times.
        
        Handles both project IDs and chat IDs/URLs:
        - If project_id is a project ID: Gets project, finds latest chat, checks chat status
        - If project_id is a chat URL/ID: Directly checks chat status
        
        Returns:
            - projectId: The project ID (camelCase to match V0 API format)
            - project_id: The project ID (snake_case for backward compatibility)
            - chat_id: Latest chat ID in the project
            - project_status: "completed", "in_progress", or "unknown"
            - project_url: URL to the prototype (if completed)
            - web_url: Web URL
            - demo_url: Demo URL
            - is_complete: Boolean indicating if prototype is ready
        """
        api_key = v0_api_key or self.v0_api_key or settings.v0_api_key
        
        if not api_key:
            raise ValueError("V0 API key is not configured")
        
        if not project_id:
            raise ValueError("project_id is required")
        
        # Detect if input is a chat URL or chat ID
        # Chat URLs: https://v0.app/chat/{slug} or https://v0.dev/chat/{chat_id}
        # Project URLs: https://v0.dev/project/{project_id} or https://v0.app/project/{project_id}
        chat_id_from_input = None
        actual_project_id = project_id
        
        # Extract chat ID or project ID from URL if it's a URL
        if project_id.startswith("http"):
            if "/chat/" in project_id:
                # Extract chat ID from URL: https://v0.app/chat/{slug} or https://v0.dev/chat/{chat_id}
                # NOTE: The slug in the URL might not be the actual chat ID - we'll need to get it from the chat response
                chat_id_from_input = project_id.split("/chat/")[-1].split("?")[0].split("#")[0]
                logger.warning("v0_chat_url_detected_in_project_id",
                             original_input=project_id,
                             extracted_chat_id=chat_id_from_input,
                             message="Chat URL passed as project_id - will try to get project_id from chat data")
                # Don't use chat_id_from_input directly - instead, we'll get the chat and extract project_id from it
                # Set actual_project_id to None so we go through the chat lookup path
                actual_project_id = None
            elif "/project/" in project_id:
                # Extract project ID from URL: https://v0.dev/project/{project_id} or https://v0.app/project/{project_id}
                actual_project_id = project_id.split("/project/")[-1].split("?")[0].split("#")[0]
                logger.info("v0_project_url_detected",
                           original_input=project_id,
                           extracted_project_id=actual_project_id)
        
        # Use longer timeout for chat status checks (60 seconds)
        async with httpx.AsyncClient(timeout=60.0, verify=False) as client:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            try:
                # If we detected a chat URL in the input, we need to get the project_id from the chat
                # Chat URLs contain slugs, not actual chat IDs, so we can't use them directly
                # Instead, we should look up the project using the project_id from the database
                # If we don't have a project_id, we'll need to list chats or use a different approach
                if chat_id_from_input and not actual_project_id:
                    logger.warning("v0_chat_url_passed_as_project_id",
                                 chat_url=project_id,
                                 extracted_slug=chat_id_from_input,
                                 user_id=user_id,
                                 product_id=product_id,
                                 message="Chat URL passed as project_id - cannot use slug directly with API. Need project_id from database.")
                    # The slug in the URL is not the actual chat ID - we can't use it with the API
                    # We need the actual project_id from the database
                    raise ValueError(
                        f"Chat URL passed as project_id: {project_id}. "
                        f"The slug '{chat_id_from_input}' is not a valid chat ID for the V0 API. "
                        f"Please ensure v0_project_id is stored in the database, not the chat URL. "
                        f"Project URLs should be in format: https://v0.dev/project/{{project_id}}"
                    )
                
                # Otherwise, treat as project_id and get project first
                # Step 1: Get project to find latest chat
                project_resp = await client.get(
                    f"https://api.v0.dev/v1/projects/{actual_project_id}",
                    headers=headers
                )
                
                if project_resp.status_code == 404:
                    # Even if project not found, construct project URL for reference
                    project_url = f"https://v0.dev/project/{actual_project_id}" if actual_project_id else None
                    return {
                        "projectId": actual_project_id,  # Use projectId (camelCase)
                        "project_id": actual_project_id,  # Keep for backward compatibility
                        "chat_id": None,
                        "project_status": "unknown",
                        "project_url": project_url,  # Return project URL even if not found
                        "web_url": None,
                        "demo_url": None,
                        "is_complete": False,
                        "error": "Project not found"
                    }
                
                if project_resp.status_code != 200:
                    raise ValueError(f"Failed to get project: {project_resp.status_code}")
                
                project_data = project_resp.json()
                chats = project_data.get("chats", [])
                
                # Get project URL from project data (this is the project page, not the chat/prototype URL)
                project_web_url = project_data.get("webUrl") or project_data.get("web_url")
                # Construct project URL: Use v0.dev for project URLs (consistent with API)
                # Note: v0.app is the new frontend URL, but project URLs should use v0.dev
                if project_web_url and "/project/" in project_web_url:
                    project_url = project_web_url
                else:
                    project_url = f"https://v0.dev/project/{actual_project_id}"
                
                if not chats or len(chats) == 0:
                    return {
                        "projectId": actual_project_id,  # Use projectId (camelCase)
                        "project_id": actual_project_id,  # Keep for backward compatibility
                        "chat_id": None,
                        "project_status": "pending",
                        "project_url": project_url,  # Return project URL, not chat URL
                        "web_url": None,
                        "demo_url": None,
                        "is_complete": False,
                        "note": "No chats found in project"
                    }
                
                # Get latest chat (first in list, usually sorted by date)
                latest_chat = chats[0]
                chat_id = latest_chat.get("id")
                
                if not chat_id:
                    return {
                        "projectId": actual_project_id,  # Use projectId (camelCase)
                        "project_id": actual_project_id,  # Keep for backward compatibility
                        "chat_id": None,
                        "project_status": "unknown",
                        "project_url": project_url,  # Return project URL, not chat URL
                        "web_url": None,
                        "demo_url": None,
                        "is_complete": False,
                        "error": "No chat ID found"
                    }
                
                # Step 2: Check chat status (with longer timeout)
                chat_resp = await client.get(
                    f"https://api.v0.dev/v1/chats/{chat_id}",
                    headers=headers
                )
                
                if chat_resp.status_code != 200:
                    return {
                        "projectId": actual_project_id,  # Use projectId (camelCase)
                        "project_id": actual_project_id,  # Keep for backward compatibility
                        "chat_id": chat_id,
                        "project_status": "unknown",
                        "project_url": project_url,  # Return project URL, not chat URL
                        "web_url": None,
                        "demo_url": None,
                        "is_complete": False,
                        "error": f"Failed to get chat: {chat_resp.status_code}"
                    }
                
                chat_data = chat_resp.json()
                web_url = chat_data.get("webUrl") or chat_data.get("web_url")
                demo_url = chat_data.get("demo") or chat_data.get("demoUrl") or chat_data.get("demo_url")
                files = chat_data.get("files", [])
                
                # Determine status
                is_complete = bool(demo_url or web_url or (files and len(files) > 0))
                project_status = "completed" if is_complete else "in_progress"
                # project_url should be the project page URL, not the chat/prototype URL
                # Keep project_url as the project page, and return demo_url/web_url separately for the prototype
                
                logger.info("v0_status_checked",
                           projectId=actual_project_id,
                           chat_id=chat_id,
                           status=project_status,
                           is_complete=is_complete,
                           user_id=user_id,
                           product_id=product_id)
                
                return {
                    "projectId": actual_project_id,  # Use projectId (camelCase) to match V0 API format
                    "project_id": actual_project_id,  # Keep for backward compatibility
                    "chat_id": chat_id,
                    "project_status": project_status,
                    "project_url": project_url,  # This is the project page URL (https://v0.dev/project/{project_id})
                    "web_url": web_url,  # Prototype web URL (if available)
                    "demo_url": demo_url,  # Prototype demo URL (if available)
                    "is_complete": is_complete,
                    "num_files": len(files),
                    "files": files
                }
                
            except httpx.RequestError as e:
                # Provide more descriptive error message
                error_msg = str(e) if str(e) else f"{e.__class__.__name__}"
                if hasattr(e, 'request') and e.request:
                    error_msg += f" (URL: {e.request.url})"
                logger.error("v0_status_check_error",
                           projectId=actual_project_id or chat_id_from_input or project_id,
                           chat_id=chat_id_from_input,
                           error=error_msg,
                           error_type=e.__class__.__name__,
                           user_id=user_id,
                           product_id=product_id)
                raise ValueError(f"V0 API connection error: {error_msg}")
            except Exception as e:
                error_msg = str(e) if str(e) else f"{e.__class__.__name__}: Unknown error occurred"
                logger.error("v0_status_check_error",
                           projectId=actual_project_id or chat_id_from_input or project_id,
                           chat_id=chat_id_from_input,
                           error=error_msg,
                           error_type=type(e).__name__,
                           user_id=user_id,
                           product_id=product_id)
                raise ValueError(f"V0 status check error: {error_msg}")
    
    async def poll_and_update_prototype_status(
        self,
        api_key: str,
        chat_id: str,
        mockup_id: str,
        db: Any,
        timeout_seconds: int = 900
    ) -> None:
        """
        Background task to poll V0 chat status and update database.
        This runs in the background after the API returns immediately.
        """
        try:
            logger.info("v0_background_polling_start",
                       chat_id=chat_id,
                       mockup_id=mockup_id,
                       timeout_seconds=timeout_seconds)
            
            poll_result = await self.poll_v0_chat_status(
                api_key,
                chat_id,
                max_polls=int(timeout_seconds / 15),  # Poll every 15 seconds
                poll_interval=15.0
            )
            
            # Get project_id from database to construct project URL
            project_id_from_db = None
            try:
                query = text("""
                    SELECT v0_project_id
                    FROM design_mockups
                    WHERE id = :mockup_id
                    LIMIT 1
                """)
                result = await db.execute(query, {"mockup_id": mockup_id})
                row = result.fetchone()
                if row:
                    project_id_from_db = row[0]
            except Exception as db_error:
                logger.warning("failed_to_get_project_id_for_url", error=str(db_error))
            
            # Update database with final status
            if poll_result.get("ready"):
                final_web_url = poll_result.get("web_url")
                final_demo_url = poll_result.get("demo_url")
                # project_url should be the project page URL, not the chat/prototype URL
                # Construct project page URL: https://v0.dev/project/{project_id}
                final_project_url = f"https://v0.dev/project/{project_id_from_db}" if project_id_from_db else None
                
                final_status = "completed"
                
                logger.info("v0_background_polling_completed",
                           chat_id=chat_id,
                           mockup_id=mockup_id,
                           project_url=final_project_url,
                           demo_url=final_demo_url,
                           web_url=final_web_url,
                           poll_count=poll_result.get("poll_count", 0),
                           elapsed_seconds=poll_result.get("elapsed_seconds", 0))
            else:
                # project_url should be the project page URL, not the chat/prototype URL
                final_project_url = f"https://v0.dev/project/{project_id_from_db}" if project_id_from_db else None
                
                final_status = "timeout" if poll_result.get("timeout") else "in_progress"
                
                logger.warning("v0_background_polling_timeout",
                             chat_id=chat_id,
                             mockup_id=mockup_id,
                             status=final_status,
                             poll_count=poll_result.get("poll_count", 0),
                             elapsed_seconds=poll_result.get("elapsed_seconds", 0))
            
            # Update database
            try:
                from sqlalchemy import text
                update_query = text("""
                    UPDATE design_mockups
                    SET project_status = :status,
                        project_url = :project_url,
                        updated_at = now()
                    WHERE id = :id
                """)
                await db.execute(update_query, {
                    "id": mockup_id,
                    "status": final_status,
                    "project_url": final_project_url
                })
                await db.commit()
                logger.info("v0_database_updated",
                           mockup_id=mockup_id,
                           status=final_status)
            except Exception as update_error:
                logger.error("v0_database_update_failed",
                           mockup_id=mockup_id,
                           error=str(update_error))
        except Exception as e:
            logger.error("v0_background_polling_error",
                        chat_id=chat_id,
                        mockup_id=mockup_id,
                        error=str(e))

