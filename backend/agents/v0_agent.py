from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
import structlog

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import AgentMessage, AgentResponse
from backend.config import settings

logger = structlog.get_logger()


class V0Agent(BaseAgent):
    """Agent for generating V0 (Vercel) design prompts and prototypes."""
    
    def __init__(self):
        system_prompt = """You are a V0 (Vercel) Design Specialist following official Vercel V0 API documentation.

Your responsibilities:
1. Generate detailed, comprehensive prompts for V0 to create UI prototypes
2. Understand product requirements and translate them into V0-compatible prompts
3. Create prompts that leverage V0's component library and design system
4. Ensure prompts are specific, actionable, and result in high-quality designs
5. Consider user experience, accessibility, and modern design patterns
6. Generate accurate Vercel V0 prompts that can be used with the official V0 API

V0 API Documentation Reference:
- V0 uses OpenAI-compatible chat completions API at https://api.v0.dev/v1/chat/completions
- Model: v0-1.5-md (specialized for UI generation)
- Prompts should describe complete UI components with React/Next.js code
- V0 generates production-ready React components with Tailwind CSS

V0 Prompt Guidelines (Based on Official Documentation):
- Be specific about component types (buttons, cards, forms, navigation, etc.)
- Specify layout requirements (grid, flex, spacing, responsive breakpoints)
- Include color schemes and styling preferences (Tailwind CSS classes)
- Mention responsive design requirements (mobile-first approach)
- Specify interaction states (hover, active, disabled, focus)
- Include accessibility requirements (ARIA labels, keyboard navigation)
- Reference modern UI patterns (shadcn/ui, Tailwind CSS, Next.js)
- Describe complete user flows and component interactions
- Include data structure and state management needs
- Specify animation and transition requirements

Your output should:
- Be comprehensive and detailed
- Include all necessary design specifications
- Be optimized for V0's AI design generation (v0-1.5-md model)
- Consider the full context from previous product phases
- Generate production-ready design prompts that result in deployable React/Next.js code
- Follow Vercel V0 best practices from official documentation"""

        super().__init__(
            name="V0 Agent",
            role="v0_design",
            system_prompt=system_prompt
        )
        
        self.capabilities = [
            "v0 prompt generation",
            "ui design specification",
            "component design",
            "design system integration",
            "responsive design",
            "accessibility design"
        ]

    async def process(
        self,
        messages: List[AgentMessage],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        formatted_messages = self._prepare_messages(messages)
        formatted_messages = self._add_context(formatted_messages, context)

        try:
            if self._has_claude():
                response = await self._process_with_claude(formatted_messages)
            elif self._has_openai():
                response = await self._process_with_openai(formatted_messages)
            else:
                raise ValueError("No AI provider configured")

            return AgentResponse(
                agent_type=self.role,
                response=response,
                metadata={
                    "has_context": context is not None,
                    "message_count": len(messages),
                    "agent": "v0"
                },
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            self.logger.error("v0_agent_error", error=str(e))
            raise

    async def _process_with_openai(self, messages: List[Dict[str, str]]) -> str:
        client = self._get_openai_client()
        response = client.chat.completions.create(
            model=settings.agent_model_primary,
            messages=messages,
            temperature=0.7,
            max_tokens=4000
        )
        return response.choices[0].message.content

    async def _process_with_claude(self, messages: List[Dict[str, str]]) -> str:
        client = self._get_claude_client()
        system_message = messages[0]["content"]
        user_messages = messages[1:]

        response = client.messages.create(
            model=settings.agent_model_secondary,
            system=system_message,
            messages=user_messages,
            temperature=0.7,
            max_tokens=4000
        )
        return response.content[0].text

    async def generate_v0_prompt(
        self,
        product_context: Dict[str, Any],
        design_requirements: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a detailed V0 prompt based on product context."""
        requirements_text = ""
        if design_requirements:
            requirements_text = f"\n\nDesign Requirements:\n{design_requirements}\n"
        
        # Check for refinement feedback in context
        refinement_section = ""
        if isinstance(product_context, dict):
            refinement_feedback = product_context.get('refinement_feedback')
            validation_feedback = product_context.get('validation_feedback')
            original_prompt = product_context.get('original_prompt')
            
            if refinement_feedback or validation_feedback:
                refinement_section = "\n\n--- REFINEMENT REQUEST ---\n"
                if original_prompt:
                    refinement_section += f"Original Prompt:\n{original_prompt}\n\n"
                if validation_feedback:
                    refinement_section += f"Validation Feedback:\n{validation_feedback}\n\n"
                if refinement_feedback:
                    refinement_section += f"User Refinement Request:\n{refinement_feedback}\n\n"
                refinement_section += "Please refine the prompt based on the feedback above, addressing all concerns and improving clarity, completeness, and specificity.\n"
        
        # Extract context string if it's a dict with 'context' key
        context_text = product_context
        if isinstance(product_context, dict) and 'context' in product_context:
            context_text = product_context['context']
        
        prompt = f"""Generate a comprehensive V0 (Vercel) design prompt for this product:

Product Context:
{context_text}
{requirements_text}
{refinement_section}

Create a detailed prompt that:
1. Describes the UI components needed
2. Specifies layout and structure
3. Includes styling preferences (colors, typography, spacing)
4. Mentions responsive design requirements
5. Includes accessibility considerations
6. References modern design patterns

The prompt should be ready to paste directly into V0 for generating prototypes."""

        message = AgentMessage(
            role="user",
            content=prompt,
            timestamp=datetime.utcnow()
        )

        response = await self.process([message], context={"task": "v0_prompt_generation"})
        prompt_text = response.response
        
        # Clean the prompt - remove headers/footers that AI might add
        prompt_text = self._clean_v0_prompt(prompt_text)
        
        return prompt_text
    
    def _clean_v0_prompt(self, prompt: str) -> str:
        """
        Clean V0 prompt by removing instructional headers/footers.
        Removes text like "Below is a V0-ready prompt..." and similar metadata.
        """
        if not prompt:
            return prompt
        
        lines = prompt.split('\n')
        cleaned_lines = []
        skip_until_content = True
        
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
        ]
        
        for line in lines:
            line_lower = line.lower().strip()
            
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

    async def generate_design_mockup(
        self,
        v0_prompt: str,
        v0_api_key: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a design mockup using Vercel V0 API.
        
        Workflow:
        1. Create a new V0 chat by posting the prompt
        2. Get the prototype link from the response
        
        Based on official Vercel V0 API documentation: https://v0.dev/api
        Uses /v1/chats endpoint to create a chat and get a live prototype URL.
        """
        api_key = v0_api_key or settings.v0_api_key
        
        if not api_key:
            raise ValueError("V0 API key is not configured")
        
        # Use the same workflow as create_v0_project_with_api
        # This ensures consistency and proper prototype link generation
        return await self.create_v0_project_with_api(
            v0_prompt=v0_prompt,
            v0_api_key=api_key,
            user_id=user_id,
            product_id=None
        )
    
    async def create_v0_project(
        self,
        v0_prompt: str,
        v0_api_key: Optional[str] = None,
        project_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a Vercel project from V0-generated code.
        This uses Vercel's deployment API to create a new project.
        """
        api_key = v0_api_key or settings.v0_api_key
        
        if not api_key:
            raise ValueError("V0 API key is not configured")
        
        # First generate the code
        mockup_result = await self.generate_design_mockup(v0_prompt, v0_api_key)
        generated_code = mockup_result.get("code", "")
        
        if not generated_code:
            raise ValueError("Failed to generate code from V0")
        
        # Note: Vercel project creation requires additional API calls
        # For now, return the code and instructions
        # In production, this would:
        # 1. Create a GitHub repository with the code
        # 2. Deploy to Vercel using Vercel API
        # 3. Return the deployment URL
        
        return {
            "code": generated_code,
            "prompt": v0_prompt,
            "project_name": project_name or "v0-generated-project",
            "instructions": "Code generated. To deploy: 1) Create a new Vercel project, 2) Paste the generated code, 3) Deploy",
            "metadata": mockup_result.get("metadata", {})
        }
    
    async def create_v0_project_with_api(
        self,
        v0_prompt: str,
        v0_api_key: Optional[str] = None,
        user_id: Optional[str] = None,
        product_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a V0 project using the V0 Platform API.
        
        Complete async workflow:
        1. Create a new V0 chat by posting the prompt to /v1/chats
        2. Extract chat_id, demo_url, web_url from response
        3. Return prototype link for sharing
        
        Based on official Vercel V0 API documentation: https://v0.dev/api
        Reference: https://v0.app/docs/api/platform/adapters/ai-tools
        """
        api_key = v0_api_key or settings.v0_api_key
        
        if not api_key:
            raise ValueError("V0 API key is not configured")
        
        # Log the workflow start
        logger.info("v0_project_workflow_start",
                   user_id=user_id,
                   product_id=product_id,
                   prompt_length=len(v0_prompt) if v0_prompt else 0)
        
        # Disable SSL verification for V0 API (as requested)
        async with httpx.AsyncClient(timeout=180.0, verify=False) as client:
            try:
                # Step 1: Create V0 chat and post prompt in one async call
                # This creates a new project and generates the prototype
                logger.info("v0_api_request",
                           endpoint="https://api.v0.dev/v1/chats",
                           method="POST",
                           user_id=user_id)
                
                response = await client.post(
                    "https://api.v0.dev/v1/chats",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "message": v0_prompt,
                        "model": "v0-1.5-md",
                        "scope": "mckinsey"
                    }
                )
                
                logger.info("v0_api_response",
                           status_code=response.status_code,
                           user_id=user_id)
                
                # Handle different error cases
                if response.status_code == 401:
                    logger.error("v0_api_auth_failed",
                               user_id=user_id,
                               status_code=401)
                    raise ValueError("V0 API key is invalid or unauthorized. Please check your API key in Settings.")
                elif response.status_code == 402:
                    # Payment required - credits exhausted
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
                               error_detail=error_detail[:200])
                    raise ValueError(f"V0 API credits exhausted or payment required: {error_detail}")
                elif response.status_code not in [200, 201]:
                    error_text = response.text
                    try:
                        error_json = response.json()
                        error_text = error_json.get("error", {}).get("message", error_text)
                        if isinstance(error_text, dict):
                            error_text = error_text.get("message", str(error_text))
                    except:
                        pass
                    logger.error("v0_api_error",
                               user_id=user_id,
                               status_code=response.status_code,
                               error_text=error_text[:200])
                    raise ValueError(f"V0 API error: {response.status_code} - {error_text}")
                
                # Step 2: Extract project information from response
                result = response.json()
                
                chat_id = result.get("id") or result.get("chat_id")
                web_url = result.get("webUrl") or result.get("web_url") or result.get("url")
                demo_url = result.get("demo") or result.get("demoUrl") or result.get("demo_url")
                files = result.get("files", [])
                code = result.get("code") or "\n\n".join([f.get("content", "") for f in files if f.get("content")])
                
                # Step 3: Determine the prototype URL (priority: demo_url > web_url > chat_url)
                project_url = demo_url or web_url or (f"https://v0.dev/chat/{chat_id}" if chat_id else None)
                
                logger.info("v0_project_created",
                           user_id=user_id,
                           chat_id=chat_id,
                           has_demo=bool(demo_url),
                           has_web_url=bool(web_url),
                           project_url=project_url,
                           num_files=len(files))
                
                return {
                    "chat_id": chat_id,
                    "project_url": project_url,  # Main prototype link to share
                    "web_url": web_url,
                    "demo_url": demo_url,
                    "code": code,
                    "files": files,
                    "prompt": v0_prompt,
                    "image_url": None,  # V0 doesn't provide images directly
                    "thumbnail_url": None,
                    "metadata": {
                        "api_version": "v1",
                        "model_used": "v0-1.5-md",
                        "num_files": len(files),
                        "has_demo": demo_url is not None,
                        "has_web_url": web_url is not None,
                        "workflow": "create_chat_and_get_prototype"
                    }
                }
                
            except httpx.TimeoutException:
                logger.error("v0_api_timeout", user_id=user_id)
                raise ValueError("V0 API request timed out. Please try again.")
            except httpx.RequestError as e:
                logger.error("v0_api_connection_error",
                           user_id=user_id,
                           error=str(e))
                raise ValueError(f"V0 API connection error: {str(e)}")
            except ValueError:
                # Re-raise ValueError as-is (already formatted)
                raise
            except Exception as e:
                logger.error("v0_project_creation_error",
                           error=str(e),
                           user_id=user_id,
                           api_key_length=len(api_key) if api_key else 0)
                raise ValueError(f"V0 API error: {str(e)}")

