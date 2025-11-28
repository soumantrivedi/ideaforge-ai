# V0 Async Polling Workflow

## Overview

This document describes the new async polling workflow for V0 project submission that solves the timeout issue by:

1. **Immediate Response**: Submit project and get `project_id` (chat_id) immediately without waiting for completion
2. **Separate Status Checks**: Use `project_id` to check status separately via polling
3. **Non-Blocking**: Poll at regular intervals instead of blocking on a single long-running request

## Problem Solved

**Previous Issue**: 
- When submitting a project to V0 API, the request would wait until the project completes (10-15 minutes)
- This causes timeouts and poor user experience
- No way to check status without creating a new project

**Solution**:
- Submit project with short timeout (90s) - returns immediately with `project_id`
- Poll status separately every 2 minutes for up to 15 minutes
- Users can check status later using the `project_id`

## Test File

**Location**: `test-workflow/v0/test_v0_async_polling.py`

## Workflow Steps

### Step 1: Generate V0 Prompt (OpenAI API)
- Uses OpenAI API key to generate a V0-ready prompt
- Model: `gpt-4o-mini`
- Cleans prompt to remove instructional headers/footers

### Step 2: Submit Project to V0 API
- Endpoint: `POST https://api.v0.dev/v1/chats`
- Scope: `mckinsey`
- Timeout: 90 seconds (returns immediately after submission)
- Returns:
  - `project_id` (chat_id) - **Use this for status checks**
  - Initial status (may be "in_progress" or "completed")
  - Project URL (if already complete)

### Step 3: Poll Status Every 2 Minutes
- Endpoint: `GET https://api.v0.dev/v1/chats/{project_id}`
- Poll interval: 2 minutes
- Max duration: 15 minutes (8 polls total)
- Each poll prints:
  - Poll number
  - Elapsed time
  - Current status
  - Project URL (when available)
  - Number of files generated

## Usage

### Run the Test

```bash
cd /Users/Souman_Trivedi/IdeaProjects/ideaforge-ai
python test-workflow/v0/test_v0_async_polling.py
```

### Required Environment Variables

```bash
OPENAI_API_KEY=sk-...  # For generating V0 prompts
V0_API_KEY=v0-...      # For V0 API (scope: mckinsey)
```

### Expected Output

```
================================================================================
V0 ASYNC POLLING WORKFLOW TEST
================================================================================

STEP 1: Generating V0 prompt using OpenAI...
✅ Generated prompt (XXX chars)

STEP 2: Submitting project to V0 API...
📤 Submitting project to V0 API...
   ✅ Project submitted successfully!
   Project ID: chat_abc123...
   Initial status: in_progress

STEP 3: Polling project status...
🔄 Starting status polling...
   Poll #1 (Elapsed: 0.0 minutes)
   ✅ Status check successful
   Status: in_progress
   Is complete: False
   ⏳ Waiting 2 minutes until next poll...

   Poll #2 (Elapsed: 2.0 minutes)
   ✅ Status check successful
   Status: in_progress
   Is complete: False
   ⏳ Waiting 2 minutes until next poll...

   ...

   Poll #N (Elapsed: X.X minutes)
   ✅ Status check successful
   Status: completed
   Is complete: True
   Project URL: https://v0.dev/...
   Files generated: 5

🎉 Project completed!
```

## API Response Structure

### Submit Project Response

```json
{
  "success": true,
  "project_id": "chat_abc123...",
  "chat_id": "chat_abc123...",
  "status": "in_progress" | "completed",
  "project_url": "https://v0.dev/...",
  "web_url": "https://...",
  "demo_url": "https://...",
  "files": [...],
  "is_complete": false
}
```

### Status Check Response

```json
{
  "success": true,
  "project_id": "chat_abc123...",
  "status": "in_progress" | "completed" | "not_found",
  "is_complete": false,
  "project_url": "https://v0.dev/...",
  "web_url": "https://...",
  "demo_url": "https://...",
  "files": [...],
  "num_files": 0
}
```

## Key Functions

### `submit_v0_project(api_key, prompt)`
- Submits project to V0 API
- Returns immediately with `project_id`
- Timeout: 90 seconds
- Returns project details including initial status

### `check_project_status(api_key, project_id)`
- Checks current status of a project
- Uses `project_id` (chat_id) from submission
- Returns current status and project details

### `poll_project_status(api_key, project_id, poll_interval_minutes=2, max_duration_minutes=15)`
- Polls project status at regular intervals
- Default: every 2 minutes for 15 minutes
- Prints detailed status at each poll
- Returns completion status and all poll results

## Integration Points

### For Backend API Integration

1. **Submit Endpoint** (`POST /api/design/create-project`):
   - Call `submit_v0_project()` with short timeout
   - Store `project_id` in database
   - Return `project_id` to user immediately
   - Start background polling task

2. **Status Endpoint** (`GET /api/design/projects/{project_id}/status`):
   - Call `check_project_status()` with stored `project_id`
   - Return current status to user
   - Update database if status changed to "completed"

3. **Background Polling**:
   - Use `poll_project_status()` in background task
   - Update database when status changes
   - Notify user when project completes

## Benefits

1. ✅ **No Timeouts**: Returns immediately after submission
2. ✅ **Better UX**: Users get project_id right away
3. ✅ **Status Tracking**: Can check status anytime using project_id
4. ✅ **Scalable**: Multiple projects can be tracked simultaneously
5. ✅ **Resumable**: Can check status later without creating new project

## Error Handling

- **401 Unauthorized**: Invalid API key
- **402 Payment Required**: Credits exhausted
- **404 Not Found**: Project not found (may still be creating)
- **Timeout**: Request timed out (shouldn't happen with 90s timeout)

## Next Steps

1. Integrate into main API endpoints
2. Add database storage for project_id tracking
3. Implement background polling service
4. Add user notifications when project completes
5. Add retry logic for failed status checks

