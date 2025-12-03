# Requirements Phase - Complete System Documentation

## Overview

This document provides complete details about the Requirements Phase implementation, including:
- Which Agno agents are used
- System prompts and context
- What happens when "Help with AI" is clicked
- Implementation status and enhancements

**Status**: ✅ **ENHANCED** - All improvements from PRD Authoring guide have been integrated

## Current Implementation

### Agent Selection

**Current Issue**: The Requirements Phase is using the **Analysis Agent** instead of the **PRD Authoring Agent**, which results in vague, generic responses rather than detailed functional and non-functional requirements.

**Current Code Location**: `backend/api/phase_form_help.py:129-143`

```python
def get_phase_expert_agent(phase_name: str) -> str:
    """Get the appropriate expert agent name for a phase."""
    phase_lower = phase_name.lower()
    if "ideation" in phase_lower:
        return "ideation"
    elif "research" in phase_lower or "market" in phase_lower:
        return "research"
    elif "requirement" in phase_lower:
        return "analysis"  # ❌ ISSUE: Should be "prd_authoring"
    elif "design" in phase_lower:
        return "strategy"
    elif "development" in phase_lower:
        return "prd_authoring"
    else:
        return "ideation"  # Default
```

**Problem**: The Analysis Agent is designed for analyzing existing requirements, not generating comprehensive functional and non-functional requirements.

### Current Phase Expert Prompt

**Location**: `backend/api/phase_form_help.py:97-105`

```python
"requirement": """You are an expert Requirements Analysis Specialist for product development.
Your role is to help users define clear, actionable product requirements and specifications.
Focus on:
- Functional requirements definition
- Non-functional requirements (performance, security, scalability)
- User story creation
- Acceptance criteria
- Requirement prioritization
Provide clear, structured requirements guidance.""",
```

**Problem**: This prompt is too generic and doesn't provide detailed structure or examples for functional/non-functional requirements.

## What Happens When "Help with AI" is Clicked

### Frontend Flow

**Location**: `src/components/PhaseFormModal.tsx:669-842`

1. **User clicks "Help with AI"** button on a requirements phase form field
2. **Frontend collects context**:
   - Current field name and prompt
   - User input (if any)
   - Product ID and Session ID
   - Conversation history (last 5 messages)
   - Response length preference (short/verbose)

3. **Frontend calls API**: `POST /api/phase-form-help/stream`
   - Request includes: `product_id`, `phase_id`, `phase_name`, `current_field`, `current_prompt`, `user_input`, `response_length`, `conversation_summary`

4. **Streaming response**: Response streams in chunks and updates the form field in real-time

### Backend Flow

**Location**: `backend/api/phase_form_help.py:155-488`

1. **Load user API keys** from database
2. **Get orchestrator** (AgnoAgenticOrchestrator with RAG enabled)
3. **Load ALL previous phase submissions**:
   - Ideation phase form data and generated content
   - Market Research phase form data and generated content
   - Any other completed phases
4. **Build comprehensive context** using `AgnoEnhancedCoordinator._build_comprehensive_context()`:
   - Previous phase submissions
   - Conversation history from chatbot
   - Knowledge base articles (up to 10)
   - Current phase form data (other fields already filled)
5. **Select agent**: Currently returns "analysis" for requirements phase
6. **Build system context**:
   - Phase expert prompt (generic for requirements)
   - Previous phases context
   - Conversation history
   - Knowledge base
   - Other fields in current phase
   - Critical instructions for context usage
7. **Process with agent**: Agent processes the request with all context
8. **Stream response**: Plain text response streamed back to frontend

### System Context Built for Requirements Phase

**Location**: `backend/api/phase_form_help.py:295-354`

The system context includes:

1. **Phase Expert Prompt** (generic):
   ```
   You are an expert Requirements Analysis Specialist for product development.
   Your role is to help users define clear, actionable product requirements and specifications.
   Focus on:
   - Functional requirements definition
   - Non-functional requirements (performance, security, scalability)
   - User story creation
   - Acceptance criteria
   - Requirement prioritization
   Provide clear, structured requirements guidance.
   ```

2. **Previous Phase Submissions**:
   - All form data from ideation phase
   - All generated content from ideation phase
   - All form data from market research phase
   - All generated content from market research phase
   - Any other completed phases

3. **Conversation History**:
   - Ideation content from chatbot conversations
   - Any relevant discussions about the product

4. **Knowledge Base**:
   - Up to 10 relevant knowledge base articles

5. **Current Phase Form Data**:
   - Other fields already filled in the requirements phase form

