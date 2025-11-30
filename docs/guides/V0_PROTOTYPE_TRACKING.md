# V0 Prototype Tracking Implementation

## Overview
This document describes the implementation of V0 prototype tracking to prevent duplicate projects and allow users to view all prototypes for a product.

## Problem Statement
Previously, each time a user generated a V0 prototype, a new project was created even if one already existed for that product. This led to:
- Orphaned projects (400 users could create 4000 stale projects)
- No way to reuse existing prototypes
- No visibility into all prototypes for a product

## Solution

### 1. Database Schema Updates
**Migration**: `20251128000000_add_v0_project_tracking.sql`

Added new columns to `design_mockups` table:
- `v0_chat_id` (text): V0 API chat_id for tracking and status polling
- `v0_project_id` (text): V0 API project_id if different from chat_id
- `project_status` (text): Status enum ('pending', 'in_progress', 'completed', 'failed', 'timeout')
- `project_url` (text): Main prototype URL (demo_url, web_url, or chat_url)

**Indexes**:
- `idx_design_mockups_product_status`: Fast lookup by product and status
- `idx_design_mockups_v0_chat_id`: Fast lookup by V0 chat_id
- `idx_design_mockups_user_product`: Fast lookup by user and product

### 2. API Changes

#### `POST /api/design/create-project`
**New Parameter**: `create_new` (bool, default: False)
- If `create_new=False`: Checks for existing prototype and returns it if found
- If `create_new=True`: Creates a new prototype even if one exists

**Response includes**:
- `v0_chat_id`: V0 chat ID for status polling
- `v0_project_id`: V0 project ID (if different)
- `project_status`: Current status
- `is_existing`: Boolean indicating if this is an existing prototype

**Workflow**:
1. Check for existing prototype (unless `create_new=True`)
2. If found, return existing prototype with current status
3. If not found or `create_new=True`, create new prototype
4. Store V0 chat_id and project_id in database
5. Return prototype with tracking information

#### `GET /api/design/mockups/{product_id}`
**Enhanced Response**: Now includes V0 tracking fields:
- `v0_chat_id`: V0 chat ID
- `v0_project_id`: V0 project ID
- `project_status`: Current status
- All prototypes for the product are returned (ordered by created_at DESC)

#### `GET /api/design/mockups/{product_id}/status`
**New Endpoint**: Check project status without creating new project
- Returns current status of most recent prototype
- For V0 projects, polls V0 API to get latest status
- Updates database if status changed to "completed"
- Allows users to check status later without creating duplicates

### 3. Agent Updates

#### `AgnoV0Agent.create_v0_project_with_api()`
- Returns `chat_id` in response (already implemented)
- Uses `scope=mckinsey` parameter in all V0 API requests
- Supports async status polling (10-15 minute timeout)

### 4. Status Polling

**Timeout**: 10-15 minutes (600-900 seconds)
- Polls V0 API every 3 seconds
- Maximum 200 polls (10 minutes) or 300 polls (15 minutes)
- Updates database when status changes to "completed"

**Status Flow**:
1. `pending`: Project created, not yet started
2. `in_progress`: Project is being generated
3. `completed`: Prototype is ready (has demo_url, web_url, or files)
4. `failed`: Error occurred during generation
5. `timeout`: Polling timeout reached

## Usage Examples

### Create/Get Prototype (Reuse Existing)
```json
POST /api/design/create-project
{
  "product_id": "123",
  "provider": "v0",
  "prompt": "...",
  "create_new": false  // Default: reuse existing
}
```

### Create New Prototype
```json
POST /api/design/create-project
{
  "product_id": "123",
  "provider": "v0",
  "prompt": "...",
  "create_new": true  // Force new prototype
}
```

### Get All Prototypes for Product
```json
GET /api/design/mockups/{product_id}
```

### Check Status Without Creating New
```json
GET /api/design/mockups/{product_id}/status?provider=v0
```

## Benefits

1. **Prevents Duplicate Projects**: Users get the same prototype when navigating back
2. **Visibility**: All prototypes for a product are visible and linked
3. **Status Tracking**: Real-time status updates via polling
4. **User Control**: Option to create new prototype when needed
5. **Resource Efficiency**: Reduces orphaned projects and API calls

## Migration Notes

- Migration is backward compatible (checks for column existence)
- Existing prototypes will have NULL values for new fields
- Status defaults to "pending" for existing records
- API gracefully handles missing columns

## Testing

See `backend/test_v0_workflow_comprehensive.py` for comprehensive testing:
- Duplicate prevention
- Status polling
- Status checking
- Handling of stale projects

