# Agno Framework Optimization Backlog

## Executive Summary

This document provides a comprehensive optimization backlog for the Agno framework implementation in IdeaforgeAI, based on the performance improvements suggested in `improvements.md`. The goal is to reduce multi-agent orchestration time from ~2 minutes to under 30 seconds while maintaining or improving response quality.

---

## 1. Current Performance Analysis

### 1.1 Performance Bottlenecks (Based on Code Review)

**Identified Issues:**
1. **No profiling/metrics** - Cannot identify where time is spent
2. **Heavy models** - Using GPT-5.1 for all agents (expensive & slow)
3. **No parallelism** - Agents likely run sequentially
4. **Large context** - Full message history sent to every agent
5. **No caching** - Repeated queries hit LLM every time
6. **Synchronous execution** - Blocking operations
7. **No tool result compression** - Large tool outputs sent to model
8. **Unbounded agent consultations** - Agents may consult multiple times

### 1.2 Current Agent Configuration

**From `agno_base_agent.py`:**
- Model priority: GPT-5.1 → Gemini 3.0 Pro → Claude 4 Sonnet
- RAG enabled for most agents
- No explicit max_tokens, temperature settings
- No history limits
- No tool result compression

**From `agno_coordinator_agent.py` & `agno_enhanced_coordinator.py`:**
- Multiple agents initialized upfront
- Enhanced coordinator with heavy contextualization
- No explicit parallelism configuration
- No reasoning step limits

---

## 2. Optimization Backlog

### Priority 1: Critical Performance Fixes (Immediate Impact)

#### 2.1.1 Add Performance Profiling & Metrics
**Current State:** No visibility into where time is spent
**Target:** Detailed metrics for every agent call, tool call, and orchestration step
**Impact:** ⭐⭐⭐⭐⭐ (Essential for optimization)
**Effort:** Medium
**Implementation:**

```python
# Add to agno_base_agent.py
class AgnoBaseAgent(ABC):
    def __init__(self, ...):
        self.metrics = {
            'total_calls': 0,
            'total_time': 0.0,
            'avg_time': 0.0,
            'tool_calls': 0,
            'token_usage': {'input': 0, 'output': 0}
        }
    
    async def process(self, ...):
        start_time = time.time()
        try:
            # Enable debug mode
            if hasattr(self.agno_agent, 'debug_mode'):
                self.agno_agent.debug_mode = True
            
            response = await self.agno_agent.arun(query)
            
            # Collect metrics
            duration = time.time() - start_time
            self.metrics['total_calls'] += 1
            self.metrics['total_time'] += duration
            self.metrics['avg_time'] = self.metrics['total_time'] / self.metrics['total_calls']
            
            # Extract token usage if available
            if hasattr(response, 'metrics'):
                self.metrics['token_usage']['input'] += response.metrics.get('input_tokens', 0)
                self.metrics['token_usage']['output'] += response.metrics.get('output_tokens', 0)
            
            return response
        finally:
            self.logger.info("agent_metrics", 
                           agent=self.name,
                           duration=duration,
                           metrics=self.metrics)
```

**Files to Modify:**
- `backend/agents/agno_base_agent.py` - Add metrics collection
- `backend/agents/agno_coordinator_agent.py` - Add orchestration metrics
- `backend/agents/agno_enhanced_coordinator.py` - Add coordination metrics
- `backend/api/multi_agent.py` - Return metrics in response

**Acceptance Criteria:**
- [ ] Every agent call logs duration, tokens, tool calls
- [ ] Orchestration logs total time, agent sequence, parallelization
- [ ] Metrics returned in API response
- [ ] Dashboard shows performance breakdown

---

#### 2.1.2 Implement Model Tier Strategy
**Current State:** All agents use GPT-5.1 (expensive & slow)
**Target:** Use fast models for most agents, heavy models only for critical reasoning
**Impact:** ⭐⭐⭐⭐⭐ (50-70% latency reduction)
**Effort:** Low-Medium
**Implementation:**

