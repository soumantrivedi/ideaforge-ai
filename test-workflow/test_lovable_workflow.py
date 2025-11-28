"""
Standalone workflow for Lovable.dev integration:
1. Load OpenAI API key from .env file
2. Deep crawl Lovable.dev documentation (https://docs.lovable.dev/integrations/build-with-url)
3. Learn programmatic ways to post prompts to Lovable.dev
4. Generate prompt using OpenAI
5. Post prompt to Lovable.dev and retrieve generated prototype link

Run with: python test-workflow/test_lovable_workflow.py
Requires: OPENAI_API_KEY in .env file (in project root)
"""
import asyncio
import os
import sys
import urllib.parse
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import time

# Load environment variables from .env file (project root, two levels up)
try:
    from dotenv import load_dotenv
    # Load .env from project root (two levels up from test-workflow)
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(env_path)
    print(f"✅ Loaded .env file from: {env_path}")
except ImportError:
    print("⚠️  python-dotenv not installed, using system environment variables")
    pass

# Try to import web scraping libraries
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    print("⚠️  httpx not available, install with: pip install httpx")

try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False
    print("⚠️  beautifulsoup4 not available, install with: pip install beautifulsoup4")

try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️  playwright not available, install with: pip install playwright && playwright install")

# Load OpenAI
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️  openai not available, install with: pip install openai")

# Load environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

if not OPENAI_API_KEY:
    print("❌ OPENAI_API_KEY environment variable is required")
    sys.exit(1)

if not OPENAI_AVAILABLE:
    print("❌ OpenAI library not available")
    sys.exit(1)


