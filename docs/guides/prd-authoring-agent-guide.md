# PRD Authoring Agent Guide

## Overview

The PRD Authoring Agent (`AgnoPRDAuthoringAgent`) specializes in creating comprehensive Product Requirements Documents (PRDs) following industry standards including ICAgile, AIPMM, BCS, and Pragmatic Institute frameworks.

## System Context

The PRD Authoring Agent uses the following system context:

- **RAG Knowledge Base**: `prd_knowledge_base` (optional, disabled by default)
- **Model Tier**: `standard` (balanced performance for important quality)
- **Capabilities**: PRD creation, ICAgile compliance, industry-standard documentation, product requirements, user stories, acceptance criteria, functional requirements, technical requirements

## System Prompt

The system prompt defines the agent's PRD structure and standards:

```
You are a Product Requirements Document (PRD) Authoring Specialist following industry standards from:
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

Use clear, concise language. Focus on measurable outcomes. Ensure all sections are comprehensive and follow industry best practices.
```

## User Prompt

The user prompt should include:

1. **Product Information**: Complete product details
2. **Section to Generate**: Specific PRD section or full document
3. **Existing Content**: Optional - content to build upon
4. **Context**: Phase data, research, analysis, etc.

### Example User Prompts

**Basic Prompt (Low Quality Output):**
```
Generate a PRD for a fitness app
```

**Good Prompt (Medium Quality Output):**
```
Generate the Functional Requirements section for FitTrack Pro. 
Include user stories and acceptance criteria.
```

**Excellent Prompt (High Quality Output):**
```
Generate a comprehensive PRD section for FitTrack Pro following ICAgile standards.

**Product Information:**
- Product Name: FitTrack Pro
- Product Type: Mobile fitness tracking application
- Target Market: Health-conscious millennials (ages 25-40) in North America
- Business Model: Freemium (free basic, $9.99/month premium)
- Development Timeline: 12 months (MVP in 6 months, full launch in 12 months)
- Budget: $500K initial investment

**Section to Generate:**
Functional Requirements (Section 5)

**Existing Content to Build Upon:**
- Executive Summary: [Previous section content]
- Problem Statement: [Previous section content]
- Product Vision: [Previous section content]
- User Personas: [Previous section content]

**Context from Previous Phases:**
- Research Phase: Market size $4.2B, top competitors MyFitnessPal/Strava, key user pain points identified
- Analysis Phase: SWOT analysis completed, technical feasibility assessed
- Ideation Phase: 15 feature ideas generated, prioritized by user value
- Strategy Phase: Go-to-market strategy defined, success metrics established

**Core Features to Document:**
1. Workout Tracking
   - Log workouts (type, duration, intensity, exercises)
   - Track progress over time
   - Set and achieve goals
   - Integration with wearables (Apple Watch, Fitbit)

2. Nutrition Logging
   - Food diary with calorie tracking
   - Macro nutrient breakdown
   - Meal planning and recipes
   - Barcode scanning

3. Social Features
   - Friend connections and following
   - Activity feed and sharing
   - Challenges and competitions
   - Community groups

4. Progress Analytics
   - Dashboard with key metrics
   - Progress charts and trends
   - Insights and recommendations
   - Achievement badges

**Requirements:**
- Follow ICAgile INVEST criteria for user stories
- Include acceptance criteria using Definition of Done
- Document user flows for each feature
- Identify edge cases and error handling
- Specify integration requirements
- Include accessibility requirements (WCAG 2.1 AA)
- Document data requirements and privacy considerations

**Output Format:**
- Structured markdown with clear sections
- User stories in format: "As a [user type], I want [goal] so that [benefit]"
- Acceptance criteria as numbered lists
- User flows as step-by-step processes
- Edge cases clearly identified
```

## How Response Quality Changes

### Low Quality Input → Generic PRD

**Input:**
```
Write a PRD for a fitness app
```

**Output Characteristics:**
- Generic PRD structure
- Vague requirements
- Missing user stories
- No acceptance criteria
- Missing technical details
- No industry standards compliance

### Medium Quality Input → Structured PRD

**Input:**
```
Generate Functional Requirements section with user stories for FitTrack Pro.
```

**Output Characteristics:**
- Structured PRD section
- Basic user stories
- Some acceptance criteria
- General technical notes
- Basic standards compliance

