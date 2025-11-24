# Multi-Agent Backend System

## Overview

The IdeaForge AI backend now features a comprehensive multi-agent system based on patterns from `awesome-ai-apps/advance_ai_agents`. This system enables multiple specialized AI agents to work together, consult each other, and provide comprehensive responses through various coordination modes.

## Architecture

### Core Components

1. **Coordinator Agent** (`coordinator_agent.py`)
   - Routes queries to appropriate agents
   - Enables agent-to-agent communication
   - Manages coordination modes
   - Tracks agent interactions

2. **Specialized Agents**
   - **Research Agent**: Market research, competitive analysis, trend analysis
   - **Analysis Agent**: SWOT analysis, requirements analysis, strategic analysis
   - **Validation Agent**: PRD validation, quality assurance, compliance checking
   - **Strategy Agent**: Strategic planning, roadmap development, GTM strategy
   - **Ideation Agent**: Brainstorming, feature generation, creative exploration
   - **PRD Authoring Agent**: PRD creation following McKinsey CodeBeyond standards
   - **Jira Agent**: Jira integration, epic/story creation

3. **Orchestrator** (`orchestrator.py`)
   - Manages agent lifecycle
   - Provides API for multi-agent coordination
   - Handles workflows and collaborative tasks

## Coordination Modes

### 1. Sequential Mode
Agents work one after another, with each agent building upon the previous agent's response.

**Use Cases:**
- Step-by-step problem solving
- Progressive refinement
- Multi-stage workflows

**Example:**
```python
request = MultiAgentRequest(
    user_id=user_id,
    query="Create a PRD and convert it to Jira tickets",
    coordination_mode="sequential",
    primary_agent="prd_authoring",
    supporting_agents=["jira_integration"]
)
```

### 2. Parallel Mode
All selected agents respond simultaneously, providing multiple perspectives at once.

**Use Cases:**
- Brainstorming
- Getting diverse viewpoints
- Comparing approaches

**Example:**
```python
request = MultiAgentRequest(
    user_id=user_id,
    query="Analyze this product idea from multiple perspectives",
    coordination_mode="parallel",
    primary_agent="ideation",
    supporting_agents=["research", "analysis", "strategy"]
)
```

### 3. Collaborative Mode (Default)
Primary agent consults supporting agents behind the scenes and synthesizes their responses.

**Use Cases:**
- Complex questions requiring multiple domains
- Comprehensive analysis
- Multi-faceted problem solving

**Example:**
```python
request = MultiAgentRequest(
    user_id=user_id,
    query="Develop a comprehensive product strategy",
    coordination_mode="collaborative",
    primary_agent="strategy",
    supporting_agents=["research", "analysis"]
)
```

### 4. Debate Mode
Multiple agents discuss and debate (2 rounds), with a final synthesis agent combining perspectives.

**Use Cases:**
- Controversial topics
- Decision-making
- Thorough analysis with multiple viewpoints

**Example:**
```python
request = MultiAgentRequest(
    user_id=user_id,
    query="Should we prioritize feature A or feature B?",
    coordination_mode="debate",
    primary_agent="strategy",
    supporting_agents=["analysis", "research"]
)
```

## Agent Capabilities

Each agent has specific capabilities and can be queried for their expertise:

### Research Agent
- Market research
- Competitive analysis
- Trend analysis
- User research
- Feasibility studies
- Benchmarking

### Analysis Agent
- Requirements analysis
- SWOT analysis
- Feasibility analysis
- Risk analysis
- Cost-benefit analysis
- Performance analysis

### Validation Agent
- PRD validation
- Requirements validation
- Quality assurance
- Compliance checking
- Standards validation

### Strategy Agent
- Strategic planning
- Roadmap development
- Go-to-market strategy
- Business model design
- Competitive positioning

### Ideation Agent
- Brainstorming
- Feature generation
- Creative exploration
- Opportunity identification

