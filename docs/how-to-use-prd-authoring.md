# How to Use the PRD Authoring Skill

## Value

Transforms vague project ideas into comprehensive, McKinsey-quality Product Requirements Documents—compressing what typically requires days of planning meetings and document drafts into structured, guided hours. This skill ensures alignment before development begins, preventing weeks of rework from unclear requirements or misaligned stakeholders.

## What is This Skill?

The `@prd-authoring` skill helps you create professional Product Requirements Documents through an interactive, McKinsey-consulting-grade workflow. It:

- Guides you through a structured 7-step process with quality gates
- Asks 5-10 targeted questions per step (grouped, interactive approach)
- Creates comprehensive 14-section PRDs with measurable objectives
- Validates against Designer Test, Tech Lead Test, and Measurability Test
- Decomposes PRDs into independently deliverable epics
- Supports document indexing for context-efficient collaboration
- Enforces SMART objectives, MECE thinking, and hypothesis-driven validation

## When to Use This Skill

Use this skill when you need to:
- Define requirements for a new project or major feature
- Align stakeholders on objectives and success criteria
- Document business value and measurable outcomes
- Bridge strategy and execution with clear specifications
- Create designer-ready, tech-lead-ready requirements
- Plan multi-sprint features requiring comprehensive documentation

## Simple Starting Prompt

**IMPORTANT:** To invoke this skill, you must explicitly mention the skill name in your prompt.

To start using this skill, say:

```
Using prd-authoring skill, I need to create a PRD for [project description]
```

or

```
With @prd-authoring, help me write a PRD for [project description]
```

### Example Starting Prompts

**Real example:**
```
Using @prd-authoring skill, create a PRD for "Payment Gateway Integration"
```
**Result:** Complete PRD with product brief, research, requirements, and epic decomposition (see `skills/prd-authoring/examples/`)

---

**For new features:**
```
Using prd-authoring skill, I need to create a PRD for a real-time notification system
```

**For platform changes:**
```
With @prd-authoring, help me write a PRD for migrating to microservices architecture
```

**For business initiatives:**
```
Using prd-authoring skill, create a PRD for launching a mobile app
```

**For internal tools:**
```
With @prd-authoring, I need a PRD for an analytics dashboard for CSTs
```

## What to Expect

### Interactive Process

The skill follows a 7-step workflow with quality gates:

1. **Step 0 (Optional): Document Upload** - Index existing specs, research, user feedback
2. **Step 1: Overview & Problem** - Project definition, problem statement, business impact
3. **Step 2: Goals & Metrics** - SMART objectives, success criteria (baseline → target → timeframe)
4. **Step 3: Users & Use Cases** - Target personas, main workflows, user journeys
5. **Step 4: Functional Requirements** - Detailed FR with acceptance criteria
6. **Step 5: Non-Functional Requirements** - Performance, security, reliability, usability
7. **Step 6: Edge Cases & Analytics** - Constraints, dependencies, instrumentation
8. **Step 7: Timeline & Questions** - Milestones, phasing, open questions

### Grouped Question Pattern

**The skill asks questions in GROUPS of 2-4 and WAITS for your response:**

```
Skill: "Let me understand the problem first.

**Group 1: Problem Definition**

Q1: What problem are we solving? What's broken or painful today?

Q2: Who experiences this problem? (specific user types)

Q3: How often does it occur? (daily, weekly, per transaction)

Please answer these three questions."

[WAITS FOR YOUR RESPONSE]

You: [Provides answers]

Skill: "Got it. Now let me quantify the impact...

**Group 2: Business Impact**

Q4: How many users/transactions are affected?

Q5: What's the business cost? (revenue loss, operational cost, time wasted)

Please provide these numbers."

[WAITS FOR YOUR RESPONSE]
```

**This is NOT a questionnaire—it's an interactive conversation!**

### Review Gates

You'll have **7 checkpoints** (Gates 1-7) where the skill:
- Shows you what it's created for that section
- Validates against Designer Test, Tech Lead Test, Measurability Test
- Waits for your approval before continuing
- You simply respond with: "approved", "confirmed", "LGTM", or "looks good"

**Example Gate:**
```
📋 GATE 1: Overview & Problem Statement Complete

Summary:
Defined Payment Gateway Integration addressing manual invoice friction
for 100% of transactions (1,000/month)

Validation Results:
✅ Designer Test: PASS - Designer knows user flows and pain points
✅ Tech Lead Test: PASS - Tech lead knows scale (1,000/month) and constraints
✅ Measurability Test: PASS - Business impact quantified at $2.4M annually

Ready to proceed to Step 2? (confirm/approved/LGTM)

⏸️ WAITING FOR APPROVAL
```

