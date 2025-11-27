# Atlassian Agent Multi-Agent Integration

## Overview
The `AgnoAtlassianAgent` has been fully integrated into the multi-agent coordination system and can work seamlessly with Export and RAG agents.

## Integration Status: ✅ Complete

### 1. Coordinator Integration

#### AgnoCoordinatorAgent
- ✅ `AgnoAtlassianAgent` imported and initialized
- ✅ Registered in agents dictionary as `"atlassian_mcp"`
- ✅ Coordinator reference set for agent-to-agent communication
- ✅ Automatic selection in `determine_supporting_agents()` when Confluence/Jira keywords detected

#### AgnoEnhancedCoordinator
- ✅ `AgnoAtlassianAgent` imported and initialized
- ✅ Registered in agents dictionary as `"atlassian_mcp"`
- ✅ Coordinator reference set for agent-to-agent communication
- ✅ Automatic selection in `determine_supporting_agents()` when Confluence/Jira keywords detected
- ✅ RAG agent automatically included alongside Atlassian agent

#### AgnoAgenticOrchestrator
- ✅ `AgnoAtlassianAgent` already registered as `"atlassian_mcp"`
- ✅ Available for direct agent routing

### 2. Multi-Agent Coordination

#### Automatic Agent Selection
The Atlassian agent is automatically included as a supporting agent when queries contain:
- `confluence`
- `jira`
- `atlassian`
- `publish`
- `page`
- `space`
- `documentation`

#### Coordination Modes
The Atlassian agent works in all coordination modes:
- **Collaborative**: Consults with RAG and Export agents before responding
- **Sequential**: Can be part of a sequential agent chain
- **Parallel**: Can process in parallel with other agents
- **Enhanced Collaborative**: Full context sharing with RAG and Export agents

### 3. Integration with Export Agent

#### Use Cases
1. **PRD Publishing to Confluence**
   - Export agent generates PRD document
   - Atlassian agent publishes to Confluence space
   - Coordination: Export → Atlassian (sequential)

2. **Document Export with Confluence Context**
   - Atlassian agent retrieves Confluence pages
   - Export agent uses Confluence content in PRD generation
   - Coordination: Atlassian → Export (collaborative)

3. **Multi-Agent PRD Generation**
   - RAG agent retrieves knowledge base content
   - Atlassian agent retrieves Confluence documentation
   - Export agent synthesizes all sources into PRD
   - Coordination: RAG + Atlassian → Export (enhanced_collaborative)

### 4. Integration with RAG Agent

#### Use Cases
1. **Knowledge Base Enrichment**
   - Atlassian agent fetches Confluence pages
   - RAG agent stores content in vector database
   - Product-scoped storage for later retrieval

2. **Contextual Retrieval**
   - RAG agent searches knowledge base
   - Atlassian agent fetches additional Confluence content
   - Combined context for comprehensive responses

3. **Multi-Source Knowledge**
   - RAG agent: Local knowledge base + uploaded documents
   - Atlassian agent: Confluence pages and spaces
   - Coordinated retrieval for complete context

### 5. Agent Capabilities

#### AgnoAtlassianAgent Capabilities
- `confluence page access`
- `confluence space navigation`
- `page content retrieval`
- `confluence search`
- `documentation extraction`
- `confluence url processing`

#### RAG Support
- ✅ RAG enabled by default (`enable_rag=True`)
- ✅ Vector database table: `confluence_knowledge_base`
- ✅ Product-scoped knowledge storage

### 6. Example Multi-Agent Workflows

#### Workflow 1: PRD Generation with Confluence Integration
```
User Query: "Generate a PRD for Product X using Confluence page 12345"

1. RAG Agent: Retrieves relevant knowledge base content
2. Atlassian Agent: Fetches Confluence page 12345
3. Export Agent: Synthesizes all sources into ICAgile PRD
4. Atlassian Agent: Publishes PRD to Confluence space
```

#### Workflow 2: Document Export with Knowledge Base
```
User Query: "Export PRD and publish to Confluence space ABC"

1. RAG Agent: Retrieves all product knowledge base content
2. Export Agent: Generates comprehensive PRD
3. Atlassian Agent: Publishes to Confluence space ABC
```

#### Workflow 3: Knowledge Base Enrichment
```
User Query: "Add Confluence page 67890 to knowledge base for Product Y"

1. Atlassian Agent: Fetches Confluence page 67890
2. RAG Agent: Stores content in vector database (product-scoped)
3. Future queries automatically include this content
```

### 7. API Endpoints

#### Direct Agent Access
- `/api/agents/process` - Can route to `atlassian_mcp` agent
- `/api/multi-agent/process` - Can include `atlassian_mcp` in supporting agents

#### Export Integration
- `/api/export/{product_id}/export-prd` - Uses Export agent
- `/api/export/{product_id}/publish-to-confluence` - Uses Atlassian agent

#### Document Upload
- `/api/documents/upload-from-confluence` - Uses Atlassian agent + RAG agent

### 8. Configuration

#### Required Settings
- Atlassian credentials (email, API token)
- Confluence URL (optional, can use MCP server)
- Cloud ID (for Confluence API access)

#### RAG Configuration
- Vector database: PostgreSQL with pgvector extension
- Table: `confluence_knowledge_base` (product-scoped)
- Embedder: OpenAI, Anthropic, or Google (based on provider registry)

### 9. Verification

#### Code Locations
- `backend/agents/agno_atlassian_agent.py` - Agent implementation
- `backend/agents/agno_coordinator_agent.py` - Coordinator integration
- `backend/agents/agno_enhanced_coordinator.py` - Enhanced coordinator integration
- `backend/agents/agno_orchestrator.py` - Orchestrator registration
- `backend/api/export.py` - Export/Confluence publish endpoints
- `backend/api/documents.py` - Document upload endpoints

#### Test Commands
```python
# Test multi-agent coordination
POST /api/multi-agent/process
{
  "query": "Generate PRD using Confluence page 12345",
  "primary_agent": "export",
  "supporting_agents": ["atlassian_mcp", "rag"],
  "coordination_mode": "enhanced_collaborative"
}
```

### 10. Status Summary

✅ **Atlassian Agent**: Fully integrated  
✅ **Export Agent**: Can coordinate with Atlassian  
✅ **RAG Agent**: Can coordinate with Atlassian  
✅ **Multi-Agent**: All coordination modes supported  
✅ **Automatic Selection**: Keywords trigger agent inclusion  
✅ **RAG Support**: Vector database storage enabled  
✅ **Product-Scoped**: Knowledge base per product  

## Conclusion

The Atlassian agent is fully integrated into the multi-agent system and can seamlessly work with Export and RAG agents in all coordination modes. The integration supports automatic agent selection, context sharing, and coordinated workflows for comprehensive document generation and Confluence publishing.

