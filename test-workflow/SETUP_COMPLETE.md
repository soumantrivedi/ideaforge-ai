# Lovable.dev Workflow - Setup Complete ✅

## Summary

A complete standalone workflow has been created in the `test-workflow/` folder that:

1. ✅ **Reads OpenAI API key from `.env` file** (project root)
2. ✅ **Deep crawls Lovable.dev documentation** (https://docs.lovable.dev/integrations/build-with-url)
3. ✅ **Generates prompts using OpenAI** (GPT-4o-mini)
4. ✅ **Posts prompts to Lovable.dev** (URL-based API with `autosubmit=true`)
5. ✅ **Retrieves generated prototype links** (via browser automation)

## Files Created

### Main Workflow Files
- **`test_lovable_workflow.py`** - Complete end-to-end workflow
  - `LovableDocumentationCrawler` - Crawls documentation
  - `LovablePromptGenerator` - Generates prompts with OpenAI
  - `LovablePrototypeGenerator` - Creates prototypes and retrieves links

- **`test_lovable_simple.py`** - Simple example (URL generation only)

### Documentation
- **`README.md`** - Setup and usage instructions
- **`LOVABLE_WORKFLOW_README.md`** - Comprehensive documentation
- **`LOVABLE_WORKFLOW_SUMMARY.md`** - Implementation summary
- **`demo_output.txt`** - Expected output demonstration

### Configuration
- **`requirements-lovable-test.txt`** - Additional dependencies needed

## Key Features

### 1. Documentation Crawling
- Deep crawls Lovable.dev documentation starting from build-with-url page
- Follows related documentation links (up to 20 pages)
- Extracts content for prompt optimization
- Uses BeautifulSoup for HTML parsing

### 2. Prompt Generation
- Uses OpenAI GPT-4o-mini
- Incorporates documentation insights
- Creates optimized Lovable.dev prompts
- Cleans prompts to remove meta-commentary

### 3. Prototype Generation
- Builds Lovable.dev URL with `autosubmit=true` parameter
- URL-encodes prompts properly
- Supports up to 10 reference images
- Uses Playwright for browser automation
- Waits for prototype completion
- Extracts prototype URLs automatically

## How Lovable.dev Integration Works

Based on the documentation crawl, Lovable.dev uses:

### URL-Based API (Not REST)
```
https://lovable.dev/?autosubmit=true#prompt=ENCODED_PROMPT&images=IMAGE_URL
```

**Key Parameters:**
- `autosubmit=true` - Automatically processes the request
- `prompt` - URL-encoded prompt (required, max 50,000 chars)
- `images` - Optional reference image URLs (max 10)

### Programmatic Access Strategy

Since there's no REST API:
1. **Generate URL** - Build URL with encoded prompt
2. **Browser Automation** - Use Playwright to open URL
3. **Wait for Generation** - Monitor page for completion
4. **Extract Link** - Retrieve prototype URL from page

## Installation & Usage

### Quick Start

```bash
# 1. Install dependencies
pip install python-dotenv httpx beautifulsoup4 openai playwright
playwright install chromium

# 2. Ensure .env has OPENAI_API_KEY
# OPENAI_API_KEY=sk-your-key-here

# 3. Run workflow
cd /Users/Souman_Trivedi/IdeaProjects/ideaforge-ai
python test-workflow/test_lovable_workflow.py
```

### Simple Example (URL Only)

```bash
python test-workflow/test_lovable_simple.py
```

## Workflow Execution Flow

```
┌─────────────────────────────────────────────────────────┐
│ STEP 1: Documentation Crawling                            │
│ - Crawls docs.lovable.dev/integrations/build-with-url   │
│ - Follows related links                                  │
│ - Extracts content                                       │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 2: Prompt Generation                               │
│ - Uses OpenAI GPT-4o-mini                               │
│ - Incorporates documentation                            │
│ - Generates optimized prompt                            │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 3: Prototype Generation                            │
│ - Builds Lovable.dev URL                                │
│ - Opens browser (Playwright)                            │
│ - Waits for generation                                  │
│ - Extracts prototype URL                                │
└─────────────────────────────────────────────────────────┘
```

## Expected Results

When run successfully, the workflow will:

1. ✅ Crawl 10+ documentation pages
2. ✅ Generate a detailed prompt (200-500 words)
3. ✅ Open browser and navigate to Lovable.dev
4. ✅ Trigger prototype generation
5. ✅ Wait for completion (1-5 minutes)
6. ✅ Return prototype URL like: `https://lovable.dev/project/abc123xyz`

## Important Notes

- **Standalone**: Makes NO changes to existing codebase
- **Environment**: Reads from `.env` in project root
- **Dependencies**: Requires additional packages (see requirements-lovable-test.txt)
- **Browser**: Requires Playwright and Chromium for link retrieval
- **Authentication**: May require manual login to Lovable.dev
- **Timeout**: Prototype generation can take 1-5 minutes

## Troubleshooting

### Missing Dependencies
```bash
pip install python-dotenv httpx beautifulsoup4 openai playwright
playwright install chromium
```

### OpenAI API Key
Ensure `.env` file in project root contains:
```bash
OPENAI_API_KEY=sk-your-key-here
```

### Browser Issues
- Playwright must be installed: `playwright install chromium`
- Browser opens in non-headless mode for visibility
- May need to log in to Lovable.dev manually

## Next Steps

To integrate into the main application:
1. Extract classes to `backend/services/lovable/`
2. Add API endpoints to `backend/api/design.py`
3. Create UI components for prototype viewing
4. Store prototype URLs in database

## Files Location

All files are in: `/Users/Souman_Trivedi/IdeaProjects/ideaforge-ai/test-workflow/`

- ✅ No files in `backend/` directory
- ✅ Completely standalone
- ✅ Ready to run when dependencies are installed

## Status

✅ **Workflow Created**
✅ **Files Organized in test-workflow/ folder**
✅ **Documentation Complete**
✅ **Ready for Execution** (requires dependency installation)

