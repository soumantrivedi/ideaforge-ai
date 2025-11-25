import { Agent } from '@openai/agents';
import { z } from 'zod';
import type { AgentContext, AgentResult, PRDContent, ResearchOutput, AnalysisOutput } from './types';

const FeatureSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  priority: z.enum(['P0', 'P1', 'P2']),
  userStories: z.array(z.string()),
  acceptanceCriteria: z.array(z.string()),
});

const PRDContentSchema = z.object({
  overview: z.object({
    title: z.string(),
    version: z.string(),
    author: z.string(),
    date: z.string(),
    summary: z.string(),
  }),
  problemStatement: z.string(),
  goals: z.array(z.string()),
  targetUsers: z.array(z.object({
    persona: z.string(),
    needs: z.array(z.string()),
    painPoints: z.array(z.string()),
  })),
  features: z.array(FeatureSchema),
  technicalRequirements: z.object({
    architecture: z.string(),
    integrations: z.array(z.string()),
    security: z.array(z.string()),
    performance: z.array(z.string()),
  }),
  successMetrics: z.array(z.object({
    metric: z.string(),
    target: z.string(),
  })),
  timeline: z.array(z.object({
    phase: z.string(),
    duration: z.string(),
    deliverables: z.array(z.string()),
  })),
});

export const createPRDWriterAgent = (openaiApiKey: string) => {
  const agent = new Agent({
    name: 'PRD Writer Agent',
    instructions: `You are an expert Product Requirements Document (PRD) writer.

Your role is to:
1. Synthesize research and analysis into a comprehensive PRD
2. Write clear, detailed feature specifications with user stories
3. Define technical requirements and architecture considerations
4. Establish success metrics and KPIs
5. Create a realistic timeline with phases

Create a professional, detailed PRD that engineering teams can use to build the product.
Include specific user stories, acceptance criteria, and technical details.
Format your response as a complete, structured JSON object.`,
    model: 'gpt-5.1',
  });

  return agent;
};

export const runPRDWriterAgent = async (
  context: AgentContext,
  researchOutput: ResearchOutput,
  analysisOutput: AnalysisOutput,
  openaiApiKey: string
): Promise<AgentResult> => {
  try {
    const agent = createPRDWriterAgent(openaiApiKey);

    const prompt = `Create a comprehensive Product Requirements Document for:

Product Title: ${context.projectTitle}
Product Description: ${context.projectDescription}

Market Research:
${JSON.stringify(researchOutput, null, 2)}

Product Analysis:
${JSON.stringify(analysisOutput, null, 2)}

Create a complete PRD with the following sections:
1. Overview (title, version, author, date, summary)
2. Problem Statement
3. Goals (3-5 key goals)
4. Target Users (2-3 personas with needs and pain points)
5. Features (detailed specs with user stories and acceptance criteria)
6. Technical Requirements (architecture, integrations, security, performance)
7. Success Metrics (measurable KPIs)
8. Timeline (phases with deliverables)

Format as JSON matching this structure:
{
  "overview": {"title": "", "version": "1.0", "author": "AI Product Manager", "date": "", "summary": ""},
  "problemStatement": "",
  "goals": [],
  "targetUsers": [{"persona": "", "needs": [], "painPoints": []}],
  "features": [{"id": "", "name": "", "description": "", "priority": "P0|P1|P2", "userStories": [], "acceptanceCriteria": []}],
  "technicalRequirements": {"architecture": "", "integrations": [], "security": [], "performance": []},
  "successMetrics": [{"metric": "", "target": ""}],
  "timeline": [{"phase": "", "duration": "", "deliverables": []}]
}`;

    const response = await agent.run({ messages: [{ role: 'user', content: prompt }] });

    const lastMessage = response.messages[response.messages.length - 1];
    const content = lastMessage.content;

    let parsedOutput: PRDContent;

    if (typeof content === 'string') {
      const jsonMatch = content.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        parsedOutput = PRDContentSchema.parse(JSON.parse(jsonMatch[0]));
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
        agentName: 'prd_writer',
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
