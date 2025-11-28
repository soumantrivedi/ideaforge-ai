# V0 Async Polling Workflow Tests

This directory contains test workflows for V0 API integration with async polling pattern.

## Structure

```
test-workflow/v0/
├── README.md                          # This file
├── test_v0_async_polling.py          # Main test workflow
└── docs/
    └── V0_ASYNC_POLLING_WORKFLOW.md  # Detailed documentation
```

## Purpose

These tests validate the async polling workflow for V0 project submission that solves timeout issues by:

1. **Immediate Response**: Submit project and get `project_id` immediately
2. **Separate Status Checks**: Use `project_id` to check status separately
3. **Non-Blocking**: Poll at regular intervals instead of blocking

## Quick Start

### Prerequisites

- Python 3.8+
- Required packages: `httpx`, `openai`, `python-dotenv`
- Environment variables: `OPENAI_API_KEY`, `V0_API_KEY`

### Run the Test

```bash
cd /Users/Souman_Trivedi/IdeaProjects/ideaforge-ai
python test-workflow/v0/test_v0_async_polling.py
```

### What It Does

1. **Generates V0 prompt** using OpenAI API
2. **Submits project** to V0 API (scope: mckinsey) - returns immediately with `project_id`
3. **Polls status** every 2 minutes for 15 minutes
4. **Prints detailed status** at each poll interval

## Files

- **`test_v0_async_polling.py`**: Main test script that implements the async polling workflow
- **`docs/V0_ASYNC_POLLING_WORKFLOW.md`**: Comprehensive documentation including API structures, integration points, and error handling

## Key Features

- ✅ No timeout issues - returns immediately after submission
- ✅ Status tracking using project_id
- ✅ Polls every 2 minutes for up to 15 minutes
- ✅ Detailed logging at each poll
- ✅ Complete end-to-end validation

## Notes

- This is a **test workflow** separate from the core ideaforge-ai codebase
- It uses the same `.env` file from the project root for API keys
- The workflow can be integrated into the main backend API endpoints

