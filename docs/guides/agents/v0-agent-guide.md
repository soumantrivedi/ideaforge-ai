# V0 Agent Guide

## Overview

The V0 Agent (`AgnoV0Agent`) specializes in generating detailed, comprehensive prompts for V0.dev to create React/Next.js UI components and prototypes. It synthesizes information from all product lifecycle phases to create production-ready design prompts.

## System Context

The V0 Agent uses the following system context:

- **RAG Knowledge Base**: `v0_knowledge_base` (optional, disabled by default)
- **Model Tier**: `fast` (optimized for speed to avoid timeout issues)
- **Capabilities**: V0 prompt generation, V0 project creation, V0 code generation, Vercel integration, UI prototype generation, React component generation, Next.js development

## System Prompt

The system prompt emphasizes comprehensive, detailed prompt generation:

```
You are a V0 (Vercel) Design Specialist expert in creating detailed, comprehensive prompts for V0.dev.

Your primary goal is to generate EXTENSIVE, DETAILED prompts that capture ALL aspects of the product design based on the complete context provided.

CRITICAL: You MUST use ALL available information from:
- ALL chatbot conversation history and context
- ALL design form content and fields
- ALL product lifecycle phase data (Ideation, Strategy, Research, PRD, Design, etc.)
- ALL generated content from previous phases
- ALL form data fields - do not skip any fields, include everything

IMPORTANT: When generating prompts (not submitting to V0):
- You are ONLY generating the prompt text - do NOT call any tools or submit to V0
- Do NOT use create_v0_project or generate_v0_code tools during prompt generation
- Simply return the prompt text that the user can then use separately to submit to V0
- The user will submit the prompt to V0 using a separate action/button

Core Requirements:
- Generate DETAILED, COMPREHENSIVE prompts (not concise - include all relevant information)
- Include ALL form data, product context, and requirements from all lifecycle phases
- Extract and use ALL information from chatbot conversations - every detail matters
- Include ALL design form fields and their values - nothing should be omitted
- Describe component types, layouts, Tailwind CSS styling, responsive breakpoints in detail
- Specify ALL interaction states, accessibility (ARIA), and complete user flows
- Reference shadcn/ui patterns, modern React practices, and Next.js App Router patterns
- Include color schemes, typography, spacing, animations, and transitions
- Describe data structures, state management, API integrations, and authentication flows
- Output ONLY the prompt text - no instructions, notes, or meta-commentary

V0 Documentation Guidelines (Based on Official Vercel V0 Docs):
- V0 uses v0-1.5-md model specialized for UI generation
- Prompts should be detailed enough to generate complete, production-ready components
- Include specific Tailwind CSS classes and responsive breakpoints (sm:, md:, lg:, xl:)
- Specify component hierarchy, props, and state management patterns
- Describe complete user interactions, form validations, and error handling
- Include accessibility features: ARIA labels, keyboard navigation, focus management
- Reference React patterns: hooks, context, server/client components
- Describe animations, transitions, and micro-interactions
```

## User Prompt

The user prompt should include:

1. **Product Context**: Complete product information from all phases
2. **Design Form Data**: All design form fields and values
3. **Conversation History**: All chatbot conversations
4. **Phase Data**: All lifecycle phase submissions
5. **Design Requirements**: Specific UI/UX requirements

### Example User Prompts

**Basic Prompt (Low Quality Output):**
```
Generate a V0 prompt for a fitness app dashboard
```

**Good Prompt (Medium Quality Output):**
```
Generate a V0 prompt for FitTrack Pro dashboard. Include workout tracking and progress charts.
```

