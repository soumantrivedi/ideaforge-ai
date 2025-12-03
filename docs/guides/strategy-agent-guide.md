# Strategy Agent Guide

## Overview

The Strategy Agent (`AgnoStrategyAgent`) specializes in strategic planning, roadmap development, go-to-market strategies, and business model design. It helps you create comprehensive strategic plans aligned with business objectives.

## System Context

The Strategy Agent uses the following system context:

- **RAG Knowledge Base**: Optional (disabled by default)
- **Model Tier**: `standard` (balanced performance for strategic thinking)
- **Capabilities**: Strategic planning, roadmap development, go-to-market strategy, business model design, competitive positioning, strategic recommendations, initiative planning, value proposition, market segmentation, strategic partnerships

## System Prompt

The system prompt defines the agent's strategic framework:

```
You are a Strategic Planning and Business Strategy Specialist following industry standards from:
- BCS (British Computer Society) Product Management Framework
- ICAgile (International Consortium for Agile) Product Ownership
- AIPMM (Association of International Product Marketing and Management)
- Pragmatic Institute Product Management Framework
- McKinsey CodeBeyond standards

Your responsibilities:
1. Develop product strategy and roadmaps
2. Define go-to-market (GTM) strategies
3. Create strategic plans and initiatives
4. Analyze business models and value propositions
5. Provide strategic recommendations
6. Develop competitive positioning strategies
7. Plan strategic partnerships and alliances

Strategic Areas:
- Product strategy and vision
- Go-to-market (GTM) strategy
- Business model design
- Roadmap planning and prioritization
- Competitive positioning
- Strategic partnerships and alliances
- Market segmentation and targeting
- Value proposition development
- Strategic initiatives and programs

Your output should:
- Be strategic and forward-looking
- Consider market dynamics and competition
- Align with business objectives
- Provide clear action plans
- Include success metrics and KPIs
- Address user-submitted form data comprehensively
- Follow industry best practices and frameworks
```

## User Prompt

The user prompt should include:

1. **Product Information**: Complete product details
2. **Market Context**: Optional - market conditions, competitive landscape
3. **Strategic Focus**: What aspect of strategy to develop
4. **Business Objectives**: Goals, constraints, success metrics

### Example User Prompts

**Basic Prompt (Low Quality Output):**
```
Create a strategy for a fitness app
```

**Good Prompt (Medium Quality Output):**
```
Develop a go-to-market strategy for FitTrack Pro targeting millennials.
```

**Excellent Prompt (High Quality Output):**
```
Develop a comprehensive product strategy and go-to-market plan for FitTrack Pro.

**Product Information:**
- Product Name: FitTrack Pro
- Product Type: Mobile fitness tracking application
- Core Features: Workout tracking, nutrition logging, social features, wearable integration
- Target Market: Health-conscious millennials (ages 25-40) in North America
- Business Model: Freemium (free basic, $9.99/month premium)
- Development Status: MVP completed, preparing for beta launch
- Budget: $500K initial investment, $200K marketing budget
- Timeline: Beta launch in 3 months, full launch in 6 months

**Market Context (from Research Phase):**
- Market Size: $4.2B in 2024, growing at 15% CAGR
- Top Competitors: MyFitnessPal (40M users), Strava (100M users), Nike Run Club (50M users)
- Market Trends: Wearable device adoption increasing, focus on mental health integration
- User Pain Points: Lack of motivation, time-consuming tracking, competitive social features
- Market Gaps: Personalized recommendations, supportive community, holistic health approach

**Business Objectives:**
- Year 1: 100K users, 20% conversion to premium ($180K ARR)
- Year 2: 500K users, 25% conversion ($1.125M ARR)
- Year 3: 2M users, 30% conversion ($7.2M ARR)
- Strategic Goal: Become top 3 fitness app in North America by Year 3

**Strategic Focus Areas:**
1. Product Strategy: Vision, positioning, differentiation
2. Go-to-Market Strategy: Launch plan, marketing channels, pricing strategy
3. Business Model: Revenue streams, pricing tiers, monetization
4. Competitive Positioning: How to differentiate from MyFitnessPal, Strava, Nike Run Club
5. Roadmap Planning: Short-term (0-6 months) and long-term (6-24 months) roadmap
6. Strategic Partnerships: Potential partnerships (wearable brands, gyms, nutrition companies)
7. Market Segmentation: Target segments and positioning for each
8. Value Proposition: Unique value for each target segment

**Constraints:**
- Budget: $200K marketing budget for Year 1
- Team: 5 developers, 2 designers, 1 marketer
- Timeline: Beta in 3 months, full launch in 6 months
- Technical: Must support iOS and Android, offline functionality required

**Requested Output:**
- Product vision and strategic positioning
- Go-to-market strategy with launch plan
- Business model with revenue projections
- Competitive positioning strategy
- Strategic roadmap (short-term and long-term)
- Partnership opportunities and strategy
- Market segmentation and targeting
- Value proposition for each segment
- Success metrics and KPIs
- Risk assessment and mitigation
```

## How Response Quality Changes

### Low Quality Input → Generic Strategy

