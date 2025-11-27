# Async Job Processing for Multi-Agent Requests

## Problem

Cloudflare has a hard 60-second timeout that cannot be changed. Multi-agent processing can take 2-5 minutes, causing 524 timeout errors. This solution implements an async job pattern to handle long-running requests.

## Solution Architecture

### Backend Changes

1. **New Job Service** (`backend/services/job_service.py`)
   - Uses Redis to store job status and results
   - Tracks job progress and status
   - Handles job expiry (1 hour TTL)

2. **New Async Endpoints** (`backend/main.py`)
   - `POST /api/multi-agent/submit` - Submit job, returns immediately with job ID
   - `GET /api/multi-agent/jobs/{job_id}/status` - Check job status
   - `GET /api/multi-agent/jobs/{job_id}/result` - Get completed job result

3. **Job Schemas** (`backend/models/schemas.py`)
   - `JobSubmitRequest` - Request wrapper
   - `JobSubmitResponse` - Immediate response with job ID
   - `JobStatusResponse` - Status with progress
   - `JobResultResponse` - Final result

### Frontend Changes

1. **Async Job Processor Utility** (`src/utils/asyncJobProcessor.ts`)
   - Handles job submission
   - Polls for status every 2 seconds
   - Returns result when completed
   - Handles errors and timeouts

2. **Updated Components**
   - `MainApp.tsx` - Uses async job processor
   - `PhaseFormModal.tsx` - Should be updated (see below)
   - `ProductChatInterface.tsx` - Should be updated (see below)

## Usage

### Backend

The old synchronous endpoint still works but will timeout on Cloudflare:
```python
POST /api/multi-agent/process  # Synchronous (may timeout)
```

New async endpoints:
```python
# Submit job
POST /api/multi-agent/submit
{
  "request": {
    "user_id": "...",
    "product_id": "...",
    "query": "...",
    ...
  }
}
# Returns: { "job_id": "...", "status": "pending", ... }

# Check status
GET /api/multi-agent/jobs/{job_id}/status
# Returns: { "status": "processing", "progress": 0.5, ... }

# Get result
GET /api/multi-agent/jobs/{job_id}/result
# Returns: { "status": "completed", "result": {...}, ... }
```

### Frontend

```typescript
import { processAsyncJob } from '../utils/asyncJobProcessor';

const result = await processAsyncJob(requestData, {
  apiUrl: API_URL,
  token,
  onProgress: (status) => {
    console.log('Progress:', status.progress);
  },
  pollInterval: 2000, // 2 seconds
  maxPollAttempts: 150, // 5 minutes
  timeout: 300000, // 5 minutes
});
```

## Remaining Updates Needed

### PhaseFormModal.tsx

Replace the synchronous fetch with async job processor:

```typescript
// OLD:
const response = await fetch(`${API_URL}/api/multi-agent/process`, {...});

// NEW:
const { processAsyncJob } = await import('../utils/asyncJobProcessor');
const data = await processAsyncJob({
  user_id: user.id,
  query: fullPrompt,
  coordination_mode: 'enhanced_collaborative',
  ...
}, {
  apiUrl: API_URL,
  token,
  onProgress: (status) => {
    // Update UI with progress if needed
  },
});
```

### ProductChatInterface.tsx

Same pattern - replace synchronous fetch with async job processor.

## Benefits

1. **No Cloudflare Timeouts** - Submit endpoint returns immediately (< 1 second)
2. **Scalable** - Can handle 400+ concurrent users
3. **Progress Tracking** - Users can see job progress
4. **Resilient** - Jobs stored in Redis, can survive pod restarts
5. **Backward Compatible** - Old endpoint still works for quick requests

## Configuration

### Ingress

The new endpoints don't need special timeout configuration since they return immediately. The existing ingress configuration is sufficient:

```yaml
nginx.ingress.kubernetes.io/proxy-read-timeout: "600"
nginx.ingress.kubernetes.io/proxy-send-timeout: "600"
```

### Redis

Ensure Redis has sufficient memory for job storage:
- Default: 1GB maxmemory
- Job TTL: 1 hour
- Estimated: ~100KB per job

For 400 concurrent users with 5-minute jobs:
- Peak jobs: ~400
- Memory needed: ~40MB
- Well within 1GB limit

## Monitoring

Monitor job service:
- Redis memory usage
- Job completion rates
- Average job duration
- Failed jobs

## Future Enhancements

1. **WebSocket Support** - Real-time progress updates instead of polling
2. **Job Queue** - Use Celery or similar for better job management
3. **Job History** - Store completed jobs in database for analytics
4. **Retry Logic** - Automatic retry for failed jobs
5. **Priority Queue** - Prioritize certain job types

