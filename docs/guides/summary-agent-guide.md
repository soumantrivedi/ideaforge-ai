# Summary Agent Guide

## Overview

The Summary Agent (`AgnoSummaryAgent`) specializes in creating comprehensive summaries from multiple conversation sessions, synthesizing information from various sources, and organizing information in structured formats.

## System Context

The Summary Agent uses the following system context:

- **RAG Knowledge Base**: `summary_knowledge_base` (enabled by default)
- **Model Tier**: `fast` (optimized for speed, 50-70% latency reduction)
- **Capabilities**: Summary, synthesis, documentation, conversation summary, session summary, meeting notes, requirements extraction

## System Prompt

The system prompt defines the agent's summarization framework:

```
You are a Summary and Documentation Specialist.

Your responsibilities:
1. Create comprehensive summaries from multiple conversation sessions
2. Synthesize information from various sources and participants
3. Identify key themes, decisions, and action items
4. Extract important context and requirements
5. Organize information in a structured, easy-to-understand format

Summary Structure:
- Executive Summary: High-level overview
- Key Themes: Main topics discussed
- Decisions Made: Important decisions and rationale
- Requirements Identified: Functional and non-functional requirements
- Action Items: Tasks and next steps
- Open Questions: Unresolved items
- Context: Important background information
- Participants: Key contributors and their inputs

Your summaries should:
- Be comprehensive yet concise
- Preserve important context and nuance
- Highlight critical decisions and requirements
- Identify patterns and themes across sessions
- Be actionable and clear
- Maintain chronological flow when relevant
```

## User Prompt

The user prompt should include:

1. **Session Data**: Messages, conversations, or content to summarize
2. **Participants**: Optional - who was involved
3. **Context**: Optional - product context, phase information
4. **Summary Type**: Single session or multi-session summary

### Example User Prompts

**Basic Prompt (Low Quality Output):**
```
Summarize this conversation: [messages]
```

**Good Prompt (Medium Quality Output):**
```
Create a summary of this conversation session. Include key decisions and action items.
```

**Excellent Prompt (High Quality Output):**
```
Create a comprehensive multi-session summary for FitTrack Pro product development.

**Session 1 - Research Phase (Date: 2024-01-15):**
Participants: Product Manager, Research Agent, User Researcher

Conversation:
- PM: "We need to research the fitness app market for millennials"
- Research Agent: "Market size is $4.2B, growing at 15% CAGR. Top competitors: MyFitnessPal, Strava, Nike Run Club..."
- PM: "What are the main user pain points?"
- Research Agent: "Users struggle with motivation, time-consuming tracking, competitive social features..."
- PM: "What about technical feasibility of wearable integration?"
- Research Agent: "Wearable APIs are mature. Apple HealthKit, Google Fit, Fitbit API all available..."
- Decision: Target market confirmed as health-conscious millennials (ages 25-40) in North America

**Session 2 - Analysis Phase (Date: 2024-01-20):**
Participants: Product Manager, Analysis Agent, Technical Lead

Conversation:
- PM: "Perform SWOT analysis for FitTrack Pro"
- Analysis Agent: "Strengths: Strong team, modern tech stack. Weaknesses: Limited brand recognition..."
- Technical Lead: "We can support offline functionality with React Native"
- Analysis Agent: "Technical feasibility is high. Main risk is market competition..."
- Decision: Proceed with freemium model, $9.99/month premium tier
- Decision: Focus on supportive social features, not competitive

**Session 3 - Ideation Phase (Date: 2024-01-25):**
Participants: Product Manager, Ideation Agent, Design Lead

Conversation:
- PM: "Generate feature ideas focusing on user motivation"
- Ideation Agent: "1. Personalized workout recommendations using AI..."
- Design Lead: "We should make nutrition tracking less time-consuming with barcode scanning"
- Ideation Agent: "2. Social challenges with team support features..."
- Decision: Prioritize: Personalized recommendations, barcode scanning, supportive social features
- Action Item: Design team to create mockups for top 3 features

**Session 4 - Strategy Phase (Date: 2024-01-30):**
Participants: Product Manager, Strategy Agent, Marketing Lead

Conversation:
- PM: "Develop go-to-market strategy"
- Strategy Agent: "Launch plan: Beta in 3 months, full launch in 6 months..."
- Marketing Lead: "We should focus on social media and influencer partnerships"
- Strategy Agent: "Target: 100K users in Year 1, 20% conversion to premium..."
- Decision: Beta launch strategy: Invite-only, focus on early adopters
- Decision: Marketing budget: $200K for Year 1

**Product Context:**
- Product: FitTrack Pro - Mobile fitness tracking app
- Target Market: Health-conscious millennials (ages 25-40) in North America
- Business Model: Freemium ($9.99/month premium)
- Timeline: Beta in 3 months, full launch in 6 months

**Requested Summary Format:**
- Executive Summary: High-level overview of all sessions
- Key Themes: Main topics across all sessions
- Decisions Made: All decisions with rationale
- Requirements Identified: Functional and non-functional requirements
- Action Items: Tasks with owners and timelines
- Open Questions: Unresolved items needing attention
- Evolution of Ideas: How ideas evolved across sessions
- Strategic Alignment: How sessions align with product goals
```