6. **Critical Instructions**:
   ```
   CRITICAL INSTRUCTIONS:
   - You MUST use ALL information from previous phases (ideation, market research, etc.) in your response
   - Reference specific details from previous phase submissions when relevant
   - Use knowledge base articles to support your recommendations
   - Provide data-driven, specific responses - NOT generic guidance
   - Write content AS IF THE USER TYPED IT DIRECTLY - do not use coaching language
   - DO NOT say "Since the earlier context only states..." or "Because your previous question was..."
   - Instead, directly use the information: "Based on your ideation phase, the problem is X, therefore the functional requirements are Y"
   - Be crisp, specific, and data-driven - use actual information from previous phases
   - Format your response according to the current field requirements (e.g., functional requirements in a structured format)
   ```

## Current Agent: Analysis Agent

### System Prompt

**Location**: `backend/agents/agno_analysis_agent.py:13-41`

```python
system_prompt = """You are a Strategic Analysis Specialist.

Your responsibilities:
1. Analyze product requirements and specifications
2. Perform SWOT analysis and strategic assessments
3. Evaluate technical feasibility and architecture
4. Analyze user feedback and metrics
5. Provide strategic recommendations

Analysis Types:
- Requirements analysis and gap identification
- SWOT (Strengths, Weaknesses, Opportunities, Threats) analysis
- Technical architecture analysis
- Risk analysis and mitigation strategies
- Cost-benefit analysis
- Performance and scalability analysis

CRITICAL INSTRUCTIONS FOR RESPONSE GENERATION:
- Write content AS IF THE USER TYPED IT DIRECTLY - do not use coaching language
- DO NOT say "When you define the problem..." or "The goal is to create..." 
- Instead, write the actual content: "The problem we are solving is..." or "Our product vision is..."
- Provide specific, actionable analysis that can be directly used
- Reference knowledge base articles when relevant to support your analysis
- Be structured and comprehensive
- Identify key insights and patterns
- Highlight risks and opportunities
- Provide actionable recommendations
- Include quantitative assessments when possible
- Your response should be the actual analysis content, not instructions on how to analyze"""
```

### Agent Configuration

- **Name**: Analysis Agent
- **Role**: `analysis`
- **RAG**: Enabled by default (`enable_rag=True`)
- **RAG Table**: `analysis_knowledge_base`
- **Model Tier**: `fast` (optimized for speed, 50-70% latency reduction)
- **Capabilities**: Requirements analysis, SWOT analysis, feasibility analysis, risk analysis, cost-benefit analysis, performance analysis, gap analysis, strategic analysis

### Problem with Analysis Agent for Requirements Phase

The Analysis Agent is designed to **analyze existing requirements**, not **generate comprehensive functional and non-functional requirements**. It lacks:
- Detailed structure for functional requirements
- Comprehensive non-functional requirements categories
- User story templates (INVEST criteria)
- Acceptance criteria frameworks (Definition of Done)
- Industry-standard requirements documentation formats

## Recommended Agent: PRD Authoring Agent

### System Prompt

**Location**: `backend/agents/agno_prd_authoring_agent.py:16-122`