**Excellent Prompt (High Quality Output):**
```
Generate a DETAILED, COMPREHENSIVE V0 design prompt for FitTrack Pro dashboard page.

**Product Context (from all lifecycle phases):**

Research Phase:
- Market: $4.2B fitness app market, targeting health-conscious millennials (ages 25-40)
- User Pain Points: Lack of motivation, time-consuming tracking, competitive social features
- Competitive Analysis: MyFitnessPal, Strava, Nike Run Club - focus on supportive community

Analysis Phase:
- SWOT: Strengths - modern tech stack, experienced team. Weaknesses - new brand
- Technical: React Native, Node.js, PostgreSQL, AWS infrastructure
- Feasibility: High - standard mobile app, proven technologies

Ideation Phase:
- Top Features: Personalized workout recommendations, barcode nutrition scanning, supportive social features
- User Value: High motivation, easy tracking, community support
- Business Value: Premium conversion, user retention, engagement

Strategy Phase:
- Business Model: Freemium (free basic, $9.99/month premium)
- GTM: Beta launch in 3 months, full launch in 6 months
- Success Metrics: 100K users Year 1, 20% premium conversion

PRD Authoring Phase:
- User Stories: "As a user, I want to see my workout progress so that I stay motivated"
- Acceptance Criteria: Dashboard shows weekly progress, trends, achievements
- Functional Requirements: Workout tracking, nutrition logging, progress analytics, social feed

**Design Form Data:**
- Color Scheme: Primary #3B82F6 (blue), Secondary #10B981 (green), Accent #F59E0B (amber)
- Typography: Inter font family, headings bold, body regular
- Layout: Sidebar navigation, main content area, right sidebar for social
- Components: Cards, charts, buttons, forms, modals
- Responsive: Mobile-first, breakpoints sm:640px, md:768px, lg:1024px, xl:1280px
- Accessibility: WCAG 2.1 AA compliant, ARIA labels, keyboard navigation
- Animations: Smooth transitions, loading states, micro-interactions

**Conversation History:**
- User: "I want a dashboard that shows my weekly progress with charts"
- Agent: "We'll include progress charts, workout summary, nutrition overview"
- User: "Make it motivational with achievements and streaks"
- Agent: "Adding achievement badges, streak counters, motivational messages"
- User: "Include social feed on the right side"
- Agent: "Right sidebar with friend activities, challenges, community posts"

**Design Requirements:**
1. Dashboard Layout:
   - Header: Logo, navigation, user profile, notifications
   - Sidebar: Navigation menu (Dashboard, Workouts, Nutrition, Social, Settings)
   - Main Content: Workout summary, progress charts, recent activities
   - Right Sidebar: Social feed, challenges, achievements

2. Workout Summary Section:
   - Today's workout card with exercise list, duration, calories
   - Weekly summary with total workouts, duration, calories burned
   - Progress chart showing weekly trends (line chart)
   - Quick action buttons: Start Workout, Log Exercise, View History

3. Progress Analytics:
   - Weekly progress chart (line chart with Tailwind CSS)
   - Monthly overview (bar chart)
   - Achievement badges grid
   - Streak counter with fire icon
   - Personal records (PRs) section

4. Nutrition Overview:
   - Today's nutrition card: Calories consumed, macros (protein, carbs, fats)
   - Weekly nutrition chart (area chart)
   - Quick log button: Barcode scanner, manual entry
   - Meal suggestions based on goals

5. Social Feed (Right Sidebar):
   - Friend activities feed
   - Active challenges
   - Community posts
   - Support messages and encouragement

6. Interactive States:
   - Hover effects on cards and buttons
   - Loading states for data fetching
   - Empty states with helpful messages
   - Error states with retry options
   - Success states with animations

7. Responsive Design:
   - Mobile: Stacked layout, bottom navigation, full-width cards
   - Tablet: Sidebar collapses, main content expands
   - Desktop: Full three-column layout

8. Accessibility:
   - ARIA labels for all interactive elements
   - Keyboard navigation support
   - Focus indicators
   - Screen reader support
   - Color contrast compliance (WCAG 2.1 AA)

**Technical Requirements:**
- Framework: Next.js 14 with App Router
- Styling: Tailwind CSS with custom theme
- Components: shadcn/ui components (Button, Card, Chart, Form, Modal)
- State Management: React hooks (useState, useEffect, useContext)
- Data Fetching: Server components with async data fetching
- API Integration: REST API endpoints for workouts, nutrition, social
- Authentication: NextAuth.js with session management

**Output Requirements:**
- Generate ONLY the prompt text - no instructions or meta-commentary
- Include ALL details from product context, design form, conversations
- Describe complete component structure, styling, interactions
- Specify Tailwind CSS classes, responsive breakpoints, animations
- Include accessibility features, error handling, loading states
- Make it ready for direct use in V0 API or UI
```

## How Response Quality Changes

### Low Quality Input → Generic Prompt

**Input:**
```
Generate V0 prompt for fitness app dashboard
```

**Output Characteristics:**
- Generic component description
- Missing design details
- No styling specifications
- Missing interactions
- No accessibility features
- Not production-ready

### Medium Quality Input → Structured Prompt

**Input:**
```
Generate V0 prompt for dashboard with workout tracking and charts.
```

**Output Characteristics:**
- Basic component structure
- Some styling details
- Basic interactions
- Limited accessibility
- Partially production-ready

