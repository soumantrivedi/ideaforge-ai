import type { AIProviderManager, Message } from '../lib/ai-providers';
import type { RAGSystem } from '../lib/rag-system';
import { ChatbotAgent, type AgentConfig, type ChatAgentMessage, AGENT_CONFIGS, type AgentRole } from './chatbot-agents';

export type CoordinationMode = 'sequential' | 'parallel' | 'collaborative' | 'debate';
export type InteractionType = 'request' | 'response' | 'consultation' | 'delegation';

export interface AgentInteraction {
  id: string;
  sourceAgent: string;
  targetAgent: string;
  interactionType: InteractionType;
  message: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface MultiAgentMessage extends ChatAgentMessage {
  agentType?: AgentRole;
  parentMessageId?: string;
  isInternal?: boolean;
  targetAgent?: string;
  interactions?: AgentInteraction[];
}

export interface AgentCapability {
  name: string;
  description: string;
  canHandle: (message: string) => boolean;
  confidence: (message: string) => number;
}

export class EnhancedAgent extends ChatbotAgent {
  private capabilities: AgentCapability[];
  private interactions: AgentInteraction[] = [];

  constructor(
    config: AgentConfig,
    aiManager: AIProviderManager,
    ragSystem?: RAGSystem,
    capabilities?: AgentCapability[]
  ) {
    super(config, aiManager, ragSystem);
    this.capabilities = capabilities || this.getDefaultCapabilities();
  }

  private getDefaultCapabilities(): AgentCapability[] {
    const baseCapabilities: Record<AgentRole, AgentCapability[]> = {
      general: [
        {
          name: 'general_conversation',
          description: 'Handle general queries and conversations',
          canHandle: () => true,
          confidence: (msg) => msg.length > 0 ? 0.5 : 0,
        },
      ],
      research: [
        {
          name: 'research_analysis',
          description: 'Conduct research and analysis',
          canHandle: (msg) => /research|analyze|study|investigate/i.test(msg),
          confidence: (msg) => /research|analyze|study|investigate/i.test(msg) ? 0.9 : 0.3,
        },
      ],
      coding: [
        {
          name: 'code_generation',
          description: 'Write and debug code',
          canHandle: (msg) => /code|program|function|debug|implement/i.test(msg),
          confidence: (msg) => /code|program|function|debug|implement/i.test(msg) ? 0.95 : 0.2,
        },
      ],
      creative: [
        {
          name: 'creative_writing',
          description: 'Generate creative content',
          canHandle: (msg) => /story|poem|creative|write|imagine/i.test(msg),
          confidence: (msg) => /story|poem|creative|write|imagine/i.test(msg) ? 0.9 : 0.3,
        },
      ],
      analysis: [
        {
          name: 'data_analysis',
          description: 'Analyze data and provide insights',
          canHandle: (msg) => /data|statistics|metrics|trends|insight/i.test(msg),
          confidence: (msg) => /data|statistics|metrics|trends|insight/i.test(msg) ? 0.9 : 0.3,
        },
      ],
      rag: [
        {
          name: 'knowledge_retrieval',
          description: 'Retrieve and synthesize knowledge',
          canHandle: (msg) => /knowledge|document|search|find/i.test(msg),
          confidence: (msg) => /knowledge|document|search|find/i.test(msg) ? 0.95 : 0.4,
        },
      ],
    };

    return baseCapabilities[this.config.role] || baseCapabilities.general;
  }

  getCapabilities(): AgentCapability[] {
    return this.capabilities;
  }

  canHandle(message: string): boolean {
    return this.capabilities.some((cap) => cap.canHandle(message));
  }

  getConfidence(message: string): number {
    const confidences = this.capabilities.map((cap) => cap.confidence(message));
    return Math.max(...confidences, 0);
  }

  async consultAgent(
    targetAgent: EnhancedAgent,
    query: string,
    context: MultiAgentMessage[]
  ): Promise<string> {
    const interaction: AgentInteraction = {
      id: crypto.randomUUID(),
      sourceAgent: this.config.name,
      targetAgent: targetAgent.config.name,
      interactionType: 'consultation',
      message: query,
      timestamp: new Date().toISOString(),
    };

    this.interactions.push(interaction);

    const consultationMessage: MultiAgentMessage = {
      role: 'user',
      content: `Consultation from ${this.config.name}: ${query}`,
      agentName: this.config.name,
      timestamp: new Date().toISOString(),
      isInternal: true,
      targetAgent: targetAgent.config.name,
    };

    const response = await targetAgent.generateResponse([
      ...context,
      consultationMessage,
    ]);

    return response as string;
  }

