# Prompt Structure Optimization

## Overview

The prompt structure has been optimized to improve AI response quality and reduce token usage by separating system content from user prompts, following best practices for LLM interactions.

## Changes Made

### 1. Timeout Configuration
- **Job Timeout**: Updated from 10 minutes to **5 minutes** (300000ms)
- **Max Polling Attempts**: Updated from 120 to **60** (5 minutes at 5s intervals)
- **Polling Interval**: Remains at 5 seconds (configurable via ConfigMap)

### 2. Prompt Structure Optimization

#### Before (All in User Prompt)
```
User Query: Generate comprehensive content...
COMPREHENSIVE CONTEXT:
[All context embedded in query string]
INSTRUCTIONS:
[Instructions embedded in query]
```

#### After (Separated System/User)
```
SYSTEM CONTEXT:
[Context, history, knowledge base - structured]

USER REQUEST:
[Clean, focused query]

INSTRUCTIONS:
[Clear instructions]
```

### 3. Context Size Reduction
- **Conversation History**: Reduced from 20 to 15 messages
- **Message Excerpts**: Reduced from 500 to 400 characters
- **Ideation Content**: Reduced from 2000 to 1500 characters
- **Knowledge Base Items**: Reduced from 200 to 300 characters (but more focused)

### 4. Query Cleanup
- **Frontend Query**: Simplified to focus on the actual request
- **Context Separation**: Form data and context passed separately, not embedded in query string
- **Better Structure**: Clear SYSTEM CONTEXT / USER REQUEST separation

## Benefits

1. **Better AI Understanding**: 
   - System content provides context without overwhelming the user request
   - AI can better distinguish between context and the actual task

2. **Reduced Token Usage**:
   - Smaller context excerpts
   - More focused queries
   - Less redundant information

3. **Improved Response Quality**:
   - AI can better synthesize information from context
   - More appropriate responses to the actual user request
   - Better coordination between agents

4. **Performance**:
   - Faster processing with smaller prompts
   - Reduced timeout to 5 minutes (more realistic)
   - Better handling of 400+ concurrent users

## Configuration

### ConfigMap Settings
```yaml
JOB_POLL_INTERVAL_MS: "5000"        # 5 seconds
JOB_MAX_POLL_ATTEMPTS: "60"         # 5 minutes total
JOB_TIMEOUT_MS: "300000"            # 5 minutes
```

### Adjusting for Load

For **400+ concurrent users**:
```yaml
JOB_POLL_INTERVAL_MS: "10000"       # 10 seconds - reduces polling by 50%
JOB_MAX_POLL_ATTEMPTS: "30"        # 5 minutes total
JOB_TIMEOUT_MS: "300000"           # 5 minutes
```

## Implementation Details

### Backend Changes

1. **`agno_enhanced_coordinator.py`**:
   - Added `_build_system_content()` method to structure context separately
   - Updated `_enhance_query_with_context()` to use SYSTEM CONTEXT / USER REQUEST structure

2. **`agno_base_agent.py`**:
   - Updated `_format_messages_to_query()` to separate system content from user prompt
   - Better context handling with size limits

3. **`configmap.yaml`**:
   - Updated timeout values to 5 minutes

### Frontend Changes

1. **`MainApp.tsx`**:
   - Simplified query to be more focused
   - Context passed separately in request body

2. **`job-config.ts`**:
   - Updated default timeout to 5 minutes
   - Updated default max attempts to 60

## Testing

After deployment, verify:
1. Jobs complete within 5 minutes
2. Responses are more appropriate and contextual
3. No timeout errors for normal requests
4. Reduced token usage in AI provider logs

## Monitoring

```bash
# Check job completion times
kubectl logs -n $EKS_NAMESPACE -l app=backend | grep "job_completed" | tail -20

# Check for timeout errors
kubectl logs -n $EKS_NAMESPACE -l app=backend | grep -i "timeout" | tail -10

# Monitor polling frequency
kubectl logs -n $EKS_NAMESPACE -l app=backend | grep "GET /api/multi-agent/jobs" | wc -l
```

## Rollback

If issues occur, revert ConfigMap:
```yaml
JOB_TIMEOUT_MS: "600000"           # Back to 10 minutes
JOB_MAX_POLL_ATTEMPTS: "120"       # Back to 10 minutes
```

Then restart frontend pods:
```bash
kubectl rollout restart deployment/frontend -n $EKS_NAMESPACE
```