### PRD Output

The skill creates **comprehensive 14-section PRD**:

1. Overview
2. Problem Statement
3. Goals & Success Metrics
4. Assumptions
5. Target Users & Personas
6. Main Use Cases
7. Functional Requirements
8. Non-Functional Requirements
9. User Flows
10. Edge Cases & Constraints
11. Analytics & Instrumentation
12. Dependencies
13. Timeline & Milestones
14. Open Questions

**Location:** `docs/prds/{project-name}/prd.md`

### McKinsey Principles Enforced

The skill embodies consulting-grade rigor:

**SMART Framework:**
- Specific, Measurable, Achievable, Relevant, Time-bound
- Example: "Reduce checkout time: 180s → 45s within 30 days post-launch"

**MECE Thinking:**
- Mutually Exclusive, Collectively Exhaustive
- Ensures no gaps, no overlaps in requirements coverage

**Progressive Depth Questioning:**
1. Broad: "What business problem?"
2. Focused: "Is it FINDING, ACCESSING, ANALYZING, or SHARING data?"
3. Specific: "What data specifically?"
4. Measurable: "How much time spent per week?"
5. Testable: "So 5,000 hours/week at $X/hour = $Y annually?"

**Vague Answer Rejection:**
```
User: "We want to improve the experience"

Skill: "That's too vague. Improve how? Give me a specific metric:
- Reduce time from X minutes to Y?
- Increase adoption from X% to Y%?
- Reduce errors from X per day to Y?"
```

### Epic Decomposition

After PRD validation, the skill breaks it into epics:
- Groups requirements into independently deliverable units
- Maps dependencies and sequencing
- Ensures 100% requirements coverage
- Creates epic breakdown in `docs/prds/{project-name}/epics.md`

### CLI Commands Available

The skill also provides bash scripts for automation:

```bash
# Check project status and get recommendations
bash helpers/prd-authoring.sh status

# Create product brief template
bash helpers/prd-authoring.sh brief "Project Name"

# Create research document template
bash helpers/prd-authoring.sh research project-name

# Create PRD structure
bash helpers/prd-authoring.sh create-prd project-name

# Validate PRD quality
bash helpers/prd-authoring.sh validate-prd project-name

# Decompose into epics
bash helpers/prd-authoring.sh decompose project-name

# Generate spec proposals from epics
bash helpers/prd-authoring.sh generate-spec project-name "Epic Name"
```

## Example Workflow

```
You: "Using prd-authoring skill, create a PRD for real-time notification system"

Skill: "I'll guide you through creating a McKinsey-quality PRD.
       This will take approximately 60-90 minutes with questions at each step.

       First, what's the project name?"

You: "Real-Time Notification System"

Skill: "Great! Before we start, do you have any existing documents that might help?
       (specs, user research, competitive analysis, business requirements)

       If yes, provide file paths and I'll create a searchable index.
       If no, say 'skip' and we'll proceed to Step 1."

You: "skip"

Skill: "Understood. Let's begin creating your PRD.

       **What to expect:**
       - I'll ask pointed questions in small groups
       - I expect specific, measurable answers
       - We'll build the PRD section-by-section
       - You can say 'show me PRD', 'edit section X', or 'next section' anytime
       - Quality gates ensure we meet the bar

       Ready to begin?"

You: "yes"

Skill: "Perfect. Let me understand the big picture first.

       **Step 1: Overview & Problem Statement**

       **Group 1: Product Definition**

       Q1: What are we building? Describe in one sentence.

       Q2: Is this:
         a) A tool (dashboard, analyzer, generator)
         b) A service (support, consulting, training)
         c) A platform (marketplace, collaboration space)
         d) A process (workflow, methodology)

       Which category best fits?"

You: "A tool - real-time notification system for users"

Skill: "Got it. Now let me understand who will use it and at what scale.

       **Group 2: Users & Scale**

       Q3: Who are the primary users?

       Q4: How many users will use this initially?

       Q5: What teams or organizations will use this?

       Please answer these three questions."

You: "Primary users are app users (customers and merchants). About 50,000 users
      initially. Used across web and mobile apps by product teams."

Skill: "Thanks! Now let me understand the problem.

       **Group 3: Problem Statement**

       Q6: What problem does this solve? What's broken or painful today?

       Q7: How often does this problem occur?

       Q8: What's the business impact? (quantify if possible)

       Please describe the problem, frequency, and impact."

[Conversation continues through all steps and gates]

Skill: "📋 GATE 1: Overview & Problem Statement Complete

       Summary:
       Defined Real-Time Notification System addressing delayed user awareness
       of critical events, affecting 50,000 users with ~500 missed opportunities/week

       Validation Results:
       ✅ Designer Test: PASS - Clear user flows and notification triggers
       ✅ Tech Lead Test: PASS - Scale defined (50K users, 500 events/week)
       ✅ Measurability Test: PASS - Impact quantified ($780K annual opportunity cost)

       Key Content:
       - Problem: Users miss time-sensitive events (orders, payments, updates)
       - Impact: 500 missed opportunities/week = $780K lost revenue annually
       - Users: 50,000 app users (customers and merchants)
       - Frequency: Real-time requirement for critical events

       Next Step: Goals, Success Metrics & Assumptions

       Ready to proceed to Step 2? (confirm/approved/LGTM)

       ⏸️ WAITING FOR APPROVAL"

You: "approved"

[Process continues through all 7 steps and gates]

Skill: "🎉 PRD Complete!

       Your Product Requirements Document is complete and validated.

       PRD Location: docs/prds/real-time-notification-system/prd.md

       Summary:
       - 14 sections complete
       - 6 functional requirements with acceptance criteria
       - 4 non-functional requirements (performance, security, reliability, usability)
       - 3 primary user personas documented
       - All sections meet McKinsey quality standards

       What's Next:

       1. Review: Read through the complete PRD
       2. Validate: Run quality check
          bash helpers/prd-authoring.sh validate-prd real-time-notification-system
       3. Share: Distribute to stakeholders
       4. Decompose: Break down into epics
          bash helpers/prd-authoring.sh decompose real-time-notification-system

       Would you like to:
         1. Review the complete PRD
         2. Run validation
         3. Start epic decomposition
         4. Export or share the PRD"
```

