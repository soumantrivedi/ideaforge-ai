# Performance Optimizations for 100+ Concurrent Users

## Overview
This document outlines optimizations to reduce response times and improve agent processing throughput for 100+ concurrent users.

## Current Performance Issues
- **P95 Response Time**: 63.84s (Target: <30s) ❌
- **Error Rate**: 20.0% (Target: <5%) ❌
- **Throughput**: 1.18 req/s (Target: >2 req/s) ❌

## Optimization Strategy

### 1. Backend Resource Optimization

#### Current Configuration
- CPU Request: 1000m (1 core)
- CPU Limit: 3000m (3 cores)
- Memory Request: 1.5Gi
- Memory Limit: 3Gi

#### Optimized Configuration
- **CPU Request**: 2000m (2 cores) - Increased for parallel agent processing
- **CPU Limit**: 4000m (4 cores) - More headroom for concurrent operations
- **Memory Request**: 2Gi - Increased for agent context and caching
- **Memory Limit**: 4Gi - Support larger agent responses and context

**Rationale**: Agent processing is CPU-intensive, especially when running multiple agents in parallel. More CPU allows faster processing of concurrent requests.

### 2. Database Connection Pool Optimization

#### Current Configuration
- `pool_size`: 15 connections per pod
- `max_overflow`: 25 connections per pod
- Total: 40 connections per pod
- With 5 pods: 200 total connections

#### Optimized Configuration
- **`pool_size`**: 30 connections per pod (increased from 15)
- **`max_overflow`**: 40 connections per pod (increased from 25)
- **Total**: 70 connections per pod
- **With 5-20 pods**: 350-1400 total connections
- **PostgreSQL max_connections**: 500 (supports up to 7 backend pods at full capacity)

**Rationale**: Each agent query may require multiple database operations (RAG, context loading, session storage, vector searches). Significantly more connections reduce connection wait time and improve throughput.

### 2.1. PostgreSQL Resource Optimization

#### Current Configuration
- CPU Request: 250m
- CPU Limit: 1000m (1 core)
- Memory Request: 512Mi
- Memory Limit: 2Gi

#### Optimized Configuration
- **CPU Request**: 1000m (1 core) - Increased from 250m
- **CPU Limit**: 2000m (2 cores) - Increased from 1000m
- **Memory Request**: 2Gi - Increased from 512Mi
- **Memory Limit**: 4Gi - Increased from 2Gi

**Rationale**: PostgreSQL needs more CPU and memory to handle concurrent queries efficiently, especially for vector searches (pgvector) and complex joins.

### 2.2. PostgreSQL Performance Tuning

#### Optimized Configuration
- **max_connections**: 500 (supports high concurrency)
- **shared_buffers**: 1GB (25% of 4Gi memory limit)
- **effective_cache_size**: 3GB (75% of 4Gi memory limit)
- **work_mem**: 8MB (increased for complex queries)
- **maintenance_work_mem**: 256MB (faster VACUUM, CREATE INDEX)
- **max_parallel_workers**: 4 (utilize multiple CPU cores)
- **max_parallel_workers_per_gather**: 2 (parallel query execution)
- **wal_buffers**: 16MB (faster write performance)
- **checkpoint_completion_target**: 0.9 (smoother checkpoints)

**Rationale**: These settings optimize PostgreSQL for high concurrency, faster query execution, and better utilization of available resources.

### 3. HPA Scaling Optimization

#### Current Configuration
- CPU Threshold: 70%
- Memory Threshold: 80%
- Scale Down: 5 minutes stabilization
- Scale Up: Immediate

#### Optimized Configuration
- **CPU Threshold**: 60% (lowered from 70%) - Scale earlier
- **Memory Threshold**: 75% (lowered from 80%) - Scale earlier
- **Scale Down**: 10 minutes stabilization (increased from 5) - Prevent thrashing
- **Scale Up**: Immediate (unchanged)
- **Scale Up Policy**: Add 6 pods at a time (increased from 4) - Faster response to load

**Rationale**: Lower thresholds trigger scaling earlier, preventing response time degradation. More aggressive scale-up handles sudden load spikes better.

### 4. Agent Processing Optimization