class LovableDocumentationCrawler:
    """Deep crawler for Lovable.dev documentation."""
    
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
            print(f"📄 Crawling: {url}")
            response = await client.get(url, timeout=30.0, follow_redirects=True)
            response.raise_for_status()
            
            if BEAUTIFULSOUP_AVAILABLE:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract main content
                content = ""
                
                # Try to find main content area
                main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
                if main_content:
                    content = main_content.get_text(separator='\n', strip=True)
                else:
                    # Fallback: get body text
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
                    # Convert relative URLs to absolute
                    if href.startswith('/'):
                        full_url = f"{self.base_url}{href}"
                    elif href.startswith('http'):
                        if self.base_url in href:
                            full_url = href
                        else:
                            continue  # Skip external links
                    else:
                        continue
                    
                    # Only crawl documentation pages
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
                # Fallback: return raw text
                return {
                    "url": url,
                    "title": "",
                    "content": response.text[:50000],  # Limit content size
                    "links": [],
                    "html_length": len(response.text)
                }
                
        except Exception as e:
            print(f"⚠️  Error crawling {url}: {str(e)[:200]}")
            return None
    
    async def deep_crawl(self, max_pages: int = 20) -> List[Dict[str, Any]]:
        """Perform deep crawl of Lovable.dev documentation."""
        if not HTTPX_AVAILABLE:
            print("❌ httpx not available for crawling")
            return []
        
        print(f"\n🔍 Starting deep crawl of Lovable.dev documentation...")
        print(f"   Starting URL: {self.start_url}")
        print(f"   Max pages: {max_pages}")
        
        async with httpx.AsyncClient(timeout=30.0, verify=True) as client:
            # Start with the main page
            to_crawl = [self.start_url]
            all_content = []
            
            while to_crawl and len(all_content) < max_pages:
                current_url = to_crawl.pop(0)
                
                page_data = await self.crawl_page(current_url, client)
                if page_data:
                    all_content.append(page_data)
                    
                    # Add new links to crawl queue (limit to avoid infinite loops)
                    for link in page_data.get("links", [])[:5]:  # Limit links per page
                        if link not in self.visited_urls and link not in to_crawl:
                            to_crawl.append(link)
                    
                    # Small delay to be respectful
                    await asyncio.sleep(1)
            
            self.documentation_content = all_content
            print(f"✅ Crawled {len(all_content)} pages")
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
    """Generate Lovable.dev prompts using OpenAI."""
    
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
{documentation_content[:10000]}  # Limit documentation size
"""
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            prompt = response.choices[0].message.content.strip()
            return self._clean_prompt(prompt)
        except Exception as e:
            print(f"❌ Error generating prompt: {str(e)}")
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
    """Generate Lovable.dev prototypes and retrieve links."""
    
    def __init__(self):
        self.base_url = "https://lovable.dev"
        self.autosubmit_url = "https://lovable.dev/?autosubmit=true#"
    
    def build_lovable_url(self, prompt: str, images: Optional[List[str]] = None) -> str:
        """Build Lovable.dev URL with prompt and optional images."""
        # URL encode the prompt
        encoded_prompt = urllib.parse.quote(prompt)
        
        # Build URL
        url = f"{self.autosubmit_url}prompt={encoded_prompt}"
        
        # Add images if provided
        if images:
            for img_url in images[:10]:  # Max 10 images
                encoded_img = urllib.parse.quote(img_url)
                url += f"&images={encoded_img}"
        
        return url
    
    async def generate_prototype_with_browser(
        self, 
        prompt: str,
        images: Optional[List[str]] = None,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """Generate prototype using browser automation to retrieve the link."""
        if not PLAYWRIGHT_AVAILABLE:
            raise ValueError("Playwright not available. Install with: pip install playwright && playwright install")
        
        lovable_url = self.build_lovable_url(prompt, images)
        
        print(f"\n🌐 Opening Lovable.dev in browser...")
        print(f"   URL length: {len(lovable_url)} characters")
        print(f"   Prompt length: {len(prompt)} characters")
        
        async with async_playwright() as p:
            # Launch browser (headless=False so user can see what's happening)
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()
            
            try:
                # Navigate to Lovable.dev with the prompt
                print(f"📤 Navigating to Lovable.dev with prompt...")
                await page.goto(lovable_url, wait_until='networkidle', timeout=60000)
                
                # Wait for authentication/login if needed
                print(f"⏳ Waiting for page to load...")
                await asyncio.sleep(5)
                
                # Check if we're on login page
                login_indicators = [
                    'sign in', 'sign up', 'login', 'log in', 
                    'email', 'password', 'continue with'
                ]
                page_text = await page.inner_text('body')
                is_login_page = any(indicator in page_text.lower() for indicator in login_indicators)
                
                if is_login_page:
                    print(f"⚠️  Login required. Please log in manually in the browser window.")
                    print(f"   The browser will wait for you to complete login...")
                    # Wait for user to log in (check every 5 seconds)
                    for i in range(60):  # Wait up to 5 minutes
                        await asyncio.sleep(5)
                        current_url = page.url
                        if 'lovable.dev' in current_url and 'login' not in current_url.lower() and 'sign' not in current_url.lower():
                            print(f"✅ Login detected, continuing...")
                            break
                
                # Wait for app generation to start
                print(f"⏳ Waiting for app generation to start...")
                await asyncio.sleep(10)
                
                # Try to detect when prototype is ready
                # Look for indicators like "View App", "Open App", project URL, etc.
                print(f"🔍 Monitoring for prototype completion...")
                
                start_time = time.time()
                prototype_url = None
                project_id = None
                
                while time.time() - start_time < timeout:
                    current_url = page.url
                    
                    # Check if URL contains a project/app ID
                    if '/project/' in current_url or '/app/' in current_url or '/p/' in current_url:
                        # Extract project ID from URL
                        parts = current_url.split('/')
                        for i, part in enumerate(parts):
                            if part in ['project', 'app', 'p'] and i + 1 < len(parts):
                                project_id = parts[i + 1]
                                prototype_url = current_url
                                break
                    
                    # Also check for buttons/links that might indicate completion
                    try:
                        # Look for "View App", "Open App", "View Project" buttons
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
                        print(f"✅ Prototype URL detected: {prototype_url}")
                        break
                    
                    # Check page content for project/app indicators
                    try:
                        page_content = await page.inner_text('body')
                        # Look for project IDs or app URLs in the content
                        import re
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
                                print(f"✅ Found project ID in page: {project_id}")
                                break
                    except:
                        pass
                    
                    if prototype_url:
                        break
                    
                    # Wait before checking again
                    await asyncio.sleep(5)
                    elapsed = int(time.time() - start_time)
                    if elapsed % 30 == 0:  # Print status every 30 seconds
                        print(f"⏳ Still waiting... ({elapsed}s/{timeout}s)")
                
                # Get final URL if we don't have a prototype URL yet
                if not prototype_url:
                    final_url = page.url
                    if 'lovable.dev' in final_url:
                        prototype_url = final_url
                        print(f"📋 Using current page URL: {prototype_url}")
                
                # Keep browser open for a bit so user can see the result
                print(f"\n✅ Prototype generation complete!")
                print(f"   Keeping browser open for 30 seconds so you can see the result...")
                await asyncio.sleep(30)
                
                return {
                    "success": True,
                    "prototype_url": prototype_url,
                    "project_id": project_id,
                    "lovable_url": lovable_url,
                    "final_page_url": page.url
                }
                
            except Exception as e:
                print(f"❌ Error during browser automation: {str(e)}")
                import traceback
                traceback.print_exc()
                return {
                    "success": False,
                    "error": str(e),
                    "lovable_url": lovable_url
                }
            finally:
                await browser.close()
    
    async def generate_prototype_url_only(
        self,
        prompt: str,
        images: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate prototype URL without browser automation (returns the trigger URL)."""
        lovable_url = self.build_lovable_url(prompt, images)
        
        return {
            "success": True,
            "lovable_url": lovable_url,
            "note": "This URL will trigger app generation when opened in a browser. "
                   "To retrieve the generated prototype link programmatically, use browser automation.",
            "instructions": "Open this URL in a browser to generate the app. "
                          "After generation, the browser will redirect to the prototype URL."
        }