### High Quality Input → Comprehensive, Standards-Compliant PRD

**Input:** (See "Excellent Prompt" example above)

**Output Characteristics:**
- Complete PRD section following ICAgile standards
- Detailed user stories following INVEST criteria:
  - Independent
  - Negotiable
  - Valuable
  - Estimable
  - Small
  - Testable
- Comprehensive acceptance criteria using Definition of Done
- Detailed user flows with step-by-step processes
- Edge cases identified with error handling
- Integration requirements specified
- Accessibility requirements (WCAG 2.1 AA)
- Data requirements and privacy considerations
- Technical architecture details
- Performance requirements
- Security requirements
- References to previous phases (research, analysis, ideation)
- Alignment with business objectives and success metrics

## Best Practices for Quality Output

### 1. Provide Complete Product Information

**Include:**
- Product name, type, and description
- Target market and user personas
- Business model and pricing
- Development timeline and budget
- Success metrics and goals

**Why:** Enables comprehensive PRD that aligns with business objectives.

### 2. Include Context from All Phases

**Include:**
- Research findings (market, competitors, users)
- Analysis results (SWOT, feasibility, risks)
- Ideation outcomes (features, ideas)
- Strategy decisions (GTM, positioning)

**Why:** Ensures PRD synthesizes all previous work and maintains consistency.

### 3. Specify Features in Detail

**Include:**
- Feature names and descriptions
- User goals and benefits
- Technical requirements
- Integration needs

**Why:** Enables detailed user stories and acceptance criteria.

### 4. Request Industry Standards Compliance

**Specify:**
- ICAgile standards
- AIPMM framework
- BCS standards
- Pragmatic Institute approach

**Why:** Ensures PRD meets industry best practices and is actionable.

### 5. Ask for Specific Formats

**Request:**
- User stories in INVEST format
- Acceptance criteria as Definition of Done
- User flows as step-by-step processes
- Edge cases clearly identified

**Why:** Makes PRD actionable for engineering teams.

## Response Quality Indicators

### High Quality Response Includes:

✅ **Complete Structure**: All required sections with comprehensive content
✅ **INVEST User Stories**: Independent, negotiable, valuable, estimable, small, testable
✅ **Definition of Done**: Clear acceptance criteria for each user story
✅ **User Flows**: Step-by-step processes for key features
✅ **Edge Cases**: Error handling and exception scenarios
✅ **Technical Details**: Architecture, integrations, data requirements
✅ **Standards Compliance**: ICAgile, AIPMM, BCS, Pragmatic Institute
✅ **Context Integration**: References to research, analysis, ideation, strategy
✅ **Measurable Outcomes**: Success metrics and KPIs
✅ **Actionable**: Ready for engineering implementation

### Low Quality Response Indicators:

❌ Incomplete sections or missing content
❌ User stories don't follow INVEST criteria
❌ Missing or vague acceptance criteria
❌ No user flows or processes
❌ Missing edge cases
❌ Vague technical details
❌ No standards compliance
❌ No context from previous phases
❌ Missing success metrics
❌ Not actionable for engineering

## Integration with Other Agents

The PRD Authoring Agent's output is often used by:

- **Research Agent**: For market context in PRD
- **Analysis Agent**: For requirements analysis
- **Validation Agent**: To validate PRD completeness
- **Export Agent**: For final PRD document generation
- **Strategy Agent**: For strategic alignment

## Tips for Maximum Quality

1. **Synthesize All Phases**: Include context from research, analysis, ideation, strategy
2. **Be Specific**: Provide detailed feature descriptions and requirements
3. **Request Standards**: Ask for ICAgile, AIPMM, BCS compliance
4. **Specify Formats**: Request INVEST user stories, Definition of Done
5. **Iterate**: Generate sections iteratively, building upon previous sections
6. **Validate**: Use Validation Agent to check completeness and quality

## Example Workflow

1. **Executive Summary**: "Generate Executive Summary for FitTrack Pro"
2. **Problem Statement**: "Generate Problem Statement building on research findings"
3. **User Stories**: "Generate user stories for workout tracking feature using INVEST criteria"
4. **Acceptance Criteria**: "Add acceptance criteria for each user story using Definition of Done"
5. **Full PRD**: "Generate complete PRD synthesizing all sections and phases"

Each iteration builds upon the previous, resulting in a comprehensive, standards-compliant PRD.

