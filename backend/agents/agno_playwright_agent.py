"""
Playwright Agent using Agno Framework
Provides end-to-end Lovable.dev prototype generation using Playwright browser automation.
Uses the test-workflow approach for content storage and interaction.
"""
import asyncio
import os
import urllib.parse
import time
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import structlog
import json

from backend.agents.agno_base_agent import AgnoBaseAgent
from backend.models.schemas import AgentMessage, AgentResponse
from backend.config import settings
from backend.services.provider_registry import provider_registry

logger = structlog.get_logger()

# Try to import required libraries
try:
    from agno.tools import tool
    AGNO_TOOLS_AVAILABLE = True
except ImportError:
    AGNO_TOOLS_AVAILABLE = False
    logger.warning("agno_tools_not_available", message="Agno tools not available")

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logger.warning("httpx_not_available", message="httpx not available")

try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False
    logger.warning("beautifulsoup4_not_available", message="beautifulsoup4 not available")

try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("playwright_not_available", message="playwright not available")

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("openai_not_available", message="openai not available")


class LovableDocumentationCrawler:
    """Deep crawler for Lovable.dev documentation (from test-workflow)."""
    
    def __init__(self):
        self.base_url = "https://docs.lovable.dev"
        self.start_url = "https://docs.lovable.dev/integrations/build-with-url"
        self.visited_urls = set()
        self.documentation_content = []
        
    async def crawl_page(self, url: str, client: httpx.AsyncClient) -> Optional[Dict[str, Any]]:
        """Crawl a single page and extract content."""
        if url in self.visited_urls:
            return None
            
        self.visited_urls.add(url)
        
        try:
            logger.info("crawling_page", url=url)
            response = await client.get(url, timeout=30.0, follow_redirects=True)
            response.raise_for_status()
            
            if BEAUTIFULSOUP_AVAILABLE:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract main content
                content = ""
                main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
                if main_content:
                    content = main_content.get_text(separator='\n', strip=True)
                else:
                    content = soup.get_text(separator='\n', strip=True)
                
                # Extract title
                title = ""
                title_tag = soup.find('title') or soup.find('h1')
                if title_tag:
                    title = title_tag.get_text(strip=True)
                
                # Extract links for further crawling
                links = []
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if href.startswith('/'):
                        full_url = f"{self.base_url}{href}"
                    elif href.startswith('http') and self.base_url in href:
                        full_url = href
                    else:
                        continue
                    
                    if '/integrations/' in full_url or '/docs/' in full_url:
                        links.append(full_url)
                
                return {
                    "url": url,
                    "title": title,
                    "content": content,
                    "links": links,
                    "html_length": len(response.text)
                }
            else:
                return {
                    "url": url,
                    "title": "",
                    "content": response.text[:50000],
                    "links": [],
                    "html_length": len(response.text)
                }
                
        except Exception as e:
            logger.warning("crawl_page_error", url=url, error=str(e))
            return None
    
    async def deep_crawl(self, max_pages: int = 20) -> List[Dict[str, Any]]:
        """Perform deep crawl of Lovable.dev documentation."""
        if not HTTPX_AVAILABLE:
            logger.error("httpx_not_available_for_crawling")
            return []
        
        logger.info("starting_deep_crawl", start_url=self.start_url, max_pages=max_pages)
        
        async with httpx.AsyncClient(timeout=30.0, verify=True) as client:
            to_crawl = [self.start_url]
            all_content = []
            
            while to_crawl and len(all_content) < max_pages:
                current_url = to_crawl.pop(0)
                page_data = await self.crawl_page(current_url, client)
                if page_data:
                    all_content.append(page_data)
                    for link in page_data.get("links", [])[:5]:
                        if link not in self.visited_urls and link not in to_crawl:
                            to_crawl.append(link)
                    await asyncio.sleep(1)
            
            self.documentation_content = all_content
            logger.info("crawl_complete", pages_crawled=len(all_content))
            return all_content
    
    def get_combined_content(self) -> str:
        """Get combined content from all crawled pages."""
        combined = []
        for page in self.documentation_content:
            combined.append(f"# {page.get('title', 'Untitled')}\n")
            combined.append(f"URL: {page.get('url')}\n")
            combined.append(page.get('content', ''))
            combined.append("\n\n" + "="*80 + "\n\n")
        return "\n".join(combined)