```python
# Add to agno_base_agent.py
def _get_agno_model(self, model_tier: str = "fast"):
    """
    Get model based on tier:
    - fast: gpt-4o-mini, claude-3-haiku, gemini-1.5-flash (for most agents)
    - standard: gpt-4o, claude-3.5-sonnet, gemini-1.5-pro (for coordinators)
    - premium: gpt-5.1, claude-4-sonnet, gemini-3.0-pro (for critical reasoning)
    """
    if model_tier == "fast":
        # Fast models for most agents
        if provider_registry.has_openai_key():
            return OpenAIChat(id="gpt-4o-mini", api_key=provider_registry.get_openai_key())
        elif provider_registry.has_gemini_key():
            return Gemini(id="gemini-1.5-flash", api_key=provider_registry.get_gemini_key())
        elif provider_registry.has_claude_key():
            return Claude(id="claude-3-haiku-20240307", api_key=provider_registry.get_claude_key())
    elif model_tier == "standard":
        # Standard models for coordinators
        if provider_registry.has_openai_key():
            return OpenAIChat(id="gpt-4o", api_key=provider_registry.get_openai_key())
        # ... similar for other providers
    elif model_tier == "premium":
        # Premium models for critical reasoning
        if provider_registry.has_openai_key():
            return OpenAIChat(id=settings.agent_model_primary, api_key=provider_registry.get_openai_key())
        # ... similar for other providers
    
    return None

# Update agent initialization
class AgnoResearchAgent(AgnoBaseAgent):
    def __init__(self, enable_rag: bool = False):
        super().__init__(
            name="Research Specialist",
            role="research",
            system_prompt=RESEARCH_PROMPT,
            enable_rag=enable_rag,
            model_tier="fast"  # Use fast model
        )

class AgnoCoordinatorAgent:
    def __init__(self, enable_rag: bool = True):
        # Coordinator uses standard model
        self.model = self._get_agno_model("standard")
        # ...
```

**Files to Modify:**
- `backend/agents/agno_base_agent.py` - Add model_tier parameter
- `backend/agents/agno_research_agent.py` - Use fast tier
- `backend/agents/agno_analysis_agent.py` - Use fast tier
- `backend/agents/agno_ideation_agent.py` - Use fast tier
- `backend/agents/agno_prd_authoring_agent.py` - Use standard tier (important)
- `backend/agents/agno_coordinator_agent.py` - Use standard tier
- `backend/agents/agno_enhanced_coordinator.py` - Use standard tier

**Acceptance Criteria:**
- [ ] Research, Analysis, Ideation agents use fast models
- [ ] PRD Authoring uses standard model
- [ ] Coordinators use standard model
- [ ] Only critical reasoning uses premium models
- [ ] 50%+ latency reduction observed

---

#### 2.1.3 Implement Parallel Agent Execution
**Current State:** Agents likely run sequentially
**Target:** Run independent agents in parallel using Agno Teams/Workflows
**Impact:** ⭐⭐⭐⭐⭐ (60-80% latency reduction for multi-agent queries)
**Effort:** Medium-High
**Implementation:**

