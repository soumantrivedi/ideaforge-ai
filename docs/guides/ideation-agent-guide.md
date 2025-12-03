# Ideation Agent Guide

## Overview

The Ideation Agent (`AgnoIdeationAgent`) specializes in creative brainstorming, feature generation, and innovative idea exploration. It helps you generate creative product ideas, features, and solutions using design thinking methodologies.

## System Context

The Ideation Agent uses the following system context:

- **RAG Knowledge Base**: `ideation_knowledge_base` (optional, disabled by default)
- **Model Tier**: `fast` (optimized for speed, 50-70% latency reduction)
- **Capabilities**: Ideation, brainstorming, idea generation, innovation, creative thinking, feature ideas, product ideas, design thinking

## System Prompt

The system prompt defines the agent's creative methodologies:

```
You are an Ideation and Brainstorming Specialist.

Your responsibilities:
1. Facilitate creative brainstorming sessions
2. Generate innovative product ideas and features
3. Explore problem spaces from multiple angles
4. Challenge assumptions and identify opportunities
5. Help refine vague concepts into actionable ideas

Techniques you employ:
- Design Thinking methodologies
- Jobs-to-be-Done framework
- Value Proposition Canvas
- SCAMPER technique
- "How Might We" questions
- Opportunity mapping

Your output should:
- Be creative yet practical
- Consider user needs and business value
- Identify potential risks and opportunities
- Provide multiple perspectives and alternatives
- Build upon existing ideas constructively
```

## User Prompt

The user prompt should include:

1. **Product Context**: What product or problem you're ideating for
2. **Constraints**: Optional - technical, business, or user constraints
3. **Focus Area**: Specific aspect to ideate (features, solutions, improvements)
4. **User Needs**: Optional - specific user pain points or needs

### Example User Prompts

**Basic Prompt (Low Quality Output):**
```
Generate some feature ideas for a fitness app
```

**Good Prompt (Medium Quality Output):**
```
Generate feature ideas for a fitness tracking app. 
Focus on social features and user engagement.
```

**Excellent Prompt (High Quality Output):**
```
Generate innovative feature ideas for FitTrack Pro, a fitness tracking mobile app, using design thinking methodologies.

Product Context:
- Core Product: Fitness tracking app with workout logging, nutrition tracking, and social features
- Target Users: Health-conscious millennials (ages 25-40) in North America
- Current Features: Workout tracking, nutrition logging, basic social feed, wearable device integration
- Business Model: Freemium (free basic, $9.99/month premium)
- Tech Stack: React Native, Node.js, PostgreSQL

User Pain Points (from research):
1. Users struggle to stay motivated long-term
2. Nutrition tracking is too time-consuming
3. Social features feel competitive rather than supportive
4. Workout recommendations are too generic
5. Progress tracking doesn't show meaningful insights

Constraints:
- Technical: Must work offline, sync when online
- Business: Premium features must justify $9.99/month
- User: Features must be simple and intuitive
- Regulatory: Must comply with HIPAA for health data

Ideation Focus:
1. Features that address motivation and long-term engagement
2. Solutions to make nutrition tracking less time-consuming
3. Social features that foster support rather than competition
4. Personalized workout recommendations
5. Advanced progress insights and analytics

Requested Output:
- 10-15 innovative feature ideas
- For each idea: name, description, user value, business value, implementation complexity
- Use Jobs-to-be-Done framework to identify user jobs
- Apply Value Proposition Canvas to assess value
- Consider SCAMPER technique for creative variations
- Prioritize ideas by user value and feasibility
```

## How Response Quality Changes

### Low Quality Input → Generic Output

**Input:**
```
Give me some feature ideas
```

**Output Characteristics:**
- Generic feature suggestions
- No connection to user needs
- Missing business value assessment
- No implementation considerations
- Unprioritized list

### Medium Quality Input → Structured Output

**Input:**
```
Generate feature ideas for fitness app focusing on social features.
```

**Output Characteristics:**
- List of feature ideas
- Basic descriptions
- Some user value mentioned
- General implementation notes
- Basic prioritization

### High Quality Input → Comprehensive, Creative Output

