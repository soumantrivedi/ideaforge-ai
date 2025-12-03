# Coordinator Agent Intelligent Selection Fix

## Problem Statement

The coordinator agent was incorrectly invoking the ideation agent for all queries, regardless of the phase context. This caused issues where:

1. **Market Research phase queries** were getting ideation responses instead of research-focused content
2. **Requirements phase queries** were getting ideation responses instead of PRD/requirements content
3. **All queries** were invoking ideation, research, and analysis agents in parallel, regardless of relevance
4. **Response summarization** was using hardcoded headings for ideation/research/analysis even when those agents weren't invoked

## Root Cause

1. `determine_primary_agent()` defaulted to "ideation" when confidence was low, without considering phase context
2. `determine_supporting_agents()` always included ideation/research/analysis based on keywords, without checking phase context
3. Response summarization used hardcoded headings instead of dynamically generating them based on invoked agents

## Solution

### 1. Phase-Aware Primary Agent Selection

**File**: `backend/agents/agno_enhanced_coordinator.py`

**Changes**:
- `determine_primary_agent()` now accepts `context` parameter
- Added `phase_agent_mapping` dictionary to map phases to appropriate agents:
  ```python
  phase_agent_mapping = {
      "ideation": "ideation",
      "market research": "research",
      "requirements": "prd_authoring",
      "strategy": "strategy",
      "analysis": "analysis",
      "validation": "validation",
  }
  ```
- Primary agent selection now:
  1. Checks `phase_name` from context first (highest priority)
  2. Scores agents based on query keywords
  3. Only defaults to ideation if no phase context AND low confidence

**Example**:
- Query: "What are the market trends?"
- Phase: "Market Research"
- Result: `primary_agent = "research"` (not "ideation")

### 2. Phase-Aware Supporting Agent Selection

**File**: `backend/agents/agno_enhanced_coordinator.py`

**Changes**:
- `determine_supporting_agents()` now accepts `context` parameter
- Only includes agents relevant to the current phase:
  - **Market Research phase**: Includes research agent, excludes ideation
  - **Requirements phase**: Includes PRD agent, excludes ideation
  - **Ideation phase**: Can include ideation agent
- Explicit exclusion logic:
  ```python
  # Explicitly exclude ideation for non-ideation phases
  if phase_name and "ideation" not in phase_name and "research" in phase_name:
      should_include_ideation = False
  if phase_name and "ideation" not in phase_name and "requirement" in phase_name:
      should_include_ideation = False
  ```

**Example**:
- Query: "What are the market trends?"
- Phase: "Market Research"
- Primary: "research"
- Supporting: `["rag"]` (ideation NOT included)

### 3. Dynamic Response Summarization

**File**: `backend/agents/agno_enhanced_coordinator.py`

**Changes**:
- Response headings are now dynamically generated based on actually invoked agents
- Only includes headings for agents that were actually called:
  ```python
  agent_headings = []
  if any(i.get("to_agent") == "ideation" for i in interactions):
      agent_headings.append("- ## Ideation Insights")
  if any(i.get("to_agent") == "research" for i in interactions):
      agent_headings.append("- ## Research Findings")
  # ... etc
  ```

**Example**:
- If only research agent was invoked: Headings = `["## Research Findings", "## Summary & Next Steps"]`
- If ideation was NOT invoked: No "## Ideation Insights" heading

### 4. Context Propagation

**Changes**:
- All `determine_primary_agent()` calls now pass `context` parameter
- All `determine_supporting_agents()` calls now pass `context` parameter
- `stream_route_query()` builds context early and passes it to agent selection methods
- `route_query()` also builds context and passes it to agent selection methods

## Test Suite

**File**: `backend/tests/test_coordinator_agent_selection.py`

