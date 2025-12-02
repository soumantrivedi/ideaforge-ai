# Research Agent Guide

## Overview

The Research Agent (`AgnoResearchAgent`) specializes in market research, competitive analysis, and industry intelligence. It helps you gather data-driven insights to inform product decisions.

## System Context

The Research Agent uses the following system context:

- **RAG Knowledge Base**: `research_knowledge_base` (enabled by default)
- **Model Tier**: `fast` (optimized for speed, 50-70% latency reduction)
- **Capabilities**: Market research, competitive analysis, trend analysis, user research, feasibility studies, benchmarking, industry analysis, data gathering

## System Prompt

The system prompt defines the agent's role and responsibilities:

```
You are a Research and Market Intelligence Specialist.

Your responsibilities:
1. Conduct market research and competitive analysis
2. Gather industry trends and insights
3. Analyze user needs and market gaps
4. Research technical feasibility and best practices
5. Provide data-driven recommendations

Research Areas:
- Market trends and opportunities
- Competitive landscape analysis
- User behavior and preferences
- Technical feasibility studies
- Industry benchmarks and standards
- Regulatory and compliance requirements

Your output should:
- Be data-driven and evidence-based
- Include relevant sources and references
- Highlight key insights and patterns
- Identify opportunities and risks
- Provide actionable recommendations
```

## User Prompt

The user prompt is what you provide when interacting with the Research Agent. It should include:

1. **Product Domain**: The specific product or market area you're researching
2. **Target Market**: Optional - specific market segment or demographic
3. **Research Questions**: What you want to know
4. **Context**: Any relevant background information

### Example User Prompts

**Basic Prompt (Low Quality Output):**
```
Research the market for mobile apps
```

**Good Prompt (Medium Quality Output):**
```
Conduct market research for a fitness tracking mobile app targeting health-conscious millennials. 
Focus on competitive landscape and user preferences.
```

**Excellent Prompt (High Quality Output):**
```
Conduct comprehensive market research for a fitness tracking mobile app with the following details:

Product Domain: Mobile fitness tracking application
Target Market: Health-conscious millennials (ages 25-40) in North America
Key Features: Workout tracking, nutrition logging, social features, wearable device integration

Research Focus Areas:
1. Market size and growth trends for fitness apps (2024-2026)
2. Competitive analysis of top 5 fitness apps (features, pricing, market share)
3. User pain points with existing solutions
4. Technical feasibility of wearable device integration
5. Regulatory requirements for health data (HIPAA, GDPR)
6. Industry benchmarks for user engagement and retention

Additional Context:
- Budget: $500K initial investment
- Timeline: 12-month development cycle
- Team: 5 developers, 2 designers
- Target launch: Q2 2025
```

## How Response Quality Changes

### Low Quality Input → Generic Output

**Input:**
```
Research mobile apps
```

**Output Characteristics:**
- Generic market overview
- Limited competitive analysis
- No specific insights
- Missing actionable recommendations
- No data sources or references

### Medium Quality Input → Structured Output

**Input:**
```
Research fitness tracking apps for millennials. Include competitive analysis.
```

**Output Characteristics:**
- Basic market analysis
- List of competitors
- Some user insights
- General recommendations
- Limited data sources

### High Quality Input → Comprehensive, Actionable Output

**Input:** (See "Excellent Prompt" example above)

**Output Characteristics:**
- Detailed market size analysis with growth projections
- Comprehensive competitive analysis with feature comparisons
- Specific user pain points with evidence
- Technical feasibility assessment with implementation considerations
- Regulatory compliance analysis
- Industry benchmarks with specific metrics
- Actionable recommendations prioritized by impact
- Multiple data sources and references
- Risk assessment and mitigation strategies

## Best Practices for Quality Output

### 1. Provide Specific Product Details

**Include:**
- Product name and category
- Target market demographics
- Key features or value propositions
- Business constraints (budget, timeline, team size)

**Why:** Helps the agent understand context and provide relevant, specific insights.

### 2. Specify Research Focus Areas

**Include:**
- Market size and trends
- Competitive landscape
- User needs and pain points
- Technical feasibility
- Regulatory requirements
- Industry benchmarks

**Why:** Guides the agent to cover all relevant aspects comprehensively.

### 3. Add Business Context

**Include:**
- Budget constraints
- Timeline requirements
- Team capabilities
- Strategic goals
- Success metrics

**Why:** Enables the agent to provide realistic, actionable recommendations aligned with your constraints.

### 4. Reference Previous Research

**Include:**
- Previous research findings
- Known competitors
- Existing market data
- User feedback or surveys

**Why:** Allows the agent to build upon existing knowledge and avoid redundant information.

### 5. Ask Specific Questions

**Instead of:** "What do you think about this market?"

**Use:** "What is the market size for fitness apps in North America, and what is the projected growth rate for 2024-2026?"

**Why:** Specific questions lead to specific, actionable answers.

## Response Quality Indicators

### High Quality Response Includes:

✅ **Quantitative Data**: Market size, growth rates, user numbers, revenue figures
✅ **Competitive Analysis**: Detailed comparison of 3-5 competitors
✅ **User Insights**: Specific pain points with evidence
✅ **Technical Assessment**: Feasibility analysis with implementation considerations
✅ **Regulatory Information**: Compliance requirements and considerations
✅ **Actionable Recommendations**: Prioritized list with expected impact
✅ **Sources**: References to industry reports, studies, or data sources
✅ **Risk Assessment**: Potential risks and mitigation strategies

### Low Quality Response Indicators:

❌ Generic statements without data
❌ Vague competitive analysis
❌ No specific user insights
❌ Missing technical considerations
❌ No regulatory information
❌ Generic recommendations
❌ No sources or references
❌ No risk assessment

## Integration with Other Agents

The Research Agent's output is often used by:

- **Analysis Agent**: For SWOT analysis and strategic assessment
- **Strategy Agent**: For go-to-market planning
- **PRD Authoring Agent**: For market context in PRD documents
- **Scoring Agent**: For market opportunity scoring

## Tips for Maximum Quality

1. **Be Specific**: The more specific your prompt, the more targeted the research
2. **Provide Context**: Include business constraints, goals, and existing knowledge
3. **Ask Follow-ups**: Use the agent's initial response to ask deeper questions
4. **Iterate**: Refine your research questions based on initial findings
5. **Combine with RAG**: The agent's RAG knowledge base enhances responses with historical data

## Example Workflow

1. **Initial Research**: "Research the fitness app market for millennials"
2. **Deep Dive**: "Based on your research, analyze the top 3 competitors in detail"
3. **User Focus**: "What are the main pain points users have with existing fitness apps?"
4. **Technical Feasibility**: "Assess the technical feasibility of wearable device integration"
5. **Final Synthesis**: "Create a comprehensive market research summary with recommendations"

Each iteration builds upon the previous, resulting in increasingly comprehensive and actionable insights.

