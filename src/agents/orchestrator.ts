import type { AgentContext, AgentResult, ResearchOutput, AnalysisOutput, PRDContent, ValidationOutput } from './types';
import { runResearchAgent } from './researchAgent';
import { runAnalysisAgent } from './analysisAgent';
import { runPRDWriterAgent } from './prdWriterAgent';
import { runValidatorAgent } from './validatorAgent';

export interface OrchestratorConfig {
  openaiApiKey: string;
  onProgress?: (stage: string, message: string) => void;
}

export interface OrchestratorResult {
  success: boolean;
  research?: ResearchOutput;
  analysis?: AnalysisOutput;
  prd?: PRDContent;
  validation?: ValidationOutput;
  error?: string;
  stageErrors?: Record<string, string>;
}

export class MultiAgentOrchestrator {
  private config: OrchestratorConfig;

  constructor(config: OrchestratorConfig) {
    this.config = config;
  }

  private updateProgress(stage: string, message: string) {
    if (this.config.onProgress) {
      this.config.onProgress(stage, message);
    }
  }

  async execute(context: AgentContext): Promise<OrchestratorResult> {
    const result: OrchestratorResult = {
      success: false,
      stageErrors: {},
    };

    try {
      this.updateProgress('research', 'Conducting market research...');
      const researchResult = await runResearchAgent(context, this.config.openaiApiKey);

      if (!researchResult.success) {
        result.stageErrors!['research'] = researchResult.error || 'Research failed';
        throw new Error('Research agent failed');
      }

      result.research = researchResult.output as ResearchOutput;
      this.updateProgress('research', 'Market research completed');

      this.updateProgress('analysis', 'Analyzing product opportunity...');
      const analysisResult = await runAnalysisAgent(
        context,
        result.research,
        this.config.openaiApiKey
      );

      if (!analysisResult.success) {
        result.stageErrors!['analysis'] = analysisResult.error || 'Analysis failed';
        throw new Error('Analysis agent failed');
      }

      result.analysis = analysisResult.output as AnalysisOutput;
      this.updateProgress('analysis', 'Product analysis completed');

      this.updateProgress('prd_writer', 'Writing Product Requirements Document...');
      const prdResult = await runPRDWriterAgent(
        context,
        result.research,
        result.analysis,
        this.config.openaiApiKey
      );

      if (!prdResult.success) {
        result.stageErrors!['prd_writer'] = prdResult.error || 'PRD writing failed';
        throw new Error('PRD writer agent failed');
      }

      result.prd = prdResult.output as PRDContent;
      this.updateProgress('prd_writer', 'PRD writing completed');

      this.updateProgress('validator', 'Validating PRD quality...');
      const validationResult = await runValidatorAgent(
        context,
        result.prd,
        this.config.openaiApiKey
      );

      if (!validationResult.success) {
        result.stageErrors!['validator'] = validationResult.error || 'Validation failed';
        throw new Error('Validator agent failed');
      }

      result.validation = validationResult.output as ValidationOutput;
      this.updateProgress('validator', 'PRD validation completed');

      result.success = true;
      this.updateProgress('completed', 'All agents completed successfully');

      return result;
    } catch (error) {
      result.error = error instanceof Error ? error.message : 'Unknown error occurred';
      this.updateProgress('error', result.error);
      return result;
    }
  }
}