class LovablePromptGenerator:
    """Generate Lovable.dev prompts using OpenAI (from test-workflow)."""
    
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def generate_prompt(
        self, 
        product_description: str,
        documentation_content: Optional[str] = None
    ) -> str:
        """Generate a Lovable.dev-ready prompt using OpenAI."""
        
        system_prompt = """You are an expert at creating prompts for Lovable.dev, a platform that generates web applications.

Lovable.dev creates React/Next.js applications with modern UI components. Your prompts should:
1. Clearly describe the application features and functionality
2. Specify UI components needed (buttons, forms, tables, charts, etc.)
3. Include layout and navigation structure
4. Mention styling preferences if relevant
5. Be concise but comprehensive (aim for 200-500 words)

Return ONLY the prompt content, no headers, footers, or meta-commentary."""

        user_prompt = f"""Create a detailed Lovable.dev prompt for: {product_description}"""
        
        if documentation_content:
            user_prompt += f"""

Based on the following Lovable.dev documentation:
{documentation_content[:10000]}"""
        
        try:
            from backend.config import get_openai_completion_param
            model = "gpt-4o-mini"
            param_name = get_openai_completion_param(model)
            completion_params = {param_name: 1000}
            
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                **completion_params
            )
            
            prompt = response.choices[0].message.content.strip()
            return self._clean_prompt(prompt)
        except Exception as e:
            logger.error("prompt_generation_error", error=str(e))
            raise
    
    def _clean_prompt(self, prompt: str) -> str:
        """Clean prompt by removing instructional headers/footers."""
        if not prompt:
            return prompt
        
        lines = prompt.split('\n')
        cleaned_lines = []
        skip_patterns = [
            "below is a lovable.dev prompt",
            "here is a prompt",
            "lovable.dev prompt:",
            "prompt for lovable.dev:",
            "you can use this prompt",
            "copy this prompt",
        ]
        
        for line in lines:
            line_lower = line.lower().strip()
            should_skip = any(pattern in line_lower for pattern in skip_patterns)
            if not should_skip:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip() or prompt


class LovablePrototypeGenerator:
    """Generate Lovable.dev prototypes and retrieve links (from test-workflow)."""
    
    def __init__(self):
        self.base_url = "https://lovable.dev"
        self.autosubmit_url = "https://lovable.dev/?autosubmit=true#"
    
    def build_lovable_url(self, prompt: str, images: Optional[List[str]] = None) -> str:
        """Build Lovable.dev URL with prompt and optional images."""
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"{self.autosubmit_url}prompt={encoded_prompt}"
        
        if images:
            for img_url in images[:10]:
                encoded_img = urllib.parse.quote(img_url)
                url += f"&images={encoded_img}"
        
        return url
    
    async def generate_prototype_with_browser(
        self, 
        prompt: str,
        images: Optional[List[str]] = None,
        timeout: int = 300,
        headless: bool = False
    ) -> Dict[str, Any]:
        """Generate prototype using browser automation to retrieve the link."""
        if not PLAYWRIGHT_AVAILABLE:
            raise ValueError("Playwright not available. Install with: pip install playwright && playwright install")
        
        lovable_url = self.build_lovable_url(prompt, images)
        
        logger.info("opening_lovable_browser", url_length=len(lovable_url), prompt_length=len(prompt))
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()
            
            try:
                logger.info("navigating_to_lovable", url=lovable_url[:100])
                await page.goto(lovable_url, wait_until='networkidle', timeout=60000)
                
                await asyncio.sleep(5)
                
                # Check if login is required
                login_indicators = [
                    'sign in', 'sign up', 'login', 'log in', 
                    'email', 'password', 'continue with'
                ]
                page_text = await page.inner_text('body')
                is_login_page = any(indicator in page_text.lower() for indicator in login_indicators)
                
                if is_login_page:
                    logger.warning("login_required", message="Waiting for manual login")
                    for i in range(60):
                        await asyncio.sleep(5)
                        current_url = page.url
                        if 'lovable.dev' in current_url and 'login' not in current_url.lower() and 'sign' not in current_url.lower():
                            logger.info("login_detected")
                            break
                
                await asyncio.sleep(10)
                
                logger.info("monitoring_prototype_completion")
                start_time = time.time()
                prototype_url = None
                project_id = None
                
                while time.time() - start_time < timeout:
                    current_url = page.url
                    
                    if '/project/' in current_url or '/app/' in current_url or '/p/' in current_url:
                        parts = current_url.split('/')
                        for i, part in enumerate(parts):
                            if part in ['project', 'app', 'p'] and i + 1 < len(parts):
                                project_id = parts[i + 1]
                                prototype_url = current_url
                                break
                    
                    try:
                        view_buttons = await page.query_selector_all(
                            'a[href*="/project/"], a[href*="/app/"], a[href*="/p/"], '
                            'button:has-text("View"), button:has-text("Open"), '
                            'a:has-text("View App"), a:has-text("Open App")'
                        )
                        
                        for button in view_buttons:
                            href = await button.get_attribute('href')
                            if href and ('/project/' in href or '/app/' in href or '/p/' in href):
                                prototype_url = href if href.startswith('http') else f"https://lovable.dev{href}"
                                break
                    except:
                        pass
                    
                    if prototype_url:
                        logger.info("prototype_url_detected", url=prototype_url)
                        break
                    
                    try:
                        page_content = await page.inner_text('body')
                        url_patterns = [
                            r'lovable\.dev/project/([a-zA-Z0-9_-]+)',
                            r'lovable\.dev/app/([a-zA-Z0-9_-]+)',
                            r'lovable\.dev/p/([a-zA-Z0-9_-]+)',
                        ]
                        for pattern in url_patterns:
                            matches = re.findall(pattern, page_content)
                            if matches:
                                project_id = matches[0]
                                prototype_url = f"https://lovable.dev/project/{project_id}"
                                logger.info("project_id_found", project_id=project_id)
                                break
                    except:
                        pass
                    
                    if prototype_url:
                        break
                    
                    await asyncio.sleep(5)
                    elapsed = int(time.time() - start_time)
                    if elapsed % 30 == 0:
                        logger.info("waiting_for_prototype", elapsed=elapsed, timeout=timeout)
                
                if not prototype_url:
                    prototype_url = page.url
                    logger.info("using_current_url", url=prototype_url)
                
                await asyncio.sleep(30)
                
                return {
                    "success": True,
                    "prototype_url": prototype_url,
                    "project_id": project_id,
                    "lovable_url": lovable_url,
                    "final_page_url": page.url
                }
                
            except Exception as e:
                logger.error("browser_automation_error", error=str(e))
                return {
                    "success": False,
                    "error": str(e),
                    "lovable_url": lovable_url
                }
            finally:
                await browser.close()


