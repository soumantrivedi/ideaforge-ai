# IdeaForgeAI-v2 Improvements Implementation Plan

## High Priority Items (Must Implement)

### AGNO Framework Optimizations (High Priority)

1. **Add Performance Profiling & Metrics** (P1 - Critical)
   - Add metrics collection to agno_base_agent.py
   - Track agent call duration, token usage, tool calls
   - Add metrics endpoint

2. **Implement Model Tier Strategy** (P1 - Critical)
   - Fast models (gpt-4o-mini) for most agents
   - Standard models (gpt-4o) for coordinators
   - Premium models only for critical reasoning

3. **Implement Parallel Agent Execution** (P1 - Critical)
   - Use Agno Teams/Workflows with parallel execution
   - Run independent agents concurrently

4. **Limit Context & History** (P1 - Critical)
   - Limit to last 3 messages
   - Compress context
   - Compress tool results

5. **Add Response Caching** (P1 - Critical)
   - Cache identical queries
   - Use Redis for cache storage

### UI/UX Improvements (High Priority)

1. **Streaming Responses** (P1 - Critical)
   - WebSocket/SSE for real-time token display
   - Update EnhancedChatInterface

2. **Message Editing & Regeneration** (P1 - Critical)
   - Edit user messages
   - Regenerate agent responses
   - Message versioning

3. **Real-time Agent Activity Visualization** (P1 - Critical)
   - Live agent thinking indicators
   - Tool calls in real-time
   - Agent consultations visualization

## Medium Priority Items

### AGNO Framework Optimizations (Medium Priority)

1. **Optimize Tool Calls** (P2)
   - Add timeouts (10s)
   - Batch operations
   - Async HTTP clients

2. **Optimize RAG Retrieval** (P2)
   - Limit top_k to 3-5
   - Pre-filter by product_id
   - Minimum similarity threshold

3. **Disable Unnecessary Features** (P2)
   - Disable memory by default
   - Disable session summaries by default

4. **Limit Reasoning Steps** (P2)
   - Cap to 1-2 steps
   - Configurable per request

5. **Use Async Database Operations** (P2)
   - Verify all DB ops are async
   - Connection pooling

### UI/UX Improvements (Medium Priority)

1. **Enhanced Code & Content Formatting** (P2)
   - Syntax highlighting (Prism.js)
   - Code blocks with copy buttons
   - Mermaid diagrams
   - Math equations (KaTeX)

2. **Conversation History with Search** (P2)
   - Full-text search
   - Filters (date, product, agent)
   - Conversation tagging

3. **Keyboard Shortcuts & Command Palette** (P2)
   - Cmd+K command palette
   - Keyboard shortcuts for actions

4. **Agent Capability Preview & Selection** (P2)
   - Visual agent selector
   - Capability tags
   - Performance metrics

5. **File Attachments & Document Preview** (P2)
   - File upload in chat
   - Preview in messages
   - Extract text from PDFs

6. **Smooth Animations & Transitions** (P3)
   - Framer Motion or CSS animations
   - Message appearance animations

7. **Dark Mode** (P3)
   - Theme toggle
   - Persist preference

8. **Progress Indicators** (P3)
   - Detailed progress for long operations
   - Step-by-step progress

9. **Error Recovery & Retry** (P3)
   - Retry button on failed messages
   - Error categorization

## Implementation Order

1. Phase 1: Foundation (AGNO Performance)
   - Performance profiling
   - Model tier strategy
   - Response caching

2. Phase 2: Parallelization (AGNO)
   - Parallel agent execution
   - Tool optimization
   - Context limiting

3. Phase 3: UI Critical Features
   - Streaming responses
   - Message editing
   - Real-time agent activity

4. Phase 4: UI High-Value Features
   - Code formatting
   - Conversation search
   - Keyboard shortcuts

5. Phase 5: Polish
   - Animations
   - Dark mode
   - Progress indicators