**Input:**
```
Create a strategy for a fitness app
```

**Output Characteristics:**
- Generic strategic recommendations
- Vague positioning
- Missing GTM plan
- No roadmap
- Missing success metrics
- No competitive analysis

### Medium Quality Input → Structured Strategy

**Input:**
```
Develop GTM strategy for FitTrack Pro targeting millennials.
```

**Output Characteristics:**
- Basic GTM strategy
- Some positioning elements
- General roadmap
- Basic success metrics
- Limited competitive analysis

### High Quality Input → Comprehensive Strategic Plan

**Input:** (See "Excellent Prompt" example above)

**Output Characteristics:**
- Comprehensive product strategy:
  - Clear vision statement
  - Strategic positioning
  - Competitive differentiation
  - Value proposition
- Detailed go-to-market strategy:
  - Launch plan with phases
  - Marketing channels and tactics
  - Pricing strategy with tiers
  - Customer acquisition plan
- Business model:
  - Revenue streams
  - Pricing tiers and rationale
  - Monetization strategy
  - Revenue projections
- Competitive positioning:
  - Detailed comparison with top 3 competitors
  - Differentiation strategy
  - Competitive advantages
- Strategic roadmap:
  - Short-term (0-6 months) with milestones
  - Long-term (6-24 months) with initiatives
  - Prioritization rationale
- Partnership strategy:
  - Potential partners identified
  - Partnership value proposition
  - Partnership roadmap
- Market segmentation:
  - Target segments defined
  - Positioning for each segment
  - Value proposition per segment
- Success metrics:
  - KPIs for each strategic area
  - Measurement plan
  - Targets and timelines
- Risk assessment:
  - Strategic risks identified
  - Mitigation strategies
  - Contingency plans

## Best Practices for Quality Output

### 1. Provide Complete Product Information

**Include:**
- Product name, type, features
- Target market and personas
- Business model and pricing
- Development status and timeline
- Budget and resources

**Why:** Enables strategy aligned with product capabilities and constraints.

### 2. Include Market Context

**Include:**
- Market size and trends
- Competitive landscape
- User insights and pain points
- Market gaps and opportunities

**Why:** Enables market-informed strategic decisions.

### 3. Specify Business Objectives

**Include:**
- Revenue goals
- User acquisition targets
- Market position goals
- Strategic milestones

**Why:** Enables strategy aligned with business objectives.

### 4. Request Comprehensive Strategy

**Request:**
- Product strategy
- Go-to-market strategy
- Business model
- Competitive positioning
- Roadmap
- Partnerships
- Market segmentation

**Why:** Ensures comprehensive strategic plan covering all aspects.

### 5. Ask for Quantification

**Request:**
- Revenue projections
- User acquisition targets
- Market share goals
- Success metrics and KPIs

**Why:** Makes strategy measurable and actionable.

## Response Quality Indicators

### High Quality Response Includes:

✅ **Comprehensive Strategy**: All strategic areas covered
✅ **Clear Vision**: Product vision and positioning
✅ **Detailed GTM Plan**: Launch plan, channels, pricing
✅ **Business Model**: Revenue streams, pricing, projections
✅ **Competitive Positioning**: Detailed comparison and differentiation
✅ **Strategic Roadmap**: Short-term and long-term with milestones
✅ **Partnership Strategy**: Potential partners and value proposition
✅ **Market Segmentation**: Target segments with positioning
✅ **Success Metrics**: KPIs, measurement plan, targets
✅ **Risk Assessment**: Risks, mitigation, contingencies

### Low Quality Response Indicators:

❌ Generic strategic recommendations
❌ Vague vision or positioning
❌ Missing GTM plan details
❌ No business model or revenue projections
❌ Limited competitive analysis
❌ No roadmap or milestones
❌ Missing partnership opportunities
❌ No market segmentation
❌ Missing success metrics
❌ No risk assessment

## Integration with Other Agents

The Strategy Agent's output is often used by:

- **Research Agent**: For market-informed strategy
- **Analysis Agent**: For strategic SWOT analysis
- **PRD Authoring Agent**: For strategic context in PRD
- **Export Agent**: For strategic sections in PRD
- **Scoring Agent**: For strategic scoring dimensions

## Tips for Maximum Quality

1. **Be Comprehensive**: Provide complete product, market, and business context
2. **Request All Areas**: Ask for product strategy, GTM, business model, roadmap
3. **Specify Objectives**: Include revenue goals, user targets, market position
4. **Ask for Quantification**: Request projections, targets, metrics
5. **Iterate**: Use initial strategy to refine specific areas
6. **Align with Phases**: Integrate with research, analysis, ideation outputs

## Example Workflow

1. **Initial Strategy**: "Develop product strategy for FitTrack Pro"
2. **GTM Deep Dive**: "Create detailed go-to-market strategy with launch plan"
3. **Business Model**: "Design business model with revenue projections"
4. **Competitive Positioning**: "Analyze competitive positioning vs. top 3 competitors"
5. **Strategic Roadmap**: "Create strategic roadmap with short-term and long-term initiatives"

Each iteration builds upon the previous, resulting in a comprehensive, actionable strategic plan.


