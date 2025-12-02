# Integration Agents Guide

## Overview

The Integration Agents (`AgnoGitHubAgent` and `AgnoAtlassianAgent`) specialize in accessing external systems (GitHub and Atlassian Confluence) via MCP (Model Context Protocol) servers to retrieve documentation, code, and content for product development.

## System Context

### GitHub Agent

- **RAG Knowledge Base**: `github_knowledge_base` (optional, disabled by default)
- **Model Tier**: `fast` (optimized for speed)
- **Capabilities**: GitHub repository access, file content retrieval, repository listing, documentation extraction, code analysis, GitHub URL processing

### Atlassian Agent

- **RAG Knowledge Base**: `confluence_knowledge_base` (enabled by default)
- **Model Tier**: `fast` (optimized for speed)
- **Capabilities**: Confluence page access, Confluence space navigation, page content retrieval, Confluence search, documentation extraction, Confluence URL processing

## System Prompts

### GitHub Agent System Prompt

```
You are a GitHub Integration Specialist. Your primary function is to:
1. Access GitHub repositories and files via the GitHub MCP server
2. Retrieve file content from GitHub repositories
3. List repositories and their contents
4. Search for specific files or content in repositories
5. Extract and process documentation from GitHub URLs

When given a GitHub URL, extract the repository name and file path, then use the MCP server to retrieve the content.
Always provide clear, structured responses with source information.
```

### Atlassian Agent System Prompt

```
You are an Atlassian Confluence Integration Specialist. Your primary function is to:
1. Access Confluence spaces and pages via the Atlassian MCP server
2. Retrieve page content from Confluence
3. Search for content in Confluence
4. Extract and process documentation from Confluence URLs
5. Navigate Confluence page hierarchies

When given a Confluence URL or page ID, use the MCP server to retrieve the content.
Always provide clear, structured responses with source information.
```

## User Prompt

The user prompt should include:

1. **URL or Identifier**: GitHub URL or Confluence page ID/URL
2. **User ID**: For authentication
3. **Product ID**: Optional - for context
4. **Specific Request**: What content to retrieve or search for

### Example User Prompts

**Basic Prompt (Low Quality Output):**
```
Get content from this GitHub URL: https://github.com/owner/repo
```

**Good Prompt (Medium Quality Output):**
```
Retrieve the README.md file from https://github.com/owner/repo/blob/main/README.md
```

**Excellent Prompt (High Quality Output):**

**For GitHub Agent:**
```
Retrieve and analyze documentation from GitHub for FitTrack Pro integration.

**GitHub URL:**
https://github.com/fitbit/web-api/blob/main/docs/authentication.md

**Request:**
1. Retrieve the authentication documentation file
2. Extract key authentication patterns and requirements
3. Identify API endpoints and authentication flows
4. Extract code examples and integration patterns
5. Summarize integration requirements for FitTrack Pro

**Context:**
- Product: FitTrack Pro - Mobile fitness tracking app
- Integration Need: Fitbit API integration for wearable device data
- Use Case: Sync workout data from Fitbit devices to FitTrack Pro
- Technical Stack: React Native, Node.js, PostgreSQL

**Expected Output:**
- Complete file content
- Key authentication patterns extracted
- API endpoints and methods identified
- Code examples and integration snippets
- Integration requirements summary
- Actionable next steps for implementation
```

**For Atlassian Agent:**
```
Retrieve and analyze Confluence documentation for FitTrack Pro requirements.

**Confluence Page:**
https://company.atlassian.net/wiki/spaces/PROD/pages/123456789/FitTrack+Pro+Requirements

**Request:**
1. Retrieve the complete page content
2. Extract product requirements and specifications
3. Identify user stories and acceptance criteria
4. Extract technical requirements and constraints
5. Summarize key requirements for PRD integration

**Context:**
- Product: FitTrack Pro - Mobile fitness tracking app
- Purpose: Integrate Confluence requirements into PRD
- Phase: PRD Authoring phase
- Need: Complete requirements documentation

**Expected Output:**
- Complete page content in Markdown format
- Requirements extracted and structured
- User stories and acceptance criteria identified
- Technical requirements summarized
- Integration recommendations for PRD
```

