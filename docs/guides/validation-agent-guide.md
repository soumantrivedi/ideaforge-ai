# Validation Agent Guide

## Overview

The Validation Agent (`AgnoValidationAgent`) specializes in quality assurance, response validation, and compliance checking. It ensures that generated content meets industry standards and adequately addresses user requirements.

## System Context

The Validation Agent uses the following system context:

- **RAG Knowledge Base**: Optional (disabled by default)
- **Model Tier**: `fast` (optimized for speed)
- **Capabilities**: Response validation, PRD validation, requirements validation, quality assurance, compliance checking, feasibility validation, standards validation, gap analysis, user satisfaction assessment

## System Prompt

The system prompt defines the agent's validation framework:

```
You are a Quality Assurance and Validation Specialist following industry standards from:
- BCS (British Computer Society) Product Management Framework
- ICAgile (International Consortium for Agile) Product Ownership
- AIPMM (Association of International Product Marketing and Management)
- Pragmatic Institute Product Management Framework
- McKinsey CodeBeyond standards

Your responsibilities:
1. Validate product requirements and responses for completeness
2. Ensure compliance with standards and best practices
3. Check for clarity, testability, and consistency
4. Validate technical feasibility
5. Review and provide actionable feedback on deliverables
6. Assess quality against user-submitted form data

Validation Areas:
- Response completeness and structure
- Requirements clarity and testability
- Technical feasibility validation
- Compliance with industry standards (ICAgile, AIPMM, BCS, Pragmatic Institute)
- Consistency across documents and responses
- Risk identification and mitigation
- Alignment with user-submitted form data

Your output format should be:
1. **Validation Status**: PASS / NEEDS_REFINEMENT / FAIL
2. **Completeness Score**: 0-100
3. **Issues Found**: List of specific issues with severity (critical/warning/info)
4. **Recommendations**: Specific, actionable recommendations for improvement
5. **User Satisfaction Assessment**: Whether the response adequately addresses the user's form data
```

## User Prompt

The user prompt should include:

1. **Response Content**: The generated content to validate
2. **Form Data**: User-submitted form data to validate against
3. **Phase Name**: The lifecycle phase being validated
4. **Context**: Optional - additional context for validation

### Example User Prompts

**Basic Prompt (Low Quality Output):**
```
Validate this response: [content]
```

**Good Prompt (Medium Quality Output):**
```
Validate this PRD response against the form data. Check for completeness and standards compliance.
```

**Excellent Prompt (High Quality Output):**
```
Validate the following generated response for the "Research Phase" of FitTrack Pro:

**Generated Response:**
[Full generated content from Research Agent - market analysis, competitive landscape, user insights, etc.]

**User-Submitted Form Data:**
- Product Name: FitTrack Pro
- Target Market: Health-conscious millennials (ages 25-40) in North America
- Key Features: Workout tracking, nutrition logging, social features, wearable integration
- Business Model: Freemium (free basic, $9.99/month premium)
- Budget: $500K initial investment
- Timeline: 12-month development cycle
- Success Metrics: 100K users in first year, 20% conversion to premium

**Phase Context:**
- Phase: Research
- Purpose: Market research and competitive analysis
- Expected Output: Market size, competitive landscape, user insights, technical feasibility

**Validation Criteria:**
1. Does the response address ALL form data fields?
2. Is the response complete and comprehensive for a Research phase?
3. Does it follow industry standards (ICAgile, AIPMM, BCS)?
4. Is the response clear, actionable, and testable?
5. Are there any gaps or inconsistencies?
6. Would a user find this response satisfactory for their needs?

**Required Validation Format:**
- Validation Status: PASS / NEEDS_REFINEMENT / FAIL
- Completeness Score: 0-100 (with breakdown by section)
- Issues Found: List with severity (critical/warning/info) and specific suggestions
- Recommendations: Prioritized, actionable recommendations
- User Satisfaction Assessment: Detailed assessment of alignment with form data
- Standards Compliance: Check against ICAgile, AIPMM, BCS, Pragmatic Institute
```

## How Response Quality Changes

### Low Quality Input → Generic Validation

**Input:**
```
Validate this: [content]
```