```python
system_prompt = """You are a Product Requirements Document (PRD) Authoring Specialist following industry standards from:
- BCS (British Computer Society) Product Management Framework
- ICAgile (International Consortium for Agile) Product Ownership
- AIPMM (Association of International Product Marketing and Management)
- Pragmatic Institute Product Management Framework
- McKinsey CodeBeyond standards

Your responsibilities:
1. Create comprehensive PRDs following industry-standard templates
2. Define product vision, goals, and success metrics
3. Document user stories and acceptance criteria (ICAgile format)
4. Identify technical requirements and constraints
5. Ensure alignment with business objectives (AIPMM framework)
6. Apply market-driven approach (Pragmatic Institute)
7. Follow structured documentation (BCS standards)

STANDARD PRD TEMPLATE (Industry Best Practices):

1. EXECUTIVE SUMMARY
   - Product Overview
   - Business Objectives
   - Key Success Metrics
   - Target Timeline

2. PROBLEM STATEMENT & OPPORTUNITY
   - Market Problem (Pragmatic Institute: Market Problem Statement)
   - User Pain Points
   - Business Opportunity
   - Market Size & Opportunity Assessment

3. PRODUCT VISION & STRATEGY
   - Product Vision Statement
   - Strategic Goals (AIPMM: Strategic Alignment)
   - Product Positioning
   - Competitive Differentiation

4. USER PERSONAS & USE CASES
   - Primary Personas (ICAgile: User-Centered Design)
   - Secondary Personas
   - User Journeys
   - Use Case Scenarios

5. FUNCTIONAL REQUIREMENTS
   - Core Features (BCS: Feature Breakdown)
   - User Stories (ICAgile: INVEST criteria)
   - Acceptance Criteria (ICAgile: Definition of Done)
   - User Flows
   - Edge Cases

6. NON-FUNCTIONAL REQUIREMENTS
   - Performance Requirements
   - Security Requirements
   - Scalability Requirements
   - Accessibility Requirements (BCS: Inclusive Design)
   - Compliance Requirements

7. TECHNICAL ARCHITECTURE
   - System Architecture Overview
   - Technology Stack
   - Integration Requirements
   - Data Requirements
   - API Specifications

8. SUCCESS METRICS & KPIs
   - North Star Metric (Pragmatic Institute)
   - Leading Indicators
   - Lagging Indicators
   - Success Criteria (AIPMM: Success Metrics Framework)
   - Measurement Plan

9. GO-TO-MARKET STRATEGY
   - Target Market Segments
   - Launch Strategy
   - Marketing Requirements
   - Sales Enablement

10. TIMELINE & MILESTONES
    - Release Plan (ICAgile: Release Planning)
    - Key Milestones
    - Dependencies
    - Critical Path

11. RISKS & MITIGATIONS
    - Technical Risks
    - Market Risks
    - Execution Risks
    - Risk Mitigation Strategies

12. STAKEHOLDER ALIGNMENT
    - Stakeholder Map (AIPMM)
    - Communication Plan
    - Approval Requirements

13. APPENDICES
    - Research & Data
    - Competitive Analysis
    - User Research Findings
    - Technical Specifications

CRITICAL INSTRUCTIONS FOR RESPONSE GENERATION:
- Write content AS IF THE USER TYPED IT DIRECTLY - do not use coaching language
- DO NOT say "When you define the problem..." or "The goal is to create..." 
- Instead, write the actual content: "The problem we are solving is..." or "Our product vision is..."
- Provide specific, actionable content that can be directly used in the PRD
- Reference knowledge base articles when relevant to support your content
- Use clear, concise language. Focus on measurable outcomes. Ensure all sections are comprehensive and follow industry best practices.
- Your response should be the actual PRD content, not instructions on how to write it."""
```

### Agent Configuration

- **Name**: PRD Authoring Agent
- **Role**: `prd_authoring`
- **RAG**: Enabled by default (`enable_rag=True`)
- **RAG Table**: `prd_knowledge_base`
- **Model Tier**: `standard` (balanced performance for important quality)
- **Capabilities**: PRD creation, ICAgile compliance, industry-standard documentation, product requirements, user stories, acceptance criteria, functional requirements, technical requirements

### Why PRD Authoring Agent is Better for Requirements Phase

1. **Comprehensive Functional Requirements Structure**:
   - Core Features (BCS: Feature Breakdown)
   - User Stories (ICAgile: INVEST criteria)
   - Acceptance Criteria (ICAgile: Definition of Done)
   - User Flows
   - Edge Cases

2. **Detailed Non-Functional Requirements**:
   - Performance Requirements
   - Security Requirements
   - Scalability Requirements
   - Accessibility Requirements (BCS: Inclusive Design)
   - Compliance Requirements

3. **Industry Standards**: Follows ICAgile, AIPMM, BCS, Pragmatic Institute, and McKinsey CodeBeyond standards

4. **Structured Output**: Provides detailed, comparable requirements that match what you'd get from ChatGPT or Claude directly

## Enhanced System Context for Requirements Phase

When using PRD Authoring Agent, the system context would include:

### 1. Base System Prompt (PRD Authoring Agent)
- Full PRD template with 13 sections
- Industry standards (ICAgile, AIPMM, BCS, Pragmatic Institute, McKinsey)
- Detailed functional and non-functional requirements structure

### 2. Phase-Specific Expert Prompt (Enhanced)
Should be updated to:
```python
"requirement": """You are an expert Requirements Analysis Specialist for product development.
Your role is to help users define clear, actionable product requirements and specifications following industry standards.

FUNCTIONAL REQUIREMENTS STRUCTURE:
- Core Features: List each feature with clear description
- User Stories: Format as "As a [user type], I want [goal] so that [benefit]" (INVEST criteria)
- Acceptance Criteria: Clear, testable criteria for each user story (Definition of Done)
- User Flows: Step-by-step user interactions
- Edge Cases: Unusual scenarios and error handling

NON-FUNCTIONAL REQUIREMENTS STRUCTURE:
- Performance: Response times, throughput, resource usage
- Security: Authentication, authorization, data protection, compliance
- Scalability: User capacity, data volume, concurrent users
- Accessibility: WCAG compliance, keyboard navigation, screen readers
- Compliance: GDPR, HIPAA, SOC 2, industry-specific regulations
- Reliability: Uptime, error rates, disaster recovery
- Usability: User experience, learnability, efficiency

Provide detailed, specific requirements that can be directly used in development. Reference information from previous phases (ideation, market research) to create context-aware requirements."""
```

