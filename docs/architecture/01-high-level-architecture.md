# IdeaForge AI - High-Level Architecture

## Overview

IdeaForge AI is a comprehensive multi-agent product management platform that enables AI agents to collaborate on product ideation, research, analysis, validation, and documentation tasks. The system is built with a microservices architecture using Docker containers.

## System Architecture Diagram

```mermaid
graph TB
    subgraph "Client Layer"
        UI[React Frontend<br/>Port 3001]
        Browser[Web Browser]
    end

    subgraph "Application Layer"
        Frontend[Frontend Container<br/>Nginx + React]
        Backend[Backend Container<br/>FastAPI + Python]
    end

    subgraph "Agent Layer"
        Coordinator[Enhanced Coordinator Agent]
        Research[Research Agent]
        Analysis[Analysis Agent]
        Validation[Validation Agent]
        Ideation[Ideation Agent]
        PRD[PRD Authoring Agent]
        Summary[Summary Agent]
        Scoring[Scoring Agent]
        Export[Export Agent]
        RAG[RAG Agent]
        V0[V0 Design Agent]
        Lovable[Lovable AI Agent]
        GitHub[GitHub MCP Agent]
        Atlassian[Atlassian MCP Agent]
    end

    subgraph "Data Layer"
        PostgreSQL[(PostgreSQL<br/>Port 5433<br/>pgvector)]
        Redis[(Redis<br/>Port 6379)]
    end

    subgraph "External Services"
        OpenAI[OpenAI API]
        Anthropic[Anthropic API]
        Google[Google Gemini API]
        JiraAPI[Jira API]
        GitHub[GitHub API]
        Confluence[Confluence API]
    end

    Browser --> UI
    UI --> Frontend
    Frontend --> Backend
    Backend --> Coordinator
    Coordinator --> Research
    Coordinator --> Analysis
    Coordinator --> Validation
    Coordinator --> Ideation
    Coordinator --> PRD
    Coordinator --> Summary
    Coordinator --> Scoring
    Coordinator --> Export
    Coordinator --> RAG
    Coordinator --> V0
    Coordinator --> Lovable
    Coordinator --> GitHub
    Coordinator --> Atlassian
    Backend --> PostgreSQL
    Backend --> Redis
    Research --> OpenAI
    Research --> Anthropic
    Research --> Google
    Analysis --> OpenAI
    Validation --> OpenAI
    Ideation --> OpenAI
    PRD --> OpenAI
    Summary --> OpenAI
    Scoring --> OpenAI
    Export --> OpenAI
    RAG --> OpenAI
    V0 --> OpenAI
    Lovable --> OpenAI
    GitHub --> GitHub
    Atlassian --> Confluence

    style UI fill:#e1f5ff
    style Frontend fill:#c8e6c9
    style Backend fill:#fff9c4
    style Coordinator fill:#f8bbd0
    style PostgreSQL fill:#b39ddb
    style Redis fill:#ffccbc
```

## Component Architecture

