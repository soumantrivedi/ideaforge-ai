# Multi-Agent Collaboration System

## Overview

The IdeaForge AI platform now features a sophisticated multi-agent collaboration system that enables multiple AI agents to work together, consult each other, and provide comprehensive responses through various coordination modes.

## Key Features

### 🤝 Agent-to-Agent Communication

Agents can now:
- **Consult other agents** for specialized expertise
- **Share context** and collaborate on complex tasks
- **Track interactions** between agents for transparency
- **Delegate subtasks** to agents with specific capabilities

### 🎯 Multiple Coordination Modes

#### 1. **Sequential Mode** 📋
- Agents work one after another
- Each agent builds upon the previous agent's response
- Best for: Step-by-step problem solving, progressive refinement

#### 2. **Parallel Mode** ⚡
- All selected agents respond simultaneously
- Multiple perspectives provided at once
- Best for: Brainstorming, getting diverse viewpoints, comparing approaches

#### 3. **Collaborative Mode** 🤝 (Default)
- Primary agent consults supporting agents
- Agents share expertise behind the scenes
- Synthesized response from primary agent
- Best for: Complex questions requiring multiple domains

#### 4. **Debate Mode** ⚖️
- Multiple agents discuss and debate (2 rounds)
- Final synthesis agent combines perspectives
- Best for: Controversial topics, decision-making, thorough analysis

### 🎨 Modern, Sleek UI

- **Gradient-based design** inspired by modern AI interfaces
- **Real-time agent status** with activity indicators
- **Confidence scoring** for each agent's capability
- **Interaction tracking** showing agent collaboration
- **Responsive layout** optimized for all screen sizes

### 🧠 Enhanced Agent Capabilities

Each agent now has:
- **Capability scoring** - Confidence levels for different tasks
- **Interaction history** - Track all agent-to-agent communications
- **Dynamic routing** - Automatic selection of best agents for the task
- **Context awareness** - Access to full conversation and agent interactions

## Agent Network

### Available Agents (Agno Framework)

The IdeaForge AI platform uses the Agno framework with the following specialized agents:

1. **🔬 Research Agent** (`research`)
   - Role: In-depth research, market analysis, competitive intelligence
   - Confidence: High for research queries
   - Capabilities: Data gathering, trend analysis, sourcing, market research
   - RAG Enabled: Yes

2. **📊 Analysis Agent** (`analysis`)
   - Role: Data analysis, SWOT analysis, feasibility studies
   - Confidence: High for analytical tasks
   - Capabilities: Pattern recognition, statistical analysis, recommendations, risk assessment
   - RAG Enabled: Yes

3. **💡 Ideation Agent** (`ideation`)
   - Role: Brainstorming, idea generation, feature ideation
   - Confidence: High for creative ideation tasks
   - Capabilities: Creative thinking, feature brainstorming, innovation
   - RAG Enabled: Yes

4. **📝 PRD Authoring Agent** (`prd_authoring`)
   - Role: Product Requirements Document creation
   - Confidence: High for documentation tasks
   - Capabilities: PRD generation, requirement documentation, industry standards compliance
   - RAG Enabled: Yes

5. **📄 Summary Agent** (`summary`)
   - Role: Creating summaries from conversation sessions
   - Confidence: High for summarization tasks
   - Capabilities: Multi-session summarization, key point extraction, synthesis
   - RAG Enabled: Yes

6. **⭐ Scoring Agent** (`scoring`)
   - Role: Product idea scoring and evaluation
   - Confidence: High for scoring tasks
   - Capabilities: Idea evaluation, success probability, risk assessment, recommendations
   - RAG Enabled: Yes

7. **✅ Validation Agent** (`validation`)
   - Role: Validating AI-generated content and responses
   - Confidence: High for validation tasks
   - Capabilities: Content validation, quality checks, refinement suggestions
   - RAG Enabled: Yes

8. **📤 Export Agent** (`export`)
   - Role: Generating comprehensive PRD documents in HTML format
   - Confidence: High for export tasks
   - Capabilities: PRD export, HTML generation, markdown conversion, document synthesis
   - RAG Enabled: Yes

9. **📚 RAG Agent** (`rag`)
   - Role: Retrieval-Augmented Generation for knowledge base access
   - Confidence: High for knowledge queries
   - Capabilities: Vector search, document retrieval, context synthesis, knowledge base management
   - RAG Enabled: Always (core functionality)

10. **🎨 V0 Design Agent** (`v0`)
    - Role: Vercel V0 integration for UI prototype generation
    - Confidence: High for design tasks
    - Capabilities: V0 prompt generation, code generation, project creation, UI prototyping
    - RAG Enabled: Yes

