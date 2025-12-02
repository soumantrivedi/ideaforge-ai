# Agent Guides Index

This directory contains comprehensive guides for each AI agent in IdeaForge AI. Each guide explains how system context, system prompts, and user prompts work, and how response quality changes based on the information you provide.

## Core Product Management Agents

### [Research Agent Guide](./research-agent-guide.md)
Specializes in market research, competitive analysis, and industry intelligence.
- **Use Cases**: Market research phase, competitive analysis, industry trends
- **Key Features**: RAG-enabled, fast model tier, data-driven insights

### [Analysis Agent Guide](./analysis-agent-guide.md)
Specializes in strategic analysis, SWOT analysis, and feasibility studies.
- **Use Cases**: Requirements phase, strategic planning, feasibility analysis
- **Key Features**: SWOT analysis, risk assessment, gap analysis

### [Ideation Agent Guide](./ideation-agent-guide.md)
Specializes in creative brainstorming and feature generation.
- **Use Cases**: Ideation phase, brainstorming sessions, feature ideation
- **Key Features**: Design thinking, Jobs-to-be-Done, SCAMPER technique

### [Validation Agent Guide](./validation-agent-guide.md)
Specializes in quality assurance and response validation.
- **Use Cases**: Validation phase, quality checks, compliance verification
- **Key Features**: Industry standards compliance, completeness scoring

### [PRD Authoring Agent Guide](./prd-authoring-agent-guide.md)
Specializes in creating comprehensive PRD documents following industry standards.
- **Use Cases**: PRD authoring phase, requirements documentation
- **Key Features**: ICAgile compliance, INVEST user stories, Definition of Done

### [Strategy Agent Guide](./strategy-agent-guide.md)
Specializes in strategic planning, roadmap development, and go-to-market strategies.
- **Use Cases**: Strategic planning, GTM strategy, business model design
- **Key Features**: Strategic frameworks, competitive positioning, roadmap planning

### [Summary Agent Guide](./summary-agent-guide.md)
Specializes in creating comprehensive summaries from multiple conversation sessions.
- **Use Cases**: Session summaries, conversation aggregation
- **Key Features**: Multi-session synthesis, requirements extraction

### [Scoring Agent Guide](./scoring-agent-guide.md)
Specializes in evaluating and scoring product ideas across multiple dimensions.
- **Use Cases**: Product scoring, idea evaluation
- **Key Features**: Multi-dimensional scoring, success probability calculation

### [Export Agent Guide](./export-agent-guide.md)
Specializes in generating comprehensive PRD documents from all lifecycle phases.
- **Use Cases**: Document export, PRD generation
- **Key Features**: Phase synthesis, ICAgile compliance, completeness review

## Design Agents

### [V0 Agent Guide](./v0-agent-guide.md)
Specializes in generating detailed prompts for V0.dev to create React/Next.js UI components.
- **Use Cases**: Design phase, UI prototyping, V0 integration
- **Key Features**: Comprehensive prompt generation, Tailwind CSS, shadcn/ui

### [Lovable Agent Guide](./lovable-agent-guide.md)
Specializes in generating detailed prompts for Lovable.dev to create full React/Next.js applications.
- **Use Cases**: Design phase, application prototyping, Lovable integration
- **Key Features**: Complete application generation, database schema, API specification

## Integration Agents

### [Integration Agents Guide](./integration-agents-guide.md)
Specializes in accessing external systems (GitHub and Atlassian Confluence) via MCP servers.
- **GitHub Agent**: Repository access, file retrieval, documentation extraction
- **Atlassian Agent**: Confluence page access, documentation retrieval
- **Use Cases**: Code documentation, requirements integration, PRD publishing

## Guide Structure

Each guide follows a consistent structure:

1. **Overview**: Agent purpose and capabilities
2. **System Context**: RAG settings, model tier, capabilities
3. **System Prompt**: The agent's instructions and framework
4. **User Prompt**: How to structure your prompts for best results
5. **How Response Quality Changes**: Examples of low, medium, and high quality inputs/outputs
6. **Best Practices**: Tips for maximizing output quality
7. **Response Quality Indicators**: What to look for in high-quality responses
8. **Integration with Other Agents**: How agents work together
9. **Tips for Maximum Quality**: Actionable recommendations
10. **Example Workflow**: Step-by-step usage examples

## Quick Start

1. **Choose the Right Agent**: Select the agent that matches your task
2. **Read the Guide**: Understand the agent's system prompt and capabilities
3. **Structure Your Prompt**: Follow the "Excellent Prompt" examples
4. **Provide Complete Context**: Include all relevant information
5. **Iterate**: Use initial responses to refine and improve

## Common Patterns

### Low Quality Input → Generic Output
- Minimal context
- Vague requirements
- Missing details
- Generic responses

### Medium Quality Input → Structured Output
- Some context provided
- Basic requirements
- Limited details
- Structured but incomplete

### High Quality Input → Comprehensive Output
- Complete context from all phases
- Detailed requirements
- All relevant information included
- Comprehensive, actionable responses

## Best Practices Across All Agents

1. **Provide Complete Context**: Include all relevant information from phases, conversations, and form data
2. **Be Specific**: Detailed requirements lead to detailed responses
3. **Request Structure**: Ask for specific formats, frameworks, or standards
4. **Iterate**: Use initial responses to ask deeper questions
5. **Synthesize**: Combine outputs from multiple agents for comprehensive results

## Getting Help

- Review the specific agent guide for detailed information
- Check the "Example Workflow" section for step-by-step guidance
- Use the "Best Practices" section for quality tips
- Refer to "Response Quality Indicators" to evaluate outputs

## Related Documentation

- [Multi-Agent System Guide](./multi-agent-system.md)
- [Agent Development Guide](./agent-development-guide.md)
- [Product Lifecycle Guide](./product-lifecycle.md)