#### Current Configuration
- `AGENT_RESPONSE_TIMEOUT`: 180 seconds (3 minutes)
- Parallel execution: Research, Analysis, Ideation run in parallel
- Sequential: RAG → (Research, Analysis, Ideation) → PRD

#### Optimized Configuration
- **`AGENT_RESPONSE_TIMEOUT`**: 180 seconds (3 minutes) - **KEPT HIGH** to avoid truncating responses and maintain quality
- **Agent Concurrency**: Add environment variable `AGENT_MAX_CONCURRENT: "10"` - Limit concurrent agent calls per pod
- **Parallel Execution**: All independent agents run in parallel (not just Research/Analysis/Ideation)
- **Streaming**: Enable streaming responses for faster time-to-first-byte

**Rationale**: Keeping timeout high ensures agents can complete complex responses without truncation. Concurrency limit prevents resource exhaustion. More parallelization reduces total processing time.

### 5. FastAPI/Uvicorn Worker Optimization

#### Current Configuration
- Default Uvicorn workers (likely 1 per pod)

#### Optimized Configuration
- **Uvicorn Workers**: 2-4 workers per pod (based on CPU cores)
- **Worker Class**: `uvicorn.workers.UvicornWorker` with async support
- **Thread Pool**: Increase default thread pool size for blocking operations

**Rationale**: Multiple workers per pod allow better CPU utilization and handle more concurrent requests.

### 6. Redis Connection Pool Optimization

#### Current Configuration
- Default Redis connection pool

#### Optimized Configuration
- **Connection Pool Size**: 20 connections per pod
- **Max Connections**: 50 per pod
- **Connection Timeout**: 5 seconds
- **Retry Policy**: Exponential backoff with max 3 retries

**Rationale**: Redis is used for token storage and caching. More connections reduce wait time during high concurrency.

### 7. Agent Model Tier Optimization

#### Current Configuration
- Fast tier: `gpt-5.1-chat-latest`
- Standard tier: `gpt-5.1`
- Premium tier: `gpt-5.1` (same as standard)

#### Optimized Configuration
- **Fast tier**: Use for simple queries, phase form help (keep current)
- **Standard tier**: Use for most multi-agent queries (keep current)
- **Premium tier**: Only for complex PRD generation (reduce usage)
- **Model Selection**: Automatically choose faster models for simple queries

**Rationale**: Using faster models for simple queries reduces latency without sacrificing quality.

## Implementation Steps

1. **Update Backend Deployment** (`k8s/eks/backend.yaml`)
   - Increase CPU/memory requests and limits
   - Add Uvicorn worker configuration

2. **Update Database Connection Pool** (`backend/database.py`)
   - Increase `pool_size` to 20
   - Increase `max_overflow` to 30

3. **Update HPA Configuration** (`k8s/eks/hpa-backend.yaml`)
   - Lower CPU threshold to 60%
   - Lower memory threshold to 75%
   - Increase scale-up policy to 6 pods

4. **Update ConfigMap** (`k8s/eks/configmap.yaml`)
   - Keep `AGENT_RESPONSE_TIMEOUT` at 180 (do not reduce to avoid truncating responses)
   - Add `AGENT_MAX_CONCURRENT: "10"`

5. **Optimize Agent Coordinator** (`backend/agents/agno_enhanced_coordinator.py`)
   - Increase parallel agent execution
   - Add concurrency limiting
   - Optimize context building

## Expected Improvements

After optimizations:
- **P95 Response Time**: <30s (from 63.84s) ✅
- **Error Rate**: <5% (from 20%) ✅
- **Throughput**: >2 req/s (from 1.18 req/s) ✅
- **Agent Processing**: 2-3x faster with better parallelization
- **Database Wait Time**: Reduced by 30-40%
- **Scaling Response**: Faster scale-up under load

## Monitoring

After deployment, monitor:
1. **Response Times**: P50, P95, P99
2. **Error Rates**: By error type
3. **Resource Utilization**: CPU, Memory per pod
4. **Database Connection Pool**: Usage, wait times
5. **HPA Scaling**: Scale-up/down frequency
6. **Agent Processing Time**: Per agent type

## Rollback Plan

If optimizations cause issues:
1. Revert resource limits to previous values
2. Revert HPA thresholds to 70%/80%
3. Revert database pool size to 15/25
4. Agent timeout remains at 180s (not changed)

