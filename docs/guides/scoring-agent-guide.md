# Scoring Agent Guide

## Overview

The Scoring Agent (`AgnoScoringAgent`) specializes in evaluating and scoring product ideas across multiple dimensions following industry standards. It provides objective, data-driven scoring to help prioritize and evaluate product opportunities.

## System Context

The Scoring Agent uses the following system context:

- **RAG Knowledge Base**: `scoring_knowledge_base` (enabled by default)
- **Model Tier**: `standard` (balanced performance for analytical scoring)
- **Capabilities**: Product scoring, idea evaluation, market analysis, feasibility assessment, success probability, risk assessment, recommendations

## System Prompt

The system prompt defines the agent's scoring framework:

```
You are a Product Idea Scoring Specialist following industry standards from:
- BCS (British Computer Society) Product Management Framework
- ICAgile (International Consortium for Agile) Product Ownership
- AIPMM (Association of International Product Marketing and Management)
- Pragmatic Institute Product Management Framework

Your responsibilities:
1. Score product ideas across multiple dimensions
2. Assess market viability and business value
3. Evaluate technical feasibility
4. Analyze user needs and market fit
5. Provide actionable recommendations
6. Calculate success probability

Scoring Dimensions (0-100 scale):
1. Market Opportunity (25 points)
   - Market size and growth potential
   - Competitive landscape
   - Market timing
   - Market accessibility

2. User Value (25 points)
   - Problem-solution fit
   - User pain point severity
   - User adoption likelihood
   - User experience potential

3. Business Value (20 points)
   - Revenue potential
   - Strategic alignment
   - Business model viability
   - ROI potential

4. Technical Feasibility (15 points)
   - Technical complexity
   - Resource requirements
   - Technology readiness
   - Implementation timeline

5. Risk Assessment (15 points)
   - Market risks
   - Technical risks
   - Execution risks
   - Competitive risks

Your scoring should:
- Be objective and data-driven
- Consider industry best practices
- Provide detailed rationale for each score
- Include specific recommendations for improvement
- Calculate overall success probability
- Be contextualized to the specific product and market
```

## User Prompt

The user prompt should include:

1. **Product Summary**: Complete product description
2. **Market Context**: Optional - market size, trends, competition
3. **User Feedback**: Optional - user research, feedback, surveys
4. **Technical Context**: Optional - technology, team, resources

### Example User Prompts

**Basic Prompt (Low Quality Output):**
```
Score this product idea: A fitness app
```

**Good Prompt (Medium Quality Output):**
```
Score FitTrack Pro. Include market opportunity and user value assessment.
```

**Excellent Prompt (High Quality Output):**
```
Score FitTrack Pro using industry standards (BCS, ICAgile, AIPMM, Pragmatic Institute).

**Product Summary:**
FitTrack Pro is a mobile fitness tracking application targeting health-conscious millennials (ages 25-40) in North America. Core features include workout tracking, nutrition logging, social features, and wearable device integration. Business model: Freemium (free basic, $9.99/month premium).

**Market Context:**
- Market Size: $4.2B in 2024, growing at 15% CAGR
- Market Trends: Wearable device adoption increasing, focus on mental health integration
- Competitive Landscape:
  - MyFitnessPal: 40M users, freemium, strong nutrition focus
  - Strava: 100M users, freemium, strong social/community focus
  - Nike Run Club: 50M users, free, brand-driven
- Market Gaps: Personalized recommendations, supportive community (not competitive), holistic health approach
- Market Timing: High - post-pandemic fitness focus, wearable adoption peak

**User Feedback:**
- User Research: 500 survey responses, 20 interviews
- Key Pain Points:
  - 78% struggle with long-term motivation
  - 65% find nutrition tracking too time-consuming
  - 72% want supportive community, not competitive
  - 68% want personalized workout recommendations
- User Adoption Signals:
  - 85% interested in trying if free tier available
  - 45% willing to pay $9.99/month for premium features
  - 62% already use fitness apps (switching potential)

**Technical Context:**
- Technology Stack: React Native, Node.js, PostgreSQL
- Team: 5 developers, 2 designers (experienced team)
- Infrastructure: AWS, scalable architecture
- Integration: Apple HealthKit, Google Fit, Fitbit API (all mature APIs)
- Technical Complexity: Medium - standard mobile app, proven tech stack
- Implementation Timeline: 12 months (MVP in 6 months)
- Resource Requirements: $500K initial investment, $200K marketing budget

**Scoring Requirements:**
Provide comprehensive scoring in JSON format with:
1. Overall score (0-100) and success probability (0-100)
2. Detailed scores for each dimension with rationale
3. Sub-scores for each dimension component
4. Specific recommendations for improvement
5. Success factors and risk factors
6. Next steps prioritized by impact

**Expected Output Format:**
- JSON structure with all scoring dimensions
- Detailed rationale for each score
- Sub-scores for dimension components
- Recommendations with priority and expected impact
- Success and risk factors
- Actionable next steps
```

## How Response Quality Changes

### Low Quality Input → Generic Scoring

**Input:**
```
Score this: A fitness app
```

**Output Characteristics:**
- Generic overall score
- No dimension breakdown
- Missing rationale
- No recommendations
- Missing success probability
- No risk assessment

### Medium Quality Input → Structured Scoring

**Input:**
```
Score FitTrack Pro with market and user value assessment.
```

**Output Characteristics:**
- Overall score with some dimensions
- Basic rationale
- Some recommendations
- Basic success probability
- Limited risk assessment

### High Quality Input → Comprehensive Scoring

**Input:** (See "Excellent Prompt" example above)