11. **🎭 Lovable AI Agent** (`lovable`)
    - Role: Lovable AI integration for full prototype generation
    - Confidence: High for design tasks
    - Capabilities: Lovable prompt generation, thumbnail previews, project creation, prototype generation
    - RAG Enabled: Yes

12. **🐙 GitHub MCP Agent** (`github_mcp`)
    - Role: GitHub integration via MCP server
    - Confidence: High for GitHub-related tasks
    - Capabilities: Repository access, file retrieval, documentation extraction, code analysis
    - RAG Enabled: Yes

13. **🔷 Atlassian MCP Agent** (`atlassian_mcp`)
    - Role: Atlassian Confluence integration via MCP server
    - Confidence: High for Confluence-related tasks
    - Capabilities: Page retrieval, documentation access, knowledge extraction, Confluence search
    - RAG Enabled: Yes

### Agent Coordination

All agents are coordinated through the **AgnoEnhancedCoordinator** which:
- Routes queries to appropriate agents based on content analysis
- Enables agent-to-agent consultation and context sharing
- Tracks all agent interactions for transparency
- Provides comprehensive context from RAG, conversations, and phase submissions
- Supports multiple coordination modes (sequential, parallel, collaborative, debate, enhanced_collaborative)

## Architecture

### Database Schema

#### `agent_interactions` Table
```sql
CREATE TABLE agent_interactions (
  id uuid PRIMARY KEY,
  session_id uuid REFERENCES conversation_sessions(id),
  source_agent text NOT NULL,
  target_agent text NOT NULL,
  interaction_type text CHECK (interaction_type IN ('request', 'response', 'consultation', 'delegation')),
  message_id uuid REFERENCES agent_messages(id),
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now()
);
```

#### `multi_agent_sessions` Table
```sql
CREATE TABLE multi_agent_sessions (
  id uuid PRIMARY KEY,
  conversation_id uuid REFERENCES conversation_sessions(id),
  active_agents text[] NOT NULL DEFAULT '{}',
  coordination_mode text CHECK (coordination_mode IN ('sequential', 'parallel', 'collaborative', 'debate')),
  current_phase text DEFAULT 'ideation',
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
```

#### Enhanced `agent_messages` Table
```sql
ALTER TABLE agent_messages ADD COLUMN agent_type text;
ALTER TABLE agent_messages ADD COLUMN parent_message_id uuid REFERENCES agent_messages(id);
ALTER TABLE agent_messages ADD COLUMN is_internal boolean DEFAULT false;
ALTER TABLE agent_messages ADD COLUMN target_agent text;
```

### Core Classes

#### `EnhancedAgent`
Extends the base `ChatbotAgent` with:
- Capability definitions and scoring
- Agent-to-agent consultation methods
- Interaction tracking
- Confidence calculation

```typescript
class EnhancedAgent extends ChatbotAgent {
  canHandle(message: string): boolean
  getConfidence(message: string): number
  consultAgent(targetAgent, query, context): Promise<string>
  getInteractions(): AgentInteraction[]
}
```

#### `CollaborativeOrchestrator`
Manages multi-agent coordination:
- Agent selection and routing
- Coordination mode management
- Message processing across modes
- Context sharing between agents

```typescript
class CollaborativeOrchestrator {
  processMessage(message, history): Promise<MultiAgentMessage[]>
  setCoordinationMode(mode: CoordinationMode): void
  routeMessage(message, history): Promise<{agent, reason, allAgents}>
}
```

## Usage Examples

### Basic Collaborative Query

```typescript
// User asks a complex question
const message = "How can I build a scalable web application with good performance?";

// System automatically:
// 1. Routes to Code Expert as primary
// 2. Code Expert consults Research Specialist for architecture patterns
// 3. Code Expert consults Data Analyst for performance metrics
// 4. Code Expert synthesizes comprehensive response
```

### Parallel Mode for Brainstorming

```typescript
// Set coordination mode to parallel
orchestrator.setCoordinationMode('parallel');

// User asks for ideas
const message = "Give me creative ideas for a mobile app";

// All agents respond simultaneously:
// - General Assistant: Market analysis perspective
// - Research Specialist: Trend-based suggestions
// - Creative Writer: Innovative concepts
// - Data Analyst: Data-driven opportunities
```

### Debate Mode for Decision Making

```typescript
// Set coordination mode to debate
orchestrator.setCoordinationMode('debate');

// User asks a controversial question
const message = "Should we use microservices or monolithic architecture?";

// System orchestrates:
// Round 1: 3 agents present different viewpoints
// Round 2: Agents respond to each other
// Synthesis: General Agent combines insights
```

### Sequential Mode for Step-by-Step

```typescript
// Set coordination mode to sequential
orchestrator.setCoordinationMode('sequential');

// User requests multi-step process
const message = "Help me plan, design, and code a REST API";

// Agents work in sequence:
// 1. Research Specialist: API best practices
// 2. Data Analyst: Endpoint design patterns
// 3. Code Expert: Implementation code
```