```python
# Update agno_enhanced_coordinator.py
from agno.team import Team
from agno.workflow import Workflow, Step
from agno.workflow.parallel import Parallel

class AgnoEnhancedCoordinator:
    def _create_enhanced_teams(self):
        """Create teams with parallel execution for independent agents."""
        
        # Create parallel workflow for research + analysis
        self.parallel_research_workflow = Workflow(
            name="Parallel Research & Analysis",
            steps=[
                Parallel(
                    Step(name="Research", agent=self.research_agent.agno_agent),
                    Step(name="Analysis", agent=self.analysis_agent.agno_agent),
                    name="Research Phase"
                ),
                Step(name="Synthesis", agent=self.summary_agent.agno_agent)
            ]
        )
        
        # Create team with parallel members
        self.parallel_team = Team(
            name="Parallel Agent Team",
            members=[
                self.research_agent.agno_agent,
                self.analysis_agent.agno_agent,
                self.ideation_agent.agno_agent,
            ],
            model=self._get_agno_model("standard"),
            # Enable parallel execution
            run_parallel=True,  # If Agno supports this
        )
    
    async def process_parallel(self, query: str, context: Dict[str, Any]):
        """Process query with parallel agent execution."""
        # Determine which agents are needed
        needed_agents = self._determine_agents(query)
        
        # If agents are independent, run in parallel
        if self._are_independent(needed_agents):
            # Use parallel workflow
            results = await self.parallel_research_workflow.arun(query)
            return results
        else:
            # Use sequential if dependencies exist
            return await self.process_sequential(query, context)
    
    def _are_independent(self, agents: List[str]) -> bool:
        """Check if agents can run in parallel."""
        # Research and Analysis are independent
        # Ideation can run parallel to Research
        # PRD Authoring depends on Research + Analysis
        independent_pairs = [
            {"research", "analysis"},
            {"research", "ideation"},
            {"analysis", "ideation"},
        ]
        agent_set = set(agents)
        return any(agent_set.issuperset(pair) for pair in independent_pairs)
```

**Files to Modify:**
- `backend/agents/agno_enhanced_coordinator.py` - Add parallel workflows
- `backend/agents/agno_coordinator_agent.py` - Add parallel execution
- `backend/api/multi_agent.py` - Use parallel processing when possible

**Acceptance Criteria:**
- [ ] Independent agents run in parallel
- [ ] Dependent agents run sequentially
- [ ] 60%+ latency reduction for multi-agent queries
- [ ] No quality degradation

---

#### 2.1.4 Limit Context & History
**Current State:** Full message history sent to every agent
**Target:** Limit history, compress context, use summaries
**Impact:** ⭐⭐⭐⭐ (30-50% latency reduction, lower costs)
**Effort:** Medium
**Implementation:**

```python
# Update agno_base_agent.py
class AgnoBaseAgent(ABC):
    def __init__(
        self,
        ...,
        max_history_runs: int = 3,
        max_tool_calls_from_history: int = 3,
        compress_tool_results: bool = True,
    ):
        self.max_history_runs = max_history_runs
        self.max_tool_calls_from_history = max_tool_calls_from_history
        self.compress_tool_results = compress_tool_results
        
        # Create agent with history limits
        self.agno_agent = Agent(
            name=name,
            model=model,
            instructions=system_prompt,
            knowledge=knowledge,
            tools=tools or [],
            markdown=True,
            # Add history limits if Agno supports
            add_history_to_context=True,
            num_history_runs=max_history_runs,
            max_tool_calls_from_history=max_tool_calls_from_history,
            compress_tool_results=compress_tool_results,
        )
    
    def _format_messages_to_query(self, messages: List[AgentMessage], context: Optional[Dict[str, Any]]) -> str:
        """Limit message history to recent messages."""
        # Only include last N messages
        recent_messages = messages[-self.max_history_runs:] if len(messages) > self.max_history_runs else messages
        
        # Build query from recent messages only
        user_messages = [msg.content for msg in recent_messages if msg.role == "user"]
        user_query = "\n".join(user_messages[-1:])  # Only last user message
        
        # Summarize older context if needed
        if len(messages) > self.max_history_runs:
            older_messages = messages[:-self.max_history_runs]
            context_summary = self._summarize_context(older_messages)
            user_query = f"Previous context: {context_summary}\n\nCurrent request: {user_query}"
        
        # Compress context
        if context:
            compressed_context = self._compress_context(context)
            return f"CONTEXT:\n{compressed_context}\n\nQUERY:\n{user_query}"
        
        return user_query
    
    def _compress_context(self, context: Dict[str, Any]) -> str:
        """Compress context to essential information."""
        # Extract only key fields
        essential = {}
        for key in ['product_id', 'phase_name', 'form_data']:
            if key in context:
                value = context[key]
                if isinstance(value, dict):
                    # Summarize dict
                    essential[key] = {k: str(v)[:100] for k, v in list(value.items())[:5]}
                else:
                    essential[key] = str(value)[:200]
        
        return json.dumps(essential, indent=2)
```