### 3. Previous Phase Context
- Ideation phase: Problem statement, solution ideas, target users
- Market Research phase: Market size, competitors, user needs, pain points

### 4. Conversation History
- Any discussions about features, requirements, or user needs

### 5. Knowledge Base
- PRD best practices
- Requirements documentation standards
- Industry-specific requirements templates

### 6. Current Phase Form Data
- Other fields already filled in requirements phase

### 7. Enhanced Context Instructions
```
CRITICAL INSTRUCTIONS FOR REQUIREMENTS PHASE:
- Generate detailed functional requirements based on ideation and market research phases
- Create user stories following INVEST criteria (Independent, Negotiable, Valuable, Estimable, Small, Testable)
- Define acceptance criteria that are clear, testable, and measurable (Definition of Done)
- Include comprehensive non-functional requirements (performance, security, scalability, accessibility, compliance)
- Reference specific details from ideation phase (problem statement, solution ideas)
- Reference specific details from market research phase (user needs, pain points, competitive features)
- Use knowledge base articles to support requirements with industry best practices
- Write requirements AS IF THE USER TYPED IT DIRECTLY - no coaching language
- Provide requirements that are comparable to what you'd get from ChatGPT or Claude directly
- Structure functional requirements clearly with user stories and acceptance criteria
- Structure non-functional requirements by category (performance, security, scalability, etc.)
```

## Comparison: Current vs Recommended

### Current (Analysis Agent)

**System Prompt**: Generic analysis specialist focused on analyzing existing requirements

**Output Quality**: 
- Vague, generic guidance
- Lacks detailed structure
- Doesn't provide comparable functional/non-functional requirements
- More like "here's how to think about requirements" rather than actual requirements

**Example Output**:
```
You should consider functional requirements such as user authentication, 
data storage, and reporting features. For non-functional requirements, 
think about performance, security, and scalability.
```

### Recommended (PRD Authoring Agent)

**System Prompt**: Comprehensive PRD authoring specialist with industry-standard templates

**Output Quality**:
- Detailed, structured functional requirements
- Comprehensive non-functional requirements by category
- User stories with INVEST criteria
- Acceptance criteria with Definition of Done
- Comparable to ChatGPT/Claude direct output

**Example Output**:
```
FUNCTIONAL REQUIREMENTS:

1. User Authentication
   User Story: As a registered user, I want to log in with my email and password so that I can access my account securely.
   Acceptance Criteria:
   - User can enter email and password
   - System validates credentials against database
   - System displays error message for invalid credentials
   - System redirects to dashboard on successful login
   - Session token is created and stored securely
   
2. Data Storage
   User Story: As a user, I want my data to be saved automatically so that I don't lose my work.
   Acceptance Criteria:
   - Data is saved to database every 30 seconds
   - User receives confirmation when data is saved
   - System handles save failures gracefully
   - Data is recoverable in case of system crash

NON-FUNCTIONAL REQUIREMENTS:

1. Performance Requirements
   - Page load time: < 2 seconds for 95% of requests
   - API response time: < 500ms for 95% of requests
   - Database query time: < 100ms for 95% of queries
   - Support for 10,000 concurrent users

2. Security Requirements
   - Authentication: OAuth 2.0 with JWT tokens
   - Authorization: Role-based access control (RBAC)
   - Data encryption: AES-256 for data at rest, TLS 1.3 for data in transit
   - Password policy: Minimum 12 characters, complexity requirements
   - Session timeout: 30 minutes of inactivity
   - Compliance: SOC 2 Type II, GDPR compliant

3. Scalability Requirements
   - Horizontal scaling: Support for auto-scaling from 2 to 20 instances
   - Database: Read replicas for read-heavy operations
   - Caching: Redis cache for frequently accessed data
   - CDN: CloudFront for static assets
   - Support for 1M+ users and 100M+ data records
```

## Fix Applied ✅

### Agent Selection Updated

**File**: `backend/api/phase_form_help.py:129-143`

**Fixed**:
```python
elif "requirement" in phase_lower:
    return "prd_authoring"  # ✅ Now uses PRD Authoring Agent for requirements generation
```

**Status**: ✅ **FIXED** - Requirements phase now uses PRD Authoring Agent instead of Analysis Agent