## UI Components

### `EnhancedChatInterface`
Modern chat interface with:
- Gradient-based message bubbles
- Agent identification badges
- Interaction indicators
- Coordination mode selector
- Loading states with agent activity

### `AgentStatusPanel`
Real-time agent monitoring:
- Active agent indicators
- Confidence level bars
- Interaction counters
- Agent selection
- Status visualization

## Benefits

### For Users
- **Comprehensive Answers**: Multiple expert perspectives
- **Transparency**: See which agents are involved
- **Flexibility**: Choose coordination mode based on needs
- **Quality**: Agents verify and enhance each other's work

### For Developers
- **Extensible**: Easy to add new agents
- **Modular**: Clean separation of concerns
- **Tracked**: Full audit trail of interactions
- **Configurable**: Multiple coordination strategies

## Performance Optimizations

### Database
- ✅ Indexed foreign keys for agent interactions
- ✅ Optimized RLS policies with `(select auth.uid())`
- ✅ Efficient query patterns for agent data

### Frontend
- ✅ Lazy loading of agent modules
- ✅ Memoized component rendering
- ✅ Optimistic UI updates
- ✅ Efficient state management

### API
- ✅ Parallel agent processing where possible
- ✅ Streaming responses for real-time feedback
- ✅ Caching of agent capabilities
- ✅ Connection pooling for database

## Testing Recommendations

### Test Agent Collaboration
```typescript
// Test sequential mode
await testSequentialMode();

// Test parallel mode
await testParallelMode();

// Test collaborative consultations
await testCollaborativeMode();

// Test debate synthesis
await testDebateMode();
```

### Test Edge Cases
- Single agent available
- Network failures during consultation
- Conflicting agent responses
- High load with many simultaneous agents

### Performance Testing
- Response time with multiple agents
- Database query performance
- Memory usage during debates
- Concurrent user sessions

## Configuration

### Environment Variables
```env
# API Configuration
VITE_API_URL=http://localhost:8000

# Optional: Okta OAuth/SSO (for enterprise authentication)
VITE_OKTA_CLIENT_ID=your_okta_client_id
VITE_OKTA_ISSUER=your_okta_issuer
```

### API Keys (in Settings)
- OpenAI API Key (required for embeddings and GPT models)
- Claude API Key (optional, for Anthropic models)
- Gemini API Key (optional, for Google models)

## Migration Path

### From Old System
1. ✅ Database migration applied (`add_agent_interaction_support`)
2. ✅ New agent classes extend existing `ChatbotAgent`
3. ✅ Old agent configurations still work
4. ✅ Backward compatible API

### New Features
1. ✅ Agent-to-agent communication
2. ✅ Multiple coordination modes
3. ✅ Enhanced UI components
4. ✅ Interaction tracking
5. ✅ Capability scoring

## Future Enhancements

### Planned Features
- [ ] Custom agent creation
- [ ] Agent memory and learning
- [ ] Cross-session agent knowledge
- [ ] Agent performance analytics
- [ ] Voice interface for agents
- [ ] Multi-modal agent capabilities (images, files)
- [ ] Agent marketplace
- [ ] Fine-tuned domain-specific agents

### UI Improvements
- [ ] Agent conversation graphs
- [ ] Real-time collaboration visualization
- [ ] Agent personality customization
- [ ] Dark mode
- [ ] Mobile app

### Advanced Coordination
- [ ] Hierarchical agent structures
- [ ] Dynamic agent teams
- [ ] Auction-based task allocation
- [ ] Consensus mechanisms
- [ ] Conflict resolution protocols

## Troubleshooting

### Agents Not Responding
1. Check API keys are configured
2. Verify database connection
3. Check browser console for errors
4. Ensure the PostgreSQL initialization script (`init-db/01-init-schema.sql`) has run

### Slow Response Times
1. Check network connection
2. Verify coordination mode (parallel can be faster)
3. Monitor database performance
4. Check API rate limits

### Missing Agent Interactions
1. Verify the relevant `product_id` exists and the request includes it
2. Check `agent_activity_log` / `conversation_history` tables for entries
3. Ensure coordination mode supports interactions
4. Look for console warnings

## Support

For issues or questions:
1. Check browser console for errors
2. Verify all migrations applied
3. Test with different coordination modes
4. Review agent status panel for active agents

## Conclusion

The multi-agent collaboration system transforms IdeaForge AI into a powerful platform where specialized AI agents work together seamlessly. Whether you need deep research, creative brainstorming, technical implementation, or comprehensive analysis, the agent network provides expert assistance through intelligent coordination.

---

**Version**: 2.0.0
**Last Updated**: 2025-01-15
**Status**: ✅ Production Ready