**Files to Modify:**
- `backend/agents/agno_base_agent.py` - Add history limits
- `backend/agents/agno_coordinator_agent.py` - Limit coordinator context
- `backend/api/multi_agent.py` - Limit message history sent to agents

**Acceptance Criteria:**
- [ ] Only last 3 messages sent to agents
- [ ] Context compressed to essential info
- [ ] Tool results compressed
- [ ] 30%+ token reduction
- [ ] 30%+ latency reduction

---

#### 2.1.5 Add Response Caching
**Current State:** Every query hits LLM
**Target:** Cache responses for identical/similar queries
**Impact:** ⭐⭐⭐⭐ (Instant responses for repeated queries)
**Effort:** Medium
**Implementation:**

```python
# Add to agno_base_agent.py
from functools import lru_cache
import hashlib
import json

class AgnoBaseAgent(ABC):
    def __init__(self, ...):
        self.cache_enabled = True
        self.cache_ttl = 3600  # 1 hour
        self.response_cache = {}  # In production, use Redis
    
    async def process(self, messages: List[AgentMessage], context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        # Generate cache key
        cache_key = self._generate_cache_key(messages, context)
        
        # Check cache
        if self.cache_enabled:
            cached_response = self._get_from_cache(cache_key)
            if cached_response:
                self.logger.info("cache_hit", agent=self.name, cache_key=cache_key[:20])
                return cached_response
        
        # Process normally
        response = await self._process_uncached(messages, context)
        
        # Store in cache
        if self.cache_enabled:
            self._store_in_cache(cache_key, response)
        
        return response
    
    def _generate_cache_key(self, messages: List[AgentMessage], context: Optional[Dict[str, Any]]) -> str:
        """Generate cache key from messages and context."""
        # Normalize messages (remove timestamps, etc.)
        normalized = {
            'messages': [{'role': m.role, 'content': m.content} for m in messages],
            'context': self._normalize_context(context) if context else None
        }
        key_str = json.dumps(normalized, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _normalize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize context for caching (remove non-deterministic fields)."""
        normalized = {}
        for key in ['product_id', 'phase_name', 'form_data']:
            if key in context:
                normalized[key] = context[key]
        return normalized
```

**Files to Modify:**
- `backend/agents/agno_base_agent.py` - Add caching
- `backend/services/cache_service.py` - New file for Redis cache (optional)
- `backend/config.py` - Add cache configuration

**Acceptance Criteria:**
- [ ] Identical queries return cached responses
- [ ] Cache TTL configurable
- [ ] Cache hit rate > 20% for development/testing
- [ ] Cache can be disabled per request

---

### Priority 2: High-Value Optimizations (Medium Impact)

#### 2.2.1 Optimize Tool Calls
**Current State:** Tools may be slow, no batching
**Target:** Fast tools, batch operations, timeouts
**Impact:** ⭐⭐⭐⭐ (20-40% latency reduction)
**Effort:** Medium
**Implementation:**

```python
# Add tool optimization
class AgnoBaseAgent(ABC):
    def __init__(self, ..., tool_timeout: int = 10):
        self.tool_timeout = tool_timeout
        # Configure tools with timeouts
        if tools:
            for tool in tools:
                if hasattr(tool, 'timeout'):
                    tool.timeout = tool_timeout
    
    async def _execute_tool_with_timeout(self, tool, *args, **kwargs):
        """Execute tool with timeout."""
        try:
            return await asyncio.wait_for(
                tool.execute(*args, **kwargs),
                timeout=self.tool_timeout
            )
        except asyncio.TimeoutError:
            self.logger.warning("tool_timeout", tool=tool.name, timeout=self.tool_timeout)
            return {"error": "Tool execution timed out"}
```

