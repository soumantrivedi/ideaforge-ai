# IdeaForge AI - Detailed Design Architecture

## Detailed System Design

This document provides a comprehensive view of the internal architecture, data models, and component interactions.

## Backend Architecture

```mermaid
graph TB
    subgraph "API Layer"
        API1[FastAPI Main<br/>main.py]
        API2[Database API<br/>api/database.py]
        API3[Agent Endpoints<br/>/api/agents/*]
        API4[Multi-Agent Endpoints<br/>/api/multi-agent/*]
    end

    subgraph "Orchestration Layer"
        ORC1[AgenticOrchestrator<br/>orchestrator.py]
        ORC2[CoordinatorAgent<br/>coordinator_agent.py]
        ORC3[Workflow Manager<br/>Collaborative Workflows]
    end

    subgraph "Agent Layer"
        AG1[BaseAgent<br/>Abstract Base Class]
        AG2[ResearchAgent]
        AG3[AnalysisAgent]
        AG4[ValidationAgent]
        AG5[StrategyAgent]
        AG6[IdeationAgent]
        AG7[PRDAuthoringAgent]
        AG8[JiraAgent]
    end

    subgraph "Data Access Layer"
        DAL1[Database Module<br/>database.py]
        DAL2[SQLAlchemy ORM<br/>Async Sessions]
        DAL3[Query Builders]
    end

    subgraph "Provider Layer"
        PR1[ProviderRegistry<br/>provider_registry.py]
        PR2[Provider Clients<br/>OpenAI/Claude/Gemini]
    end

    subgraph "External Integration Layer"
        EXT1[AI Provider Clients]
        EXT2[MCP Servers]
        EXT3[External APIs]
    end

    API1 --> API2
    API1 --> API3
    API1 --> API4
    API3 --> ORC1
    API4 --> ORC2
    ORC1 --> ORC2
    ORC2 --> AG1
    AG1 --> AG2
    AG1 --> AG3
    AG1 --> AG4
    AG1 --> AG5
    AG1 --> AG6
    AG1 --> AG7
    AG1 --> AG8
    AG2 --> DAL1
    AG3 --> DAL1
    AG4 --> DAL1
    AG5 --> DAL1
    AG6 --> DAL1
    AG7 --> DAL1
    AG8 --> DAL1
    DAL1 --> DAL2
    DAL2 --> DAL3
    API1 --> PR1
    API2 --> PR1
    AG1 --> PR1
    PR1 --> PR2
    PR2 --> EXT1
    AG8 --> EXT2
    AG8 --> EXT3

    style API1 fill:#e3f2fd
    style ORC2 fill:#f3e5f5
    style AG1 fill:#fff3e0
    style DAL1 fill:#e8f5e9
    style PR1 fill:#fff9c4
```

### Provider Registry & Key Verification

- `/api/providers/verify` accepts a payload of API keys and performs lightweight calls (`openai.models.list()`, `anthropic.models.list()`, Gemini `count_tokens`) from within the backend container to ensure outbound connectivity and credential validity.
- `/api/providers/configure` persists the verified keys in memory, instantiates reusable clients (AsyncOpenAI, Anthropic, Gemini), and exposes the active provider list for the health check route.
- `BaseAgent` and all derived agents call `provider_registry.get_<provider>_client()` so runtime changes take effect immediately—no backend restart required.
- Health responses and the ProviderConfig UI consume the configured provider list to display live status to operators.

## Frontend Architecture

```mermaid
graph TB
    subgraph "Application Root"
        APP[App.tsx<br/>Main Component]
    end

    subgraph "UI Components"
        UI1[EnhancedChatInterface<br/>Chat UI]
        UI2[AgentStatusPanel<br/>Agent Monitoring]
        UI3[ProductLifecycleSidebar<br/>Lifecycle Management]
        UI4[KnowledgeBaseManager<br/>RAG Interface]
        UI5[ProviderConfig<br/>Settings]
        UI6[PhaseFormModal<br/>Phase Forms]
    end

    subgraph "State Management"
        ST1[React Hooks<br/>useState/useEffect]
        ST2[Context API<br/>Global State]
        ST3[Local Storage<br/>Persistent Config]
    end

    subgraph "Service Layer"
        SV1[AI Provider Manager<br/>ai-providers.ts]
        SV2[RAG System<br/>rag-system.ts]
        SV3[Product Lifecycle<br/>product-lifecycle-service.ts]
        SV4[Multi-Agent System<br/>multi-agent-system.ts]
    end

    subgraph "API Communication"
        API1[Fetch API<br/>HTTP Client]
        API2[WebSocket<br/>Streaming]
        API3[Error Handling]
    end

    APP --> UI1
    APP --> UI2
    APP --> UI3
    APP --> UI4
    APP --> UI5
    APP --> UI6
    APP --> ST1
    ST1 --> ST2
    ST2 --> ST3
    UI1 --> SV1
    UI1 --> SV2
    UI1 --> SV4
    UI3 --> SV3
    UI4 --> SV2
    SV1 --> API1
    SV2 --> API1
    SV3 --> API1
    SV4 --> API1
    API1 --> API2
    API1 --> API3

    style APP fill:#e3f2fd
    style SV1 fill:#fff3e0
    style API1 fill:#e8f5e9
```