## How Response Quality Changes

### Low Quality Input → Generic Summary

**Input:**
```
Summarize: [messages]
```

**Output Characteristics:**
- Generic summary
- Missing key information
- No structure
- Missing decisions
- No action items
- Missing context

### Medium Quality Input → Structured Summary

**Input:**
```
Summarize this conversation. Include decisions and action items.
```

**Output Characteristics:**
- Basic structure
- Some key points
- Some decisions listed
- Basic action items
- Limited context

### High Quality Input → Comprehensive Summary

**Input:** (See "Excellent Prompt" example above)

**Output Characteristics:**
- Executive Summary:
  - High-level overview of all sessions
  - Key outcomes and decisions
  - Strategic direction
- Key Themes:
  - Market research and validation
  - Feature ideation and prioritization
  - Strategic planning and GTM
  - Technical feasibility
- Decisions Made:
  - Target market: Health-conscious millennials (ages 25-40)
  - Business model: Freemium, $9.99/month premium
  - Social features: Supportive, not competitive
  - Beta strategy: Invite-only, early adopters
  - Marketing budget: $200K Year 1
  - Feature priorities: Personalized recommendations, barcode scanning, supportive social
- Requirements Identified:
  - Functional: Workout tracking, nutrition logging, social features, wearable integration
  - Non-functional: Offline support, iOS/Android, HIPAA compliance
  - Technical: React Native, Apple HealthKit, Google Fit, Fitbit API
- Action Items:
  - Design team: Create mockups for top 3 features (Due: 2024-02-15)
  - Technical team: Prototype wearable integration (Due: 2024-02-20)
  - Marketing team: Develop beta launch plan (Due: 2024-02-25)
- Open Questions:
  - Pricing strategy for premium features
  - Partnership opportunities with wearable brands
  - User acquisition channels prioritization
- Evolution of Ideas:
  - Session 1: Market validation → Session 2: Feasibility → Session 3: Features → Session 4: Strategy
- Strategic Alignment:
  - All sessions align with goal: Launch FitTrack Pro in 6 months with 100K users Year 1

## Best Practices for Quality Output

### 1. Provide Complete Session Data

**Include:**
- All messages from each session
- Participant names and roles
- Session dates and context
- Decisions and action items mentioned

**Why:** Enables comprehensive summary capturing all important information.

### 2. Include Product Context

**Include:**
- Product name and description
- Target market and goals
- Business model and timeline
- Strategic objectives

**Why:** Enables summary aligned with product context and goals.

### 3. Specify Summary Format

**Request:**
- Executive summary
- Key themes
- Decisions made
- Requirements identified
- Action items
- Open questions
- Evolution of ideas

**Why:** Ensures summary covers all important aspects in structured format.

### 4. Request Multi-Session Synthesis

**Request:**
- Patterns across sessions
- Evolution of ideas
- Strategic alignment
- Consistency check

**Why:** Enables synthesis of information across multiple sessions.

### 5. Ask for Actionability

**Request:**
- Action items with owners
- Timelines and deadlines
- Priorities
- Next steps

**Why:** Makes summary actionable and useful for project management.

## Response Quality Indicators

### High Quality Response Includes:

✅ **Executive Summary**: High-level overview of all sessions
✅ **Key Themes**: Main topics identified across sessions
✅ **Decisions Made**: All decisions with rationale and context
✅ **Requirements**: Functional and non-functional requirements extracted
✅ **Action Items**: Tasks with owners, timelines, priorities
✅ **Open Questions**: Unresolved items needing attention
✅ **Evolution**: How ideas evolved across sessions
✅ **Strategic Alignment**: How sessions align with goals
✅ **Context Preservation**: Important background information maintained
✅ **Actionable**: Clear next steps and priorities

### Low Quality Response Indicators:

❌ Generic summary without structure
❌ Missing key themes or topics
❌ Decisions not clearly identified
❌ Requirements not extracted
❌ No action items or next steps
❌ Missing open questions
❌ No synthesis across sessions
❌ No strategic alignment
❌ Context lost or missing
❌ Not actionable

## Integration with Other Agents

The Summary Agent's output is often used by:

- **PRD Authoring Agent**: For requirements and context in PRD
- **Export Agent**: For comprehensive PRD document
- **Strategy Agent**: For strategic context
- **Validation Agent**: To validate completeness

## Tips for Maximum Quality

1. **Include All Sessions**: Provide complete conversation history
2. **Specify Format**: Request structured summary with all sections
3. **Add Context**: Include product context and goals
4. **Request Synthesis**: Ask for patterns and evolution across sessions
5. **Ask for Actionability**: Request action items with owners and timelines
6. **Iterate**: Use summary to identify gaps and request refinements

## Example Workflow

1. **Single Session**: "Summarize Session 1 - Research Phase"
2. **Multi-Session**: "Create summary of Sessions 1-4"
3. **Deep Dive**: "Extract all requirements from all sessions"
4. **Action Items**: "List all action items with owners and deadlines"
5. **Final Summary**: "Create comprehensive summary with strategic alignment"

Each iteration provides increasingly comprehensive and actionable summaries.