**Files to Modify:**
- `backend/agents/agno_base_agent.py` - Add tool timeouts
- All tool implementations - Add async support, timeouts
- `backend/agents/agno_v0_agent.py` - Optimize V0 API calls
- `backend/agents/agno_lovable_agent.py` - Optimize Lovable API calls

**Acceptance Criteria:**
- [ ] All tools have 10s timeout
- [ ] Tools use async HTTP clients
- [ ] Tool results compressed before sending to model
- [ ] Batch operations where possible

---

#### 2.2.2 Optimize RAG Retrieval
**Current State:** RAG may retrieve too many documents
**Target:** Limit top_k, pre-filter, use summaries
**Impact:** ⭐⭐⭐ (20-30% latency reduction)
**Effort:** Low-Medium
**Implementation:**

```python
# Update agno_base_agent.py
def _create_knowledge_base(self, table_name: str) -> Optional[Any]:
    """Create knowledge base with optimized retrieval."""
    knowledge = Knowledge(
        vector_db=vector_db,
        embedder=embedder,
        num_documents=3,  # Reduce from 5 to 3
        # Add filters if Agno supports
        # min_similarity=0.7,  # Only return highly relevant docs
    )
    return knowledge
```

**Files to Modify:**
- `backend/agents/agno_base_agent.py` - Reduce num_documents
- `backend/lib/rag-system.ts` - Optimize retrieval

**Acceptance Criteria:**
- [ ] top_k reduced to 3-5
- [ ] Minimum similarity threshold
- [ ] Pre-filter by product_id if available
- [ ] 20%+ latency reduction

---

#### 2.2.3 Disable Unnecessary Features
**Current State:** All features enabled by default
**Target:** Disable features not needed for simple queries
**Impact:** ⭐⭐⭐ (10-20% latency reduction)
**Effort:** Low
**Implementation:**

```python
# Update agent initialization
class AgnoBaseAgent(ABC):
    def __init__(
        self,
        ...,
        enable_agentic_memory: bool = False,  # Disable by default
        enable_session_summaries: bool = False,  # Disable by default
    ):
        self.agno_agent = Agent(
            name=name,
            model=model,
            instructions=system_prompt,
            knowledge=knowledge,
            tools=tools or [],
            markdown=True,
            # Disable memory features for simple queries
            enable_agentic_memory=enable_agentic_memory,
            enable_session_summaries=enable_session_summaries,
        )
```

**Files to Modify:**
- `backend/agents/agno_base_agent.py` - Add feature flags
- `backend/agents/agno_coordinator_agent.py` - Disable for simple queries

**Acceptance Criteria:**
- [ ] Memory features disabled by default
- [ ] Session summaries disabled by default
- [ ] Can be enabled per request
- [ ] 10%+ latency reduction

---

#### 2.2.4 Limit Reasoning Steps
**Current State:** No limits on reasoning steps
**Target:** Cap reasoning steps for coordinators
**Impact:** ⭐⭐⭐ (20-30% latency reduction)
**Effort:** Low
**Implementation:**

```python
# Update agno_enhanced_coordinator.py
class AgnoEnhancedCoordinator:
    def _create_enhanced_teams(self):
        """Create teams with limited reasoning steps."""
        self.team = Team(
            name="Enhanced Coordination Team",
            members=[...],
            model=self._get_agno_model("standard"),
            reasoning_agent=None,  # Disable team-level reasoning
            reasoning_min_steps=1,
            reasoning_max_steps=2,  # Limit to 2 steps
        )
```

**Files to Modify:**
- `backend/agents/agno_enhanced_coordinator.py` - Limit reasoning steps
- `backend/agents/agno_coordinator_agent.py` - Limit reasoning steps