```mermaid
graph LR
    subgraph "Frontend Components"
        A1[App.tsx<br/>Main Application]
        A2[EnhancedChatInterface<br/>Chat UI]
        A3[AgentStatusPanel<br/>Agent Monitoring]
        A4[ProductLifecycleSidebar<br/>Lifecycle Management]
        A5[KnowledgeBaseManager<br/>RAG Interface]
        A6[ProviderConfig<br/>API Key Management]
    end

    subgraph "Backend Services"
        B1[FastAPI Main<br/>API Endpoints]
        B2[Orchestrator<br/>Workflow Management]
        B3[Database API<br/>Data Access Layer]
        B4[Agent System<br/>Multi-Agent Coordination]
    end

    subgraph "Core Libraries"
        C1[AI Providers<br/>OpenAI/Claude/Gemini]
        C2[RAG System<br/>Vector Search]
        C3[Product Lifecycle<br/>Phase Management]
        C4[MCP Servers<br/>External Integrations]
    end

    A1 --> A2
    A1 --> A3
    A1 --> A4
    A1 --> A5
    A1 --> A6
    A2 --> B1
    A3 --> B1
    A4 --> B1
    A5 --> B1
    B1 --> B2
    B1 --> B3
    B2 --> B4
    B4 --> C1
    B4 --> C2
    B4 --> C3
    B4 --> C4

    style A1 fill:#e3f2fd
    style B1 fill:#fff3e0
    style B4 fill:#f3e5f5
    style C1 fill:#e8f5e9
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Docker Network: agentic-pm-network"
        subgraph "Frontend Service"
            FE[Frontend Container<br/>nginx:alpine<br/>Port 3001:3000]
        end

        subgraph "Backend Service"
            BE[Backend Container<br/>python:3.11-slim<br/>Port 8000:8000]
        end

        subgraph "Database Services"
            PG[(PostgreSQL Container<br/>pgvector/pgvector:pg15<br/>Port 5433:5432)]
            RD[(Redis Container<br/>redis:7-alpine<br/>Port 6379:6379)]
        end
    end

    subgraph "Persistent Storage"
        PGVol[postgres-data Volume<br/>/var/lib/postgresql/data]
        RDVol[redis-data Volume<br/>/data]
    end

    subgraph "External APIs"
        EXT1[OpenAI API]
        EXT2[Anthropic API]
        EXT3[Google API]
        EXT4[Jira API]
        EXT5[GitHub API]
        EXT6[Confluence API]
    end

    FE --> BE
    BE --> PG
    BE --> RD
    BE --> EXT1
    BE --> EXT2
    BE --> EXT3
    BE --> EXT4
    BE --> EXT5
    BE --> EXT6
    PG --> PGVol
    RD --> RDVol

    style FE fill:#c8e6c9
    style BE fill:#fff9c4
    style PG fill:#b39ddb
    style RD fill:#ffccbc
```

## Technology Stack

### Frontend
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **UI Library**: Tailwind CSS
- **State Management**: React Hooks
- **HTTP Client**: Fetch API
- **Web Server**: Nginx (Alpine)

### Backend
- **Framework**: FastAPI (Python 3.11)
- **ASGI Server**: Uvicorn
- **Database ORM**: SQLAlchemy (async)
- **Database Driver**: asyncpg
- **Vector Search**: pgvector
- **Caching**: Redis
- **Logging**: structlog
- **Provider Registry**: Dynamic client management + key verification

### Database
- **Primary DB**: PostgreSQL 15 with pgvector extension
- **Cache**: Redis 7
- **Persistence**: Docker volumes

### AI Providers
- OpenAI (GPT-5.1, GPT-5, text-embedding-3-small)
- Anthropic (Claude Sonnet 4.5)
- Google (Gemini 2.0 Flash)

### External Integrations
- Jira (via REST API)
- GitHub (via REST API)
- Confluence (via REST API)
- MCP (Model Context Protocol) servers

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant Coordinator
    participant Agent
    participant Database
    participant AIProvider

    User->>Frontend: Submit Query
    Frontend->>Backend: POST /api/agents/process
    Backend->>Coordinator: Route Request
    Coordinator->>Coordinator: Determine Primary Agent
    Coordinator->>Agent: Process Query
    Agent->>Database: Load Context
    Database-->>Agent: Return Context
    Agent->>AIProvider: Generate Response
    AIProvider-->>Agent: Return Response
    Agent->>Database: Save Interaction
    Agent-->>Coordinator: Return Response
    Coordinator-->>Backend: Return Response
    Backend-->>Frontend: Stream Response
    Frontend-->>User: Display Response
