# Multi-Agent Memory and Conversation History

## Overview

The IdeaForge-AI orchestrator maintains a shared multi-agent memory that stores all chatbot conversations and makes them available to all agents. This allows users to provide ideation externally or any other content relevant for product lifecycle phases, and the multi-agent system will automatically use this information when processing requests.

## How It Works

### Shared Context Storage

The `AgnoEnhancedCoordinator` maintains a `shared_context` dictionary that stores:

- **Conversation History**: All chatbot messages for a product
- **Ideation Content**: Extracted ideation and product concepts from conversations
- **User Inputs**: All user inputs from the chatbot
- **Product Context**: Product-specific metadata and context
- **Phase Context**: Lifecycle phase-specific information

### Automatic Loading

When a request is made with a `product_id`, the orchestrator automatically:

1. Loads conversation history from the database
2. Extracts ideation-related content
3. Stores everything in shared context
4. Makes it available to all agents

### Agent Access

All agents automatically receive:

- Full conversation history
- Extracted ideation content
- User inputs summary
- Previous agent interactions

This context is included in every agent query, ensuring continuity and context awareness.

## Usage

### Providing Ideation Externally

Users can provide ideation through the chatbot interface. The orchestrator will:

1. Store the conversation in the database
2. Extract ideation keywords and concepts
3. Make them available to all agents automatically

### Accessing Any Lifecycle Phase

Since phases are no longer locked, users can:

1. Provide ideation in the chatbot
2. Navigate to any lifecycle phase
3. The agents will automatically use the ideation from chatbot conversations

### Example Flow

```
1. User provides ideation in chatbot:
   "I want to build a mobile app for fitness tracking"

2. User navigates to Research phase:
   - Research agent automatically receives the ideation
   - Uses it to generate relevant research queries

3. User navigates to Design phase:
   - Design agent automatically receives the ideation
   - Uses it to generate design prompts
```

## Implementation Details

### Coordinator Methods

- `load_conversation_history()`: Loads conversation history from database
- `_extract_ideation_from_history()`: Extracts ideation-related content
- `_build_comprehensive_context()`: Builds context including conversation history
- `_enhance_query_with_context()`: Enhances queries with conversation history

### Database Integration

Conversation history is stored in the `conversation_history` table with:
- `product_id`: Links conversations to products
- `message_type`: Role (user, assistant, agent)
- `content`: Message content
- `agent_name`: Which agent generated the response
- `created_at`: Timestamp

### Context Enhancement

Every agent query is enhanced with:

```
=== CONVERSATION HISTORY (Multi-Agent Memory) ===
All previous chatbot interactions for this product:
[Last 20 messages with roles and content]

=== IDEATION FROM CHATBOT ===
Relevant ideation and product concepts from previous conversations:
[Extracted ideation content]

=== USER INPUTS SUMMARY ===
Total user inputs: X
Recent user inputs:
[Last 5 user inputs]
```

## Benefits

1. **No Data Loss**: All chatbot conversations are preserved and used
2. **Context Continuity**: Agents always have full context
3. **Flexible Workflow**: Users can provide information in any order
4. **Automatic Integration**: No manual steps required
5. **Multi-Agent Coordination**: All agents share the same context

## Configuration

The shared context is automatically managed by the orchestrator. No additional configuration is required.

## Troubleshooting

### Conversation History Not Loading

- Check database connectivity
- Verify `product_id` is provided in requests
- Check logs for database query errors

### Ideation Not Being Used

- Ensure conversation contains ideation keywords
- Check that `product_id` matches the conversation
- Verify shared context is being built correctly

## Related Documentation

- [Flexible Lifecycle and Export](./flexible-lifecycle-and-export.md)
- [Multi-Agent System](./multi-agent-system.md)
- [Product Lifecycle](./product-lifecycle.md)