**Acceptance Criteria:**
- [ ] Reasoning steps limited to 1-2
- [ ] Can be increased for complex queries
- [ ] 20%+ latency reduction

---

#### 2.2.5 Use Async Database Operations
**Current State:** May use sync database operations
**Target:** All database operations async
**Impact:** ⭐⭐⭐ (10-20% latency reduction)
**Effort:** Low-Medium
**Implementation:**

```python
# Ensure all DB operations are async
# Already using AsyncSession, but verify all queries are async
# Use AsyncSqliteDb or AsyncMongoDb if using those
```

**Files to Modify:**
- All database queries - Verify async
- `backend/database.py` - Use async connections

**Acceptance Criteria:**
- [ ] All DB operations async
- [ ] No blocking DB calls
- [ ] Connection pooling enabled

---

### Priority 3: Advanced Optimizations (Lower Priority)

#### 2.3.1 Implement Workflow Optimization
**Current State:** Workflows may have unnecessary steps
**Target:** Optimize workflow structure, remove redundant steps
**Impact:** ⭐⭐⭐ (10-15% latency reduction)
**Effort:** Medium
**Implementation:**
- Analyze workflow patterns
- Remove redundant agent consultations
- Combine similar steps
- Use conditional workflows

---

#### 2.3.2 Add Request Batching
**Current State:** Each request processed separately
**Target:** Batch similar requests
**Impact:** ⭐⭐ (5-10% latency reduction)
**Effort:** High
**Implementation:**
- Identify similar requests
- Batch LLM calls
- Distribute results

---

#### 2.3.3 Implement Smart Agent Selection
**Current State:** All agents may be consulted
**Target:** Intelligently select only needed agents
**Impact:** ⭐⭐⭐ (20-30% latency reduction)
**Effort:** Medium
**Implementation:**
- Use lightweight classifier to determine needed agents
- Skip unnecessary agents
- Cache agent selection decisions

---

## 3. Implementation Plan

### Phase 1: Foundation (Week 1-2)
1. ✅ Add performance profiling & metrics
2. ✅ Implement model tier strategy
3. ✅ Add response caching

**Expected Impact:** 40-50% latency reduction

### Phase 2: Parallelization (Week 3-4)
1. ✅ Implement parallel agent execution
2. ✅ Optimize tool calls
3. ✅ Limit context & history

**Expected Impact:** Additional 30-40% latency reduction

### Phase 3: Fine-tuning (Week 5-6)
1. ✅ Optimize RAG retrieval
2. ✅ Disable unnecessary features
3. ✅ Limit reasoning steps
4. ✅ Use async database operations

**Expected Impact:** Additional 10-20% latency reduction

### Phase 4: Advanced (Week 7-8)
1. ✅ Implement workflow optimization
2. ✅ Add request batching (if needed)
3. ✅ Implement smart agent selection

**Expected Impact:** Additional 5-15% latency reduction

---

## 4. Success Metrics

### Performance Targets
- **Current:** ~120 seconds (2 minutes)
- **Target:** <30 seconds for typical queries
- **Stretch Goal:** <15 seconds for simple queries

### Metrics to Track
- Total orchestration time
- Per-agent call time
- Tool call time
- Token usage per agent
- Cache hit rate
- Parallelization efficiency

### Monitoring
- Add metrics endpoint: `/api/metrics/performance`
- Dashboard showing performance breakdown
- Alerts for performance regressions

---

## 5. Testing Strategy

### Performance Tests
1. **Baseline Test:** Measure current performance
2. **After Each Phase:** Measure improvement
3. **Regression Tests:** Ensure no quality degradation

### Test Scenarios
1. Simple query (1 agent)
2. Medium query (2-3 agents)
3. Complex query (4+ agents, consultations)
4. Repeated query (cache test)

