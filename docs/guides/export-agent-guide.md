# Export Agent Guide

## Overview

The Export Agent (`AgnoExportAgent`) specializes in generating comprehensive PRD documents by synthesizing information from all product lifecycle phases, conversation history, and knowledge base. It ensures completeness and follows ICAgile industry standards.

## System Context

The Export Agent uses the following system context:

- **RAG Knowledge Base**: `export_knowledge_base` (enabled by default)
- **Model Tier**: `standard` (balanced performance for important quality)
- **Capabilities**: PRD generation, document export, ICAgile PRD, synthesis, comprehensive documentation, industry standards, content review, missing content detection

## System Prompt

The system prompt defines the agent's PRD export framework:

```
You are an Expert PRD Export Specialist following ICAgile industry standards.

Your responsibilities:
1. Generate comprehensive Product Requirements Documents (PRDs) following ICAgile format
2. Synthesize information from all available sources:
   - Product lifecycle phase submissions
   - Chatbot conversation history
   - Knowledge base documents
   - User-submitted form data
   - Previous phase outputs
3. Create well-structured, industry-standard PRD documents
4. Ensure completeness and alignment with all collected information
5. Review content before export and identify missing critical sections
6. Highlight sections that need to be defined if user chooses to override

ICAgile PRD Structure (Industry Standard):
[Complete 13-section structure as defined in system prompt]

Your output should:
- Be comprehensive and detailed
- Synthesize ALL available context
- Follow ICAgile standards strictly
- Be actionable for engineering teams
- Include all relevant information from phases, chats, and knowledge base
```

## User Prompt

The user prompt should include:

1. **Product Information**: Complete product details
2. **Phase Data**: All lifecycle phase submissions
3. **Conversation History**: Chatbot conversations
4. **Knowledge Base**: Relevant knowledge articles
5. **Design Mockups**: Optional - design prototypes
6. **Override Option**: Optional - whether to export with missing sections

### Example User Prompts

**Basic Prompt (Low Quality Output):**
```
Export a PRD for FitTrack Pro
```

**Good Prompt (Medium Quality Output):**
```
Generate a PRD for FitTrack Pro using phase submissions and conversation history.
```

**Excellent Prompt (High Quality Output):**
```
Generate a comprehensive ICAgile PRD for FitTrack Pro.

**Product Information:**
- Product Name: FitTrack Pro
- Product Type: Mobile fitness tracking application
- Target Market: Health-conscious millennials (ages 25-40) in North America
- Business Model: Freemium (free basic, $9.99/month premium)
- Development Timeline: 12 months (MVP in 6 months, full launch in 12 months)

**Phase Submissions (All Lifecycle Phases):**

1. Research Phase:
   - Form Data: Market size $4.2B, top competitors MyFitnessPal/Strava, user pain points identified
   - Generated Content: Comprehensive market research, competitive analysis, user insights, technical feasibility

2. Analysis Phase:
   - Form Data: SWOT analysis requested, feasibility assessment needed
   - Generated Content: Detailed SWOT analysis, technical feasibility, risk assessment, gap analysis

3. Ideation Phase:
   - Form Data: Feature ideas for motivation, nutrition, social features
   - Generated Content: 15 feature ideas with user value, business value, implementation complexity

4. Strategy Phase:
   - Form Data: GTM strategy, business model, roadmap
   - Generated Content: Comprehensive strategy, GTM plan, business model, competitive positioning, roadmap

5. PRD Authoring Phase:
   - Form Data: Functional requirements, user stories, acceptance criteria
   - Generated Content: Detailed functional requirements, user stories (INVEST), acceptance criteria (Definition of Done)

**Conversation History:**
[Last 100 messages from chatbot conversations covering all phases, decisions, clarifications]

**Knowledge Base Articles:**
- Article 1: "Fitness App Market Trends 2024"
- Article 2: "Wearable Device Integration Best Practices"
- Article 3: "Freemium Business Model Strategies"
- Article 4: "HIPAA Compliance for Health Apps"
- Article 5: "User Engagement Strategies for Fitness Apps"

**Design Mockups:**
- V0 Prototype: Status=completed, URL=https://v0.dev/project/abc123
- Lovable Prototype: Status=completed, URL=https://lovable.dev/project/xyz789

**Export Requirements:**
1. Synthesize ALL information from phases, conversations, and knowledge base
2. Follow ICAgile PRD structure strictly (all 13 sections)
3. Ensure every section is comprehensive and detailed
4. Reference specific information from phases, conversations, and knowledge base
5. Include design prototypes section with clickable links
6. Make it actionable for engineering teams
7. Follow ICAgile standards strictly

**Review Before Export:**
- Check completeness: Are all phases represented?
- Check alignment: Does PRD align with all form data?
- Check standards: Does it follow ICAgile standards?
- Check actionability: Is it ready for engineering?

**Override Option:** No - only export if all critical sections are complete
```

## How Response Quality Changes

### Low Quality Input → Generic PRD

**Input:**
```
Export PRD for FitTrack Pro
```