## Database Schema Architecture

```mermaid
erDiagram
    USER_PROFILES ||--o{ PRODUCTS : creates
    USER_PROFILES ||--o{ CONVERSATION_SESSIONS : has
    PRODUCTS ||--o{ PRD_DOCUMENTS : contains
    PRODUCTS ||--o{ PHASE_SUBMISSIONS : tracks
    PRODUCTS ||--o{ KNOWLEDGE_ARTICLES : has
    PRODUCTS ||--o{ EXPORTED_DOCUMENTS : generates
    CONVERSATION_SESSIONS ||--o{ AGENT_MESSAGES : contains
    CONVERSATION_SESSIONS ||--o{ CONVERSATION_HISTORY : tracks
    PRODUCT_LIFECYCLE_PHASES ||--o{ PHASE_SUBMISSIONS : defines
    PRODUCT_LIFECYCLE_PHASES ||--o{ CONVERSATION_HISTORY : references
    PRODUCTS ||--o{ AGENT_ACTIVITY_LOG : logs
    PRODUCTS ||--o{ FEEDBACK_ENTRIES : receives

    USER_PROFILES {
        uuid id PK
        text email UK
        text full_name
        text persona
        jsonb preferences
        timestamptz created_at
        timestamptz updated_at
    }

    PRODUCTS {
        uuid id PK
        uuid user_id FK
        text name
        text description
        text status
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
    }

    PRODUCT_LIFECYCLE_PHASES {
        uuid id PK
        text phase_name UK
        integer phase_order
        text description
        text icon
        jsonb required_fields
        jsonb template_prompts
        timestamptz created_at
    }

    PHASE_SUBMISSIONS {
        uuid id PK
        uuid product_id FK
        uuid phase_id FK
        uuid user_id
        jsonb form_data
        text generated_content
        text status
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
    }

    KNOWLEDGE_ARTICLES {
        uuid id PK
        uuid product_id FK
        text title
        text content
        text source
        vector embedding
        jsonb metadata
        timestamptz created_at
    }

    CONVERSATION_HISTORY {
        uuid id PK
        uuid session_id FK
        uuid product_id FK
        uuid phase_id FK
        text message_type
        text agent_name
        text agent_role
        text content
        text formatted_content
        uuid parent_message_id FK
        jsonb interaction_metadata
        timestamptz created_at
    }
```

## Request Processing Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant BackendAPI
    participant Orchestrator
    participant Coordinator
    participant Agent
    participant Database
    participant AIProvider
    participant Redis

    User->>Frontend: Submit Message
    Frontend->>Frontend: Validate Input
    Frontend->>BackendAPI: POST /api/agents/process
    BackendAPI->>BackendAPI: Validate Request
    BackendAPI->>Orchestrator: route_request()
    Orchestrator->>Coordinator: route_request()
    Coordinator->>Coordinator: determine_primary_agent()
    Coordinator->>Coordinator: determine_supporting_agents()
    Coordinator->>Agent: process(messages, context)
    Agent->>Database: Load Conversation History
    Database-->>Agent: Return History
    Agent->>Redis: Check Cache
    alt Cache Hit
        Redis-->>Agent: Return Cached Response
    else Cache Miss
        Agent->>AIProvider: Generate Response
        AIProvider-->>Agent: Stream Response
        Agent->>Redis: Cache Response
    end
    Agent->>Database: Save Message
    Agent->>Database: Save Interaction
    Agent-->>Coordinator: Return Response
    Coordinator-->>Orchestrator: Return Response
    Orchestrator-->>BackendAPI: Return Response
    BackendAPI-->>Frontend: Stream Response
    Frontend->>Frontend: Update UI
    Frontend-->>User: Display Response