**Test Cases**:
1. `test_determine_primary_agent_market_research_phase` - Verifies research agent selected for Market Research phase
2. `test_determine_primary_agent_requirements_phase` - Verifies PRD agent selected for Requirements phase
3. `test_determine_primary_agent_ideation_phase` - Verifies ideation agent selected for Ideation phase
4. `test_determine_primary_agent_no_ideation_for_market_research` - Verifies ideation NOT selected for Market Research
5. `test_determine_primary_agent_no_ideation_for_requirements` - Verifies ideation NOT selected for Requirements
6. `test_determine_supporting_agents_market_research_phase` - Verifies ideation NOT in supporting agents for Market Research
7. `test_determine_supporting_agents_requirements_phase` - Verifies ideation NOT in supporting agents for Requirements
8. `test_stream_route_query_market_research_phase` - End-to-end test for Market Research phase
9. `test_stream_route_query_requirements_phase` - End-to-end test for Requirements phase
10. `test_stream_route_query_negative_response` - Tests negative response handling

## Makefile Targets

**File**: `Makefile`

**New Targets**:
- `make kind-test-coordinator` - Run coordinator agent selection tests in Kind cluster
- `make eks-test-coordinator` - Run coordinator agent selection tests in EKS production cluster

**Usage**:
```bash
# Test in Kind cluster
make kind-test-coordinator K8S_NAMESPACE=ideaforge-ai

# Test in EKS production
make eks-test-coordinator EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50 KUBECONFIG=/path/to/kubeconfig
```

## Verification

### Expected Behavior

1. **Market Research Phase**:
   - Primary agent: `research`
   - Supporting agents: `["rag"]` (ideation NOT included)
   - Response: Market research content, no ideation content

2. **Requirements Phase**:
   - Primary agent: `prd_authoring`
   - Supporting agents: `["rag"]` (ideation NOT included)
   - Response: Requirements/PRD content, no ideation content

3. **Ideation Phase**:
   - Primary agent: `ideation`
   - Supporting agents: `["rag"]` (ideation is primary, so not in supporting)
   - Response: Ideation content

4. **No Phase Context**:
   - Primary agent: Determined by query keywords
   - Supporting agents: Determined by query keywords
   - Response: Relevant content based on query

### Testing in Production

1. **Deploy changes to EKS**:
   ```bash
   make eks-rollout-images \
     EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50 \
     BACKEND_IMAGE_TAG=latest \
     FRONTEND_IMAGE_TAG=latest \
     KUBECONFIG=/path/to/kubeconfig \
     BASE_URL=https://ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud
   ```

2. **Run automated tests**:
   ```bash
   make eks-test-coordinator \
     EKS_NAMESPACE=20890-ideaforge-ai-dev-58a50 \
     KUBECONFIG=/path/to/kubeconfig
   ```

3. **Manual verification**:
   - Open chatbot in Market Research phase
   - Submit query: "What are the market trends?"
   - Verify: Response contains market research content, NOT ideation content
   - Check backend logs: Should see `primary_agent=research`, not `primary_agent=ideation`

## Files Modified

1. `backend/agents/agno_enhanced_coordinator.py`
   - `determine_primary_agent()` - Added phase-aware logic
   - `determine_supporting_agents()` - Added phase-aware logic
   - `stream_route_query()` - Passes context to agent selection
   - `route_query()` - Passes context to agent selection
   - Response summarization - Dynamic headings

2. `backend/tests/test_coordinator_agent_selection.py` (NEW)
   - Comprehensive test suite for agent selection

3. `Makefile`
   - `kind-test-coordinator` target
   - `eks-test-coordinator` target

## Impact

✅ **Fixed**: Coordinator now intelligently selects agents based on phase context
✅ **Fixed**: Ideation agent NOT invoked for Market Research or Requirements phases
✅ **Fixed**: Only relevant agents are invoked based on query content and phase
✅ **Fixed**: Response summarization only includes headings for invoked agents
✅ **Added**: Comprehensive test suite for automated verification
✅ **Added**: Makefile targets for easy testing in Kind and EKS clusters

## Next Steps

1. Deploy changes to EKS production
2. Run automated tests to verify behavior
3. Monitor chatbot responses to ensure correct agent selection
4. Collect user feedback on response quality and relevance

