# Deployment Notes - IdeaForgeAI v2

## Latest Changes (November 30, 2025)

### Removed Features
- **Lovable Prototype Generation Button**: Removed from Design panel - users now copy prompts manually
- **Playwright Integration**: Removed browser automation complexity
- **Lovable API Key Requirement**: No longer needed (Lovable uses link generator)

### Enhanced Features

#### 1. Lovable Agent Enhancement
- **Comprehensive Platform Knowledge**: Agent now includes full Lovable.dev capabilities (as of Nov 2025)
- **Industry Best Practices**: Integrated modern React/Next.js patterns, accessibility standards, performance optimization
- **All Phase Context**: Prompt generation now uses data from all product lifecycle phases
- **Clean Prompts**: Generated prompts are ready for direct copy-paste into Lovable.dev UI

#### 2. Agent Dashboard
- **Endpoint**: `GET /api/agents/usage-stats`
- **Features**:
  - Agent usage statistics from first login
  - Percentage usage by agent
  - Processing time metrics
  - Cache hit rates
  - Token usage tracking
  - Usage trends (last 30 days)
  - Usage by product lifecycle phase

#### 3. System Optimizations
- **Redis Cache**: Distributed caching for agent responses
- **Rate Limiting**: API protection with Redis-backed rate limiting
- **Error Handling**: Centralized error handling framework
- **Natural Language Understanding**: Prevents unnecessary AI calls for negative responses

### API Endpoints

#### Design Endpoints
- `POST /api/design/generate-prompt` - Generate V0 or Lovable prompts
- `POST /api/design/generate-mockup` - Generate V0 mockups
- `POST /api/design/create-project` - Create V0 project
- `POST /api/design/submit-chat` - Submit chat to V0 project
- `GET /api/design/check-status` - Check V0 project status

#### Agent Endpoints
- `GET /api/agents/usage-stats` - Get agent usage statistics
- `POST /api/multi-agent/process` - Process multi-agent requests
- `GET /api/streaming/multi-agent/stream` - Stream multi-agent responses

### Database Schema
- Uses `product_lifecycle_phases` table (not `phases`)
- `conversation_history` table tracks agent usage with `tenant_id`

### Deployment

#### Kind Cluster
```bash
# Build images
docker build -f Dockerfile.backend -t ideaforge-ai-backend:final-production .
docker build -f Dockerfile.frontend -t ideaforge-ai-frontend:final-production .

# Load to Kind
kind load docker-image ideaforge-ai-backend:final-production --name ideaforge-ai
kind load docker-image ideaforge-ai-frontend:final-production --name ideaforge-ai

# Deploy
kubectl set image deployment/backend backend=ideaforge-ai-backend:final-production -n ideaforge-ai
kubectl set image deployment/frontend frontend=ideaforge-ai-frontend:final-production -n ideaforge-ai
kubectl rollout restart deployment/backend deployment/frontend -n ideaforge-ai
```

#### Environment Variables
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Claude API key
- `GOOGLE_API_KEY` - Gemini API key
- `V0_API_KEY` - V0 API key (for V0 mockup generation)
- `REDIS_URL` - Redis connection URL (default: `redis://redis:6379/0`)
- `DATABASE_URL` - PostgreSQL connection URL

### User Workflow

#### Lovable Prototype Generation
1. Navigate to Design phase
2. Click "Help with AI" in Lovable Prompt section
3. Agent generates optimized prompt with all product data
4. User selects all, copies the prompt
5. User pastes into Lovable.dev UI manually

#### V0 Prototype Generation
1. Navigate to Design phase
2. Generate V0 prompt using "Help with AI"
3. Click "Generate V0 Prototype"
4. System creates project and submits chat
5. Check status using "Check Status" button

### Known Issues
- None currently

### Production Readiness
- ✅ All endpoints tested
- ✅ Database queries optimized
- ✅ Error handling implemented
- ✅ Rate limiting configured
- ✅ Caching implemented
- ✅ Documentation updated