## Key Points

- **Interactive workflow** - Questions asked in groups of 2-4, not all at once
- **McKinsey rigor** - SMART objectives, MECE thinking, hypothesis-driven
- **Vague answer rejection** - "That's too vague. Be specific: [follow-up questions]"
- **Quality gates** - 7 checkpoints with Designer/Tech Lead/Measurability tests
- **Incremental saves** - PRD updated after each step (no data loss)
- **Resume support** - Can pause and continue later from progress tracker
- **Document indexing** - Optional reference document upload for context-efficiency
- **Epic decomposition** - Breaks PRD into independently deliverable units
- **CLI automation** - Bash scripts for status checks, validation, decomposition

## User Commands During Workflow

At any point, you can interrupt with:

- **"show me PRD"** or **"show me PRD so far"**: Display current PRD content
- **"edit section X"** or **"revise Overview"**: Modify specific section
- **"next"** or **"move to next step"**: Skip to next step (if current validated)
- **"pause"** or **"save progress"**: Save state for resumption later
- **"help"**: Get guidance on current question
- **"example"**: See sample answer for current question

## Two Modes Available

**Interactive Mode (default):**
- Conversational workflow with grouped questions
- Dynamic questioning that adapts to your responses
- Quality gates with approval requirements
- Ideal for new PRDs requiring deep thinking

**CLI Mode (automation):**
- Bash scripts for quick operations
- Status checks and validation
- Template creation and decomposition
- Ideal for experienced users or CI/CD integration

## Validation Quality Checks

The `validate-prd` command checks for:

**Completeness:**
- All 14 sections present and non-empty
- YAML frontmatter with required fields

**Quality:**
- No vague language ("should", "might", "probably", "fast", "good")
- Success criteria are measurable (include numbers/percentages)
- Functional requirements have acceptance criteria
- No ambiguous terms without quantification

**SMART Criteria:**
- Objectives are Specific, Measurable, Achievable, Relevant, Time-bound

**Example validation output:**
```
=== PRD Validation Report ===
Project: real-time-notification-system

Completeness: 14/14 ✓

Quality Issues: 2
⚠ Line 89: Vague language - "reasonable time"
  Suggestion: Define specific time threshold (e.g., "within 5 seconds")

⚠ Line 124: Success criterion lacks measurement - "improve user engagement"
  Suggestion: Specify measurable UX metric (e.g., "engagement rate >75%")

Recommendations:
1. Quantify vague success criteria
2. Add specific time thresholds

Overall: GOOD (Minor revisions recommended)
```

## No Preparation Needed

Just start with a simple prompt about your project. The skill will:
- Guide you through the entire process
- Ask all necessary questions as it goes
- Validate quality at each checkpoint
- Save your work continuously
- Generate a professional PRD

