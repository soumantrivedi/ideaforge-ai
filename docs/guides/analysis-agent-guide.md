# Analysis Agent Guide

## Overview

The Analysis Agent (`AgnoAnalysisAgent`) specializes in strategic analysis, SWOT analysis, requirements analysis, and feasibility studies. It helps you evaluate products, strategies, and opportunities from multiple analytical perspectives.

## System Context

The Analysis Agent uses the following system context:

- **RAG Knowledge Base**: `analysis_knowledge_base` (optional, disabled by default)
- **Model Tier**: `fast` (optimized for speed, 50-70% latency reduction)
- **Capabilities**: Requirements analysis, SWOT analysis, feasibility analysis, risk analysis, cost-benefit analysis, performance analysis, gap analysis, strategic analysis

## System Prompt

The system prompt defines the agent's role and analytical framework:

```
You are a Strategic Analysis Specialist.

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

Your output should:
- Be structured and comprehensive
- Identify key insights and patterns
- Highlight risks and opportunities
- Provide actionable recommendations
- Include quantitative assessments when possible
```

## User Prompt

The user prompt should include:

1. **Product/Strategy Information**: What you want analyzed
2. **Market Context**: Optional - market conditions, competitive landscape
3. **Analysis Type**: SWOT, requirements, feasibility, etc.
4. **Specific Questions**: What aspects to focus on

### Example User Prompts

**Basic Prompt (Low Quality Output):**
```
Analyze this product idea: A fitness app
```

**Good Prompt (Medium Quality Output):**
```
Perform a SWOT analysis for a fitness tracking mobile app. 
Include market context and competitive positioning.
```

**Excellent Prompt (High Quality Output):**
```
Perform a comprehensive SWOT analysis for a fitness tracking mobile app with the following details:

Product Information:
- Name: FitTrack Pro
- Core Features: Workout tracking, nutrition logging, social features, wearable integration
- Target Market: Health-conscious millennials (ages 25-40) in North America
- Business Model: Freemium (free basic, $9.99/month premium)
- Development Status: MVP completed, preparing for beta launch

Market Context:
- Market Size: $4.2B in 2024, growing at 15% CAGR
- Top Competitors: MyFitnessPal, Strava, Nike Run Club
- Market Trends: Wearable device adoption increasing, focus on mental health integration
- Regulatory: HIPAA compliance required for health data

Technical Context:
- Tech Stack: React Native, Node.js, PostgreSQL
- Team: 5 developers, 2 designers
- Infrastructure: AWS, scalable architecture
- Integration: Apple HealthKit, Google Fit, Fitbit API

Analysis Focus:
1. Internal Strengths and Weaknesses (team, technology, product)
2. External Opportunities and Threats (market, competition, regulations)
3. Risk assessment with mitigation strategies
4. Cost-benefit analysis for key features
5. Gap analysis: What's missing vs. competitors
6. Strategic recommendations prioritized by impact

Please provide:
- Detailed SWOT matrix with specific examples
- Risk assessment with probability and impact
- Cost-benefit analysis for premium features
- Gap analysis comparing to top 3 competitors
- Prioritized strategic recommendations
```

## How Response Quality Changes

### Low Quality Input → Generic Output

**Input:**
```
Do a SWOT analysis for a fitness app
```

**Output Characteristics:**
- Generic SWOT categories
- Vague strengths/weaknesses
- No specific examples
- Missing quantitative data
- No actionable recommendations

### Medium Quality Input → Structured Output

**Input:**
```
SWOT analysis for fitness app targeting millennials. Include competitive analysis.
```

**Output Characteristics:**
- Structured SWOT matrix
- Some specific examples
- Basic competitive comparison
- General recommendations
- Limited quantitative analysis

### High Quality Input → Comprehensive, Actionable Output

**Input:** (See "Excellent Prompt" example above)

**Output Characteristics:**
- Detailed SWOT matrix with specific, evidence-based points
- Quantitative risk assessment (probability × impact)
- Cost-benefit analysis with ROI calculations
- Detailed gap analysis with feature comparisons
- Prioritized strategic recommendations with implementation roadmap
- Technical feasibility assessment
- Market opportunity quantification
- Risk mitigation strategies with timelines
- Performance benchmarks and scalability considerations

## Best Practices for Quality Output

### 1. Provide Complete Product Information

**Include:**
- Product name and description
- Core features and value propositions
- Target market and user personas
- Business model and pricing
- Development status and timeline

**Why:** Enables comprehensive analysis of internal factors (strengths/weaknesses).

### 2. Include Market Context

**Include:**
- Market size and growth trends
- Competitive landscape
- Market trends and dynamics
- Regulatory environment

**Why:** Enables analysis of external factors (opportunities/threats).

### 3. Specify Technical Context

**Include:**
- Technology stack
- Team capabilities
- Infrastructure and scalability
- Integration requirements

**Why:** Enables technical feasibility and architecture analysis.

### 4. Request Specific Analysis Types

**Specify:**
- SWOT analysis
- Requirements analysis
- Feasibility study
- Risk assessment
- Cost-benefit analysis
- Gap analysis

**Why:** Guides the agent to provide the specific type of analysis you need.

### 5. Ask for Quantitative Assessments

**Request:**
- Risk scores (probability × impact)
- Cost-benefit ratios
- Performance metrics
- Market opportunity size
- ROI calculations

**Why:** Quantitative data makes analysis more actionable and comparable.

## Response Quality Indicators

### High Quality Response Includes:

✅ **Structured Analysis**: Clear framework (SWOT, requirements, etc.)
✅ **Specific Examples**: Concrete examples, not generic statements
✅ **Quantitative Data**: Numbers, percentages, scores, metrics
✅ **Risk Assessment**: Probability, impact, mitigation strategies
✅ **Gap Analysis**: Comparison with competitors or benchmarks
✅ **Prioritized Recommendations**: Ranked by impact and feasibility
✅ **Actionable Insights**: Specific next steps, not vague suggestions
✅ **Evidence-Based**: References to data, research, or examples

### Low Quality Response Indicators:

❌ Generic categories without specifics
❌ Vague statements without examples
❌ Missing quantitative data
❌ No risk assessment
❌ No competitive comparison
❌ Unprioritized recommendations
❌ Vague suggestions without next steps
❌ No evidence or data to support conclusions

## Integration with Other Agents

The Analysis Agent's output is often used by:

- **Research Agent**: To identify research gaps
- **Strategy Agent**: For strategic planning
- **PRD Authoring Agent**: For requirements documentation
- **Validation Agent**: To validate analysis completeness
- **Scoring Agent**: For scoring dimensions

## Tips for Maximum Quality

1. **Be Comprehensive**: Provide all relevant context (product, market, technical)
2. **Request Specific Analysis**: Specify SWOT, requirements, feasibility, etc.
3. **Ask for Quantification**: Request scores, metrics, and calculations
4. **Iterate**: Use initial analysis to ask deeper questions
5. **Compare**: Request comparisons with competitors or benchmarks
6. **Prioritize**: Ask for prioritized recommendations based on impact

## Example Workflow

1. **Initial Analysis**: "Perform a SWOT analysis for FitTrack Pro"
2. **Deep Dive**: "Analyze the technical risks in detail with mitigation strategies"
3. **Competitive Analysis**: "Compare our features with MyFitnessPal and Strava"
4. **Cost-Benefit**: "Analyze the ROI of premium features"
5. **Strategic Recommendations**: "Prioritize recommendations by impact and feasibility"

Each iteration builds upon the previous, resulting in increasingly comprehensive and actionable analysis.


