import { Agent } from '@openai/agents';
import { z } from 'zod';
import type { AgentContext, AgentResult, AnalysisOutput, ResearchOutput } from './types';

const FeatureSchema = z.object({
  name: z.string(),
  description: z.string(),
  priority: z.enum(['high', 'medium', 'low']),
});

const AnalysisOutputSchema = z.object({
  targetAudience: z.string(),
  valueProposition: z.string(),
  coreFeatures: z.array(FeatureSchema),
  technicalFeasibility: z.string(),
  marketOpportunity: z.string(),
  risks: z.array(z.string()),
});

export const createAnalysisAgent = (openaiApiKey: string) => {
  const agent = new Agent({
    name: 'Analysis Agent',
    instructions: `You are a product analyst specializing in product strategy and feature planning.

Your role is to:
1. Define the target audience based on research
2. Craft a compelling value proposition
3. Identify and prioritize core features (5-8 features)
4. Assess technical feasibility
5. Evaluate market opportunity
6. Identify potential risks

Use the market research to inform your analysis.
Provide strategic insights that will guide PRD development.
Format your response as a structured JSON object.`,
    model: 'gpt-4o',
  });

  return agent;
};

export const runAnalysisAgent = async (
  context: AgentContext,
  researchOutput: ResearchOutput,
  openaiApiKey: string
): Promise<AgentResult> => {
  try {
    const agent = createAnalysisAgent(openaiApiKey);

    const prompt = `Analyze the following product idea and research findings:

Product Title: ${context.projectTitle}
Product Description: ${context.projectDescription}

Market Research:
${JSON.stringify(researchOutput, null, 2)}

Please provide:
1. Clear target audience definition
2. Compelling value proposition
3. 5-8 core features with priorities (high/medium/low)
4. Technical feasibility assessment
5. Market opportunity evaluation
6. Key risks to consider

Format as JSON with structure:
{
  "targetAudience": "",
  "valueProposition": "",
  "coreFeatures": [{"name": "", "description": "", "priority": "high|medium|low"}],
  "technicalFeasibility": "",
  "marketOpportunity": "",
  "risks": []
}`;

    const response = await agent.run({ messages: [{ role: 'user', content: prompt }] });

    const lastMessage = response.messages[response.messages.length - 1];
    const content = lastMessage.content;

    let parsedOutput: AnalysisOutput;

    if (typeof content === 'string') {
      const jsonMatch = content.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        parsedOutput = AnalysisOutputSchema.parse(JSON.parse(jsonMatch[0]));
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
        agentName: 'analysis',
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
