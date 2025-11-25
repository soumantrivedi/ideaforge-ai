import { Agent } from '@openai/agents';
import { z } from 'zod';
import type { AgentContext, AgentResult, ResearchOutput } from './types';

const CompetitorSchema = z.object({
  name: z.string(),
  description: z.string(),
  strengths: z.array(z.string()),
  weaknesses: z.array(z.string()),
});

const ResearchOutputSchema = z.object({
  competitors: z.array(CompetitorSchema),
  marketTrends: z.array(z.string()),
  userNeeds: z.array(z.string()),
  technologicalConsiderations: z.array(z.string()),
});

export const createResearchAgent = (openaiApiKey: string) => {
  const agent = new Agent({
    name: 'Research Agent',
    instructions: `You are a market research specialist focused on product discovery.

Your role is to:
1. Analyze the product idea and identify the market space
2. Research and identify 3-5 key competitors or similar solutions
3. Identify current market trends relevant to this product
4. Discover user needs and pain points that this product could address
5. Consider technological trends and opportunities

Provide comprehensive but concise research that will inform product requirements.
Format your response as a structured JSON object with competitors, marketTrends, userNeeds, and technologicalConsiderations.`,
    model: 'gpt-5.1',
  });

  return agent;
};

export const runResearchAgent = async (
  context: AgentContext,
  openaiApiKey: string
): Promise<AgentResult> => {
  try {
    const agent = createResearchAgent(openaiApiKey);

    const prompt = `Conduct market research for the following product idea:

Title: ${context.projectTitle}
Description: ${context.projectDescription}

Please provide:
1. Analysis of 3-5 competitors or similar solutions
2. Current market trends
3. Key user needs and pain points
4. Relevant technological considerations

Format as JSON with structure:
{
  "competitors": [{"name": "", "description": "", "strengths": [], "weaknesses": []}],
  "marketTrends": [],
  "userNeeds": [],
  "technologicalConsiderations": []
}`;

    const response = await agent.run({ messages: [{ role: 'user', content: prompt }] });

    const lastMessage = response.messages[response.messages.length - 1];
    const content = lastMessage.content;

    let parsedOutput: ResearchOutput;

    if (typeof content === 'string') {
      const jsonMatch = content.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        parsedOutput = ResearchOutputSchema.parse(JSON.parse(jsonMatch[0]));
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
        agentName: 'research',
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
