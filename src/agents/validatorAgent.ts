import { Agent } from '@openai/agents';
import { z } from 'zod';
import type { AgentContext, AgentResult, PRDContent, ValidationOutput } from './types';

const IssueSchema = z.object({
  severity: z.enum(['critical', 'warning', 'info']),
  section: z.string(),
  message: z.string(),
  suggestion: z.string(),
});

const ValidationOutputSchema = z.object({
  isValid: z.boolean(),
  completeness: z.number().min(0).max(100),
  issues: z.array(IssueSchema),
  recommendations: z.array(z.string()),
});

export const createValidatorAgent = (openaiApiKey: string) => {
  const agent = new Agent({
    name: 'Validator Agent',
    instructions: `You are a PRD quality assurance specialist.

Your role is to:
1. Review the PRD for completeness and quality
2. Check that all essential sections are present and detailed
3. Identify gaps, ambiguities, or inconsistencies
4. Provide actionable recommendations for improvement
5. Assign a completeness score (0-100)

Be thorough but constructive. Focus on making the PRD actionable for engineering teams.
Format your response as a structured JSON object.`,
    model: 'gpt-5.1',
  });

  return agent;
};

export const runValidatorAgent = async (
  context: AgentContext,
  prdContent: PRDContent,
  openaiApiKey: string
): Promise<AgentResult> => {
  try {
    const agent = createValidatorAgent(openaiApiKey);

    const prompt = `Review the following Product Requirements Document for quality and completeness:

${JSON.stringify(prdContent, null, 2)}

Please evaluate:
1. Completeness - Are all essential sections present and detailed?
2. Clarity - Are requirements clear and unambiguous?
3. Technical Feasibility - Are technical requirements well-defined?
4. User Stories - Are they specific and testable?
5. Success Metrics - Are they measurable and relevant?

Provide:
- isValid: boolean (true if no critical issues)
- completeness: score 0-100
- issues: array of issues with severity (critical/warning/info), section, message, and suggestion
- recommendations: array of general recommendations

Format as JSON with structure:
{
  "isValid": true|false,
  "completeness": 0-100,
  "issues": [{"severity": "critical|warning|info", "section": "", "message": "", "suggestion": ""}],
  "recommendations": []
}`;

    const response = await agent.run({ messages: [{ role: 'user', content: prompt }] });

    const lastMessage = response.messages[response.messages.length - 1];
    const content = lastMessage.content;

    let parsedOutput: ValidationOutput;

    if (typeof content === 'string') {
      const jsonMatch = content.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        parsedOutput = ValidationOutputSchema.parse(JSON.parse(jsonMatch[0]));
      } else {
        throw new Error('No JSON found in response');
      }
    } else {
      throw new Error('Unexpected content type');
    }

    return {
      success: true,
      output: parsedOutput,
      metadata: {
        agentName: 'validator',
        tokensUsed: response.usage,
      },
    };
  } catch (error) {
    return {
      success: false,
      output: {},
      error: error instanceof Error ? error.message : 'Unknown error occurred',
    };
  }
};