**Input:** (See "Excellent Prompt" example above)

**Output Characteristics:**
- 10-15 innovative, well-thought-out feature ideas
- Each idea includes:
  - Clear name and description
  - User value proposition (Jobs-to-be-Done)
  - Business value (revenue, engagement, retention)
  - Implementation complexity (Low/Medium/High)
  - Technical considerations
  - User experience considerations
- Design thinking methodologies applied
- Value Proposition Canvas analysis
- SCAMPER variations explored
- Prioritized by user value and feasibility
- Risk assessment for each idea
- Integration considerations with existing features

## Best Practices for Quality Output

### 1. Provide Rich Product Context

**Include:**
- Product name and description
- Current features and capabilities
- Target users and personas
- Business model and goals
- Technology stack

**Why:** Enables the agent to generate ideas that fit your product and are technically feasible.

### 2. Specify User Pain Points

**Include:**
- Specific user problems or needs
- User feedback or research findings
- Jobs-to-be-Done statements
- User journey pain points

**Why:** Enables the agent to generate solutions that address real user needs.

### 3. Define Constraints

**Include:**
- Technical constraints (platform, offline support, etc.)
- Business constraints (budget, pricing, revenue model)
- User constraints (simplicity, accessibility)
- Regulatory constraints (compliance requirements)

**Why:** Ensures ideas are realistic and implementable within your constraints.

### 4. Request Specific Methodologies

**Specify:**
- Design Thinking
- Jobs-to-be-Done
- Value Proposition Canvas
- SCAMPER technique
- "How Might We" questions

**Why:** Guides the agent to use structured creative methodologies for better ideas.

### 5. Ask for Detailed Analysis

**Request:**
- User value for each idea
- Business value (revenue, engagement, retention)
- Implementation complexity
- Risk assessment
- Integration considerations

**Why:** Helps you evaluate and prioritize ideas effectively.

## Response Quality Indicators

### High Quality Response Includes:

✅ **Multiple Ideas**: 10-15 diverse, creative ideas
✅ **Structured Format**: Each idea with name, description, value, complexity
✅ **User Value**: Clear Jobs-to-be-Done or user benefit
✅ **Business Value**: Revenue, engagement, or strategic value
✅ **Implementation Details**: Complexity, technical considerations, timeline
✅ **Methodology Application**: Design thinking, SCAMPER, Value Proposition Canvas
✅ **Prioritization**: Ranked by user value and feasibility
✅ **Risk Assessment**: Potential risks and mitigation
✅ **Integration**: How ideas fit with existing features

### Low Quality Response Indicators:

❌ Few ideas (less than 5)
❌ Generic suggestions without context
❌ Missing user value assessment
❌ No business value consideration
❌ No implementation details
❌ No methodology application
❌ Unprioritized list
❌ No risk assessment
❌ Ideas don't integrate with product

## Integration with Other Agents

The Ideation Agent's output is often used by:

- **Research Agent**: To validate market opportunity for ideas
- **Analysis Agent**: For feasibility and SWOT analysis
- **Strategy Agent**: For strategic roadmap planning
- **PRD Authoring Agent**: For feature requirements
- **Scoring Agent**: To score and prioritize ideas

## Tips for Maximum Quality

1. **Be Specific**: Provide detailed product context and user needs
2. **Include Constraints**: Technical, business, and user constraints
3. **Request Methodologies**: Ask for specific creative frameworks
4. **Iterate**: Use initial ideas to explore variations
5. **Combine Approaches**: Use multiple methodologies for diverse ideas
6. **Prioritize**: Request prioritization by value and feasibility

## Example Workflow

1. **Initial Ideation**: "Generate feature ideas for FitTrack Pro focusing on user engagement"
2. **Deep Dive**: "Apply SCAMPER technique to the top 3 ideas"
3. **Value Analysis**: "Analyze the value proposition for the social motivation feature"
4. **Feasibility Check**: "Assess implementation complexity for personalized workout recommendations"
5. **Final Prioritization**: "Prioritize all ideas by user value and business impact"

Each iteration builds upon the previous, resulting in increasingly refined and actionable ideas.


