# Lovable.dev Integration Workflow

This standalone workflow demonstrates how to:
1. Load OpenAI API key from `.env` file
2. Deep crawl Lovable.dev documentation
3. Generate prompts using OpenAI
4. Programmatically post prompts to Lovable.dev
5. Retrieve generated prototype links

## Overview

The workflow (`test_lovable_workflow.py`) is a complete standalone test that:
- **Crawls Documentation**: Deep crawls Lovable.dev documentation starting from the "Build with URL" page
- **Generates Prompts**: Uses OpenAI to create optimized prompts for Lovable.dev
- **Creates Prototypes**: Posts prompts to Lovable.dev using URL-based API
- **Retrieves Links**: Uses browser automation to wait for prototype generation and extract the link

## Prerequisites

1. **OpenAI API Key**: Must be set in `.env` file
   ```bash
   OPENAI_API_KEY=sk-your-key-here
   ```

2. **Python Dependencies**: Install additional requirements
   ```bash
   pip install -r backend/requirements-lovable-test.txt
   playwright install chromium
   ```

## Installation

### Step 1: Install Dependencies

```bash
# Install Python packages
pip install beautifulsoup4 playwright

# Install Playwright browser (required for link retrieval)
playwright install chromium
```

### Step 2: Configure Environment

Ensure your `.env` file contains:
```bash
OPENAI_API_KEY=sk-your-openai-api-key-here
```

## Usage

### Run the Complete Workflow

```bash
python backend/test_lovable_workflow.py
```

### What It Does

1. **Documentation Crawling** (Step 1)
   - Crawls `https://docs.lovable.dev/integrations/build-with-url`
   - Follows related documentation links
   - Extracts content for prompt generation

2. **Prompt Generation** (Step 2)
   - Uses OpenAI GPT-4o-mini to generate optimized prompts
   - Incorporates documentation insights
   - Creates Lovable.dev-ready prompts

3. **Prototype Generation** (Step 3)
   - Builds Lovable.dev URL with `autosubmit=true` parameter
   - Opens browser and navigates to trigger generation
   - Waits for prototype completion
   - Extracts and returns prototype URL

## How Lovable.dev Integration Works

### URL-Based API

Lovable.dev uses a URL-based approach (not a traditional REST API):

```
https://lovable.dev/?autosubmit=true#prompt=YOUR_PROMPT&images=IMAGE_URL
```

**Parameters:**
- `autosubmit=true`: Automatically processes the request
- `prompt`: URL-encoded prompt describing the app (required)
- `images`: Optional reference image URLs (max 10)

### Programmatic Access

Since Lovable.dev uses URL-based generation, the workflow:

1. **Generates the URL**: Builds the URL with encoded prompt
2. **Opens Browser**: Uses Playwright to open the URL
3. **Waits for Generation**: Monitors the page for completion
4. **Extracts Link**: Retrieves the generated prototype URL

### Alternative: Manual URL Generation

If you don't want browser automation, the workflow can generate the trigger URL:

```python
from backend.test_lovable_workflow import LovablePrototypeGenerator

generator = LovablePrototypeGenerator()
url = generator.build_lovable_url("Create a todo app")
print(url)  # Open this URL in browser manually
```

## Workflow Components

### 1. LovableDocumentationCrawler

Deep crawls Lovable.dev documentation:
- Starts from the Build with URL page
- Follows related documentation links
- Extracts content for analysis

### 2. LovablePromptGenerator

Generates optimized prompts using OpenAI:
- Incorporates documentation insights
- Creates detailed, actionable prompts
- Optimized for Lovable.dev's generation engine

### 3. LovablePrototypeGenerator

Handles prototype generation and link retrieval:
- Builds Lovable.dev URLs
- Uses browser automation to trigger generation
- Waits for completion and extracts links

## Example Output

```
================================================================================
LOVABLE.DEV INTEGRATION WORKFLOW TEST
================================================================================

================================================================================
STEP 1: Deep crawling Lovable.dev documentation...
================================================================================
📄 Crawling: https://docs.lovable.dev/integrations/build-with-url
✅ Crawled 10 pages
✅ Combined content length: 45230 characters

================================================================================
STEP 2: Generating Lovable.dev prompt using OpenAI...
================================================================================
✅ Generated prompt (342 chars)
--------------------------------------------------------------------------------
Create a modern task management dashboard with the following features:
- Drag-and-drop task boards (To Do, In Progress, Done)
- User authentication with email/password
- Real-time collaboration with live updates
- Analytics charts showing task completion trends
- Responsive design for mobile and desktop
...

================================================================================
STEP 3: Generating Lovable.dev prototype and retrieving link...
================================================================================
🌐 Opening Lovable.dev in browser...
📤 Navigating to Lovable.dev with prompt...
⏳ Waiting for page to load...
✅ Login detected, continuing...
⏳ Waiting for app generation to start...
🔍 Monitoring for prototype completion...
✅ Prototype URL detected: https://lovable.dev/project/abc123xyz

================================================================================
✅ WORKFLOW COMPLETED SUCCESSFULLY!
================================================================================
✅ Prototype URL: https://lovable.dev/project/abc123xyz
✅ Project ID: abc123xyz
```

## Troubleshooting

### Browser Automation Issues

If Playwright fails:
1. Ensure Chromium is installed: `playwright install chromium`
2. Check browser permissions
3. Try running with `headless=False` (default) to see what's happening

### Documentation Crawling Issues

If crawling fails:
1. Install `httpx` and `beautifulsoup4`
2. Check internet connection
3. Verify Lovable.dev documentation is accessible

### OpenAI API Issues

If prompt generation fails:
1. Verify `OPENAI_API_KEY` in `.env`
2. Check API key validity
3. Ensure sufficient API credits

### Prototype Link Not Retrieved

If the prototype link isn't automatically retrieved:
1. The workflow will still provide the trigger URL
2. Open the URL manually in a browser
3. Wait for generation to complete
4. Copy the prototype URL from the browser

## Limitations

1. **Browser Automation Required**: To retrieve prototype links automatically, Playwright is required
2. **Login Required**: If not logged in, the workflow will wait for manual login
3. **Generation Time**: Prototype generation can take several minutes
4. **URL Length Limits**: Very long prompts may hit browser URL length limits

## Best Practices

1. **Keep Prompts Concise**: Aim for 200-500 words
2. **Use Reference Images**: Include image URLs when relevant
3. **Monitor Generation**: Watch the browser window to see progress
4. **Handle Timeouts**: Increase timeout if generation takes longer

## Integration with Existing Codebase

This workflow is **completely standalone** and makes **NO changes** to the existing codebase. It:
- Uses only standard Python libraries and dependencies
- Reads from `.env` file (doesn't modify it)
- Creates no new files in the main codebase
- Can be run independently

## Next Steps

To integrate this into the main application:
1. Extract the classes into separate modules
2. Add to the existing agent system
3. Create API endpoints for Lovable.dev integration
4. Add UI components for prototype viewing

## References

- [Lovable.dev Build with URL Documentation](https://docs.lovable.dev/integrations/build-with-url)
- [Lovable.dev Link Generator](https://lovable.dev/links)
- [Playwright Documentation](https://playwright.dev/python/)