```

## Multi-Agent Coordination Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant Coordinator
    participant PrimaryAgent
    participant SupportingAgent1
    participant SupportingAgent2
    participant Database

    User->>Frontend: Submit Multi-Agent Query
    Frontend->>Backend: POST /api/multi-agent/process
    Backend->>Coordinator: process_multi_agent_request()
    Coordinator->>Coordinator: Determine Coordination Mode
    
    alt Sequential Mode
        Coordinator->>PrimaryAgent: Process Step 1
        PrimaryAgent-->>Coordinator: Response 1
        Coordinator->>SupportingAgent1: Process Step 2 (with Response 1)
        SupportingAgent1-->>Coordinator: Response 2
        Coordinator->>SupportingAgent2: Process Step 3 (with Response 2)
        SupportingAgent2-->>Coordinator: Final Response
    else Parallel Mode
        par Parallel Processing
            Coordinator->>PrimaryAgent: Process Query
            Coordinator->>SupportingAgent1: Process Query
            Coordinator->>SupportingAgent2: Process Query
        end
        PrimaryAgent-->>Coordinator: Response 1
        SupportingAgent1-->>Coordinator: Response 2
        SupportingAgent2-->>Coordinator: Response 3
        Coordinator->>Coordinator: Synthesize Responses
    else Collaborative Mode
        Coordinator->>PrimaryAgent: Process Query
        PrimaryAgent->>Coordinator: consult_agent(SupportingAgent1)
        Coordinator->>SupportingAgent1: Process Consultation
        SupportingAgent1-->>Coordinator: Consultation Response
        Coordinator-->>PrimaryAgent: Return Consultation
        PrimaryAgent->>Coordinator: consult_agent(SupportingAgent2)
        Coordinator->>SupportingAgent2: Process Consultation
        SupportingAgent2-->>Coordinator: Consultation Response
        Coordinator-->>PrimaryAgent: Return Consultation
        PrimaryAgent->>PrimaryAgent: Synthesize with Consultations
        PrimaryAgent-->>Coordinator: Final Response
    else Debate Mode
        Coordinator->>PrimaryAgent: Round 1 - Present View
        Coordinator->>SupportingAgent1: Round 1 - Present View
        Coordinator->>SupportingAgent2: Round 1 - Present View
        PrimaryAgent-->>Coordinator: View 1
        SupportingAgent1-->>Coordinator: View 2
        SupportingAgent2-->>Coordinator: View 3
        Coordinator->>PrimaryAgent: Round 2 - Respond to Views
        Coordinator->>SupportingAgent1: Round 2 - Respond to Views
        Coordinator->>SupportingAgent2: Round 2 - Respond to Views
        PrimaryAgent-->>Coordinator: Refined View 1
        SupportingAgent1-->>Coordinator: Refined View 2
        SupportingAgent2-->>Coordinator: Refined View 3
        Coordinator->>Coordinator: Synthesize All Views
    end
    
    Coordinator->>Database: Save Agent Interactions
    Coordinator-->>Backend: Return Multi-Agent Response
    Backend-->>Frontend: Return Response
    Frontend-->>User: Display Response
```

## Data Persistence Architecture

```mermaid
graph TB
    subgraph "Application Layer"
        APP[Application Code]
    end

    subgraph "ORM Layer"
        ORM[SQLAlchemy Async]
        MODELS[Pydantic Models]
    end

    subgraph "Database Connection Pool"
        POOL[Async Connection Pool<br/>Size: 10<br/>Max Overflow: 20]
    end

    subgraph "PostgreSQL Database"
        PG[(PostgreSQL 15)]
        EXT1[pgvector Extension]
        EXT2[uuid-ossp Extension]
        FUNC[Vector Search Functions]
    end

    subgraph "Storage Layer"
        VOL[Docker Volume<br/>postgres-data]
        DISK[Host Filesystem]
    end

    APP --> ORM
    ORM --> MODELS
    ORM --> POOL
    POOL --> PG
    PG --> EXT1
    PG --> EXT2
    PG --> FUNC
    PG --> VOL
    VOL --> DISK

    style APP fill:#e3f2fd
    style ORM fill:#fff3e0
    style PG fill:#b39ddb
    style VOL fill:#c8e6c9
```

## Caching Architecture

```mermaid
graph TB
    subgraph "Application Layer"
        APP[Backend Application]
    end

    subgraph "Cache Strategy"
        L1[L1: In-Memory Cache<br/>Python dict]
        L2[L2: Redis Cache<br/>Distributed Cache]
        L3[L3: Database<br/>PostgreSQL]
    end

    subgraph "Cache Types"
        CT1[Agent Responses<br/>TTL: 1 hour]
        CT2[User Sessions<br/>TTL: 24 hours]
        CT3[API Keys<br/>TTL: 5 minutes]
        CT4[Query Results<br/>TTL: 30 minutes]
    end

    subgraph "Redis Instance"
        RD[(Redis 7<br/>Port 6379)]
        RDVOL[redis-data Volume]
    end

    APP --> L1
    L1 -->|Cache Miss| L2
    L2 -->|Cache Miss| L3
    L2 --> CT1
    L2 --> CT2
    L2 --> CT3
    L2 --> CT4
    L2 --> RD
    RD --> RDVOL

    style APP fill:#e3f2fd
    style L2 fill:#ffccbc
    style RD fill:#ffccbc
```

