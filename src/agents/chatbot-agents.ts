import type { AIProvider, Message, AIProviderManager } from '../lib/ai-providers';
import type { RAGSystem } from '../lib/rag-system';

export type AgentRole =
  | 'general'
  | 'research'
  | 'coding'
  | 'creative'
  | 'analysis'
  | 'rag';

export interface AgentConfig {
  name: string;
  role: AgentRole;
  systemPrompt: string;
  provider: AIProvider;
  temperature?: number;
  useRAG?: boolean;
}

export interface ChatAgentMessage extends Message {
  agentName?: string;
  timestamp?: string;
}

export class ChatbotAgent {
  public config: AgentConfig;
  private aiManager: AIProviderManager;
  private ragSystem?: RAGSystem;

  constructor(
    config: AgentConfig,
    aiManager: AIProviderManager,
    ragSystem?: RAGSystem
  ) {
    this.config = config;
    this.aiManager = aiManager;
    this.ragSystem = ragSystem;
  }

  async generateResponse(
    messages: ChatAgentMessage[],
    options?: { stream?: boolean }
  ): Promise<string | AsyncGenerator<string>> {
    const conversationMessages = await this.prepareMessages(messages);

    if (options?.stream) {
      return this.streamResponse(conversationMessages);
    }

    return await this.aiManager.generateResponse(
      this.config.provider,
      conversationMessages,
      {
        temperature: this.config.temperature,
      }
    );
  }

  private async prepareMessages(
    messages: ChatAgentMessage[]
  ): Promise<Message[]> {
    const preparedMessages: Message[] = [
      {
        role: 'system',
        content: this.config.systemPrompt,
      },
    ];

    if (this.config.useRAG && this.ragSystem && messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      if (lastMessage.role === 'user') {
        const context = await this.ragSystem.getRelevantContext(
          lastMessage.content
        );
        preparedMessages.push({
          role: 'system',
          content: `${context}\n\nUse the above context to inform your response when relevant.`,
        });
      }
    }

    preparedMessages.push(
      ...messages.map((m) => ({
        role: m.role,
        content: m.content,
      }))
    );

    return preparedMessages;
  }

  private async *streamResponse(
    messages: Message[]
  ): AsyncGenerator<string> {
    const stream = this.aiManager.streamResponse(
      this.config.provider,
      messages,
      {
        temperature: this.config.temperature,
      }
    );

    for await (const chunk of stream) {
      if (!chunk.done && chunk.content) {
        yield chunk.content;
      }
    }
  }
}

export const AGENT_CONFIGS: Record<AgentRole, Omit<AgentConfig, 'provider'>> = {
  general: {
    name: 'General Assistant',
    role: 'general',
    systemPrompt: `You are a helpful, knowledgeable AI assistant. You provide clear, accurate, and friendly responses to user queries. You can help with a wide range of topics including general knowledge, problem-solving, and advice.`,
    temperature: 0.7,
    useRAG: true,
  },
  research: {
    name: 'Research Specialist',
    role: 'research',
    systemPrompt: `You are a research specialist AI. Your role is to:
- Conduct thorough research on topics
- Provide well-sourced information
- Analyze trends and patterns
- Identify key insights from data
- Present findings in a structured, clear manner
- Always cite sources and provide context`,
    temperature: 0.5,
    useRAG: true,
  },
  coding: {
    name: 'Code Expert',
    role: 'coding',
    systemPrompt: `You are an expert software developer and coding assistant. You:
- Write clean, efficient, well-documented code
- Explain programming concepts clearly
- Debug and optimize code
- Follow best practices and design patterns
- Support multiple programming languages
- Provide complete, runnable code examples
- Always include error handling and edge cases`,
    temperature: 0.3,
    useRAG: true,
  },
  creative: {
    name: 'Creative Writer',
    role: 'creative',
    systemPrompt: `You are a creative writing assistant. You excel at:
- Generating creative content (stories, poems, scripts)
- Brainstorming ideas
- Writing in various styles and tones
- Creating engaging narratives
- Developing characters and plots
- Providing constructive feedback on writing
Be imaginative, expressive, and help users unlock their creativity.`,
    temperature: 0.9,
    useRAG: false,
  },
  analysis: {
    name: 'Data Analyst',
    role: 'analysis',
    systemPrompt: `You are a data analysis and business intelligence expert. You:
- Analyze data and identify patterns
- Create insights from complex information
- Provide strategic recommendations
- Explain findings clearly to non-technical audiences
- Use statistical reasoning
- Consider multiple perspectives
- Focus on actionable insights`,
    temperature: 0.4,
    useRAG: true,
  },
  rag: {
    name: 'Knowledge Retrieval Agent',
    role: 'rag',
    systemPrompt: `You are a specialized knowledge retrieval assistant. You:
- Access and synthesize information from the knowledge base
- Provide accurate, contextual answers based on stored documents
- Clearly indicate when information comes from the knowledge base
- Ask clarifying questions when needed
- Suggest related topics from the knowledge base
- Always ground responses in available documentation`,
    temperature: 0.5,
    useRAG: true,
  },
};