### High Quality Input → Comprehensive, Production-Ready Prompt

**Input:** (See "Excellent Prompt" example above)

**Output Characteristics:**
- Comprehensive component description:
  - Complete layout structure (header, sidebar, main, right sidebar)
  - Detailed component hierarchy
  - Specific Tailwind CSS classes
  - Responsive breakpoints (sm:, md:, lg:, xl:)
  - Color scheme and typography
- Detailed Interactions:
  - Hover effects and transitions
  - Loading states and animations
  - Error handling and retry
  - Form validations
  - Modal interactions
- Accessibility Features:
  - ARIA labels for all elements
  - Keyboard navigation
  - Focus management
  - Screen reader support
  - WCAG 2.1 AA compliance
- Technical Specifications:
  - Next.js App Router patterns
  - Server/client components
  - State management (hooks, context)
  - API integration patterns
  - Authentication flows
- Complete Context Integration:
  - All phase data synthesized
  - All design form fields included
  - All conversation history referenced
  - All requirements addressed
- Production-Ready:
  - Complete component structure
  - All styling specified
  - All interactions described
  - Error handling included
  - Ready for direct V0 use

## Best Practices for Quality Output

### 1. Provide Complete Product Context

**Include:**
- All lifecycle phase data (research, analysis, ideation, strategy, PRD)
- All generated content from phases
- All decisions and requirements

**Why:** Enables prompt that captures complete product vision and requirements.

### 2. Include All Design Form Data

**Include:**
- Color schemes and themes
- Typography and fonts
- Layout preferences
- Component requirements
- Responsive breakpoints
- Accessibility requirements

**Why:** Ensures prompt includes all design specifications.

### 3. Synthesize Conversation History

**Include:**
- All chatbot conversations
- User preferences and requirements
- Design discussions
- Feature clarifications

**Why:** Captures all design decisions and user preferences from conversations.

### 4. Specify Technical Requirements

**Include:**
- Framework and version (Next.js 14)
- Styling approach (Tailwind CSS)
- Component library (shadcn/ui)
- State management patterns
- API integration requirements

**Why:** Ensures prompt generates technically correct components.

### 5. Request Comprehensive Details

**Request:**
- Complete component structure
- Detailed styling (Tailwind classes)
- All interaction states
- Accessibility features
- Error handling
- Responsive design

**Why:** Ensures production-ready, comprehensive prompt.

## Response Quality Indicators

### High Quality Response Includes:

✅ **Complete Structure**: All components, layouts, sections described
✅ **Detailed Styling**: Specific Tailwind CSS classes, colors, typography
✅ **Responsive Design**: Breakpoints and mobile/tablet/desktop layouts
✅ **Interactions**: Hover, loading, error, success states
✅ **Accessibility**: ARIA labels, keyboard navigation, WCAG compliance
✅ **Technical Patterns**: Next.js, React, state management, API integration
✅ **Context Integration**: All phases, form data, conversations synthesized
✅ **Production-Ready**: Complete, detailed, ready for V0 use

### Low Quality Response Indicators:

❌ Generic component descriptions
❌ Missing styling details
❌ No responsive design
❌ Missing interactions
❌ No accessibility features
❌ Vague technical patterns
❌ Missing context integration
❌ Not production-ready

## Integration with Other Agents

The V0 Agent's output is often used by:

- **Research Agent**: For market-informed design decisions
- **Analysis Agent**: For technical feasibility in design
- **Ideation Agent**: For feature ideas in UI
- **Strategy Agent**: For strategic design alignment
- **PRD Authoring Agent**: For UI requirements in PRD
- **Export Agent**: For design references in PRD

## Tips for Maximum Quality

1. **Synthesize All Phases**: Include context from all lifecycle phases
2. **Include All Form Data**: Every design form field matters
3. **Specify Technical Details**: Request specific frameworks, libraries, patterns
4. **Request Comprehensive Details**: Ask for complete component structure
5. **Iterate**: Use initial prompt to refine specific sections
6. **Test in V0**: Use generated prompt in V0 to validate and refine

## Example Workflow

1. **Initial Prompt**: "Generate V0 prompt for FitTrack Pro dashboard"
2. **Refinement**: "Add detailed styling and Tailwind CSS classes"
3. **Interactions**: "Specify all interaction states and animations"
4. **Accessibility**: "Add ARIA labels and keyboard navigation"
5. **Final Prompt**: "Generate comprehensive, production-ready prompt"

Each iteration results in increasingly detailed and production-ready V0 prompts.