  getInteractions(): AgentInteraction[] {
    return this.interactions;
  }

  clearInteractions(): void {
    this.interactions = [];
  }
}

export class CollaborativeOrchestrator {
  private agents: Map<AgentRole, EnhancedAgent>;
  private aiManager: AIProviderManager;
  private ragSystem?: RAGSystem;
  private coordinationMode: CoordinationMode = 'collaborative';
  private activeAgents: Set<AgentRole> = new Set();

  constructor(
    aiManager: AIProviderManager,
    ragSystem?: RAGSystem,
    mode: CoordinationMode = 'collaborative'
  ) {
    this.aiManager = aiManager;
    this.ragSystem = ragSystem;
    this.coordinationMode = mode;
    this.agents = new Map();
    this.initializeAgents();
  }

  private initializeAgents() {
    const providers = this.aiManager.getConfiguredProviders();
    if (providers.length === 0) {
      throw new Error('No AI providers configured');
    }

    const providerMap: Record<AgentRole, any> = {
      general: providers[0],
      research: providers.length > 1 ? providers[1] : providers[0],
      coding: providers[0],
      creative: providers.length > 2 ? providers[2] : providers[0],
      analysis: providers.length > 1 ? providers[1] : providers[0],
      rag: providers[0],
    };

    Object.entries(AGENT_CONFIGS).forEach(([role, config]) => {
      const agentConfig: AgentConfig = {
        ...config,
        provider: providerMap[role as AgentRole],
      };

      this.agents.set(
        role as AgentRole,
        new EnhancedAgent(agentConfig, this.aiManager, this.ragSystem)
      );
    });
  }

  getAgent(role: AgentRole): EnhancedAgent {
    const agent = this.agents.get(role);
    if (!agent) {
      throw new Error(`Agent not found: ${role}`);
    }
    return agent;
  }

  getAllAgents(): EnhancedAgent[] {
    return Array.from(this.agents.values());
  }

  setCoordinationMode(mode: CoordinationMode): void {
    this.coordinationMode = mode;
  }

  getCoordinationMode(): CoordinationMode {
    return this.coordinationMode;
  }

  async processMessage(
    message: string,
    conversationHistory: MultiAgentMessage[]
  ): Promise<MultiAgentMessage[]> {
    switch (this.coordinationMode) {
      case 'sequential':
        return this.processSequential(message, conversationHistory);
      case 'parallel':
        return this.processParallel(message, conversationHistory);
      case 'collaborative':
        return this.processCollaborative(message, conversationHistory);
      case 'debate':
        return this.processDebate(message, conversationHistory);
      default:
        return this.processCollaborative(message, conversationHistory);
    }
  }

  private async processSequential(
    message: string,
    history: MultiAgentMessage[]
  ): Promise<MultiAgentMessage[]> {
    const selectedAgents = this.selectAgentsForTask(message);
    const responses: MultiAgentMessage[] = [];

    let currentContext = [...history];

    for (const agent of selectedAgents) {
      const response = await agent.generateResponse([
        ...currentContext,
        {
          role: 'user',
          content: message,
          timestamp: new Date().toISOString(),
        },
      ]);

      const agentMessage: MultiAgentMessage = {
        role: 'assistant',
        content: response as string,
        agentName: agent.config.name,
        agentType: agent.config.role,
        timestamp: new Date().toISOString(),
        interactions: agent.getInteractions(),
      };

      responses.push(agentMessage);
      currentContext.push(agentMessage);
    }

    return responses;
  }

