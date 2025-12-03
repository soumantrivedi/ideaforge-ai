# Lovable Agent Guide

## Overview

The Lovable Agent (`AgnoLovableAgent`) specializes in generating detailed, comprehensive prompts for Lovable.dev to create fully deployable React/Next.js applications. It synthesizes information from all product lifecycle phases to create production-ready application prompts.

## System Context

The Lovable Agent uses the following system context:

- **RAG Knowledge Base**: `lovable_knowledge_base` (optional, disabled by default)
- **Model Tier**: `fast` (optimized for speed to avoid timeout issues)
- **Capabilities**: Lovable prompt generation, Lovable link generation, Lovable integration, UI prototype generation, React application generation, Next.js development

## System Prompt

The system prompt emphasizes comprehensive, detailed prompt generation for full applications:

```
You are a Lovable AI Design Specialist expert in creating detailed, comprehensive prompts for Lovable.dev.

Your primary goal is to generate EXTENSIVE, DETAILED prompts that capture ALL aspects of the application based on the complete context provided.

CRITICAL: You MUST use ALL available information from:
- ALL chatbot conversation history and context
- ALL design form content and fields
- ALL product lifecycle phase data (Ideation, Strategy, Research, PRD, Design, etc.)
- ALL generated content from previous phases
- ALL form data fields - do not skip any fields, include everything

Core Requirements:
- Generate DETAILED, COMPREHENSIVE prompts (not concise - include all relevant information)
- Include ALL form data, product context, and requirements from all lifecycle phases
- Extract and use ALL information from chatbot conversations - every detail matters
- Include ALL design form fields and their values - nothing should be omitted
- Describe complete application architecture, component structure, and data flow
- Specify ALL features, user flows, API integrations, and authentication patterns
- Include detailed Tailwind CSS styling, responsive breakpoints, and design system
- Describe state management, routing (Next.js App Router), and data fetching patterns
- Include accessibility (WCAG 2.1 AA), performance optimization, and modern React patterns
- Output ONLY the prompt text - no instructions, notes, or meta-commentary

Lovable Platform Documentation Guidelines (Based on Official Lovable.dev Docs):
- Lovable.dev generates fully deployable React/Next.js applications
- Supports Server Components, Client Components, and App Router patterns
- Uses Tailwind CSS for styling with responsive breakpoints
- Supports Supabase, Firebase, REST APIs, GraphQL, and authentication patterns
- Prompts should be detailed enough to generate complete, production-ready applications
- Include database schemas, API endpoints, authentication flows, and user management
- Describe complete application structure: pages, components, layouts, routing
- Include form validations, error handling, loading states, and user feedback
- Specify data models, relationships, and data flow throughout the application
```

## User Prompt

The user prompt should include:

1. **Product Context**: Complete product information from all phases
2. **Design Form Data**: All design form fields and values
3. **Conversation History**: All chatbot conversations
4. **Phase Data**: All lifecycle phase submissions
5. **Application Requirements**: Complete app structure, features, and flows

### Example User Prompts

**Basic Prompt (Low Quality Output):**
```
Generate a Lovable prompt for a fitness app
```

**Good Prompt (Medium Quality Output):**
```
Generate a Lovable prompt for FitTrack Pro. Include workout tracking and user dashboard.
```

**Excellent Prompt (High Quality Output):**
```
Generate a DETAILED, COMPREHENSIVE Lovable prompt for FitTrack Pro - a complete fitness tracking application.

**Product Context (from all lifecycle phases):**

[Same comprehensive context as V0 Agent example, but focused on full application]

**Application Architecture Requirements:**
1. **Pages Structure:**
   - `/` - Landing page with hero, features, pricing, CTA
   - `/dashboard` - Main dashboard with workout summary, progress, social feed
   - `/workouts` - Workout library, create workout, workout history
   - `/nutrition` - Nutrition logging, meal planning, macro tracking
   - `/social` - Social feed, friends, challenges, community
   - `/profile` - User profile, settings, achievements, stats
   - `/auth/login` - Login page
   - `/auth/signup` - Signup page

2. **Database Schema:**
   - Users: id, email, name, avatar, premium_status, created_at
   - Workouts: id, user_id, type, duration, calories, exercises, date
   - Nutrition: id, user_id, meal_type, food, calories, macros, date
   - Friends: id, user_id, friend_id, status, created_at
   - Challenges: id, name, description, start_date, end_date, participants
   - Achievements: id, user_id, achievement_type, unlocked_at

3. **API Endpoints:**
   - `/api/auth/login` - POST - User authentication
   - `/api/auth/signup` - POST - User registration
   - `/api/workouts` - GET/POST - Workout CRUD
   - `/api/nutrition` - GET/POST - Nutrition logging
   - `/api/social/feed` - GET - Social feed
   - `/api/social/friends` - GET/POST - Friend management
   - `/api/challenges` - GET/POST - Challenge management

4. **Authentication Flow:**
   - NextAuth.js with email/password
   - Session management
   - Protected routes
   - Premium status check

5. **State Management:**
   - React Context for user state
   - Server Components for data fetching
   - Client Components for interactions
   - React Query for API caching

6. **Features to Implement:**
   - Workout tracking with exercise logging
   - Nutrition logging with barcode scanning
   - Progress analytics with charts
   - Social feed with friend activities
   - Challenges and competitions
   - Achievement system
   - Premium subscription management

7. **Design System:**
   - Colors: Primary #3B82F6, Secondary #10B981, Accent #F59E0B
   - Typography: Inter font, headings bold, body regular
   - Components: shadcn/ui (Button, Card, Form, Modal, Chart, Table)
   - Layout: Responsive, mobile-first, sidebar navigation

8. **Technical Stack:**
   - Framework: Next.js 14 with App Router
   - Database: Supabase (PostgreSQL)
   - Authentication: NextAuth.js
   - Styling: Tailwind CSS
   - Charts: Recharts or Chart.js
   - Forms: React Hook Form with Zod validation

**Output Requirements:**
- Generate ONLY the prompt text - no instructions or meta-commentary
- Include ALL details from product context, design form, conversations
- Describe complete application structure, pages, components, database
- Specify API endpoints, authentication flows, state management
- Include Tailwind CSS styling, responsive design, accessibility
- Make it ready for direct use in Lovable Link Generator
```

