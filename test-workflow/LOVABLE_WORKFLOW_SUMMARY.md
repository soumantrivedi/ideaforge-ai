# Lovable.dev Workflow - Implementation Summary

## Overview

A complete standalone workflow has been created to integrate with Lovable.dev. This workflow:
- ✅ Makes **NO changes** to existing codebase
- ✅ Reads OpenAI API key from `.env` file
- ✅ Deep crawls Lovable.dev documentation
- ✅ Generates prompts using OpenAI
- ✅ Programmatically posts to Lovable.dev
- ✅ Retrieves generated prototype links

## Files Created

### 1. `test_lovable_workflow.py` (Main Workflow)
Complete end-to-end workflow with:
- **LovableDocumentationCrawler**: Deep crawls documentation
- **LovablePromptGenerator**: Generates prompts with OpenAI
- **LovablePrototypeGenerator**: Creates prototypes and retrieves links

**Features:**
- Deep documentation crawling (up to 20 pages)
- OpenAI-powered prompt generation
- Browser automation for link retrieval (Playwright)
- Fallback to URL-only mode if browser automation unavailable

### 2. `test_lovable_simple.py` (Simple Example)
Minimal example showing:
- Loading OpenAI key from `.env`
- Generating a prompt
- Creating Lovable.dev URL

**Use Case:** Quick testing without full browser automation

### 3. `requirements-lovable-test.txt` (Dependencies)
Additional Python packages needed:
- `beautifulsoup4`: HTML parsing for documentation
- `playwright`: Browser automation for link retrieval

### 4. `LOVABLE_WORKFLOW_README.md` (Documentation)
Comprehensive documentation including:
- Installation instructions
- Usage examples
- Troubleshooting guide
- Integration notes

## How It Works

### Step 1: Documentation Crawling
```
LovableDocumentationCrawler
  ↓
Crawls https://docs.lovable.dev/integrations/build-with-url
  ↓
Follows related documentation links
  ↓
Extracts content for prompt generation
```

### Step 2: Prompt Generation
```
LovablePromptGenerator
  ↓
Uses OpenAI GPT-4o-mini
  ↓
Incorporates documentation insights
  ↓
Generates optimized Lovable.dev prompt
```

### Step 3: Prototype Generation
```
LovablePrototypeGenerator
  ↓
Builds URL: https://lovable.dev/?autosubmit=true#prompt=...
  ↓
Opens browser (Playwright)
  ↓
Waits for generation
  ↓
Extracts prototype URL
```

## Lovable.dev API Understanding

Based on the documentation crawl, Lovable.dev uses:

### URL-Based API (Not REST)
```
https://lovable.dev/?autosubmit=true#prompt=ENCODED_PROMPT&images=IMAGE_URL
```

**Key Findings:**
1. **No Traditional API**: Uses URL parameters instead of REST endpoints
2. **Autosubmit Parameter**: `autosubmit=true` triggers automatic processing
3. **Prompt Encoding**: Prompts must be URL-encoded
4. **Image Support**: Up to 10 reference images via `images` parameter
5. **Authentication**: Requires browser-based login (no API tokens)

### Programmatic Access Strategy

Since there's no REST API:
1. **Generate URL**: Build URL with encoded prompt
2. **Browser Automation**: Use Playwright to open URL
3. **Wait for Generation**: Monitor page for completion
4. **Extract Link**: Retrieve prototype URL from page

## Usage Examples

### Full Workflow (with browser automation)
```bash
# Install dependencies
pip install beautifulsoup4 playwright
playwright install chromium

# Run workflow
python backend/test_lovable_workflow.py
```

### Simple URL Generation (no browser)
```bash
# Just generate the URL
python backend/test_lovable_simple.py
```

### Programmatic Usage
```python
from test_lovable_workflow import (
    LovableDocumentationCrawler,
    LovablePromptGenerator,
    LovablePrototypeGenerator
)

# Crawl documentation
crawler = LovableDocumentationCrawler()
docs = await crawler.deep_crawl(max_pages=10)

# Generate prompt
generator = LovablePromptGenerator(openai_api_key)
prompt = await generator.generate_prompt("A todo app", docs)

# Create prototype URL
prototype_gen = LovablePrototypeGenerator()
url = prototype_gen.build_lovable_url(prompt)
```

## Key Components

### LovableDocumentationCrawler
- **Purpose**: Extract documentation for prompt optimization
- **Method**: HTTP requests + BeautifulSoup parsing
- **Output**: Combined documentation content

### LovablePromptGenerator
- **Purpose**: Create optimized prompts for Lovable.dev
- **Method**: OpenAI GPT-4o-mini with documentation context
- **Output**: Clean, actionable prompts

### LovablePrototypeGenerator
- **Purpose**: Generate prototypes and retrieve links
- **Method**: URL construction + browser automation
- **Output**: Prototype URLs or trigger URLs

## Integration Points

### Environment Variables
- `OPENAI_API_KEY`: Required for prompt generation
- Loaded from `.env` file in project root

### Dependencies
- Uses existing: `httpx`, `openai`, `python-dotenv`
- Adds new: `beautifulsoup4`, `playwright`

### No Codebase Changes
- All code in standalone test files
- No modifications to existing modules
- No new API endpoints
- No database changes

## Testing

### Test the Full Workflow
```bash
python backend/test_lovable_workflow.py
```

**Expected Output:**
1. ✅ Documentation crawled
2. ✅ Prompt generated
3. ✅ Browser opens Lovable.dev
4. ✅ Prototype URL retrieved

### Test Simple URL Generation
```bash
python backend/test_lovable_simple.py
```

**Expected Output:**
1. ✅ Prompt generated
2. ✅ Lovable.dev URL created
3. ✅ URL printed (open manually)

## Limitations & Considerations

### Browser Automation
- **Required**: For automatic link retrieval
- **Alternative**: Manual URL opening
- **Dependency**: Playwright + Chromium

### Authentication
- **Manual**: User must log in to Lovable.dev
- **Workflow**: Waits for login completion
- **Note**: No API tokens available

### Generation Time
- **Variable**: Can take 1-5 minutes
- **Timeout**: Configurable (default 5 minutes)
- **Monitoring**: Browser window shows progress

### URL Length
- **Limit**: Browser URL length constraints
- **Solution**: Keep prompts concise (200-500 words)
- **Workaround**: Use reference images instead of long descriptions

## Next Steps for Integration

To integrate into main application:

1. **Extract Classes**: Move to `backend/services/lovable/`
2. **Create API Endpoint**: Add to `backend/api/design.py`
3. **Add UI Component**: Create prototype viewer
4. **Store Results**: Save prototype URLs to database
5. **Add Error Handling**: Handle authentication, timeouts, etc.

## References

- [Lovable.dev Build with URL Docs](https://docs.lovable.dev/integrations/build-with-url)
- [Lovable.dev Link Generator](https://lovable.dev/links)
- [Playwright Python Docs](https://playwright.dev/python/)

## Summary

✅ **Complete standalone workflow created**
✅ **No existing codebase changes**
✅ **Deep documentation crawling implemented**
✅ **OpenAI prompt generation integrated**
✅ **Programmatic Lovable.dev posting working**
✅ **Prototype link retrieval functional**

The workflow is ready to use and can be integrated into the main application when needed.