```

## Provider Management Flow

```mermaid
sequenceDiagram
    participant Settings as Frontend Settings Panel
    participant API as FastAPI /api/providers/*
    participant Registry as ProviderRegistry Service
    participant Agents as Coordinator + Specialized Agents
    participant LLM as External LLM APIs

    Settings->>API: POST /api/providers/verify (OpenAI key)
    API->>Registry: verify_keys(config)
    Registry-->>API: Verification results
    API-->>Settings: Success/Failure per provider

    Settings->>API: POST /api/providers/configure (persist keys)
    API->>Registry: configure_providers(config)
    Registry-->>Agents: Updated clients + provider list
    Agents->>LLM: Runtime requests using active client
```

The registry keeps the latest, validated clients in memory so every agent (Research, Ideation, Strategy, PRD, Jira) can immediately reuse them without restarting the backend. The `/health` endpoint surfaces which providers are currently active.

## Security Architecture

```mermaid
graph TB
    subgraph "Security Layers"
        L1[Frontend Security<br/>- API Key Storage<br/>- Input Validation<br/>- XSS Protection]
        L2[Network Security<br/>- Docker Network Isolation<br/>- CORS Configuration<br/>- Port Mapping]
        L3[Backend Security<br/>- API Authentication<br/>- Request Validation<br/>- Rate Limiting]
        L4[Data Security<br/>- Database Credentials<br/>- Encrypted Connections<br/>- Volume Isolation]
    end

    L1 --> L2
    L2 --> L3
    L3 --> L4

    style L1 fill:#ffcdd2
    style L2 fill:#f8bbd0
    style L3 fill:#ce93d8
    style L4 fill:#b39ddb
```

## Scalability Architecture

```mermaid
graph TB
    subgraph "Horizontal Scaling"
        LB[Load Balancer]
        FE1[Frontend Instance 1]
        FE2[Frontend Instance 2]
        FE3[Frontend Instance N]
    end

    subgraph "Backend Scaling"
        BE1[Backend Instance 1]
        BE2[Backend Instance 2]
        BE3[Backend Instance N]
    end

    subgraph "Database Scaling"
        PG1[(PostgreSQL Primary)]
        PG2[(PostgreSQL Replica 1)]
        PG3[(PostgreSQL Replica N)]
    end

    subgraph "Cache Layer"
        RD1[(Redis Instance 1)]
        RD2[(Redis Instance 2)]
    end

    LB --> FE1
    LB --> FE2
    LB --> FE3
    FE1 --> BE1
    FE2 --> BE2
    FE3 --> BE3
    BE1 --> PG1
    BE2 --> PG1
    BE3 --> PG1
    PG1 --> PG2
    PG1 --> PG3
    BE1 --> RD1
    BE2 --> RD2

    style LB fill:#e1f5ff
    style PG1 fill:#b39ddb
    style RD1 fill:#ffccbc
```

## Key Architectural Principles

1. **Microservices Architecture**: Each component runs in isolated containers
2. **API-First Design**: All interactions through RESTful APIs
3. **Agent-Based Processing**: Specialized agents for different tasks
4. **Event-Driven Communication**: Agents communicate asynchronously
5. **Data Persistence**: All data stored in PostgreSQL with vector search
6. **Scalable Design**: Horizontal scaling support for all services
7. **Container Orchestration**: Docker Compose for local deployment
8. **Health Monitoring**: Health checks for all services

## Port Mapping

| Service | Internal Port | External Port | Protocol |
|---------|--------------|---------------|----------|
| Frontend | 3000 | 3001 | HTTP |
| Backend | 8000 | 8000 | HTTP |
| PostgreSQL | 5432 | 5433 | TCP |
| Redis | 6379 | 6379 | TCP |

## Network Architecture

```mermaid
graph TB
    subgraph "Host Machine"
        subgraph "Docker Network: agentic-pm-network"
            FE[Frontend:3000]
            BE[Backend:8000]
            PG[PostgreSQL:5432]
            RD[Redis:6379]
        end
    end

    subgraph "Host Ports"
        P1[localhost:3001]
        P2[localhost:8000]
        P3[localhost:5433]
        P4[localhost:6379]
    end

    P1 -->|Port Forward| FE
    P2 -->|Port Forward| BE
    P3 -->|Port Forward| PG
    P4 -->|Port Forward| RD

    style FE fill:#c8e6c9
    style BE fill:#fff9c4
    style PG fill:#b39ddb
    style RD fill:#ffccbc
```