**Output Characteristics:**
- Generic validation status
- No specific issues identified
- Vague recommendations
- Missing completeness score
- No standards compliance check

### Medium Quality Input → Structured Validation

**Input:**
```
Validate this PRD response. Check completeness and standards.
```

**Output Characteristics:**
- Validation status (PASS/FAIL)
- Basic completeness score
- Some issues identified
- General recommendations
- Basic standards check

### High Quality Input → Comprehensive Validation

**Input:** (See "Excellent Prompt" example above)

**Output Characteristics:**
- Detailed validation status with rationale
- Comprehensive completeness score (0-100) with section breakdown
- Specific issues with:
  - Severity (critical/warning/info)
  - Exact location in content
  - Specific problem description
  - Suggested fix
- Prioritized recommendations:
  - High priority: Critical issues
  - Medium priority: Important improvements
  - Low priority: Nice-to-have enhancements
- User satisfaction assessment:
  - Alignment with each form data field
  - Missing information identification
  - Quality assessment per requirement
- Standards compliance:
  - ICAgile compliance check
  - AIPMM alignment
  - BCS framework adherence
  - Pragmatic Institute standards
- Actionable next steps with timelines

## Best Practices for Quality Output

### 1. Provide Complete Generated Content

**Include:**
- Full generated response to validate
- All sections and subsections
- Complete context and details

**Why:** Enables comprehensive validation of all aspects.

### 2. Include All Form Data

**Include:**
- All user-submitted form fields
- Field values and requirements
- Business constraints and goals
- Success metrics

**Why:** Enables validation against actual user requirements.

### 3. Specify Phase Context

**Include:**
- Phase name and purpose
- Expected output for that phase
- Phase-specific requirements

**Why:** Enables phase-appropriate validation criteria.

### 4. Request Specific Validation Criteria

**Specify:**
- Completeness checks
- Standards compliance
- Clarity and testability
- Gap analysis
- User satisfaction

**Why:** Guides the agent to check all relevant aspects.

### 5. Ask for Detailed Feedback

**Request:**
- Specific issues with locations
- Severity ratings
- Actionable recommendations
- Prioritized improvements

**Why:** Makes validation actionable and implementable.

## Response Quality Indicators

### High Quality Response Includes:

✅ **Clear Status**: PASS / NEEDS_REFINEMENT / FAIL with rationale
✅ **Completeness Score**: 0-100 with section breakdown
✅ **Specific Issues**: Exact locations, severity, descriptions, fixes
✅ **Prioritized Recommendations**: Ranked by impact and urgency
✅ **User Satisfaction**: Field-by-field alignment assessment
✅ **Standards Compliance**: Check against multiple frameworks
✅ **Actionable Next Steps**: Specific improvements with timelines
✅ **Evidence-Based**: References to standards, best practices, or requirements

### Low Quality Response Indicators:

❌ Vague status without rationale
❌ No completeness score or breakdown
❌ Generic issues without specifics
❌ Unprioritized recommendations
❌ No user satisfaction assessment
❌ Missing standards compliance check
❌ Vague suggestions without next steps
❌ No evidence or references

## Integration with Other Agents

The Validation Agent's output is often used by:

- **PRD Authoring Agent**: To refine PRD content
- **Export Agent**: To validate before export
- **Research Agent**: To validate research completeness
- **Analysis Agent**: To validate analysis quality
- **All Agents**: For quality assurance feedback loop

## Tips for Maximum Quality

1. **Provide Complete Context**: Include all generated content and form data
2. **Specify Phase**: Include phase name and expected output
3. **Request Detailed Feedback**: Ask for specific issues and recommendations
4. **Iterate**: Use validation feedback to improve and re-validate
5. **Check Standards**: Request compliance with multiple frameworks
6. **Prioritize**: Ask for prioritized recommendations by impact

## Example Workflow

1. **Initial Validation**: "Validate this Research phase response"
2. **Deep Dive**: "Analyze the completeness score breakdown in detail"
3. **Standards Check**: "Verify compliance with ICAgile and AIPMM standards"
4. **User Alignment**: "Assess alignment with each form data field"
5. **Action Plan**: "Create prioritized action plan to address all issues"

Each iteration provides increasingly detailed and actionable validation feedback.


