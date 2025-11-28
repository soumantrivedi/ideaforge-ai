# Agent Development Guide

Complete guide for developing, testing, and deploying AI agents in IdeaForge AI.

## Overview

IdeaForge AI uses a multi-agent architecture where specialized agents collaborate to handle different aspects of product management. Agents are built using the Agno framework and can communicate with each other, share context, and work together on complex tasks.

## Agent Architecture

### Base Agent Structure

All agents inherit from `AgnoBaseAgent` which provides:

- **Provider Management**: Automatic API key handling and provider selection
- **Memory System**: Context retention across conversations
- **Tool System**: Structured tools for agent capabilities
- **Error Handling**: Robust error handling and retry logic
- **Logging**: Comprehensive logging for debugging

### Agent Types

1. **Specialized Agents**: Handle specific domains (Ideation, Research, Analysis, etc.)
2. **Coordinator Agents**: Orchestrate multi-agent workflows
3. **Integration Agents**: Connect with external services (Jira, Confluence, GitHub, V0)

## Creating a New Agent

### Step 1: Create Agent File

Create a new file in `backend/agents/`:

```python
# backend/agents/agno_my_agent.py

from backend.agents.agno_base_agent import AgnoBaseAgent
from agno import Agent
from typing import Optional, Dict, Any

class AgnoMyAgent(AgnoBaseAgent):
    """My custom agent for specific tasks."""
    
    def __init__(self, user_id: Optional[str] = None):
        super().__init__(
            name="my_agent",
            description="Description of what this agent does",
            user_id=user_id
        )
    
    def get_agent(self) -> Agent:
        """Create and configure the Agno agent."""
        agent = Agent(
            name=self.name,
            description=self.description,
            model=self.get_model(),
            instructions=self.get_instructions(),
            tools=self.get_tools(),
            markdown=True,
            show_tool_calls=True
        )
        return agent
    
    def get_instructions(self) -> str:
        """Agent-specific instructions."""
        return """
        You are a specialized agent for [specific task].
        Your responsibilities include:
        - Task 1
        - Task 2
        - Task 3
        """
    
    def get_tools(self) -> list:
        """Agent-specific tools."""
        return [
            # Add your tools here
        ]
```

### Step 2: Register Agent

Add your agent to the agent registry in `backend/api/agents.py`:

```python
from backend.agents.agno_my_agent import AgnoMyAgent

# In the agent registry
AGENT_REGISTRY = {
    # ... existing agents
    "my_agent": AgnoMyAgent,
}
```

### Step 3: Add Agent Tools

Tools allow agents to perform actions. Example:

```python
from agno.tools import Toolkit
from agno.tool import tool

class MyAgentToolkit(Toolkit):
    """Tools for my agent."""
    
    @tool
    def my_custom_tool(self, param1: str, param2: int) -> str:
        """Description of what this tool does.
        
        Args:
            param1: Description of param1
            param2: Description of param2
            
        Returns:
            Description of return value
        """
        # Tool implementation
        return f"Result: {param1} {param2}"

# In your agent class
def get_tools(self) -> list:
    return [MyAgentToolkit()]
```

### Step 4: Test Agent

```python
# backend/test_my_agent.py

import asyncio
from backend.agents.agno_my_agent import AgnoMyAgent

async def test_agent():
    agent = AgnoMyAgent(user_id="test-user")
    
    response = await agent.run(
        messages=[{"role": "user", "content": "Test query"}]
    )
    
    print(response.content)

if __name__ == "__main__":
    asyncio.run(test_agent())
```

## Agent Communication

### Agent-to-Agent Consultation

Agents can consult other agents:

```python
from backend.agents.agno_base_agent import AgnoBaseAgent

class MyAgent(AgnoBaseAgent):
    async def consult_other_agent(self, agent_name: str, query: str):
        """Consult another agent."""
        from backend.api.agents import get_agent_instance
        
        other_agent = get_agent_instance(agent_name, self.user_id)
        response = await other_agent.run(
            messages=[{"role": "user", "content": query}]
        )
        return response.content
```

### Multi-Agent Coordination

Use the coordinator agent for multi-agent workflows:

```python
from backend.agents.agno_enhanced_coordinator import AgnoEnhancedCoordinator

coordinator = AgnoEnhancedCoordinator(user_id="user-id")

response = await coordinator.coordinate(
    query="Complex query requiring multiple agents",
    coordination_mode="enhanced_collaborative",
    primary_agent="ideation",
    supporting_agents=["research", "analysis"]
)
```

## Agent Tools

### Database Tools

```python
from backend.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

@tool
async def get_product_info(self, product_id: str) -> Dict[str, Any]:
    """Get product information from database."""
    async for db in get_db():
        # Database query
        product = await db.get(Product, product_id)
        return {
            "id": product.id,
            "name": product.name,
            # ... other fields
        }
```

### API Tools

```python
import httpx

@tool
async def call_external_api(self, url: str, data: Dict) -> Dict:
    """Call external API."""
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data)
        return response.json()
```

### File Tools

