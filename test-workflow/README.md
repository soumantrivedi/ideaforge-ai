# Lovable.dev Integration Workflow

Complete standalone workflow for integrating with Lovable.dev.

## Files

- `test_lovable_workflow.py` - Complete end-to-end workflow
- `test_lovable_simple.py` - Simple example (URL generation only)
- `requirements-lovable-test.txt` - Additional dependencies

## Setup

### 1. Install Dependencies

```bash
# Install Python packages
pip install python-dotenv httpx beautifulsoup4 openai playwright

# Install Playwright browser (required for link retrieval)
playwright install chromium
```

Or use a virtual environment:

```bash
python3 -m venv test-workflow/venv
source test-workflow/venv/bin/activate
pip install python-dotenv httpx beautifulsoup4 openai playwright
playwright install chromium
```

### 2. Configure Environment

Ensure `.env` file in project root contains:
```bash
OPENAI_API_KEY=sk-your-openai-api-key-here
```

## Usage

### Full Workflow (with browser automation)

```bash
cd /Users/Souman_Trivedi/IdeaProjects/ideaforge-ai
python test-workflow/test_lovable_workflow.py
```

This will:
1. ✅ Crawl Lovable.dev documentation
2. ✅ Generate prompt using OpenAI
3. ✅ Open browser and post to Lovable.dev
4. ✅ Wait for prototype generation
5. ✅ Retrieve and display prototype URL

### Simple Example (URL only)

```bash
python test-workflow/test_lovable_simple.py
```

This generates the Lovable.dev URL without browser automation.

## Workflow Steps

### Step 1: Documentation Crawling
- Crawls `https://docs.lovable.dev/integrations/build-with-url`
- Follows related documentation links
- Extracts content for prompt optimization

### Step 2: Prompt Generation
- Uses OpenAI GPT-4o-mini
- Incorporates documentation insights
- Creates optimized Lovable.dev prompts

### Step 3: Prototype Generation
- Builds URL: `https://lovable.dev/?autosubmit=true#prompt=...`
- Opens browser (Playwright)
- Waits for generation completion
- Extracts prototype URL

## Expected Output

```
================================================================================
LOVABLE.DEV INTEGRATION WORKFLOW TEST
================================================================================

================================================================================
STEP 1: Deep crawling Lovable.dev documentation...
================================================================================
🔍 Starting deep crawl of Lovable.dev documentation...
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
🌐 Using browser automation to retrieve prototype link...
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

================================================================================
WORKFLOW SUMMARY
================================================================================
✅ Documentation crawled
✅ Prompt generated with OpenAI
✅ Lovable.dev prototype triggered
✅ Prototype link retrieved
```

## Troubleshooting

### Missing Dependencies
Install all required packages:
```bash
pip install python-dotenv httpx beautifulsoup4 openai playwright
playwright install chromium
```

### OpenAI API Key
Ensure `OPENAI_API_KEY` is set in `.env` file in project root.

### Browser Automation Issues
- Ensure Playwright is installed: `playwright install chromium`
- Browser will open in non-headless mode so you can see progress
- May require manual login to Lovable.dev

### Documentation Crawling
- Requires internet connection
- May need to adjust timeout if pages load slowly

## Notes

- This workflow is **completely standalone** and makes **no changes** to the existing codebase
- All files are in the `test-workflow/` directory
- The workflow reads from `.env` in the project root
- Browser automation requires Playwright and Chromium

