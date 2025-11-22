# IdeaForge AI - Multi-Agent Collaboration Platform
## Advanced AI System with Agent-to-Agent Communication

A sophisticated multi-agent AI platform where specialized agents collaborate in real-time, featuring multiple coordination modes, RAG (Retrieval Augmented Generation), and a modern, intuitive interface inspired by leading AI tools.

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![Status](https://img.shields.io/badge/status-production--ready-green)
![Build](https://img.shields.io/badge/build-passing-brightgreen)

## 🚀 Quick Start

```bash
# 1. Start the platform
docker-compose up -d

# 2. Access at http://localhost:3000

# 3. Configure API keys in Settings

# 4. Start chatting with multiple AI agents!
```

**📖 Full Guide**: See [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md) for detailed instructions

---

## ✨ Key Features

### 🤝 Multi-Agent Collaboration
- **Agent-to-agent communication** - Agents consult each other for specialized expertise
- **4 coordination modes** - Sequential, Parallel, Collaborative, and Debate
- **Real-time interaction tracking** - See how agents work together
- **Dynamic agent selection** - Automatic routing based on query analysis and confidence scoring
- **Context sharing** - Agents seamlessly share information and build on each other's responses

### 🎯 Coordination Modes

1. **🤝 Collaborative Mode** (Default)
   - Primary agent consults supporting agents
   - Synthesized comprehensive response
   - Best for: Complex questions requiring multiple domains

2. **⚡ Parallel Mode**
   - All agents respond simultaneously
   - Multiple perspectives at once
   - Best for: Brainstorming, diverse viewpoints

3. **📋 Sequential Mode**
   - Agents work one after another
   - Progressive refinement
   - Best for: Step-by-step processes

4. **⚖️ Debate Mode**
   - Multi-round discussion between agents
   - Final synthesis of perspectives
   - Best for: Decision-making, controversial topics

### 🤖 Six Specialized AI Agents
Each agent has unique capabilities and confidence scoring:

1. **🤖 General Assistant** - Versatile helper, task coordination, broad knowledge
2. **🔬 Research Specialist** - Deep research, trend analysis, information gathering
3. **💻 Code Expert** - Programming, debugging, code review, optimization
4. **✨ Creative Writer** - Content creation, storytelling, creative exploration
5. **📊 Data Analyst** - Business intelligence, metrics, data-driven insights
6. **📚 Knowledge Retrieval Agent** - RAG-powered responses with knowledge base access

### 🎨 Modern, Sleek UI
- **Gradient-based design** inspired by contemporary AI tools
- **Real-time agent status panel** with activity monitoring
- **Confidence indicators** showing agent expertise levels
- **Interaction badges** displaying agent collaboration
- **Smooth animations** and responsive layout
- **Enhanced chat interface** with color-coded agent responses

### 🧠 Multi-Provider AI Integration
- **OpenAI GPT-4** - Industry-leading language models
- **Anthropic Claude Sonnet** - Advanced reasoning and analysis
- **Google Gemini 2.0** - Latest multimodal AI capabilities
- Seamless provider switching and intelligent fallback
- Unified API interface across all providers
- Streaming responses for real-time interaction

### RAG (Retrieval Augmented Generation) System
- **Vector embeddings** using OpenAI's `text-embedding-3-small` model
- **Semantic search** with cosine similarity matching
- **Knowledge base management** - Add, update, search, and delete documents
- **Automatic context injection** into agent conversations
- **Supabase pgvector** integration for scalable, production-ready storage
- **Full-text search** as fallback option

### MCP (Model Context Protocol) Server
- **Resources** - Structured access to chat history, knowledge base, documents
- **Tools** - Search knowledge base, save documents, retrieve chat context
- **Stdio transport** for local development and testing
- Full MCP 2025 specification compliance
- Ready for integration with Claude Code, VS Code, and other MCP clients

### Smart Features
- **Intelligent agent routing** based on message content analysis
- **Conversation history** with timestamps and metadata
- **Real-time streaming** responses from all providers
- **Provider status** indicators and health checks
- **Local API key storage** for maximum privacy
- **Responsive design** optimized for desktop and mobile
- **Dark mode ready** interface components

---

## Architecture

### System Diagram
```
┌─────────────────────────────────────────────────────────────┐
│                    React Frontend                            │
│  ┌────────────┐  ┌────────────┐  ┌─────────────────────┐  │
│  │   Chat UI  │  │   Agent    │  │  Knowledge Base     │  │
│  │ Interface  │  │  Selector  │  │    Manager          │  │
│  └────────────┘  └────────────┘  └─────────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────┐
│             Multi-Agent Orchestrator                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ General  │ │ Research │ │  Coding  │ │ Creative │  ... │
│  │  Agent   │ │  Agent   │ │  Agent   │ │  Agent   │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────┐
│            AI Provider Manager                               │
│  ┌─────────┐     ┌─────────┐     ┌──────────┐             │
│  │ OpenAI  │     │ Claude  │     │  Gemini  │             │
│  │   API   │     │   API   │     │   API    │             │
│  └─────────┘     └─────────┘     └──────────┘             │
└──────────────────────────────────────────────────────────────┘
            │                    │
┌───────────┴────────┐  ┌───────┴──────────────────────────┐
│    RAG System      │  │     MCP Server                    │
│  ┌──────────────┐  │  │  ┌──────────┐  ┌─────────────┐  │
│  │  Embeddings  │  │  │  │Resources │  │   Tools     │  │
│  │  + Search    │  │  │  │          │  │             │  │
│  └──────────────┘  │  │  └──────────┘  └─────────────┘  │
└────────────────────┘  └──────────────────────────────────┘
            │
┌───────────┴─────────────────────────────────────────────────┐
│               Supabase PostgreSQL + pgvector                 │
│  ┌─────────────┐ ┌──────────────┐ ┌────────────────┐      │
│  │  Knowledge  │ │  Chat        │ │  Conversations │      │
│  │  Base       │ │  Messages    │ │  & Activity    │      │
│  └─────────────┘ └──────────────┘ └────────────────┘      │
└──────────────────────────────────────────────────────────────┘
```

### Project Structure
```
src/
├── agents/
│   ├── chatbot-agents.ts      # 6 specialized agent implementations
│   ├── types.ts               # Shared type definitions
│   └── orchestrator.ts        # Legacy PRD system orchestrator
├── components/
│   ├── ChatInterface.tsx          # Main chat UI with streaming
│   ├── AgentSelector.tsx          # Agent selection panel
│   ├── ProviderConfig.tsx         # Multi-provider API setup
│   └── KnowledgeBaseManager.tsx   # Document management UI
├── lib/
│   ├── ai-providers.ts        # Multi-provider abstraction layer
│   ├── rag-system.ts          # RAG implementation with pgvector
│   ├── mcp-server.ts          # MCP protocol server
│   └── supabase.ts            # Database client configuration
└── App.tsx                    # Root application component
```

---

## Getting Started

### Prerequisites
- **Node.js 18+** with npm
- At least **one API key** from:
  - [OpenAI Platform](https://platform.openai.com/api-keys) - GPT-4, embeddings
  - [Anthropic Console](https://console.anthropic.com/) - Claude Sonnet
  - [Google AI Studio](https://ai.google.dev/) - Gemini 2.0
- **Supabase account** (free tier works) for RAG features

### Quick Start

1. **Clone and Install**
```bash
git clone <repository>
cd project
npm install
```

2. **Configure Environment**

Create `.env` file:
```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key_here
```

3. **Run Development Server**
```bash
npm run dev
```

4. **Open Browser** to `http://localhost:5173`

5. **Configure AI Providers**
   - Click "Settings" tab
   - Enter API keys for desired providers
   - Click "Save Configuration"
   - Navigate to "Chat" tab to start

### Database Setup (Optional but Recommended)

For RAG features, set up Supabase:

1. Create a Supabase project
2. Enable the `vector` extension
3. Run the migration SQL to create tables
4. Update your `.env` file

---

## Usage Guide

### Basic Chat

1. **Select an agent** or let auto-routing handle it
2. **Type your message** in the input field
3. **Send** and watch the agent respond in real-time
4. **Responses stream** as they're generated

### Auto-Routing Keywords

The system intelligently routes based on message content:

- **Programming** → Code Expert: "code", "debug", "function", "program"
- **Research** → Research Specialist: "research", "analyze", "study", "investigate"
- **Writing** → Creative Writer: "story", "write", "poem", "creative"
- **Data** → Data Analyst: "data", "metrics", "statistics", "trends"
- **Knowledge** → RAG Agent: "knowledge base", "documents", "search"
- **Default** → General Assistant

### Knowledge Base Management

1. Navigate to **"Knowledge Base"** tab
2. Click **"Add Document"** button
3. Enter title and content
4. Document is automatically:
   - Embedded using OpenAI
   - Stored in Supabase
   - Indexed for vector search
5. **Search** using semantic or keyword queries
6. **Delete** documents as needed

### Provider Configuration

Configure multiple providers for:
- **Redundancy** - Fallback if one provider is down
- **Cost optimization** - Route to cheaper models
- **Feature access** - Use best model for each task

---

## API Documentation

### AIProviderManager

Central manager for all AI providers.

```typescript
import { AIProviderManager } from './lib/ai-providers';

const manager = new AIProviderManager({
  openaiKey: 'sk-...',
  claudeKey: 'sk-ant-...',
  geminiKey: 'AIza...'
});

// Standard generation
const response = await manager.generateResponse(
  'openai',
  [{ role: 'user', content: 'Hello!' }],
  { temperature: 0.7, maxTokens: 2000 }
);

// Streaming generation
for await (const chunk of manager.streamResponse('claude', messages)) {
  if (!chunk.done) {
    console.log(chunk.content);
  }
}

// Check configuration
const providers = manager.getConfiguredProviders();
// ['openai', 'claude', 'gemini']
```

### RAGSystem

Manage knowledge base with vector embeddings.

```typescript
import { RAGSystem } from './lib/rag-system';

const rag = new RAGSystem(openaiApiKey);

// Add document with automatic embedding
const doc = await rag.addDocument(
  'Product Roadmap Q1 2025',
  'Our Q1 priorities include...'
);

// Semantic search
const results = await rag.searchSimilar('Q1 priorities', 5);
results.forEach(r => {
  console.log(r.document.title, r.similarity);
});

// Get context for AI prompt
const context = await rag.getRelevantContext(
  'What are our Q1 goals?',
  2000 // max tokens
);

// Keyword search
const docs = await rag.searchByKeywords('roadmap', 10);
```

### ChatbotAgent

Individual specialized agent.

```typescript
import { ChatbotAgent, AGENT_CONFIGS } from './agents/chatbot-agents';

const agent = new ChatbotAgent(
  { ...AGENT_CONFIGS.research, provider: 'openai' },
  aiManager,
  ragSystem
);

// Generate response
const response = await agent.generateResponse(messages);

// Stream response
for await (const chunk of agent.generateResponse(messages, { stream: true })) {
  process.stdout.write(chunk);
}
```

### MultiAgentOrchestrator

Coordinate multiple agents.

```typescript
import { MultiAgentOrchestrator } from './agents/chatbot-agents';

const orchestrator = new MultiAgentOrchestrator(aiManager, ragSystem);

// Get specific agent
const codeAgent = orchestrator.getAgent('coding');

// Auto-route message
const { agent, reason } = await orchestrator.routeMessage(
  'How do I implement binary search?',
  conversationHistory
);
console.log(reason); // "Message contains coding-related keywords"
```

---

## MCP Server Integration

The Model Context Protocol server provides standardized access to your system.

### Available Resources

- **`chat://history`** - Recent conversation messages
- **`knowledge://documents`** - All knowledge base documents
- **`projects://list`** - User projects (if available)

### Available Tools

#### `search_knowledge_base`
Search for relevant documents using semantic similarity.

```json
{
  "name": "search_knowledge_base",
  "arguments": {
    "query": "product roadmap",
    "limit": 5
  }
}
```

#### `save_to_knowledge_base`
Add a new document to the knowledge base.

```json
{
  "name": "save_to_knowledge_base",
  "arguments": {
    "title": "Meeting Notes",
    "content": "Discussion about...",
    "metadata": { "date": "2025-01-15" }
  }
}
```

#### `get_chat_context`
Retrieve conversation history for context.

```json
{
  "name": "get_chat_context",
  "arguments": {
    "conversationId": "uuid-here",
    "limit": 10
  }
}
```

### Starting the MCP Server

```typescript
import { MCPServer } from './lib/mcp-server';

const server = new MCPServer();
await server.start();
// Server listening on stdio
```

---

## Advanced Configuration

### Custom Agent Creation

```typescript
const customAgent: AgentConfig = {
  name: 'Legal Expert',
  role: 'legal',
  systemPrompt: `You are a legal expert specializing in contract review...`,
  provider: 'claude', // Claude excels at legal reasoning
  temperature: 0.3, // Lower for factual accuracy
  useRAG: true // Enable knowledge base access
};

const agent = new ChatbotAgent(customAgent, aiManager, ragSystem);
```

### RAG Tuning

```typescript
// Adjust similarity threshold
const strictResults = await rag.searchSimilar(query, 5, 0.85); // 85% match

// More context for complex queries
const longContext = await rag.getRelevantContext(query, 4000);

// Update existing document
await rag.updateDocument(docId, {
  content: 'Updated content...',
  metadata: { updated: new Date().toISOString() }
});
```

### Provider-Specific Options

```typescript
// OpenAI with custom settings
await manager.generateResponse('openai', messages, {
  model: 'gpt-4-turbo-preview',
  temperature: 0.9,
  maxTokens: 4000
});

// Claude for complex reasoning
await manager.generateResponse('claude', messages, {
  model: 'claude-sonnet-4-5-20250929',
  temperature: 0.5,
  maxTokens: 8000
});

// Gemini for multimodal tasks
await manager.generateResponse('gemini', messages, {
  model: 'gemini-2.0-flash-exp',
  temperature: 0.7,
  maxTokens: 2000
});
```

---

## Technology Stack

### Frontend
- **React 18** with TypeScript for type-safe components
- **Vite** for lightning-fast builds and HMR
- **Tailwind CSS** for utility-first styling
- **Lucide React** for consistent iconography

### AI & ML
- **OpenAI SDK** - GPT-4 and text-embedding-3-small
- **Anthropic SDK** - Claude Sonnet 4.5
- **Google Generative AI** - Gemini 2.0 Flash
- **MCP SDK** - Model Context Protocol 2025 spec

### Database & Backend
- **Supabase** - PostgreSQL with real-time subscriptions
- **pgvector** - Vector similarity search
- **Row Level Security (RLS)** - Data protection

### Validation & Types
- **Zod** - Runtime type validation
- **TypeScript** - Compile-time type safety

---

## Security & Privacy

### Data Protection
- **Local storage** of API keys in browser localStorage
- **No cloud relay** - Direct API calls to providers
- **RLS policies** protect multi-tenant data in Supabase
- **No tracking** or analytics

### Best Practices
- API keys never leave your browser
- All database queries are user-scoped
- Vector embeddings stored securely
- No cross-user data leakage

---

## Troubleshooting

### API Keys Not Accepted
- Verify keys have no leading/trailing spaces
- Check provider account has sufficient credits
- Confirm API key permissions (some keys are restricted)

### RAG Not Finding Documents
- Ensure OpenAI key is configured (required for embeddings)
- Check documents were added successfully
- Try broader or more specific queries
- Verify Supabase connection is working

### Slow Responses
- Check internet connection stability
- Consider using faster models (gpt-3.5-turbo, Gemini Flash)
- Reduce context length in RAG queries
- Enable streaming for better UX

### Database Errors
- Verify Supabase URL and anon key in `.env`
- Confirm project is not paused (free tier limitation)
- Check database migrations were applied
- Review browser console for specific errors

---

## Performance Tips

- **Streaming** - Always use streaming for better perceived performance
- **Caching** - Browser caches embeddings and responses
- **Indexes** - Vector indexes dramatically speed up similarity search
- **Batching** - Batch multiple embeddings when possible
- **Model selection** - Use faster models for simple tasks

---

## Roadmap

- [ ] **Voice I/O** - Speech-to-text and text-to-speech
- [ ] **Image generation** - DALL-E and Midjourney integration
- [ ] **PDF support** - Extract text and images from PDFs
- [ ] **Export** - Save conversations as Markdown/PDF
- [ ] **Teams** - Multi-user collaboration features
- [ ] **Analytics** - Usage tracking and insights
- [ ] **Plugins** - Extensible agent system
- [ ] **Mobile app** - Native iOS and Android

---

## License

MIT License - See LICENSE file for details

---

## Acknowledgments

- **OpenAI** for GPT-4 and embeddings
- **Anthropic** for Claude's exceptional reasoning
- **Google** for Gemini's multimodal capabilities
- **Supabase** for best-in-class PostgreSQL hosting
- **Model Context Protocol** community

---

**Built with ❤️ using TypeScript, React, and cutting-edge AI**