## How Response Quality Changes

### Low Quality Input → Generic Prompt

**Input:**
```
Generate Lovable prompt for fitness app
```

**Output Characteristics:**
- Generic application description
- Missing architecture details
- No database schema
- Missing API specifications
- No authentication flow
- Not production-ready

### Medium Quality Input → Structured Prompt

**Input:**
```
Generate Lovable prompt for FitTrack Pro with workout and nutrition features.
```

**Output Characteristics:**
- Basic application structure
- Some features described
- Basic database schema
- Limited API details
- Basic authentication
- Partially production-ready

### High Quality Input → Comprehensive, Production-Ready Prompt

**Input:** (See "Excellent Prompt" example above)

**Output Characteristics:**
- Complete Application Architecture:
  - All pages and routes defined
  - Component hierarchy specified
  - Layout structure detailed
  - Navigation flow described
- Comprehensive Database Schema:
  - All tables and relationships
  - Field types and constraints
  - Indexes and relationships
  - Data models complete
- Complete API Specification:
  - All endpoints defined
  - Request/response formats
  - Authentication requirements
  - Error handling
- Authentication Flow:
  - NextAuth.js configuration
  - Session management
  - Protected routes
  - Premium status checks
- State Management:
  - React Context patterns
  - Server/Client components
  - Data fetching strategies
  - Caching strategies
- Complete Feature Implementation:
  - All features detailed
  - User flows described
  - Interactions specified
  - Error handling included
- Design System:
  - Complete styling specification
  - Component library usage
  - Responsive design
  - Accessibility features
- Production-Ready:
  - Complete application structure
  - All technical patterns specified
  - Ready for Lovable generation

## Best Practices for Quality Output

### 1. Provide Complete Application Context

**Include:**
- All lifecycle phase data
- Complete feature requirements
- User flows and interactions
- Business logic requirements

**Why:** Enables prompt that captures complete application vision.

### 2. Specify Complete Architecture

**Include:**
- Pages and routes
- Component structure
- Database schema
- API endpoints
- Authentication flow

**Why:** Ensures prompt generates complete, functional application.

### 3. Include Technical Stack Details

**Include:**
- Framework and version
- Database and ORM
- Authentication library
- Styling approach
- State management

**Why:** Ensures technically correct application generation.

### 4. Request Complete Implementation

**Request:**
- All features detailed
- All user flows described
- All interactions specified
- Error handling included
- Loading states included

**Why:** Ensures production-ready application.

### 5. Specify Design System

**Request:**
- Color scheme and themes
- Typography and fonts
- Component library
- Responsive design
- Accessibility features

**Why:** Ensures consistent, accessible design.

## Response Quality Indicators

### High Quality Response Includes:

✅ **Complete Architecture**: All pages, components, routes defined
✅ **Database Schema**: All tables, relationships, constraints
✅ **API Specification**: All endpoints, formats, authentication
✅ **Authentication Flow**: Complete auth implementation
✅ **State Management**: Patterns and strategies specified
✅ **Feature Implementation**: All features detailed with flows
✅ **Design System**: Complete styling and component usage
✅ **Production-Ready**: Complete, deployable application

### Low Quality Response Indicators:

❌ Generic application description
❌ Missing architecture details
❌ No database schema
❌ Missing API specifications
❌ No authentication flow
❌ Incomplete features
❌ Missing design system
❌ Not production-ready

## Integration with Other Agents

The Lovable Agent's output is often used by:

- **Research Agent**: For market-informed features
- **Analysis Agent**: For technical feasibility
- **Ideation Agent**: For feature ideas
- **Strategy Agent**: For strategic alignment
- **PRD Authoring Agent**: For application requirements
- **Export Agent**: For application documentation

## Tips for Maximum Quality

1. **Specify Complete Architecture**: Request all pages, components, database, APIs
2. **Include All Features**: Provide complete feature requirements
3. **Specify Technical Stack**: Request specific frameworks, libraries, patterns
4. **Request Complete Implementation**: Ask for all user flows and interactions
5. **Iterate**: Use initial prompt to refine specific sections
6. **Test in Lovable**: Use generated prompt in Lovable to validate and refine

## Example Workflow

1. **Initial Prompt**: "Generate Lovable prompt for FitTrack Pro application"
2. **Architecture**: "Add complete database schema and API endpoints"
3. **Features**: "Detail all features with user flows and interactions"
4. **Authentication**: "Specify complete authentication flow with NextAuth.js"
5. **Final Prompt**: "Generate comprehensive, production-ready application prompt"

Each iteration results in increasingly detailed and production-ready Lovable prompts.