### PRD Authoring Agent
- PRD creation
- Requirements documentation
- Technical specifications
- User stories

### Jira Agent
- Epic creation
- Story creation
- Ticket management
- Work breakdown

## API Endpoints

### List All Agents
```http
GET /api/agents
```

Returns list of all available agents with their names and roles.

### Get Agent Capabilities
```http
GET /api/agents/capabilities
```

Returns detailed capabilities of all agents.

### Process Multi-Agent Request
```http
POST /api/multi-agent/process
Content-Type: application/json

{
  "user_id": "uuid",
  "product_id": "uuid (optional)",
  "query": "Your query here",
  "coordination_mode": "collaborative",
  "primary_agent": "strategy",
  "supporting_agents": ["research", "analysis"],
  "context": {}
}
```

### Get Agent Interactions
```http
GET /api/multi-agent/interactions
```

Returns recent agent-to-agent interactions for transparency.

## Agent-to-Agent Communication

Agents can consult each other for specialized expertise:

```python
# Inside an agent's process method
research_result = await self.consult_agent(
    target_agent_type="research",
    query="What are the latest market trends in this domain?",
    context={"product_domain": "AI/ML"}
)
```

The coordinator tracks all agent interactions for transparency and debugging.

## Usage Examples

### Example 1: Comprehensive Product Strategy
```python
from backend.models.schemas import MultiAgentRequest

request = MultiAgentRequest(
    user_id=user_id,
    product_id=product_id,
    query="Develop a comprehensive product strategy for an AI-powered project management tool",
    coordination_mode="collaborative",
    primary_agent="strategy",
    supporting_agents=["research", "analysis", "validation"]
)

response = await orchestrator.process_multi_agent_request(user_id, request)
```

### Example 2: PRD Creation with Validation
```python
request = MultiAgentRequest(
    user_id=user_id,
    product_id=product_id,
    query="Create a PRD for user authentication features",
    coordination_mode="sequential",
    primary_agent="prd_authoring",
    supporting_agents=["validation"]
)
```

### Example 3: Multi-Perspective Analysis
```python
request = MultiAgentRequest(
    user_id=user_id,
    query="Analyze the feasibility of implementing real-time collaboration",
    coordination_mode="parallel",
    primary_agent="analysis",
    supporting_agents=["research", "validation"]
)
```

## Integration with Existing System

The multi-agent system integrates seamlessly with the existing backend:

1. **Existing Agents**: PRD Authoring, Ideation, and Jira agents are now part of the coordinator system
2. **Backward Compatibility**: Single-agent requests still work through `/api/agents/process`
3. **Workflows**: Existing workflows (idea-to-jira, prd-to-jira) continue to function
4. **Database**: Agent interactions are tracked and can be stored in the database

## Configuration

Agent behavior can be configured through:

1. **Environment Variables**: AI provider API keys, model selection
2. **Agent Prompts**: System prompts define each agent's behavior
3. **Coordination Logic**: Coordinator determines agent routing based on query analysis

## Best Practices

1. **Choose Appropriate Mode**: Select coordination mode based on task complexity
2. **Specify Agents**: Explicitly specify primary and supporting agents for better control
3. **Provide Context**: Include relevant context for better agent responses
4. **Monitor Interactions**: Review agent interactions to understand collaboration patterns
5. **Iterate**: Use sequential mode for iterative refinement

## Future Enhancements

- [ ] Agent learning from interactions
- [ ] Dynamic agent selection based on performance
- [ ] Agent specialization through fine-tuning
- [ ] Real-time agent collaboration visualization
- [ ] Agent performance metrics and analytics

## References

This implementation is based on patterns from:
- `awesome-ai-apps/multi-agent-sre-bot` - Coordinator-based architecture
- `awesome-ai-apps/advance_ai_agents` - Specialized agent patterns
- `awesome-ai-apps/course/aws_strands/06_multi_agent_pattern` - Agent as tools pattern