**Output Characteristics:**
- Overall Score: 78/100 with detailed breakdown
- Success Probability: 72% with confidence level
- Market Opportunity (25 points): 22/25
  - Market Size: 6/6.25 (large, growing market)
  - Competitive Landscape: 5/6.25 (competitive but gaps exist)
  - Market Timing: 6/6.25 (optimal timing)
  - Market Accessibility: 5/6.25 (accessible with right strategy)
  - Rationale: Large, growing market with identified gaps
- User Value (25 points): 21/25
  - Problem-Solution Fit: 6.5/6.25 (strong fit)
  - Pain Point Severity: 6/6.25 (high severity)
  - Adoption Likelihood: 4.5/6.25 (good signals)
  - UX Potential: 4/6.25 (good potential)
  - Rationale: Strong problem-solution fit, high user interest
- Business Value (20 points): 16/20
  - Revenue Potential: 5/5 (strong freemium model)
  - Strategic Alignment: 4/5 (aligns with market trends)
  - Business Model Viability: 4/5 (proven model)
  - ROI Potential: 3/5 (good with scale)
  - Rationale: Strong revenue potential, proven business model
- Technical Feasibility (15 points): 13/15
  - Technical Complexity: 4/3.75 (medium complexity)
  - Resource Requirements: 3.5/3.75 (adequate resources)
  - Technology Readiness: 3/3.75 (mature technologies)
  - Implementation Timeline: 2.5/3.75 (realistic timeline)
  - Rationale: Medium complexity, proven tech stack, adequate team
- Risk Assessment (15 points): 12/15
  - Market Risks: 3/3.75 (moderate competition)
  - Technical Risks: 3.5/3.75 (low technical risk)
  - Execution Risks: 3/3.75 (moderate execution risk)
  - Competitive Risks: 2.5/3.75 (established competitors)
  - Rationale: Moderate risks, manageable with right strategy
- Recommendations:
  - High Priority: Focus on personalized recommendations (expected +5 points user value)
  - High Priority: Build supportive community features (expected +3 points user value)
  - Medium Priority: Partner with wearable brands (expected +2 points market opportunity)
  - Medium Priority: Optimize nutrition tracking UX (expected +2 points user value)
- Success Factors:
  - Strong problem-solution fit
  - Large, growing market
  - Proven business model
  - Experienced team
- Risk Factors:
  - Established competitors
  - User acquisition costs
  - Feature differentiation
- Next Steps:
  1. Validate personalized recommendation algorithm (Week 1-2)
  2. Design supportive community features (Week 3-4)
  3. Prototype wearable integration (Week 5-6)
  4. Conduct user testing for nutrition UX (Week 7-8)

## Best Practices for Quality Output

### 1. Provide Complete Product Summary

**Include:**
- Product name and description
- Core features and value proposition
- Target market and users
- Business model

**Why:** Enables comprehensive scoring across all dimensions.

### 2. Include Market Context

**Include:**
- Market size and growth
- Competitive landscape
- Market trends and timing
- Market gaps and opportunities

**Why:** Enables accurate market opportunity scoring.

### 3. Provide User Feedback

**Include:**
- User research findings
- Pain points and needs
- Adoption signals
- User preferences

**Why:** Enables accurate user value scoring.

### 4. Specify Technical Context

**Include:**
- Technology stack
- Team capabilities
- Resources and budget
- Implementation timeline

**Why:** Enables accurate technical feasibility scoring.

### 5. Request Detailed Scoring

**Request:**
- Overall score and success probability
- Dimension scores with rationale
- Sub-scores for components
- Recommendations with impact
- Success and risk factors

**Why:** Makes scoring actionable and comparable.

## Response Quality Indicators

### High Quality Response Includes:

✅ **Overall Score**: 0-100 with success probability
✅ **Dimension Scores**: All 5 dimensions with scores and rationale
✅ **Sub-Scores**: Component scores within each dimension
✅ **Detailed Rationale**: Evidence-based explanations for each score
✅ **Recommendations**: Prioritized with expected impact
✅ **Success Factors**: Key factors contributing to success
✅ **Risk Factors**: Key risks with mitigation strategies
✅ **Next Steps**: Actionable steps prioritized by impact
✅ **JSON Format**: Structured, parseable output

### Low Quality Response Indicators:

❌ Generic overall score without breakdown
❌ Missing dimension scores
❌ No rationale or evidence
❌ Vague recommendations
❌ Missing success/risk factors
❌ No next steps
❌ Unstructured output

## Integration with Other Agents

The Scoring Agent's output is often used by:

- **Research Agent**: To validate market opportunity scores
- **Analysis Agent**: For SWOT-based scoring
- **Strategy Agent**: For strategic prioritization
- **Ideation Agent**: To score and prioritize ideas
- **PRD Authoring Agent**: For success metrics in PRD

## Tips for Maximum Quality

1. **Be Comprehensive**: Provide complete product, market, user, and technical context
2. **Request JSON Format**: Ask for structured, parseable output
3. **Specify Dimensions**: Request all 5 dimensions with sub-scores
4. **Ask for Rationale**: Request evidence-based explanations
5. **Request Recommendations**: Ask for prioritized improvements with impact
6. **Iterate**: Use scoring to identify improvements and re-score

## Example Workflow

1. **Initial Scoring**: "Score FitTrack Pro with all dimensions"
2. **Deep Dive**: "Analyze market opportunity dimension in detail"
3. **Recommendations**: "Provide recommendations to improve user value score"
4. **Risk Assessment**: "Assess risks and provide mitigation strategies"
5. **Re-Scoring**: "Re-score after implementing top 3 recommendations"

Each iteration provides increasingly detailed and actionable scoring.