export class MultiAgentOrchestrator {
  private agents: Map<AgentRole, ChatbotAgent>;
  private aiManager: AIProviderManager;
  private ragSystem?: RAGSystem;

  constructor(aiManager: AIProviderManager, ragSystem?: RAGSystem) {
    this.aiManager = aiManager;
    this.ragSystem = ragSystem;
    this.agents = new Map();
    this.initializeAgents();
  }

  private initializeAgents() {
    const providers = this.aiManager.getConfiguredProviders();
    if (providers.length === 0) {
      throw new Error('No AI providers configured');
    }

    const providerMap: Record<AgentRole, AIProvider> = {
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
        new ChatbotAgent(agentConfig, this.aiManager, this.ragSystem)
      );
    });
  }

  getAgent(role: AgentRole): ChatbotAgent {
    const agent = this.agents.get(role);
    if (!agent) {
      throw new Error(`Agent not found: ${role}`);
    }
    return agent;
  }

  getAllAgents(): ChatbotAgent[] {
    return Array.from(this.agents.values());
  }

  async routeMessage(
    message: string,
    conversationHistory: ChatAgentMessage[]
  ): Promise<{ agent: ChatbotAgent; reason: string }> {
    const lowerMessage = message.toLowerCase();

    if (
      lowerMessage.includes('code') ||
      lowerMessage.includes('program') ||
      lowerMessage.includes('debug') ||
      lowerMessage.includes('function')
    ) {
      return {
        agent: this.getAgent('coding'),
        reason: 'Message contains coding-related keywords',
      };
    }

    if (
      lowerMessage.includes('research') ||
      lowerMessage.includes('study') ||
      lowerMessage.includes('analyze') ||
      lowerMessage.includes('investigate')
    ) {
      return {
        agent: this.getAgent('research'),
        reason: 'Message requires research and analysis',
      };
    }

    if (
      lowerMessage.includes('creative') ||
      lowerMessage.includes('story') ||
      lowerMessage.includes('write') ||
      lowerMessage.includes('poem')
    ) {
      return {
        agent: this.getAgent('creative'),
        reason: 'Message requires creative writing',
      };
    }

    if (
      lowerMessage.includes('data') ||
      lowerMessage.includes('statistics') ||
      lowerMessage.includes('metrics') ||
      lowerMessage.includes('trends')
    ) {
      return {
        agent: this.getAgent('analysis'),
        reason: 'Message requires data analysis',
      };
    }

    if (
      lowerMessage.includes('knowledge base') ||
      lowerMessage.includes('documents') ||
      lowerMessage.includes('search')
    ) {
      return {
        agent: this.getAgent('rag'),
        reason: 'Message requires knowledge base access',
      };
    }

    return {
      agent: this.getAgent('general'),
      reason: 'General conversation',
    };
  }
}
