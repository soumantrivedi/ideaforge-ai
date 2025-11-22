# IdeaScribe - Multi-Agent PRD Generator

A sophisticated multi-agent system built with OpenAI Agents SDK that transforms product ideas into comprehensive Product Requirements Documents (PRDs).

## Overview

IdeaScribe uses four specialized AI agents working collaboratively to analyze product ideas and generate production-ready PRDs:

1. **Research Agent** - Conducts market research, identifies competitors, and analyzes trends
2. **Analysis Agent** - Defines target audience, value proposition, and core features
3. **PRD Writer Agent** - Creates comprehensive, structured PRDs with user stories and technical specs
4. **Validator Agent** - Reviews PRD quality, completeness, and provides recommendations

## Architecture

### Multi-Agent System

The system is orchestrated using the **OpenAI Agents SDK**, which provides:
- Fast agent instantiation and execution
- Structured tool calling and function integration
- Type-safe message handling with Zod validation
- Seamless handoffs between specialized agents

### Agent Workflow

```
User Input → Research Agent → Analysis Agent → PRD Writer Agent → Validator Agent → Final PRD
```

Each agent:
- Receives context from previous agents
- Performs specialized analysis using GPT-4
- Outputs structured JSON validated with Zod
- Passes results to the next agent in the pipeline

### Technology Stack

- **Frontend**: React 18 + TypeScript + Vite
- **UI**: Tailwind CSS with custom components
- **AI Framework**: OpenAI Agents SDK (@openai/agents)
- **Validation**: Zod for schema validation
- **Database**: Supabase (schema prepared for future persistence)
- **Icons**: Lucide React

## Features

### Core Functionality

- **Interactive Project Form**: Simple interface to input product ideas
- **Real-time Progress Tracking**: Visual feedback as agents process your idea
- **Comprehensive PRD Generation**: Includes all essential sections:
  - Executive Summary
  - Problem Statement
  - Goals & Objectives
  - Target Users & Personas
  - Feature Specifications with User Stories
  - Technical Requirements
  - Success Metrics
  - Implementation Timeline
- **Quality Validation**: Automated PRD review with completeness scoring
- **PRD Export**: Download generated PRDs as JSON

### Security

- API keys stored locally in browser (localStorage)
- No server-side storage of credentials
- Direct browser-to-OpenAI communication

## Getting Started

### Prerequisites

- Node.js 18+
- OpenAI API Key (get one at https://platform.openai.com/api-keys)

### Installation

```bash
npm install
```

### Running the Application

```bash
npm run dev
```

The app will prompt you for your OpenAI API key on first use.

### Building for Production

```bash
npm run build
```

## Project Structure

```
src/
├── agents/
│   ├── types.ts              # TypeScript interfaces for agent I/O
│   ├── researchAgent.ts      # Market research specialist
│   ├── analysisAgent.ts      # Product analysis specialist
│   ├── prdWriterAgent.ts     # PRD writing specialist
│   ├── validatorAgent.ts     # Quality assurance specialist
│   └── orchestrator.ts       # Multi-agent coordination
├── components/
│   ├── ApiKeyPrompt.tsx      # API key input interface
│   ├── ProjectForm.tsx       # Product idea input form
│   ├── ProgressTracker.tsx   # Agent progress visualization
│   └── PRDViewer.tsx         # PRD display and export
├── lib/
│   └── supabase.ts           # Database client and types
└── App.tsx                   # Main application component
```

## How It Works

### 1. Research Phase

The Research Agent analyzes your product idea to identify:
- 3-5 key competitors or similar solutions
- Current market trends
- User needs and pain points
- Technological considerations

### 2. Analysis Phase

The Analysis Agent processes research findings to define:
- Target audience segments
- Unique value proposition
- 5-8 core features with priorities
- Technical feasibility assessment
- Market opportunity evaluation
- Risk analysis

### 3. PRD Writing Phase

The PRD Writer Agent synthesizes research and analysis into:
- Complete product overview
- Detailed problem statement
- Measurable goals
- User personas with needs and pain points
- Feature specifications with:
  - User stories
  - Acceptance criteria
  - Priority levels (P0, P1, P2)
- Technical requirements (architecture, integrations, security, performance)
- Success metrics and KPIs
- Implementation timeline with phases and deliverables

### 4. Validation Phase

The Validator Agent reviews the PRD for:
- Completeness (0-100 score)
- Clarity and ambiguity
- Technical feasibility
- User story quality
- Measurability of success metrics

Issues are categorized as:
- **Critical**: Must be addressed before implementation
- **Warning**: Should be considered
- **Info**: Nice-to-have improvements

## Agent Communication Pattern

Agents communicate through a structured orchestration pattern:

```typescript
interface AgentContext {
  projectId: string;
  projectTitle: string;
  projectDescription: string;
  previousOutputs?: Record<string, unknown>;
}

interface AgentResult {
  success: boolean;
  output: Record<string, unknown>;
  error?: string;
  metadata?: Record<string, unknown>;
}
```

Each agent:
1. Receives strongly-typed context
2. Executes specialized analysis
3. Returns validated JSON output
4. Passes context + output to next agent

## Future Enhancements

- [ ] Save PRDs to Supabase database
- [ ] User authentication and project management
- [ ] Version control for PRDs
- [ ] Collaborative editing features
- [ ] Export to PDF and Markdown formats
- [ ] Integration with project management tools
- [ ] Custom agent configurations
- [ ] Multi-language support

## Development

### Type Checking

```bash
npm run typecheck
```

### Linting

```bash
npm run lint
```

## License

MIT