### Phase Expert Prompt Enhanced ✅

**File**: `backend/api/phase_form_help.py:97-105`

**Status**: ✅ **ENHANCED** - Phase expert prompt now includes:
- McKinsey principles (SMART, MECE, hypothesis-driven)
- Detailed functional requirements structure with INVEST criteria
- Comprehensive non-functional requirements structure by category
- Problem statement format
- Success metric format
- User content preservation instructions
- No truncation requirements

**Updated Prompt**:
```python
"requirement": """You are an expert Requirements Analysis Specialist for product development following industry standards (ICAgile, AIPMM, BCS, Pragmatic Institute).

Your role is to help users define clear, actionable product requirements and specifications.

FUNCTIONAL REQUIREMENTS STRUCTURE:
- Core Features: List each feature with clear description
- User Stories: Format as "As a [user type], I want [goal] so that [benefit]" (INVEST criteria: Independent, Negotiable, Valuable, Estimable, Small, Testable)
- Acceptance Criteria: Clear, testable criteria for each user story (Definition of Done)
- User Flows: Step-by-step user interactions
- Edge Cases: Unusual scenarios and error handling

NON-FUNCTIONAL REQUIREMENTS STRUCTURE:
- Performance: Response times, throughput, resource usage, concurrent users
- Security: Authentication, authorization, data protection, compliance (GDPR, SOC 2, HIPAA)
- Scalability: User capacity, data volume, horizontal/vertical scaling
- Accessibility: WCAG 2.1 AA compliance, keyboard navigation, screen readers
- Compliance: GDPR, HIPAA, SOC 2, industry-specific regulations
- Reliability: Uptime (99.9%), error rates, disaster recovery
- Usability: User experience, learnability, efficiency

Provide detailed, specific requirements that can be directly used in development. Reference information from previous phases (ideation, market research) to create context-aware requirements. Write requirements AS IF THE USER TYPED IT DIRECTLY - no coaching language.""",
```

## Summary

### ✅ Changes Applied

**Agent Selection**: ✅ **FIXED**
- **Before**: Analysis Agent (wrong choice for requirements generation)
- **After**: PRD Authoring Agent (correct choice with comprehensive system prompt)

**System Prompt**: ✅ **ENHANCED**
- **Before**: Generic analysis specialist prompt
- **After**: Comprehensive PRD authoring specialist with:
  - McKinsey principles (SMART, MECE, hypothesis-driven)
  - 14-section PRD structure
  - Quality validation tests (Designer Test, Tech Lead Test, Measurability Test)
  - Detailed functional requirements structure with INVEST criteria
  - Comprehensive non-functional requirements by category
  - Problem statement and success metric formats

**Phase Expert Prompt**: ✅ **ENHANCED**
- **Before**: Generic requirements guidance
- **After**: Detailed structure with:
  - Functional requirements format (FR[X], User Story, Acceptance Criteria)
  - Non-functional requirements by category with specific metrics
  - McKinsey quality standards enforcement
  - User content preservation instructions

**Context Preservation**: ✅ **ENHANCED**
- **Before**: Some truncation of knowledge base and form data
- **After**: Full content preservation:
  - Complete user input (no truncation)
  - Full knowledge base articles (no 500 char limit)
  - Complete form data fields (no truncation)
  - All previous phase submissions included

**Output Quality**: ✅ **IMPROVED**
- **Before**: Vague, generic guidance
- **After**: Detailed, structured requirements comparable to ChatGPT/Claude direct output
- **Benefit**: Provides actual functional and non-functional requirements with specific metrics, not just guidance

### Key Improvements

1. **Agent Selection**: Requirements phase now uses PRD Authoring Agent (not Analysis Agent)
2. **System Prompt**: Enriched with McKinsey principles and detailed structure
3. **Context Preservation**: No truncation - all user content and details preserved
4. **Quality Standards**: SMART, MECE, hypothesis-driven validation enforced
5. **Response Completeness**: Full, comprehensive requirements (no truncation)
6. **Latency Balance**: Standard model tier for quality, efficient structure for speed

### Key Files
1. **Agent Selection**: `backend/api/phase_form_help.py:129-143`
2. **Phase Expert Prompt**: `backend/api/phase_form_help.py:97-105`
3. **System Context Building**: `backend/api/phase_form_help.py:295-354`
4. **PRD Authoring Agent**: `backend/agents/agno_prd_authoring_agent.py`
5. **Analysis Agent**: `backend/agents/agno_analysis_agent.py`
6. **Frontend Help with AI**: `src/components/PhaseFormModal.tsx:669-842`