class AgnoPlaywrightAgent(AgnoBaseAgent):
    """
    Playwright Agent using Agno Framework.
    Provides end-to-end Lovable.dev prototype generation with browser automation.
    Uses test-workflow approach for content storage and interaction.
    """
    
    def __init__(self, enable_rag: bool = False, content_storage_path: Optional[str] = None):
        """
        Initialize Playwright Agent.
        
        Args:
            enable_rag: Enable RAG for knowledge base
            content_storage_path: Path to store all workflow contents (defaults to test-workflow/)
        """
        system_prompt = """You are a Playwright Automation Specialist for Lovable.dev prototype generation.

Your responsibilities:
1. Generate detailed prompts for Lovable.dev using OpenAI
2. Crawl Lovable.dev documentation to optimize prompts
3. Use Playwright browser automation to submit prompts to Lovable.dev
4. Monitor prototype generation and retrieve prototype URLs
5. Store all workflow contents (documentation, prompts, results) for reference
6. Complete end-to-end journey from prompt generation to prototype retrieval

Workflow Steps:
1. Crawl Lovable.dev documentation (https://docs.lovable.dev/integrations/build-with-url)
2. Generate optimized prompts using OpenAI based on product requirements
3. Build Lovable.dev URL with autosubmit parameter
4. Use Playwright to open browser and submit prompt
5. Wait for prototype generation completion
6. Extract and return prototype URL
7. Store all contents (documentation, prompts, URLs, results) for future reference

You have access to tools for:
- Crawling Lovable.dev documentation
- Generating prompts with OpenAI
- Building Lovable.dev URLs
- Browser automation with Playwright
- Content storage and retrieval

Always store workflow contents for demo and test purposes."""

        # Set content storage path (defaults to test-workflow directory)
        if content_storage_path is None:
            project_root = Path(__file__).parent.parent.parent
            self.content_storage_path = project_root / "test-workflow" / "playwright_storage"
        else:
            self.content_storage_path = Path(content_storage_path)
        
        # Create storage directory if it doesn't exist
        self.content_storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.documentation_crawler = LovableDocumentationCrawler() if HTTPX_AVAILABLE else None
        self.prompt_generator = None  # Will be initialized when OpenAI key is available
        self.prototype_generator = LovablePrototypeGenerator() if PLAYWRIGHT_AVAILABLE else None
        
        # Initialize base agent
        super().__init__(
            name="Playwright Agent",
            role="playwright",
            system_prompt=system_prompt,
            enable_rag=enable_rag,
            rag_table_name="playwright_knowledge_base",
            tools=[],  # Tools will be added after initialization
            capabilities=[
                "playwright automation",
                "lovable.dev integration",
                "browser automation",
                "prototype generation",
                "documentation crawling",
                "prompt generation",
                "content storage"
            ]
        )
        
        # Add tools after initialization
        if AGNO_TOOLS_AVAILABLE:
            created_tools = [
                self._crawl_lovable_docs_tool(),
                self._generate_lovable_prompt_tool(),
                self._generate_prototype_tool(),
                self._store_content_tool(),
                self._retrieve_stored_content_tool(),
            ]
            if hasattr(self.agno_agent, 'tools') and self.agno_agent.tools is not None:
                valid_tools = [t for t in created_tools if t is not None]
                if valid_tools:
                    self.agno_agent.tools.extend(valid_tools)
    
    def _get_openai_key(self) -> Optional[str]:
        """Get OpenAI API key from provider registry."""
        if provider_registry.has_openai_key():
            return provider_registry.get_openai_key()
        return os.getenv("OPENAI_API_KEY")
    
    def _initialize_prompt_generator(self):
        """Initialize prompt generator with OpenAI key."""
        if self.prompt_generator is None:
            api_key = self._get_openai_key()
            if api_key and OPENAI_AVAILABLE:
                self.prompt_generator = LovablePromptGenerator(api_key)
            else:
                logger.warning("openai_not_available_for_prompt_generation")
    
    def _crawl_lovable_docs_tool(self):
        """Create Agno tool for crawling Lovable.dev documentation."""
        if not AGNO_TOOLS_AVAILABLE:
            return None
        
        @tool
        async def crawl_lovable_documentation(max_pages: int = 20) -> str:
            """
            Crawl Lovable.dev documentation to gather information for prompt optimization.
            
            Args:
                max_pages: Maximum number of pages to crawl (default: 20)
            
            Returns:
                Summary of crawled documentation
            """
            if not self.documentation_crawler:
                return "Error: httpx not available. Install with: pip install httpx beautifulsoup4"
            
            try:
                docs = await self.documentation_crawler.deep_crawl(max_pages=max_pages)
                combined_content = self.documentation_crawler.get_combined_content()
                
                # Store documentation
                storage_file = self.content_storage_path / f"documentation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(storage_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "timestamp": datetime.now().isoformat(),
                        "pages_crawled": len(docs),
                        "documentation": docs,
                        "combined_content": combined_content
                    }, f, indent=2, ensure_ascii=False)
                
                logger.info("documentation_crawled_and_stored", 
                           pages=len(docs), 
                           storage_file=str(storage_file))
                
                return f"✅ Crawled {len(docs)} pages of Lovable.dev documentation.\n" \
                       f"Combined content length: {len(combined_content)} characters.\n" \
                       f"Stored at: {storage_file}"
            except Exception as e:
                logger.error("crawl_error", error=str(e))
                return f"Error crawling documentation: {str(e)}"
        
        return crawl_lovable_documentation
    
    def _generate_lovable_prompt_tool(self):
        """Create Agno tool for generating Lovable.dev prompts."""
        if not AGNO_TOOLS_AVAILABLE:
            return None
        
        @tool
        async def generate_lovable_prompt(
            product_description: str,
            use_documentation: bool = True
        ) -> str:
            """
            Generate a Lovable.dev-ready prompt using OpenAI.
            
            Args:
                product_description: Description of the product/application to generate
                use_documentation: Whether to use crawled documentation for optimization (default: True)
            
            Returns:
                Generated Lovable.dev prompt
            """
            self._initialize_prompt_generator()
            
            if not self.prompt_generator:
                return "Error: OpenAI not available. Please configure OPENAI_API_KEY."
            
            try:
                documentation_content = None
                if use_documentation and self.documentation_crawler:
                    combined_content = self.documentation_crawler.get_combined_content()
                    if combined_content:
                        documentation_content = combined_content
                
                prompt = await self.prompt_generator.generate_prompt(
                    product_description,
                    documentation_content
                )
                
                # Store prompt
                storage_file = self.content_storage_path / f"prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(storage_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "timestamp": datetime.now().isoformat(),
                        "product_description": product_description,
                        "prompt": prompt,
                        "used_documentation": use_documentation,
                        "prompt_length": len(prompt)
                    }, f, indent=2, ensure_ascii=False)
                
                logger.info("prompt_generated_and_stored", 
                           prompt_length=len(prompt),
                           storage_file=str(storage_file))
                
                return f"✅ Generated Lovable.dev prompt ({len(prompt)} characters):\n\n{prompt}\n\nStored at: {storage_file}"
            except Exception as e:
                logger.error("prompt_generation_error", error=str(e))
                return f"Error generating prompt: {str(e)}"
        
        return generate_lovable_prompt
    
    def _generate_prototype_tool(self):
        """Create Agno tool for generating Lovable.dev prototypes with browser automation."""
        if not AGNO_TOOLS_AVAILABLE:
            return None
        
        @tool
        async def generate_lovable_prototype(
            prompt: str,
            images: Optional[List[str]] = None,
            timeout: int = 300,
            headless: bool = False
        ) -> str:
            """
            Generate a Lovable.dev prototype using browser automation and retrieve the prototype URL.
            
            Args:
                prompt: The Lovable.dev prompt to use
                images: Optional list of image URLs (up to 10)
                timeout: Maximum time to wait for prototype generation in seconds (default: 300)
                headless: Whether to run browser in headless mode (default: False)
            
            Returns:
                Prototype URL and generation details
            """
            if not self.prototype_generator:
                return "Error: Playwright not available. Install with: pip install playwright && playwright install chromium"
            
            try:
                result = await self.prototype_generator.generate_prototype_with_browser(
                    prompt=prompt,
                    images=images,
                    timeout=timeout,
                    headless=headless
                )
                
                # Store result
                storage_file = self.content_storage_path / f"prototype_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(storage_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "timestamp": datetime.now().isoformat(),
                        "prompt": prompt,
                        "images": images or [],
                        "result": result
                    }, f, indent=2, ensure_ascii=False)
                
                logger.info("prototype_generated_and_stored",
                           success=result.get("success"),
                           prototype_url=result.get("prototype_url"),
                           storage_file=str(storage_file))
                
                if result.get("success"):
                    return f"✅ Prototype generated successfully!\n" \
                           f"Prototype URL: {result.get('prototype_url')}\n" \
                           f"Project ID: {result.get('project_id', 'N/A')}\n" \
                           f"Lovable URL: {result.get('lovable_url')}\n" \
                           f"Stored at: {storage_file}"
                else:
                    return f"⚠️ Prototype generation completed with warnings.\n" \
                           f"Error: {result.get('error', 'Unknown error')}\n" \
                           f"Lovable URL: {result.get('lovable_url')}\n" \
                           f"Stored at: {storage_file}"
            except Exception as e:
                logger.error("prototype_generation_error", error=str(e))
                return f"Error generating prototype: {str(e)}"
        
        return generate_lovable_prototype
    
    def _store_content_tool(self):
        """Create Agno tool for storing custom content."""
        if not AGNO_TOOLS_AVAILABLE:
            return None
        
        @tool
        def store_content(content_type: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
            """
            Store custom content for demo and test purposes.
            
            Args:
                content_type: Type of content (e.g., 'workflow', 'result', 'note')
                content: Content to store
                metadata: Optional metadata dictionary
            
            Returns:
                Storage confirmation with file path
            """
            try:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                storage_file = self.content_storage_path / f"{content_type}_{timestamp}.json"
                
                data = {
                    "timestamp": datetime.now().isoformat(),
                    "content_type": content_type,
                    "content": content,
                    "metadata": metadata or {}
                }
                
                with open(storage_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                logger.info("content_stored", content_type=content_type, storage_file=str(storage_file))
                
                return f"✅ Content stored successfully at: {storage_file}"
            except Exception as e:
                logger.error("content_storage_error", error=str(e))
                return f"Error storing content: {str(e)}"
        
        return store_content
    
    def _retrieve_stored_content_tool(self):
        """Create Agno tool for retrieving stored content."""
        if not AGNO_TOOLS_AVAILABLE:
            return None
        
        @tool
        def retrieve_stored_content(content_type: Optional[str] = None, limit: int = 10) -> str:
            """
            Retrieve stored content from storage directory.
            
            Args:
                content_type: Filter by content type (optional)
                limit: Maximum number of files to return (default: 10)
            
            Returns:
                Summary of stored content files
            """
            try:
                files = list(self.content_storage_path.glob("*.json"))
                
                if content_type:
                    files = [f for f in files if content_type in f.name]
                
                files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                files = files[:limit]
                
                if not files:
                    return f"No stored content found{' for type: ' + content_type if content_type else ''}"
                
                result = f"Found {len(files)} stored content file(s):\n\n"
                for file in files:
                    try:
                        with open(file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            timestamp = data.get('timestamp', 'Unknown')
                            content_type = data.get('content_type', 'unknown')
                            result += f"- {file.name}\n"
                            result += f"  Type: {content_type}\n"
                            result += f"  Timestamp: {timestamp}\n"
                            if 'prompt' in data:
                                result += f"  Prompt length: {len(data.get('prompt', ''))} chars\n"
                            if 'prototype_url' in data.get('result', {}):
                                result += f"  Prototype URL: {data['result'].get('prototype_url', 'N/A')}\n"
                            result += "\n"
                    except Exception as e:
                        result += f"- {file.name} (error reading: {str(e)})\n"
                
                return result
            except Exception as e:
                logger.error("content_retrieval_error", error=str(e))
                return f"Error retrieving content: {str(e)}"
        
        return retrieve_stored_content
    
    async def execute_full_workflow(
        self,
        product_description: str,
        max_docs_pages: int = 20,
        timeout: int = 300,
        headless: bool = False
    ) -> Dict[str, Any]:
        """
        Execute complete end-to-end workflow:
        1. Crawl documentation
        2. Generate prompt
        3. Generate prototype
        4. Store all contents
        
        Args:
            product_description: Product description for prompt generation
            max_docs_pages: Maximum documentation pages to crawl
            timeout: Timeout for prototype generation
            headless: Whether to run browser in headless mode
        
        Returns:
            Complete workflow results
        """
        workflow_results = {
            "timestamp": datetime.now().isoformat(),
            "product_description": product_description,
            "steps": {}
        }
        
        try:
            # Step 1: Crawl documentation
            logger.info("workflow_step_1", step="crawl_documentation")
            if self.documentation_crawler:
                docs = await self.documentation_crawler.deep_crawl(max_pages=max_docs_pages)
                combined_content = self.documentation_crawler.get_combined_content()
                workflow_results["steps"]["documentation"] = {
                    "pages_crawled": len(docs),
                    "content_length": len(combined_content)
                }
            else:
                workflow_results["steps"]["documentation"] = {"error": "httpx not available"}
            
            # Step 2: Generate prompt
            logger.info("workflow_step_2", step="generate_prompt")
            self._initialize_prompt_generator()
            if self.prompt_generator:
                documentation_content = None
                if self.documentation_crawler:
                    documentation_content = self.documentation_crawler.get_combined_content()
                
                prompt = await self.prompt_generator.generate_prompt(
                    product_description,
                    documentation_content
                )
                workflow_results["steps"]["prompt"] = {
                    "prompt": prompt,
                    "length": len(prompt)
                }
            else:
                workflow_results["steps"]["prompt"] = {"error": "OpenAI not available"}
                return workflow_results
            
            # Step 3: Generate prototype
            logger.info("workflow_step_3", step="generate_prototype")
            if self.prototype_generator:
                result = await self.prototype_generator.generate_prototype_with_browser(
                    prompt=workflow_results["steps"]["prompt"]["prompt"],
                    timeout=timeout,
                    headless=headless
                )
                workflow_results["steps"]["prototype"] = result
            else:
                workflow_results["steps"]["prototype"] = {"error": "Playwright not available"}
            
            # Store complete workflow
            storage_file = self.content_storage_path / f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(storage_file, 'w', encoding='utf-8') as f:
                json.dump(workflow_results, f, indent=2, ensure_ascii=False)
            
            workflow_results["storage_file"] = str(storage_file)
            logger.info("workflow_complete", storage_file=str(storage_file))
            
            return workflow_results
            
        except Exception as e:
            logger.error("workflow_error", error=str(e))
            workflow_results["error"] = str(e)
            return workflow_results