**Output Characteristics:**
- Generic PRD structure
- Missing phase information
- No conversation history integration
- Missing knowledge base content
- Incomplete sections
- Not actionable

### Medium Quality Input → Structured PRD

**Input:**
```
Generate PRD using phase submissions and conversations.
```

**Output Characteristics:**
- Basic PRD structure
- Some phase information included
- Limited conversation integration
- Basic knowledge base references
- Some sections complete
- Partially actionable

### High Quality Input → Comprehensive PRD

**Input:** (See "Excellent Prompt" example above)

**Output Characteristics:**
- Complete ICAgile PRD with all 13 sections:
  1. Executive Summary: Synthesizes all phases, includes key metrics
  2. Problem Statement: From research phase, user pain points
  3. Product Vision: From strategy phase, aligned with all phases
  4. User Personas: From research and ideation phases
  5. Functional Requirements: From PRD authoring phase, detailed user stories
  6. Non-Functional Requirements: From analysis phase, technical requirements
  7. Technical Architecture: From analysis and strategy phases
  8. Success Metrics: From strategy phase, aligned with business goals
  9. Go-to-Market Strategy: From strategy phase, comprehensive plan
  10. Timeline: From all phases, integrated roadmap
  11. Risks & Mitigations: From analysis phase, comprehensive assessment
  12. Stakeholder Alignment: From strategy phase
  13. Appendices: All research, analysis, ideation, strategy content
- Comprehensive Synthesis:
  - All phase submissions integrated
  - Conversation history referenced
  - Knowledge base articles cited
  - Design mockups included with links
- ICAgile Compliance:
  - INVEST user stories
  - Definition of Done acceptance criteria
  - Release planning structure
  - User-centered design approach
- Actionability:
  - Clear requirements for engineering
  - Technical specifications
  - API requirements
  - Integration details
- Completeness:
  - All sections comprehensive
  - No missing critical information
  - All form data addressed
  - All decisions documented

## Best Practices for Quality Output

### 1. Provide All Phase Submissions

**Include:**
- All lifecycle phase form data
- All generated content from each phase
- Phase status and completion
- Phase order and dependencies

**Why:** Enables comprehensive PRD synthesizing all phases.

### 2. Include Complete Conversation History

**Include:**
- All chatbot conversations
- Decisions and clarifications
- Context and background
- User preferences and requirements

**Why:** Enables PRD that captures all discussions and decisions.

### 3. Provide Knowledge Base Articles

**Include:**
- Relevant knowledge articles
- Industry best practices
- Technical documentation
- Market research

**Why:** Enhances PRD with additional context and best practices.

### 4. Include Design Mockups

**Include:**
- V0 prototypes
- Lovable prototypes
- Design mockups
- UI/UX references

**Why:** Enables PRD to reference actual designs and prototypes.

### 5. Request Review Before Export

**Request:**
- Completeness check
- Alignment verification
- Standards compliance
- Actionability assessment

**Why:** Ensures PRD quality before export.

## Response Quality Indicators

### High Quality Response Includes:

✅ **Complete Structure**: All 13 ICAgile sections comprehensive
✅ **Phase Synthesis**: All phases integrated and referenced
✅ **Conversation Integration**: Key conversations and decisions included
✅ **Knowledge Base**: Relevant articles cited and used
✅ **Design References**: Mockups included with links
✅ **ICAgile Compliance**: INVEST, Definition of Done, standards followed
✅ **Actionability**: Clear requirements for engineering
✅ **Completeness**: All form data addressed, no missing sections
✅ **Standards**: ICAgile, AIPMM, BCS compliance
✅ **Review**: Completeness and quality verified

### Low Quality Response Indicators:

❌ Incomplete sections or missing content
❌ Phases not integrated
❌ Conversation history not used
❌ Knowledge base not referenced
❌ Design mockups missing
❌ Not ICAgile compliant
❌ Not actionable for engineering
❌ Missing form data
❌ No standards compliance
❌ No review or validation

## Integration with Other Agents

The Export Agent's output synthesizes:

- **Research Agent**: Market research and competitive analysis
- **Analysis Agent**: SWOT analysis and feasibility
- **Ideation Agent**: Feature ideas and concepts
- **Strategy Agent**: Strategic plan and GTM
- **PRD Authoring Agent**: Requirements and user stories
- **Validation Agent**: Quality assurance feedback
- **Summary Agent**: Session summaries

## Tips for Maximum Quality

1. **Complete All Phases**: Ensure all lifecycle phases have submissions
2. **Provide Complete Context**: Include all phases, conversations, knowledge base
3. **Request Review**: Ask for completeness check before export
4. **Specify Standards**: Request ICAgile compliance
5. **Include Designs**: Add design mockups and prototypes
6. **Iterate**: Use validation feedback to improve before export

## Example Workflow

1. **Content Review**: "Review content completeness before export"
2. **Initial Export**: "Generate PRD with all available content"
3. **Validation**: "Validate PRD completeness and quality"
4. **Refinement**: "Refine PRD based on validation feedback"
5. **Final Export**: "Export final PRD document"

Each iteration ensures increasingly comprehensive and high-quality PRD export.