### Acceptance Criteria
- [ ] 60%+ latency reduction overall
- [ ] No quality degradation (user testing)
- [ ] Cache hit rate > 20% in dev
- [ ] Parallelization working correctly
- [ ] All metrics being collected

---

## 6. Risk Mitigation

### Risks
1. **Quality Degradation:** Fast models may reduce quality
   - **Mitigation:** A/B test, user feedback, fallback to better models

2. **Cache Staleness:** Cached responses may be outdated
   - **Mitigation:** Short TTL, cache invalidation, disable for dynamic queries

3. **Parallelization Complexity:** Bugs in parallel execution
   - **Mitigation:** Thorough testing, gradual rollout, fallback to sequential

4. **Breaking Changes:** API changes may break frontend
   - **Mitigation:** Version API, backward compatibility, gradual migration

---

## 7. Feature Checklist Template

For each optimization:

- [ ] **Optimization Name:** [Name]
- [ ] **Priority:** [P1/P2/P3]
- [ ] **Expected Impact:** [% latency reduction]
- [ ] **Effort:** [Low/Medium/High]
- [ ] **Files to Modify:** [List files]
- [ ] **Dependencies:** [List dependencies]
- [ ] **Testing Plan:** [List tests]
- [ ] **Rollback Plan:** [How to revert]
- [ ] **Metrics:** [What to measure]
- [ ] **Estimated Time:** [Hours/days]

---

## 8. Quick Reference: Agno Optimization Checklist

Based on `improvements.md`, here's a quick checklist:

### Model Selection
- [ ] Use fast models (gpt-4o-mini) for most agents
- [ ] Use standard models (gpt-4o) for coordinators
- [ ] Use premium models (gpt-5.1) only for critical reasoning
- [ ] Set max_tokens to reasonable limits (256-512 for most)
- [ ] Use appropriate temperature (0.4-0.7)

### Context & History
- [ ] Limit num_history_runs to 3
- [ ] Limit max_tool_calls_from_history to 3
- [ ] Enable compress_tool_results
- [ ] Don't dump huge chat history
- [ ] Use add_history_to_context=False when not needed

### Parallelization
- [ ] Use Parallel steps in Workflows
- [ ] Use Teams with parallel execution
- [ ] Run independent agents concurrently
- [ ] Use async (arun) instead of sync (run)

### Tools & RAG
- [ ] Optimize tool timeouts (10s)
- [ ] Batch tool operations
- [ ] Keep RAG top_k modest (3-5)
- [ ] Pre-chunk and summarize documents
- [ ] Enable tool result caching

### Features
- [ ] Disable enable_agentic_memory unless needed
- [ ] Disable enable_session_summaries unless needed
- [ ] Limit reasoning_min_steps to 1
- [ ] Limit reasoning_max_steps to 2-3
- [ ] Disable team-level reasoning if not needed

### Caching
- [ ] Enable cache_response=True for dev/testing
- [ ] Set cache_ttl appropriately (3600s = 1 hour)
- [ ] Disable caching for dynamic queries
- [ ] Use tool result caching

### Infrastructure
- [ ] Use production mode (not reload=True)
- [ ] Use gunicorn/uvicorn with multiple workers
- [ ] Place services in same region
- [ ] Use connection pooling
- [ ] Keep retries low (0-1) to avoid hidden delays

---

## Conclusion

This optimization backlog provides a systematic approach to reducing IdeaforgeAI's multi-agent orchestration time from ~2 minutes to under 30 seconds. The key is to:

1. **Measure first** - Add profiling to understand bottlenecks
2. **Optimize models** - Use fast models for most agents
3. **Parallelize** - Run independent agents concurrently
4. **Limit context** - Reduce token usage
5. **Cache** - Cache repeated queries
6. **Fine-tune** - Disable unnecessary features

Start with Phase 1 (Foundation) for immediate impact, then proceed through phases systematically. Monitor metrics at each step to ensure improvements and catch regressions early.