## Getting Started Now

Ready to try it? Use this prompt format:

```
Using prd-authoring skill, I need to create a PRD for [your project]
```

or

```
With @prd-authoring, help me write a PRD for [your project]
```

The skill will take it from there!

## Success Patterns

### Problem Statement Format
```
[What problem] + [Who experiences] + [Frequency] + [Business impact]

Example: "Our e-commerce platform lacks payment processing, forcing customers
through manual invoices. This affects 100% of transactions (1,000/month),
causing 45% cart abandonment and $2.4M lost revenue annually."
```

### Success Metric Format
```
[Metric name]: [Baseline] → [Target] within [Timeframe]

Example: "Checkout conversion rate: 55% → 75% within 30 days post-launch"
```

### Functional Requirement Structure
```markdown
### FR1: [Requirement Name]

**Description**: [What the system must do]

**User Story**: As a [user], I want [capability], so that [benefit]

**Acceptance Criteria**:
- [ ] Given [precondition], when [action], then [result]
- [ ] Given [precondition], when [action], then [result]
- [ ] Given [precondition], when [action], then [result]

**Priority**: Must Have / Should Have / Could Have

**Dependencies**: [Other requirements or systems]
```

## Tips for Success

### Do This ✓
- Be specific with numbers (avoid "fast", "good", "many")
- Quantify business impact with evidence
- Define success metrics with baseline → target → timeframe
- Include acceptance criteria for every requirement
- Time-box research phase (4-8 hours max)
- Link requirements back to objectives (traceability)
- Validate frequently (use CLI for quick checks)

### Avoid This ✗
- Vague language ("should be fast and secure")
- Unmeasurable success criteria ("improve experience")
- Missing acceptance criteria (how to test?)
- Skipping validation before decomposition
- Changing PRD endlessly (lock after 2-3 iterations)
- Proceeding without gate approval

## Time Budget

| Activity | Time | Purpose |
|----------|------|---------|
| Document Upload (optional) | 15-30 min | Index reference materials |
| Step 1: Overview & Problem | 20-30 min | Define context and business case |
| Step 2: Goals & Metrics | 15-25 min | Set measurable objectives |
| Step 3: Users & Use Cases | 15-25 min | Document target users and workflows |
| Step 4: Functional Reqs | 30-45 min | Detail system capabilities |
| Step 5: Non-Functional Reqs | 20-30 min | Define quality attributes |
| Step 6: Edge Cases | 15-25 min | Document constraints and dependencies |
| Step 7: Timeline | 10-20 min | Set milestones and open questions |
| **Total Interactive Time** | **60-90 min** | |

**Plus:**
- Validation iterations: 15-30 min
- Epic decomposition: 30-60 min
- **Total end-to-end:** 2-3 hours for complete PRD with epic breakdown

**ROI:** 2-3 hours of structured planning prevents 2-4 weeks of rework from unclear requirements

## Requirements

**On your system:**
- Bash (standard on Mac/Linux)
- Git (for version control) - optional

That's it! No other dependencies needed.

## Example Files

Complete example available in `skills/prd-authoring/examples/`:

- `01-product-brief-example.md` - Product brief with problem, users, value, metrics
- `02-research-example.md` - Competitive analysis with 3 competitors (Stripe, PayPal, Square)
- `03-prd-example-abbreviated.md` - Full PRD with 5 FRs, 4 NFRs, success criteria
- `workflow-test-log.md` - Complete workflow test with all happy paths and edge cases

Review these to see what completed outputs look like!

## Integration with Other Workflows

**Transition to spec-authoring:**
After epic decomposition, use spec-authoring skill to create detailed technical specs for each epic.

**Link to sprint-planner:**
After specs approved, use sprint-planner to select specs for sprint execution.

**Traceability chain:**
```
Business Goal → PRD Objective → Epic → Spec Proposal → Spec PR → GitHub Issues → Code
```

## Help & Resources

**Quick Start:**
- `skills/prd-authoring/examples/QUICK_START.md` - 5-minute overview

**Full Documentation:**
- `skills/prd-authoring/SKILL.md` - Complete 2,355-line skill documentation

**CLI Reference:**
- `skills/prd-authoring/helpers/README.md` - Bash script documentation

**Prompts & Questions:**
- `skills/prd-authoring/reference/prompts/` - 7 step-specific prompt files
- `skills/prd-authoring/reference/questions/` - Question templates for each step

**Checklists:**
- `skills/prd-authoring/reference/checklists/` - Quality gate validation checklists
