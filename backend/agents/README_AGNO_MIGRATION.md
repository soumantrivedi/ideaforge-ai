# Agno Framework Migration Guide

This document describes the complete migration to Agno framework for consistent agent patterns.

## Overview

The codebase now supports two agent frameworks:
1. **Legacy Framework**: Original custom implementation (still available for backward compatibility)
2. **Agno Framework**: New standardized framework with RAG support (recommended)

## Architecture

### Agno Base Agent (`agno_base_agent.py`)

Extensible base class for all Agno-based agents:
- Model-agnostic (OpenAI, Claude, Gemini)
- Optional RAG support with pgvector
- Built-in knowledge base integration
- Extensible tool support
- Agent-to-agent consultation

### RAG Agent (`rag_agent.py`)

Specialized agent for knowledge retrieval:
- Vector database (pgvector) integration
- Semantic search capabilities
- Knowledge base management
- Document retrieval and synthesis

### Agno Coordinator (`agno_coordinator_agent.py`)

Multi-agent coordination using Agno Teams:
- Collaborative mode: Primary agent consults supporting agents
- Sequential mode: Agents work one after another
- Parallel mode: All agents respond simultaneously
- Built-in team management

## Usage

### Enabling Agno Framework

Set the feature flag in `.env`:
```bash
FEATURE_AGNO_FRAMEWORK=true
```

### Creating a New Agent

```python
from backend.agents.agno_base_agent import AgnoBaseAgent

class MyCustomAgent(AgnoBaseAgent):
    def __init__(self, enable_rag: bool = False):
        system_prompt = """Your agent instructions here..."""
        
        super().__init__(
            name="My Custom Agent",
            role="my_agent",
            system_prompt=system_prompt,
            enable_rag=enable_rag,  # Enable RAG if needed
            rag_table_name="my_agent_knowledge",  # Custom table name
            capabilities=["capability1", "capability2"]  # For routing
        )
```

### Using RAG Agent

```python
from backend.agents.rag_agent import RAGAgent

rag_agent = RAGAgent()

# Search knowledge base
results = await rag_agent.search_knowledge("query", top_k=5)

# Add to knowledge base
await rag_agent.add_knowledge("content", metadata={"source": "doc"})
```

## Vector Database Setup

The system uses PostgreSQL with pgvector extension (already configured in docker-compose.yml).

### Knowledge Base Tables

Each agent with RAG enabled creates its own table:
- `rag_knowledge_base` - RAG agent
- `prd_knowledge_base` - PRD agent
- `research_knowledge_base` - Research agent
- etc.

### Adding Content to Knowledge Base

```python
agent = AgnoPRDAuthoringAgent(enable_rag=True)
agent.add_to_knowledge_base(
    content="Your document content here",
    metadata={
        "product_id": "uuid",
        "source": "prd",
        "title": "Document Title"
    }
)
```

## Migration Status

✅ **Completed:**
- Agno base agent framework
- RAG agent with pgvector
- PRD Authoring Agent (Agno)
- Ideation Agent (Agno)
- Research Agent (Agno)
- Analysis Agent (Agno)
- Coordinator Agent (Agno Teams)
- Orchestrator (Agno)

🔄 **In Progress:**
- Additional agents (Jira, Validation, Strategy, etc.)
- Full integration testing

📝 **Legacy Support:**
- Original agents still available
- Automatic fallback if Agno unavailable
- Feature flag to toggle frameworks

## Extensibility

### Adding Custom Tools

```python
from agno.tools import tool

@tool
def my_custom_tool(param: str) -> str:
    """Tool description for agent."""
    return f"Processed: {param}"

# Use in agent
agent = AgnoBaseAgent(
    name="Agent",
    role="agent",
    system_prompt="...",
    tools=[my_custom_tool]
)
```

### Custom Knowledge Base

```python
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector

custom_kb = Knowledge(
    vector_db=PgVector(
        table_name="custom_table",
        db_url=settings.database_url
    ),
    embedder=OpenAIEmbedder()
)

agent = AgnoBaseAgent(
    name="Agent",
    role="agent",
    system_prompt="...",
    knowledge_base=custom_kb
)
```

## Testing

```bash
# Test Agno framework
python -m pytest backend/tests/test_agno_agents.py

# Test RAG functionality
python -m pytest backend/tests/test_rag_agent.py
```

## Troubleshooting

### Agno Not Available

If you see `ImportError: Agno framework is not available`:
```bash
pip install agno>=2.0.0
```

### Vector Database Issues

Ensure pgvector extension is enabled:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### RAG Not Working

1. Check database connection
2. Verify embedder API keys
3. Check table exists: `SELECT * FROM rag_knowledge_base LIMIT 1;`

## Next Steps

1. Migrate remaining agents (Jira, Validation, Strategy)
2. Add more specialized tools
3. Enhance RAG with better chunking strategies
4. Add evaluation metrics
5. Production deployment with AgentOS

