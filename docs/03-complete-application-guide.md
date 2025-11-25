# IdeaForge AI - Complete Application Guide

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Agent System](#agent-system)
4. [Product Lifecycle](#product-lifecycle)
5. [Data Flow & Workflows](#data-flow--workflows)
6. [Deployment Architecture](#deployment-architecture)
7. [API Integration](#api-integration)
8. [Security & Permissions](#security--permissions)

## Overview

IdeaForge AI is a comprehensive multi-agent product management platform that enables AI agents to collaborate on product ideation, research, analysis, validation, documentation, and execution tasks. The system uses the Agno framework for multi-agent coordination and supports multiple AI providers (OpenAI, Anthropic, Google).

### Key Features

- **15+ Specialized AI Agents** for different product management tasks
- **Multi-Agent Coordination** with collaborative, sequential, and parallel modes
- **RAG (Retrieval-Augmented Generation)** with pgvector for knowledge management
- **Product Lifecycle Management** across Ideation, Research, Analysis, Validation, PRD, Design, and Execution phases
- **Industry-Standard Scoring** using BCS, ICAgile, AIPMM, and Pragmatic Institute frameworks
- **External Integrations** via MCP servers (GitHub, Jira, Confluence)
- **Design Tools Integration** (V0, Lovable AI)
- **Multi-tenant Architecture** with role-based access control

## System Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        Browser[Web Browser]
        UI[React Frontend<br/>Port 3001]
    end

    subgraph "Application Layer"
        Frontend[Frontend Container<br/>Nginx + React Build]
        Backend[Backend Container<br/>FastAPI + Python 3.11]
    end

    subgraph "Orchestration Layer"
        Orchestrator[AgnoAgenticOrchestrator<br/>Workflow Management]
        Coordinator[AgnoCoordinatorAgent<br/>Multi-Agent Coordination]
    end

    subgraph "Agent Layer - Agno Framework"
        BaseAgent[AgnoBaseAgent<br/>Base Class]
        
        subgraph "Core Agents"
            Research[AgnoResearchAgent]
            Analysis[AgnoAnalysisAgent]
            Ideation[AgnoIdeationAgent]
            Validation[AgnoValidationAgent]
            PRD[AgnoPRDAuthoringAgent]
            Summary[AgnoSummaryAgent]
            Scoring[AgnoScoringAgent]
            Export[AgnoExportAgent]
        end
        
        subgraph "Design Agents"
            V0[AgnoV0Agent]
            Lovable[AgnoLovableAgent]
        end
        
        subgraph "Integration Agents"
            GitHub[AgnoGitHubAgent]
            Atlassian[AgnoAtlassianAgent]
        end
        
        RAG[RAGAgent<br/>Knowledge Retrieval]
    end

    subgraph "Data Layer"
        PostgreSQL[(PostgreSQL 15<br/>pgvector Extension<br/>Port 5433)]
        Redis[(Redis 7<br/>Cache & Sessions<br/>Port 6379)]
    end

    subgraph "Provider Layer"
        ProviderRegistry[ProviderRegistry<br/>Dynamic Client Management]
        OpenAI[OpenAI API]
        Anthropic[Anthropic API]
        Google[Google Gemini API]
    end

    subgraph "External Services"
        JiraAPI[Jira API]
        GitHubAPI[GitHub API]
        ConfluenceAPI[Confluence API]
        V0API[V0 Platform API]
        LovableAPI[Lovable AI]
    end

    Browser --> UI
    UI --> Frontend
    Frontend --> Backend
    Backend --> Orchestrator
    Orchestrator --> Coordinator
    Coordinator --> BaseAgent
    BaseAgent --> Research
    BaseAgent --> Analysis
    BaseAgent --> Ideation
    BaseAgent --> Validation
    BaseAgent --> PRD
    BaseAgent --> Summary
    BaseAgent --> Scoring
    BaseAgent --> Export
    BaseAgent --> V0
    BaseAgent --> Lovable
    BaseAgent --> GitHub
    BaseAgent --> Atlassian
    BaseAgent --> RAG
    Backend --> ProviderRegistry
    ProviderRegistry --> OpenAI
    ProviderRegistry --> Anthropic
    ProviderRegistry --> Google
    Backend --> PostgreSQL
    Backend --> Redis
    RAG --> PostgreSQL
    GitHub --> GitHubAPI
    Atlassian --> JiraAPI
    Atlassian --> ConfluenceAPI
    V0 --> V0API
    Lovable --> LovableAPI

    style UI fill:#e1f5ff
    style Frontend fill:#c8e6c9
    style Backend fill:#fff9c4
    style Orchestrator fill:#f8bbd0
    style Coordinator fill:#f8bbd0
    style BaseAgent fill:#ffccbc
    style PostgreSQL fill:#b39ddb
    style Redis fill:#ffccbc
    style ProviderRegistry fill:#c5e1a5
```

## Agent System

### Agent Hierarchy

```mermaid
graph TB
    Base[AgnoBaseAgent<br/>Abstract Base Class]
    
    subgraph "Core Product Management Agents"
        Research[AgnoResearchAgent<br/>Market Research & Competitive Analysis]
        Analysis[AgnoAnalysisAgent<br/>Strategic Analysis & SWOT]
        Ideation[AgnoIdeationAgent<br/>Creative Brainstorming]
        Validation[AgnoValidationAgent<br/>Idea Validation]
        PRD[AgnoPRDAuthoringAgent<br/>PRD Generation]
        Summary[AgnoSummaryAgent<br/>Multi-Session Summarization]
        Scoring[AgnoScoringAgent<br/>Product Idea Scoring]
        Export[AgnoExportAgent<br/>Jira Export]
    end
    
    subgraph "Design Agents"
        V0[AgnoV0Agent<br/>V0 Design Generation]
        Lovable[AgnoLovableAgent<br/>Lovable AI Integration]
    end
    
    subgraph "Integration Agents"
        GitHub[AgnoGitHubAgent<br/>GitHub Integration]
        Atlassian[AgnoAtlassianAgent<br/>Jira & Confluence]
    end
    
    subgraph "Knowledge Agent"
        RAG[RAGAgent<br/>Knowledge Retrieval & Synthesis]
    end
    
    Base --> Research
    Base --> Analysis
    Base --> Ideation
    Base --> Validation
    Base --> PRD
    Base --> Summary
    Base --> Scoring
    Base --> Export
    Base --> V0
    Base --> Lovable
    Base --> GitHub
    Base --> Atlassian
    Base --> RAG
    
    style Base fill:#ffccbc
    style Research fill:#c8e6c9
    style Analysis fill:#c8e6c9
    style Ideation fill:#c8e6c9
    style Validation fill:#c8e6c9
    style PRD fill:#c8e6c9
    style Summary fill:#c8e6c9
    style Scoring fill:#c8e6c9
    style Export fill:#c8e6c9
    style V0 fill:#fff9c4
    style Lovable fill:#fff9c4
    style GitHub fill:#e1f5ff
    style Atlassian fill:#e1f5ff
    style RAG fill:#f8bbd0
```

### Multi-Agent Coordination Modes

```mermaid
graph LR
    subgraph "Collaborative Mode"
        C1[Primary Agent]
        C2[Supporting Agent 1]
        C3[Supporting Agent 2]
        C1 -->|Consult| C2
        C1 -->|Consult| C3
        C2 -->|Response| C1
        C3 -->|Response| C1
    end
    
    subgraph "Sequential Mode"
        S1[Agent 1] -->|Output| S2[Agent 2]
        S2 -->|Output| S3[Agent 3]
    end
    
    subgraph "Parallel Mode"
        P1[Agent 1]
        P2[Agent 2]
        P3[Agent 3]
        P1 -->|Independent| Result[Combined Result]
        P2 -->|Independent| Result
        P3 -->|Independent| Result
    end
    
    style C1 fill:#c8e6c9
    style S1 fill:#fff9c4
    style P1 fill:#e1f5ff
```

### Agent Workflow Example

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant Orchestrator
    participant Coordinator
    participant RAG as RAG Agent
    participant Research as Research Agent
    participant Analysis as Analysis Agent
    participant PRD as PRD Agent
    participant Database

    User->>Frontend: Submit Product Query
    Frontend->>Backend: POST /api/multi-agent/process
    Backend->>Orchestrator: Route Request
    Orchestrator->>Coordinator: Initialize Multi-Agent Team
    
    Coordinator->>RAG: Retrieve Knowledge Base Context
    RAG->>Database: Vector Search
    Database-->>RAG: Relevant Context
    RAG-->>Coordinator: Knowledge Context
    
    Coordinator->>Research: Research Market & Competitors
    Research->>Database: Load Product Data
    Database-->>Research: Product Information
    Research-->>Coordinator: Research Results
    
    Coordinator->>Analysis: Analyze with Research Context
    Analysis->>Database: Load Historical Data
    Database-->>Analysis: Historical Context
    Analysis-->>Coordinator: Analysis Results
    
    Coordinator->>PRD: Generate PRD with All Context
    PRD->>Database: Save PRD Document
    Database-->>PRD: Confirmation
    PRD-->>Coordinator: PRD Document
    
    Coordinator-->>Orchestrator: Complete Response
    Orchestrator-->>Backend: Stream Response
    Backend-->>Frontend: Stream Response
    Frontend-->>User: Display Results
```

## Product Lifecycle

### Lifecycle Phases

```mermaid
graph LR
    I[Ideation<br/>Phase 1]
    R[Research<br/>Phase 2]
    A[Analysis<br/>Phase 3]
    V[Validation<br/>Phase 4]
    P[PRD Authoring<br/>Phase 5]
    D[Design<br/>Phase 6]
    E[Execution<br/>Phase 7]
    
    I -->|Ideas Generated| R
    R -->|Research Complete| A
    A -->|Analysis Done| V
    V -->|Validated| P
    P -->|PRD Ready| D
    D -->|Designs Created| E
    E -->|Feedback| I
    
    style I fill:#e1f5ff
    style R fill:#c8e6c9
    style A fill:#fff9c4
    style V fill:#ffccbc
    style P fill:#f8bbd0
    style D fill:#b39ddb
    style E fill:#c5e1a5
```

### Phase-Specific Agents

```mermaid
graph TB
    subgraph "Ideation Phase"
        I1[Ideation Agent]
        I2[Research Agent]
    end
    
    subgraph "Research Phase"
        R1[Research Agent]
        R2[Analysis Agent]
        R3[RAG Agent]
    end
    
    subgraph "Analysis Phase"
        A1[Analysis Agent]
        A2[Research Agent]
        A3[Scoring Agent]
    end
    
    subgraph "Validation Phase"
        V1[Validation Agent]
        V2[Analysis Agent]
    end
    
    subgraph "PRD Phase"
        P1[PRD Authoring Agent]
        P2[Summary Agent]
        P3[Research Agent]
    end
    
    subgraph "Design Phase"
        D1[V0 Agent]
        D2[Lovable Agent]
        D3[PRD Agent]
    end
    
    subgraph "Execution Phase"
        E1[Export Agent]
        E2[GitHub Agent]
        E3[Atlassian Agent]
    end
    
    style I1 fill:#e1f5ff
    style R1 fill:#c8e6c9
    style A1 fill:#fff9c4
    style V1 fill:#ffccbc
    style P1 fill:#f8bbd0
    style D1 fill:#b39ddb
    style E1 fill:#c5e1a5
```

## Data Flow & Workflows

### Product Scoring Workflow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant Summary as Summary Agent
    participant Scoring as Scoring Agent
    participant Database

    User->>Frontend: Select Sessions & Generate Summary
    Frontend->>Backend: POST /api/products/{id}/summarize
    Backend->>Summary: Generate Summary from Sessions
    Summary->>Database: Load Session Data
    Database-->>Summary: Conversation History
    Summary->>Database: Save Summary
    Database-->>Summary: Summary ID
    Summary-->>Backend: Summary Document
    Backend-->>Frontend: Summary Response
    
    User->>Frontend: Generate Score
    Frontend->>Backend: POST /api/products/{id}/score
    Backend->>Scoring: Score Product Idea
    Scoring->>Database: Load Summary & Product Data
    Database-->>Scoring: Context Data
    Scoring->>Scoring: Calculate Scores<br/>(Market, User Value, Business, Technical, Risk)
    Scoring->>Database: Save Score
    Database-->>Scoring: Score ID
    Scoring-->>Backend: Detailed Score Report
    Backend-->>Frontend: Score Response
    Frontend-->>User: Display Score Dashboard
```

### PRD Generation Workflow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant Summary as Summary Agent
    participant Scoring as Scoring Agent
    participant PRD as PRD Authoring Agent
    participant RAG as RAG Agent
    participant Database

    User->>Frontend: Generate PRD
    Frontend->>Backend: POST /api/products/{id}/generate-prd
    
    Backend->>Summary: Load Summary
    Summary->>Database: Retrieve Summary
    Database-->>Summary: Summary Data
    
    Backend->>Scoring: Load Score
    Scoring->>Database: Retrieve Score
    Database-->>Scoring: Score Data
    
    Backend->>RAG: Retrieve Knowledge Base
    RAG->>Database: Vector Search
    Database-->>RAG: Relevant Knowledge
    
    Backend->>PRD: Generate PRD with Context
    PRD->>PRD: Create Industry-Standard PRD<br/>(BCS, ICAgile, AIPMM, Pragmatic)
    PRD->>Database: Save PRD Document
    Database-->>PRD: PRD ID
    
    PRD-->>Backend: PRD Document
    Backend-->>Frontend: PRD Response
    Frontend-->>User: Display PRD
```

### RAG Knowledge Flow

```mermaid
graph TB
    subgraph "Knowledge Input"
        K1[Conversation Sessions]
        K2[Product Submissions]
        K3[PRD Documents]
        K4[External Documents]
    end
    
    subgraph "RAG Processing"
        R1[RAG Agent]
        R2[Embedding Generation]
        R3[Vector Storage]
    end
    
    subgraph "Knowledge Retrieval"
        Q1[Query Processing]
        Q2[Vector Search]
        Q3[Context Synthesis]
    end
    
    subgraph "Agent Usage"
        A1[Research Agent]
        A2[Analysis Agent]
        A3[PRD Agent]
    end
    
    K1 --> R1
    K2 --> R1
    K3 --> R1
    K4 --> R1
    R1 --> R2
    R2 --> R3
    R3 --> Q1
    Q1 --> Q2
    Q2 --> Q3
    Q3 --> A1
    Q3 --> A2
    Q3 --> A3
    
    style R1 fill:#f8bbd0
    style R2 fill:#f8bbd0
    style R3 fill:#f8bbd0
    style Q3 fill:#c8e6c9
```

## Deployment Architecture

### Docker Compose Deployment

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
        PGVol[postgres-data Volume]
        RDVol[redis-data Volume]
    end
    
    subgraph "External APIs"
        EXT1[OpenAI API]
        EXT2[Anthropic API]
        EXT3[Google API]
        EXT4[Jira API]
        EXT5[GitHub API]
        EXT6[Confluence API]
        EXT7[V0 API]
        EXT8[Lovable AI]
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
    BE --> EXT7
    BE --> EXT8
    PG --> PGVol
    RD --> RDVol
    
    style FE fill:#c8e6c9
    style BE fill:#fff9c4
    style PG fill:#b39ddb
    style RD fill:#ffccbc
```

### Kubernetes Deployment (Kind/EKS)

```mermaid
graph TB
    subgraph "Kubernetes Cluster"
        subgraph "Namespace: ideaforge-ai"
            subgraph "Frontend Deployment"
                FE1[Frontend Pod 1]
                FE2[Frontend Pod 2]
                FESVC[Frontend Service<br/>ClusterIP:3000]
            end
            
            subgraph "Backend Deployment"
                BE1[Backend Pod 1]
                BE2[Backend Pod 2]
                BESVC[Backend Service<br/>ClusterIP:8000]
            end
            
            subgraph "Database Deployment"
                PG[PostgreSQL Pod<br/>PersistentVolumeClaim]
                PGSVC[PostgreSQL Service<br/>ClusterIP:5432]
                RD[Redis Pod<br/>PersistentVolumeClaim]
                RDSVC[Redis Service<br/>ClusterIP:6379]
            end
            
            ING[Ingress Controller<br/>NGINX/ALB]
        end
    end
    
    subgraph "Storage"
        PVC1[postgres-pvc<br/>20Gi]
        PVC2[redis-pvc<br/>5Gi]
    end
    
    ING --> FESVC
    FESVC --> FE1
    FESVC --> FE2
    FE1 --> BESVC
    FE2 --> BESVC
    BESVC --> BE1
    BESVC --> BE2
    BE1 --> PGSVC
    BE2 --> PGSVC
    BE1 --> RDSVC
    BE2 --> RDSVC
    PGSVC --> PG
    RDSVC --> RD
    PG --> PVC1
    RD --> PVC2
    
    style FE1 fill:#c8e6c9
    style BE1 fill:#fff9c4
    style PG fill:#b39ddb
    style RD fill:#ffccbc
    style ING fill:#e1f5ff
```

## API Integration

### Provider Registry Flow

```mermaid
sequenceDiagram
    participant User
    participant Settings as Settings UI
    participant API as FastAPI /api/providers/*
    participant Registry as ProviderRegistry
    participant Agents as AI Agents
    participant LLM as External LLM APIs

    User->>Settings: Enter API Keys
    Settings->>API: POST /api/providers/verify
    API->>Registry: verify_keys(config)
    Registry->>LLM: Test API Keys
    LLM-->>Registry: Verification Results
    Registry-->>API: Success/Failure per Provider
    API-->>Settings: Verification Status
    
    User->>Settings: Save Configuration
    Settings->>API: POST /api/providers/configure
    API->>Registry: configure_providers(config)
    Registry->>Registry: Update Client Instances
    Registry-->>Agents: Updated Clients Available
    Agents->>LLM: Use Active Clients
    LLM-->>Agents: API Responses
```

### Design Tools Integration

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant V0 as V0 Agent
    participant Lovable as Lovable Agent
    participant V0API as V0 Platform API
    participant LovableAPI as Lovable AI

    User->>Frontend: Create V0 Project
    Frontend->>Backend: POST /api/design/create-project
    Backend->>V0: create_v0_project_with_api()
    V0->>V0API: POST /v1/chats
    V0API-->>V0: Project URL & Code
    V0-->>Backend: Project Details
    Backend-->>Frontend: Project Response
    Frontend-->>User: Display V0 Project
    
    User->>Frontend: Create Lovable Project
    Frontend->>Backend: POST /api/design/create-project
    Backend->>Lovable: generate_lovable_link()
    Lovable->>Lovable: Build URL with Prompt
    Lovable-->>Backend: Lovable Shareable URL
    Backend-->>Frontend: URL Response
    Frontend-->>User: Open Lovable Link
```

## Security & Permissions

### Permission Model

```mermaid
graph TB
    subgraph "Permission Levels"
        Owner[Owner<br/>Full Access]
        Admin[Admin<br/>Full Access]
        Edit[Edit<br/>Create & Modify]
        View[View<br/>Read Only]
    end
    
    subgraph "Product Operations"
        Create[Create Product]
        Modify[Modify Product]
        Delete[Delete Product]
        GeneratePRD[Generate PRD]
        Export[Export to Jira]
        ViewOnly[View Content]
    end
    
    Owner --> Create
    Owner --> Modify
    Owner --> Delete
    Owner --> GeneratePRD
    Owner --> Export
    Owner --> ViewOnly
    
    Admin --> Create
    Admin --> Modify
    Admin --> Delete
    Admin --> GeneratePRD
    Admin --> Export
    Admin --> ViewOnly
    
    Edit --> Create
    Edit --> Modify
    Edit --> GeneratePRD
    Edit --> Export
    Edit --> ViewOnly
    
    View --> ViewOnly
    
    style Owner fill:#ffcdd2
    style Admin fill:#f8bbd0
    style Edit fill:#c8e6c9
    style View fill:#e1f5ff
```

### Multi-Tenant Architecture

```mermaid
graph TB
    subgraph "Tenant Isolation"
        T1[Tenant 1<br/>Products, Users, Data]
        T2[Tenant 2<br/>Products, Users, Data]
        T3[Tenant N<br/>Products, Users, Data]
    end
    
    subgraph "Database Layer"
        DB[(PostgreSQL<br/>Row-Level Security)]
    end
    
    subgraph "Application Layer"
        Backend[FastAPI Backend<br/>Tenant Middleware]
    end
    
    T1 --> Backend
    T2 --> Backend
    T3 --> Backend
    Backend --> DB
    
    style T1 fill:#e1f5ff
    style T2 fill:#c8e6c9
    style T3 fill:#fff9c4
    style Backend fill:#f8bbd0
    style DB fill:#b39ddb
```

## Key Technologies

### Frontend Stack
- **React 18** with TypeScript
- **Vite** for build tooling
- **Tailwind CSS** for styling
- **Nginx** for serving static files

### Backend Stack
- **FastAPI** (Python 3.11) for API server
- **Agno Framework** for multi-agent coordination
- **SQLAlchemy** (async) for database ORM
- **pgvector** for vector search
- **Redis** for caching and sessions

### Database
- **PostgreSQL 15** with pgvector extension
- **Row-level security** for multi-tenant isolation
- **Vector embeddings** for RAG knowledge base

### AI Providers
- **OpenAI** (GPT-4, GPT-4o, embeddings)
- **Anthropic** (Claude Sonnet 4.5)
- **Google** (Gemini 2.0 Flash)

### External Integrations
- **Jira** via REST API
- **GitHub** via REST API
- **Confluence** via REST API
- **V0 Platform** for design generation
- **Lovable AI** for app generation

## Deployment Options

### Local Development (Docker Compose)
```bash
make build-apps      # Build backend and frontend
make up             # Start all services
make health         # Check service health
```

### Kubernetes (Kind - Local Testing)
```bash
make kind-create           # Create Kind cluster
make rebuild-and-deploy-kind  # Build and deploy
make kind-status          # Check deployment status
```

### Kubernetes (EKS - Production)
```bash
make eks-deploy    # Deploy to EKS cluster
make eks-status    # Check deployment status
```

## Summary

IdeaForge AI provides a comprehensive platform for AI-driven product management with:

- **15+ specialized agents** working collaboratively
- **Full product lifecycle** support from ideation to execution
- **Industry-standard scoring** and PRD generation
- **RAG-powered knowledge base** for context-aware responses
- **Multi-tenant architecture** with role-based permissions
- **Flexible deployment** options (Docker Compose, Kind, EKS)
- **External integrations** for seamless workflow

The system is designed for scalability, maintainability, and extensibility, making it suitable for enterprise product management teams.