## How Response Quality Changes

### Low Quality Input → Basic Retrieval

**Input:**
```
Get content from: [URL]
```

**Output Characteristics:**
- Basic content retrieval
- No analysis or extraction
- Missing context
- No structured output
- Not actionable

### Medium Quality Input → Structured Retrieval

**Input:**
```
Retrieve README.md and extract key information.
```

**Output Characteristics:**
- Content retrieved
- Some key information extracted
- Basic structure
- Limited analysis
- Partially actionable

### High Quality Input → Comprehensive Analysis

**Input:** (See "Excellent Prompt" examples above)

**Output Characteristics:**
- Complete Content Retrieval:
  - Full file/page content
  - All sections and details
  - Code examples included
  - Metadata and context
- Detailed Analysis:
  - Key patterns extracted
  - Requirements identified
  - Technical specifications summarized
  - Integration points identified
- Structured Output:
  - Requirements organized
  - User stories extracted
  - Acceptance criteria listed
  - Technical constraints noted
- Actionable Recommendations:
  - Integration steps
  - Implementation guidance
  - Next steps prioritized
  - Best practices identified
- Context Integration:
  - Aligned with product context
  - Technical stack considered
  - Use cases addressed
  - Phase requirements met

## Best Practices for Quality Output

### 1. Provide Complete URLs

**Include:**
- Full GitHub URL with file path
- Complete Confluence URL or page ID
- Branch or version if relevant

**Why:** Enables accurate content retrieval.

### 2. Specify Analysis Requirements

**Request:**
- What to extract (requirements, code, patterns)
- How to structure output
- What analysis to perform

**Why:** Guides agent to provide relevant, structured analysis.

### 3. Include Product Context

**Include:**
- Product name and description
- Integration needs
- Technical stack
- Use cases

**Why:** Enables context-aware analysis and recommendations.

### 4. Request Structured Output

**Request:**
- Requirements organized by category
- Code examples extracted
- Integration steps outlined
- Next steps prioritized

**Why:** Makes output actionable and useful.

### 5. Ask for Integration Guidance

**Request:**
- How to integrate with product
- Implementation steps
- Best practices
- Potential issues

**Why:** Provides actionable integration guidance.

## Response Quality Indicators

### High Quality Response Includes:

✅ **Complete Content**: Full file/page content retrieved
✅ **Structured Analysis**: Requirements, patterns, code extracted
✅ **Context Integration**: Aligned with product and technical stack
✅ **Actionable Recommendations**: Integration steps and next steps
✅ **Code Examples**: Relevant code snippets and patterns
✅ **Best Practices**: Industry standards and recommendations
✅ **Error Handling**: Potential issues and solutions
✅ **Source Information**: URLs, page IDs, file paths referenced

### Low Quality Response Indicators:

❌ Incomplete content retrieval
❌ No analysis or extraction
❌ Missing structure
❌ No context integration
❌ Vague recommendations
❌ Missing code examples
❌ No best practices
❌ No source information

## Integration with Other Agents

The Integration Agents' output is often used by:

- **Research Agent**: For technical documentation and API research
- **Analysis Agent**: For technical feasibility analysis
- **PRD Authoring Agent**: For requirements integration
- **Export Agent**: For documentation in PRD
- **V0 Agent**: For technical specifications in design prompts

## Tips for Maximum Quality

1. **Provide Complete URLs**: Include full paths and identifiers
2. **Specify Analysis**: Request what to extract and how to structure
3. **Include Context**: Add product context and integration needs
4. **Request Structure**: Ask for organized, actionable output
5. **Iterate**: Use initial retrieval to request deeper analysis
6. **Validate**: Check retrieved content and request clarifications

## Example Workflow

1. **Initial Retrieval**: "Retrieve README.md from GitHub repository"
2. **Analysis**: "Extract API endpoints and authentication requirements"
3. **Integration**: "How to integrate this API with FitTrack Pro?"
4. **Code Examples**: "Extract code examples for authentication flow"
5. **Final Summary**: "Create integration guide with implementation steps"

Each iteration provides increasingly detailed and actionable integration guidance.

