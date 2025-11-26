# Flexible Lifecycle and Enhanced Export Guide

## Overview

IdeaForge AI now supports a flexible, non-sequential product lifecycle workflow with enhanced export capabilities including content review, missing section detection, and Confluence publishing.

## Key Features

### 1. Flexible Lifecycle Phases

**No Sequential Locking**: All product lifecycle phases are now accessible without requiring previous phases to be completed. Users can:
- Jump to any phase at any time
- Work on phases in any order
- Provide ideation from external sources via chatbot
- Access phases based on their workflow needs

**How It Works**:
- Select any phase from the Product Lifecycle sidebar
- No "locked" state - all phases show as available
- Phase status still tracks completion and progress
- Previous phase data is available but not required

### 2. Ideation from Chatbot

Users can provide ideation information through chatbot interactions:
- All chatbot messages are stored in `conversation_history`
- Multi-agent orchestrator automatically includes conversation history in context
- When accessing lifecycle phases, relevant ideation is passed to agents
- Agents can reference ideation from chatbot when processing phase-specific tasks

**Example Workflow**:
1. User provides product ideation via chatbot: "I want to build a mobile app for fitness tracking"
2. User selects "Market Research" phase
3. Research agent receives ideation context from conversation history
4. Agent generates market research based on the ideation

### 3. Design Phase - Prompt Display

The Design phase now:
- **Displays prompts in UI modal** instead of auto-posting to V0/Lovable
- Shows V0 and Lovable prompts side-by-side
- Provides "Help with AI" button to refine prompts
- Requires manual action to generate prototypes
- Allows users to review and edit prompts before generating

**Workflow**:
1. Click "Help with AI" to generate prompts based on all previous phases
2. Review and refine prompts manually
3. Use "Help with AI" again to improve prompts if needed
4. Click "Generate V0 Prototype" or "Generate Lovable Prototype" when ready

### 4. Enhanced PRD Export

#### Content Review Before Export

Before exporting, the system reviews content for completeness:

**Review Endpoint**: `POST /api/products/{product_id}/review-prd`

**Response**:
```json
{
  "is_complete": false,
  "missing_sections": ["Market Research", "User Personas"],
  "recommendations": [
    "Consider adding Market Research",
    "Consider adding User Personas"
  ],
  "warnings": []
}
```

**Missing Sections Detected**:
- Market Research / Competitive Analysis
- User Personas
- Functional Requirements
- Technical Architecture
- Success Metrics
- Go-to-Market Strategy

#### Export Options

**Export Endpoint**: `POST /api/products/{product_id}/export-prd`

**Request**:
```json
{
  "format": "markdown",  // or "html"
  "override_missing": false,  // If true, export with "TO BE DEFINED" sections
  "conversation_history": []  // Optional: override conversation history
}
```

**Export Formats**:
- **Markdown**: Raw markdown file (`.md`)
- **HTML**: Styled HTML document (`.html`)

**Override Missing Content**:
- If `override_missing: true`, missing sections are marked as "TO BE DEFINED"
- Sections include guidance on what information is needed
- Related lifecycle phases are suggested
- User can return later to complete sections and regenerate PRD

#### Export Workflow

1. **Review Content** (Optional but Recommended):
   ```bash
   POST /api/products/{product_id}/review-prd
   ```
   - Check for missing sections
   - Get recommendations

2. **Handle Missing Content**:
   - **Option A**: Complete missing sections using lifecycle phases
   - **Option B**: Export with override (sections marked "TO BE DEFINED")

3. **Export PRD**:
   ```bash
   POST /api/products/{product_id}/export-prd
   {
     "format": "markdown",
     "override_missing": false
   }
   ```

4. **Return Later** (if needed):
   - Access product in application
   - Complete missing sections (e.g., Market Research phase)
   - Regenerate PRD with updated content

### 5. Confluence Publishing

Publish PRD directly to Confluence spaces:

**Publish Endpoint**: `POST /api/products/{product_id}/publish-to-confluence`

**Request**:
```json
{
  "space_id": "SPACE123",
  "title": "Product Requirements Document",
  "prd_content": "# PRD Content in Markdown...",
  "parent_page_id": "123456"  // Optional: parent page ID
}
```

**Features**:
- **Unique Naming**: Automatically appends timestamp to avoid name clashes
- **Format**: Confluence storage format (converted from Markdown)
- **Authentication**: Uses Atlassian API token from user settings
- **Space Support**: Publish to any Confluence space user has access to

**Prerequisites**:
- Atlassian email configured in Settings
- Atlassian API token configured in Settings
- Atlassian Cloud ID configured (if using REST API)

**Example**:
```bash
POST /api/products/{product_id}/publish-to-confluence
{
  "space_id": "PROD",
  "title": "Mobile Fitness App PRD",
  "prd_content": "# Product Requirements Document\n\n..."
}
```

**Response**:
```json
{
  "success": true,
  "page_id": "987654",
  "page_url": "https://your-domain.atlassian.net/wiki/spaces/PROD/pages/987654",
  "title": "Mobile Fitness App PRD - 20251126-143022",
  "space_id": "PROD"
}
```

## ICAgile PRD Structure

The exported PRD follows ICAgile industry standards with 13 comprehensive sections:

1. Executive Summary
2. Problem Statement & Opportunity
3. Product Vision & Strategy
4. User Personas & Use Cases
5. Functional Requirements
6. Non-Functional Requirements
7. Technical Architecture
8. Success Metrics & KPIs
9. Go-to-Market Strategy
10. Timeline & Milestones
11. Risks & Mitigations
12. Stakeholder Alignment
13. Appendices

## Multi-Agent Review Process

Before export, multiple agents review the content:
- **Export Agent**: Primary reviewer, checks for completeness
- **Research Agent**: Validates market research presence
- **Analysis Agent**: Checks for strategic analysis
- **Validation Agent**: Ensures quality and completeness

If content is missing:
- User is prompted in chatbot to complete missing sections
- Recommendations provided for which phases to use
- User can override and export with placeholders

## Best Practices

1. **Start with Ideation**: Use chatbot to provide initial product ideas
2. **Review Before Export**: Always review content before exporting
3. **Complete Critical Sections**: Market research and user personas are essential
4. **Iterate**: Return to product later to refine and regenerate PRD
5. **Use Override Sparingly**: Only override when absolutely necessary
6. **Publish to Confluence**: Share PRD with team via Confluence

## Troubleshooting

**Missing Sections Detected**:
- Use the recommended lifecycle phases to generate content
- Check conversation history for relevant information
- Use "Help with AI" in phase forms to generate content

**Confluence Publishing Fails**:
- Verify Atlassian credentials in Settings
- Check space ID is correct
- Ensure user has write permissions to space
- Verify Cloud ID is configured (if using REST API)

**Export Format Issues**:
- Markdown format is recommended for version control
- HTML format is better for sharing and printing
- Both formats contain the same content

