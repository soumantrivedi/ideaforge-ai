# Agno Playwright Agent Integration Guide

## Overview

The `AgnoPlaywrightAgent` provides end-to-end Lovable.dev prototype generation using Playwright browser automation. It uses the test-workflow approach for content storage and interaction.

## Features

- **Documentation Crawling**: Deep crawls Lovable.dev documentation for prompt optimization
- **Prompt Generation**: Uses OpenAI to generate optimized Lovable.dev prompts
- **Browser Automation**: Uses Playwright to submit prompts and retrieve prototype URLs
- **Content Storage**: Stores all workflow contents (documentation, prompts, results) in `test-workflow/playwright_storage/`
- **End-to-End Workflow**: Complete journey from prompt generation to prototype retrieval

## Prerequisites

### 1. Install Dependencies

```bash
# Install Python packages
pip install playwright beautifulsoup4 httpx

# Install Playwright browser
playwright install chromium
```

### 2. Configure Environment

Ensure your `.env` file contains:
```bash
OPENAI_API_KEY=sk-your-openai-api-key-here
```

## Agent Structure

The agent extends `AgnoBaseAgent` and provides the following tools:

1. **crawl_lovable_documentation**: Crawls Lovable.dev docs
2. **generate_lovable_prompt**: Generates prompts using OpenAI
3. **generate_lovable_prototype**: Creates prototypes with browser automation
4. **store_content**: Stores custom content
5. **retrieve_stored_content**: Retrieves stored content

## Integration Steps

### Step 1: Add Agent to Coordinator

Edit `backend/agents/agno_coordinator_agent.py`:

```python
from backend.agents.agno_playwright_agent import AgnoPlaywrightAgent

class AgnoCoordinatorAgent:
    def __init__(self, enable_rag: bool = True):
        # ... existing agents ...
        self.playwright_agent = AgnoPlaywrightAgent(enable_rag=enable_rag)
        
        # Register in agents dict
        self.agents: Dict[str, AgnoBaseAgent] = {
            # ... existing agents ...
            "playwright": self.playwright_agent,
        }
        
        # Set coordinator reference
        self.playwright_agent.set_coordinator(self)
```

### Step 2: Add Agent to Enhanced Coordinator

Edit `backend/agents/agno_enhanced_coordinator.py`:

```python
from backend.agents.agno_playwright_agent import AgnoPlaywrightAgent

class AgnoEnhancedCoordinator:
    def __init__(self, enable_rag: bool = True):
        # ... existing agents ...
        self.playwright_agent = AgnoPlaywrightAgent(enable_rag=enable_rag)
        
        # Register in agents dict
        self.agents: Dict[str, AgnoBaseAgent] = {
            # ... existing agents ...
            "playwright": self.playwright_agent,
        }
        
        # Set coordinator reference
        self.playwright_agent.set_coordinator(self)
```

### Step 3: Add Agent to Orchestrator

Edit `backend/agents/agno_orchestrator.py`:

```python
from backend.agents.agno_playwright_agent import AgnoPlaywrightAgent

class AgnoAgenticOrchestrator:
    def _initialize_components(self):
        # ... existing agents ...
        self.agents: Dict[str, Any] = {
            # ... existing agents ...
            "playwright": AgnoPlaywrightAgent(enable_rag=self.enable_rag),
        }
```

### Step 4: Update Agent Exports (Optional)

Edit `backend/agents/__init__.py`:

```python
from backend.agents.agno_playwright_agent import AgnoPlaywrightAgent

__all__ = [
    # ... existing exports ...
    "AgnoPlaywrightAgent",
]
```

## Usage Examples

### Direct Agent Usage

```python
from backend.agents.agno_playwright_agent import AgnoPlaywrightAgent

# Initialize agent
agent = AgnoPlaywrightAgent(enable_rag=False)

# Execute full workflow
result = await agent.execute_full_workflow(
    product_description="A modern task management dashboard with drag-and-drop boards",
    max_docs_pages=10,
    timeout=300,
    headless=False
)

print(f"Prototype URL: {result['steps']['prototype']['prototype_url']}")
```

### Using Agent Tools via Coordinator

```python
# The agent tools are automatically available when agent is registered
# Tools can be called through the coordinator or directly via agent.process()
```

### Content Storage

All workflow contents are automatically stored in:
```
test-workflow/playwright_storage/
├── documentation_YYYYMMDD_HHMMSS.json
├── prompt_YYYYMMDD_HHMMSS.json
├── prototype_YYYYMMDD_HHMMSS.json
└── workflow_YYYYMMDD_HHMMSS.json
```

## Configuration Options

### Content Storage Path

You can customize the storage path:

```python
agent = AgnoPlaywrightAgent(
    enable_rag=False,
    content_storage_path="/custom/path/to/storage"
)
```

### Browser Mode

Control headless mode in tool calls:

```python
# Headless mode (no visible browser)
result = await agent.prototype_generator.generate_prototype_with_browser(
    prompt=prompt,
    headless=True
)

# Visible browser (default)
result = await agent.prototype_generator.generate_prototype_with_browser(
    prompt=prompt,
    headless=False
)
```

## Workflow Details

### Step 1: Documentation Crawling
- Crawls `https://docs.lovable.dev/integrations/build-with-url`
- Follows related documentation links
- Extracts content for prompt optimization
- Stores in `documentation_*.json`

### Step 2: Prompt Generation
- Uses OpenAI GPT-4o-mini
- Incorporates documentation insights
- Creates Lovable.dev-ready prompts
- Stores in `prompt_*.json`

### Step 3: Prototype Generation
- Builds Lovable.dev URL with autosubmit parameter
- Opens browser with Playwright
- Waits for prototype generation
- Extracts prototype URL
- Stores in `prototype_*.json`

### Step 4: Complete Workflow Storage
- Stores all steps and results
- Includes timestamps and metadata
- Stores in `workflow_*.json`

## Error Handling

The agent handles:
- Missing dependencies (httpx, beautifulsoup4, playwright)
- OpenAI API errors
- Browser automation failures
- Login requirements (waits for manual login)
- Timeout scenarios

## Testing

Test the agent independently:

```python
import asyncio
from backend.agents.agno_playwright_agent import AgnoPlaywrightAgent

async def test_agent():
    agent = AgnoPlaywrightAgent(enable_rag=False)
    
    result = await agent.execute_full_workflow(
        product_description="A simple todo app",
        max_docs_pages=5,
        timeout=180,
        headless=False
    )
    
    print(json.dumps(result, indent=2))

asyncio.run(test_agent())
```

## Notes

- The agent stores all contents in `test-workflow/playwright_storage/` by default
- Browser automation requires Playwright and Chromium
- Login may be required - the agent waits for manual login if needed
- All workflow contents are stored for demo and test purposes
- The agent follows the same approach as `test-workflow/test_lovable_workflow.py`

## Integration Checklist

- [ ] Install dependencies (`playwright`, `beautifulsoup4`, `httpx`)
- [ ] Install Playwright browser (`playwright install chromium`)
- [ ] Configure `OPENAI_API_KEY` in `.env`
- [ ] Add agent to `AgnoCoordinatorAgent`
- [ ] Add agent to `AgnoEnhancedCoordinator`
- [ ] Add agent to `AgnoAgenticOrchestrator`
- [ ] Test agent independently
- [ ] Test agent via coordinator
- [ ] Verify content storage in `test-workflow/playwright_storage/`