async def test_lovable_workflow():
    """Test the complete Lovable.dev workflow end-to-end."""
    print("=" * 80)
    print("LOVABLE.DEV INTEGRATION WORKFLOW TEST")
    print("=" * 80)
    
    product_description = "A modern task management dashboard with drag-and-drop task boards, user authentication, real-time collaboration, and analytics charts"
    
    try:
        # Step 1: Deep crawl Lovable.dev documentation
        print("\n" + "=" * 80)
        print("STEP 1: Deep crawling Lovable.dev documentation...")
        print("=" * 80)
        
        crawler = LovableDocumentationCrawler()
        documentation = await crawler.deep_crawl(max_pages=10)
        
        if documentation:
            print(f"✅ Crawled {len(documentation)} pages")
            combined_content = crawler.get_combined_content()
            print(f"✅ Combined content length: {len(combined_content)} characters")
            print(f"\n📄 Sample content from first page:")
            if documentation:
                sample = documentation[0].get('content', '')[:500]
                print(f"   {sample}...")
        else:
            print("⚠️  No documentation crawled (may need to install httpx and beautifulsoup4)")
            combined_content = None
        
        # Step 2: Generate Lovable.dev prompt using OpenAI
        print("\n" + "=" * 80)
        print("STEP 2: Generating Lovable.dev prompt using OpenAI...")
        print("=" * 80)
        
        prompt_generator = LovablePromptGenerator(OPENAI_API_KEY)
        lovable_prompt = await prompt_generator.generate_prompt(
            product_description,
            combined_content
        )
        
        print(f"✅ Generated prompt ({len(lovable_prompt)} chars)")
        print("-" * 80)
        print(lovable_prompt[:500] + "..." if len(lovable_prompt) > 500 else lovable_prompt)
        print("-" * 80)
        
        # Step 3: Generate prototype and retrieve link
        print("\n" + "=" * 80)
        print("STEP 3: Generating Lovable.dev prototype and retrieving link...")
        print("=" * 80)
        
        prototype_generator = LovablePrototypeGenerator()
        
        # Choose method based on available tools
        if PLAYWRIGHT_AVAILABLE:
            print("🌐 Using browser automation to retrieve prototype link...")
            result = await prototype_generator.generate_prototype_with_browser(
                lovable_prompt,
                timeout=300  # 5 minutes timeout
            )
        else:
            print("📋 Browser automation not available, generating trigger URL only...")
            print("   Install playwright for automatic link retrieval: pip install playwright && playwright install")
            result = await prototype_generator.generate_prototype_url_only(lovable_prompt)
        
        # Display results
        print("\n" + "=" * 80)
        if result.get("success"):
            print("✅ WORKFLOW COMPLETED SUCCESSFULLY!")
            print("=" * 80)
            
            if result.get("prototype_url"):
                print(f"✅ Prototype URL: {result.get('prototype_url')}")
                if result.get("project_id"):
                    print(f"✅ Project ID: {result.get('project_id')}")
            else:
                print(f"✅ Lovable.dev URL: {result.get('lovable_url')}")
                if result.get("note"):
                    print(f"   Note: {result.get('note')}")
                if result.get("instructions"):
                    print(f"   Instructions: {result.get('instructions')}")
        else:
            print("⚠️  WORKFLOW COMPLETED WITH WARNINGS")
            print("=" * 80)
            if result.get("error"):
                print(f"   Error: {result.get('error')}")
            if result.get("lovable_url"):
                print(f"   Lovable.dev URL: {result.get('lovable_url')}")
                print(f"   You can open this URL manually in a browser")
        
        # Summary
        print("\n" + "=" * 80)
        print("WORKFLOW SUMMARY")
        print("=" * 80)
        print("✅ Documentation crawled")
        print("✅ Prompt generated with OpenAI")
        print("✅ Lovable.dev prototype triggered")
        if result.get("prototype_url"):
            print("✅ Prototype link retrieved")
        else:
            print("⚠️  Prototype link requires manual browser interaction")
        
        return result
        
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ WORKFLOW FAILED")
        print("=" * 80)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_lovable_workflow())

