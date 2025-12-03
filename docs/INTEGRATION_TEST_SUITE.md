# Integration Test Suite

## Overview

Comprehensive automated test suite for coordinator agent selection, V0 project retention, prompt format, and chatbot content handling. Optimized for latency with 100+ concurrent users in EKS production.

## Test Coverage

### 1. Coordinator Agent Selection
- Tests intelligent agent selection across all product phases:
  - Market Research → Research Agent
  - Requirements → PRD Authoring Agent
  - Ideation → Ideation Agent
  - Strategy → Strategy Agent
  - Analysis → Analysis Agent
  - Validation → Validation Agent
- Verifies ideation agent is NOT invoked for non-ideation phases
- Validates phase-aware agent routing

### 2. V0 Project ID Retention
- Tests that V0 project IDs are correctly stored in database
- Verifies project ID reuse across multiple calls for same product_id
- Ensures no duplicate projects are created unnecessarily
- Validates project association with product_id and user_id

### 3. V0 Prompt Format
- Verifies prompt generation returns non-conversational text
- Checks for absence of instructional headers/footers
- Validates prompt is substantial (>100 characters)
- Ensures prompt is ready for direct use in V0 API

### 4. Latency Monitoring
- API calls: 2 second threshold
- Agent calls: 10 second threshold
- Test timeout: 60 seconds (reduced from 180s)
- Tracks average and maximum latency
- Warns on high latency scenarios

## Test Files

### `backend/tests/test_v0_coordinator_integration.py`
Main integration test suite that:
- Authenticates with demo account
- Creates test product
- Runs all test scenarios
- Monitors latency
- Generates comprehensive test report

### `backend/tests/test_coordinator_agent_selection.py`
Unit tests for coordinator agent selection logic:
- Phase-aware agent selection
- Supporting agent determination
- Response summarization
- Negative query handling

## Makefile Targets

### Kind Cluster
```bash
make kind-test-integration K8S_NAMESPACE=ideaforge-ai
```

### EKS Cluster
```bash
make eks-test-integration EKS_NAMESPACE=ns KUBECONFIG=path
```

## Performance Considerations

### Latency Thresholds
- **API Calls**: 2000ms (2 seconds)
- **Agent Calls**: 10000ms (10 seconds)
- **Test Timeout**: 60000ms (60 seconds)

### Optimizations
1. **Reduced Timeouts**: Test timeout reduced from 180s to 60s
2. **Async Operations**: All tests use async/await for parallel execution
3. **Connection Pooling**: Reuses HTTP client connections
4. **Early Failures**: Fails fast on authentication/product creation errors
5. **Streaming**: Uses streaming for agent responses to reduce memory

### For 100+ Concurrent Users
- Tests are designed to run quickly (< 5 minutes total)
- Can be run in parallel across multiple pods
- Minimal resource consumption
- No blocking operations

## Running Tests

### Prerequisites
1. Backend pod must be running
2. Database must be accessible
3. Demo account must exist (admin@ideaforge.ai / password123)
4. V0 API key configured (for V0 tests)

### Local Development (Kind)
```bash
# Deploy to kind first
make kind-deploy

# Run integration tests
make kind-test-integration K8S_NAMESPACE=ideaforge-ai
```

### Production (EKS)
```bash
# Set kubeconfig
export KUBECONFIG=/path/to/kubeconfig

# Run integration tests
make eks-test-integration EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50
```

## Test Results

Tests output:
- ✅/❌ status for each test
- Latency metrics (average, maximum)
- Agent invocation details
- Error messages with context
- Warnings for high latency

## Continuous Integration

These tests should be run:
1. Before every deployment
2. After code changes to coordinator/V0/chatbot logic
3. As part of CI/CD pipeline
4. During performance testing

## Troubleshooting

### Authentication Failed
- Verify demo account exists: `admin@ideaforge.ai / password123`
- Check database connectivity
- Verify backend pod is running

### High Latency Warnings
- Check database connection pool
- Verify Redis connectivity
- Check agent model tier (should use "fast" for prompt generation)
- Review HPA scaling configuration

### V0 Project Retention Failed
- Verify V0 API key is configured
- Check database for existing v0_project_id
- Verify design_mockups table exists
- Check V0 API connectivity

### Prompt Format Failed
- Check agent system prompts
- Verify _clean_v0_prompt method
- Review prompt generation logic
- Check for conversational elements in responses

## Future Enhancements

1. **Chatbot Content Tests**: Add tests for chatbot content handling
2. **Concurrent User Simulation**: Add tests simulating 100+ concurrent users
3. **Performance Benchmarks**: Track latency trends over time
4. **Load Testing**: Integrate with performance test suite
5. **Coverage Reports**: Generate code coverage reports