```python
from pathlib import Path

@tool
def read_file(self, file_path: str) -> str:
    """Read file from filesystem."""
    path = Path(file_path)
    if not path.exists():
        raise ValueError(f"File not found: {file_path}")
    return path.read_text()
```

## Agent Testing

### Unit Tests

```python
# tests/test_my_agent.py

import pytest
from backend.agents.agno_my_agent import AgnoMyAgent

@pytest.mark.asyncio
async def test_my_agent_basic():
    agent = AgnoMyAgent(user_id="test-user")
    response = await agent.run(
        messages=[{"role": "user", "content": "Test"}]
    )
    assert response.content is not None
    assert len(response.content) > 0
```

### Integration Tests

```python
# tests/integration/test_agent_workflow.py

@pytest.mark.asyncio
async def test_multi_agent_workflow():
    from backend.agents.agno_enhanced_coordinator import AgnoEnhancedCoordinator
    
    coordinator = AgnoEnhancedCoordinator(user_id="test-user")
    response = await coordinator.coordinate(
        query="Test query",
        coordination_mode="collaborative",
        primary_agent="ideation",
        supporting_agents=["research"]
    )
    
    assert response is not None
    assert "content" in response or hasattr(response, 'content')
```

## Agent Configuration

### Model Selection

```python
def get_model(self) -> str:
    """Select model for this agent."""
    # Use primary model from config
    return self.settings.agent_model_primary
    
    # Or use specific model
    # return "gpt-4"
```

### Timeout Configuration

```python
# In backend/config.py
AGENT_RESPONSE_TIMEOUT: float = 180.0  # 3 minutes

# Agent will respect this timeout
```

### Provider Selection

Agents automatically select providers based on:
1. User-configured API keys
2. Provider availability
3. Model compatibility

## Agent Memory

### Context Retention

```python
# Agents automatically retain context within a session
agent = AgnoMyAgent(user_id="user-id")

# First message
response1 = await agent.run(
    messages=[{"role": "user", "content": "What is X?"}]
)

# Second message (agent remembers previous context)
response2 = await agent.run(
    messages=[{"role": "user", "content": "Tell me more about it"}]
)
```

### Memory Management

```python
# Clear agent memory
agent.clear_memory()

# Get conversation history
history = agent.get_conversation_history()
```

## Error Handling

### Provider Errors

```python
try:
    response = await agent.run(messages)
except ValueError as e:
    if "API key" in str(e):
        # Handle API key error
        pass
    elif "credits" in str(e):
        # Handle credits error
        pass
```

### Timeout Handling

```python
import asyncio

try:
    response = await asyncio.wait_for(
        agent.run(messages),
        timeout=180.0
    )
except asyncio.TimeoutError:
    # Handle timeout
    pass
```

## Agent Logging

### Structured Logging

```python
from backend.agents.agno_base_agent import AgnoBaseAgent

class MyAgent(AgnoBaseAgent):
    async def run(self, messages):
        self.logger.info(
            "agent_request",
            agent=self.name,
            user_id=self.user_id,
            message_count=len(messages)
        )
        
        response = await super().run(messages)
        
        self.logger.info(
            "agent_response",
            agent=self.name,
            user_id=self.user_id,
            response_length=len(response.content)
        )
        
        return response
```

## Best Practices

1. **Clear Instructions**: Write clear, specific instructions for your agent
2. **Tool Descriptions**: Provide detailed tool descriptions with examples
3. **Error Handling**: Always handle errors gracefully
4. **Logging**: Log important events for debugging
5. **Testing**: Write tests for your agent
6. **Documentation**: Document agent capabilities and usage
7. **Resource Management**: Clean up resources (database connections, HTTP clients)
8. **Async Operations**: Use async/await for I/O operations

## Example: Complete Agent

```python
from backend.agents.agno_base_agent import AgnoBaseAgent
from agno import Agent
from agno.tools import Toolkit
from agno.tool import tool
from typing import Optional, Dict, Any

class MyToolkit(Toolkit):
    @tool
    def process_data(self, data: str) -> str:
        """Process input data.
        
        Args:
            data: Input data to process
            
        Returns:
            Processed data
        """
        return f"Processed: {data}"

class AgnoMyAgent(AgnoBaseAgent):
    """My custom agent."""
    
    def __init__(self, user_id: Optional[str] = None):
        super().__init__(
            name="my_agent",
            description="Agent for processing data",
            user_id=user_id
        )
    
    def get_agent(self) -> Agent:
        return Agent(
            name=self.name,
            description=self.description,
            model=self.get_model(),
            instructions=self.get_instructions(),
            tools=[MyToolkit()],
            markdown=True
        )
    
    def get_instructions(self) -> str:
        return """
        You are a data processing agent.
        Your role is to process and analyze data.
        Use the process_data tool to process user input.
        """
```

## Additional Resources

- [Multi-Agent System Guide](./multi-agent-system.md)
- [Agno Framework Documentation](https://agno.readthedocs.io/)
- [Agent Base Implementation](../architecture/04-multi-agent-orchestration.md)
- [Tool Development Guide](./tool-development.md) (if exists)