## Error Handling Architecture

```mermaid
graph TB
    subgraph "Error Sources"
        E1[User Input Errors]
        E2[API Errors]
        E3[Database Errors]
        E4[AI Provider Errors]
        E5[Network Errors]
    end

    subgraph "Error Handling Layer"
        H1[Input Validation<br/>Pydantic Models]
        H2[API Error Handlers<br/>FastAPI Exception Handlers]
        H3[Database Error Handlers<br/>SQLAlchemy Exceptions]
        H4[AI Provider Error Handlers<br/>Retry Logic]
        H5[Network Error Handlers<br/>Timeout & Retry]
    end

    subgraph "Error Response"
        R1[Structured Error Response<br/>JSON Format]
        R2[Error Logging<br/>structlog]
        R3[Error Monitoring<br/>Health Checks]
    end

    E1 --> H1
    E2 --> H2
    E3 --> H3
    E4 --> H4
    E5 --> H5
    H1 --> R1
    H2 --> R1
    H3 --> R1
    H4 --> R1
    H5 --> R1
    H1 --> R2
    H2 --> R2
    H3 --> R2
    H4 --> R2
    H5 --> R2
    R1 --> R3

    style E1 fill:#ffcdd2
    style R1 fill:#c8e6c9
    style R2 fill:#fff9c4
```

## Configuration Management

```mermaid
graph TB
    subgraph "Configuration Sources"
        C1[Environment Variables<br/>.env file]
        C2[Docker Compose<br/>docker-compose.yml]
        C3[Application Config<br/>config.py]
        C4[Frontend Config<br/>vite.config.ts]
    end

    subgraph "Configuration Types"
        T1[Database Config<br/>DATABASE_URL]
        T2[API Keys<br/>OPENAI_API_KEY, etc.]
        T3[Service URLs<br/>VITE_API_URL]
        T4[Feature Flags<br/>LOG_LEVEL, etc.]
    end

    subgraph "Configuration Loading"
        L1[Backend: pydantic-settings]
        L2[Frontend: import.meta.env]
        L3[Docker: Environment Variables]
    end

    subgraph "Runtime Configuration"
        R1[Backend Settings Object]
        R2[Frontend Config State]
        R3[Container Environment]
    end

    C1 --> L1
    C1 --> L2
    C2 --> L3
    C3 --> L1
    C4 --> L2
    L1 --> T1
    L1 --> T2
    L2 --> T3
    L3 --> T4
    T1 --> R1
    T2 --> R1
    T3 --> R2
    T4 --> R3

    style C1 fill:#e3f2fd
    style R1 fill:#fff3e0
    style R2 fill:#e8f5e9
```

## Logging Architecture

```mermaid
graph TB
    subgraph "Log Sources"
        S1[Frontend<br/>Console Logs]
        S2[Backend<br/>Application Logs]
        S3[Database<br/>Query Logs]
        S4[Containers<br/>Docker Logs]
    end

    subgraph "Logging Framework"
        F1[Frontend: console.log]
        F2[Backend: structlog]
        F3[Database: PostgreSQL Logs]
        F4[Container: Docker Logging]
    end

    subgraph "Log Levels"
        L1[DEBUG<br/>Detailed Information]
        L2[INFO<br/>General Information]
        L3[WARNING<br/>Warnings]
        L4[ERROR<br/>Errors]
        L5[CRITICAL<br/>Critical Issues]
    end

    subgraph "Log Output"
        O1[Console Output<br/>Development]
        O2[File Output<br/>Production]
        O3[Docker Logs<br/>Container Logs]
        O4[Structured JSON<br/>Machine Readable]
    end

    S1 --> F1
    S2 --> F2
    S3 --> F3
    S4 --> F4
    F1 --> L1
    F2 --> L2
    F2 --> L3
    F2 --> L4
    F2 --> L5
    L1 --> O1
    L2 --> O1
    L3 --> O2
    L4 --> O2
    L5 --> O2
    F4 --> O3
    F2 --> O4

    style S2 fill:#e3f2fd
    style F2 fill:#fff3e0
    style O4 fill:#e8f5e9
```