  private async processParallel(
    message: string,
    history: MultiAgentMessage[]
  ): Promise<MultiAgentMessage[]> {
    const selectedAgents = this.selectAgentsForTask(message);

    const responsePromises = selectedAgents.map(async (agent) => {
      const response = await agent.generateResponse([
        ...history,
        {
          role: 'user',
          content: message,
          timestamp: new Date().toISOString(),
        },
      ]);

      const agentMessage: MultiAgentMessage = {
        role: 'assistant',
        content: response as string,
        agentName: agent.config.name,
        agentType: agent.config.role,
        timestamp: new Date().toISOString(),
        interactions: agent.getInteractions(),
      };

      return agentMessage;
    });

    return await Promise.all(responsePromises);
  }

  private async processCollaborative(
    message: string,
    history: MultiAgentMessage[]
  ): Promise<MultiAgentMessage[]> {
    const selectedAgents = this.selectAgentsForTask(message);
    const responses: MultiAgentMessage[] = [];

    const primaryAgent = selectedAgents[0];
    const supportingAgents = selectedAgents.slice(1);

    for (const supportAgent of supportingAgents) {
      const consultation = await primaryAgent.consultAgent(
        supportAgent,
        `I need your expertise on: ${message}`,
        history
      );

      responses.push({
        role: 'assistant',
        content: consultation,
        agentName: supportAgent.config.name,
        agentType: supportAgent.config.role,
        timestamp: new Date().toISOString(),
        isInternal: true,
        targetAgent: primaryAgent.config.name,
      });
    }

    const finalResponse = await primaryAgent.generateResponse([
      ...history,
      ...responses,
      {
        role: 'user',
        content: message,
        timestamp: new Date().toISOString(),
      },
    ]);

    responses.push({
      role: 'assistant',
      content: finalResponse as string,
      agentName: primaryAgent.config.name,
      agentType: primaryAgent.config.role,
      timestamp: new Date().toISOString(),
      interactions: primaryAgent.getInteractions(),
    });

    return responses;
  }

  private async processDebate(
    message: string,
    history: MultiAgentMessage[]
  ): Promise<MultiAgentMessage[]> {
    const selectedAgents = this.selectAgentsForTask(message).slice(0, 3);
    const responses: MultiAgentMessage[] = [];
    const rounds = 2;

    for (let round = 0; round < rounds; round++) {
      for (const agent of selectedAgents) {
        const response = await agent.generateResponse([
          ...history,
          ...responses,
          {
            role: 'user',
            content: round === 0
              ? message
              : `Continue the debate, considering previous responses: ${message}`,
            timestamp: new Date().toISOString(),
          },
        ]);

        responses.push({
          role: 'assistant',
          content: response as string,
          agentName: agent.config.name,
          agentType: agent.config.role,
          timestamp: new Date().toISOString(),
          metadata: { round, debatePosition: selectedAgents.indexOf(agent) },
        });
      }
    }

    const synthesizer = this.getAgent('general');
    const synthesis = await synthesizer.generateResponse([
      ...history,
      ...responses,
      {
        role: 'user',
        content: `Synthesize the debate above into a coherent response for: ${message}`,
        timestamp: new Date().toISOString(),
      },
    ]);

    responses.push({
      role: 'assistant',
      content: synthesis as string,
      agentName: 'Synthesis Agent',
      agentType: 'general',
      timestamp: new Date().toISOString(),
      metadata: { type: 'debate_synthesis' },
    });

    return responses;
  }

  private selectAgentsForTask(message: string): EnhancedAgent[] {
    const agentScores = this.getAllAgents().map((agent) => ({
      agent,
      confidence: agent.getConfidence(message),
    }));

    agentScores.sort((a, b) => b.confidence - a.confidence);

    const selected = agentScores
      .filter((score) => score.confidence > 0.3)
      .slice(0, 3)
      .map((score) => score.agent);

    if (selected.length === 0) {
      selected.push(this.getAgent('general'));
    }

    return selected;
  }

  async routeMessage(
    message: string,
    conversationHistory: MultiAgentMessage[]
  ): Promise<{ agent: EnhancedAgent; reason: string; allAgents?: EnhancedAgent[] }> {
    const selectedAgents = this.selectAgentsForTask(message);

    return {
      agent: selectedAgents[0],
      reason: `Selected ${selectedAgents[0].config.name} (confidence: ${selectedAgents[0].getConfidence(message).toFixed(2)})`,
      allAgents: selectedAgents,
    };
  }
}
