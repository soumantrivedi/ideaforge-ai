import OpenAI from 'openai';
import Anthropic from '@anthropic-ai/sdk';
import { GoogleGenAI } from '@google/genai';

export type AIProvider = 'openai' | 'claude' | 'gemini';

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface StreamChunk {
  content: string;
  done: boolean;
}

export interface AIConfig {
  openaiKey?: string;
  claudeKey?: string;
  geminiKey?: string;
}

export class AIProviderManager {
  private openai?: OpenAI;
  private claude?: Anthropic;
  private gemini?: GoogleGenAI;

  constructor(config: AIConfig) {
    if (config.openaiKey) {
      this.openai = new OpenAI({ apiKey: config.openaiKey, dangerouslyAllowBrowser: true });
    }
    if (config.claudeKey) {
      this.claude = new Anthropic({ apiKey: config.claudeKey, dangerouslyAllowBrowser: true });
    }
    if (config.geminiKey) {
      this.gemini = new GoogleGenAI({ apiKey: config.geminiKey });
    }
  }

  async generateResponse(
    provider: AIProvider,
    messages: Message[],
    options?: { model?: string; temperature?: number; maxTokens?: number }
  ): Promise<string> {
    switch (provider) {
      case 'openai':
        return this.generateOpenAI(messages, options);
      case 'claude':
        return this.generateClaude(messages, options);
      case 'gemini':
        return this.generateGemini(messages, options);
      default:
        throw new Error(`Unknown provider: ${provider}`);
    }
  }

  async *streamResponse(
    provider: AIProvider,
    messages: Message[],
    options?: { model?: string; temperature?: number; maxTokens?: number }
  ): AsyncGenerator<StreamChunk> {
    switch (provider) {
      case 'openai':
        yield* this.streamOpenAI(messages, options);
        break;
      case 'claude':
        yield* this.streamClaude(messages, options);
        break;
      case 'gemini':
        yield* this.streamGemini(messages, options);
        break;
      default:
        throw new Error(`Unknown provider: ${provider}`);
    }
  }

  private async generateOpenAI(
    messages: Message[],
    options?: { model?: string; temperature?: number; maxTokens?: number }
  ): Promise<string> {
    if (!this.openai) throw new Error('OpenAI not configured');

    const response = await this.openai.chat.completions.create({
      model: options?.model || 'gpt-5.1',
      messages: messages as OpenAI.Chat.ChatCompletionMessageParam[],
      temperature: options?.temperature || 0.7,
      max_tokens: options?.maxTokens || 2000,
    });

    return response.choices[0]?.message?.content || '';
  }

  private async *streamOpenAI(
    messages: Message[],
    options?: { model?: string; temperature?: number; maxTokens?: number }
  ): AsyncGenerator<StreamChunk> {
    if (!this.openai) throw new Error('OpenAI not configured');

    const stream = await this.openai.chat.completions.create({
      model: options?.model || 'gpt-5.1',
      messages: messages as OpenAI.Chat.ChatCompletionMessageParam[],
      temperature: options?.temperature || 0.7,
      max_tokens: options?.maxTokens || 2000,
      stream: true,
    });

    for await (const chunk of stream) {
      const content = chunk.choices[0]?.delta?.content || '';
      if (content) {
        yield { content, done: false };
      }
    }

    yield { content: '', done: true };
  }

  private async generateClaude(
    messages: Message[],
    options?: { model?: string; temperature?: number; maxTokens?: number }
  ): Promise<string> {
    if (!this.claude) throw new Error('Claude not configured');

    const systemMessage = messages.find((m) => m.role === 'system');
    const conversationMessages = messages.filter((m) => m.role !== 'system');

    const response = await this.claude.messages.create({
      model: options?.model || 'claude-sonnet-4-20250522',
      max_tokens: options?.maxTokens || 2000,
      temperature: options?.temperature || 0.7,
      system: systemMessage?.content,
      messages: conversationMessages.map((m) => ({
        role: m.role === 'assistant' ? 'assistant' : 'user',
        content: m.content,
      })),
    });

    return response.content[0].type === 'text' ? response.content[0].text : '';
  }

  private async *streamClaude(
    messages: Message[],
    options?: { model?: string; temperature?: number; maxTokens?: number }
  ): AsyncGenerator<StreamChunk> {
    if (!this.claude) throw new Error('Claude not configured');

    const systemMessage = messages.find((m) => m.role === 'system');
    const conversationMessages = messages.filter((m) => m.role !== 'system');

    const stream = await this.claude.messages.create({
      model: options?.model || 'claude-sonnet-4-20250522',
      max_tokens: options?.maxTokens || 2000,
      temperature: options?.temperature || 0.7,
      system: systemMessage?.content,
      messages: conversationMessages.map((m) => ({
        role: m.role === 'assistant' ? 'assistant' : 'user',
        content: m.content,
      })),
      stream: true,
    });

    for await (const event of stream) {
      if (event.type === 'content_block_delta' && event.delta.type === 'text_delta') {
        yield { content: event.delta.text, done: false };
      }
    }

    yield { content: '', done: true };
  }

  private async generateGemini(
    messages: Message[],
    options?: { model?: string; temperature?: number; maxTokens?: number }
  ): Promise<string> {
    if (!this.gemini) throw new Error('Gemini not configured');

    const systemMessage = messages.find((m) => m.role === 'system');
    const conversationMessages = messages.filter((m) => m.role !== 'system');

    const contents = conversationMessages.map((m) => ({
      role: m.role === 'assistant' ? 'model' : 'user',
      parts: [{ text: m.content }],
    }));

    const response = await this.gemini.models.generateContent({
      model: options?.model || 'gemini-3.0-pro',
      contents,
      systemInstruction: systemMessage?.content,
      generationConfig: {
        temperature: options?.temperature || 0.7,
        maxOutputTokens: options?.maxTokens || 2000,
      },
    });

    return response.text || '';
  }

  private async *streamGemini(
    messages: Message[],
    options?: { model?: string; temperature?: number; maxTokens?: number }
  ): AsyncGenerator<StreamChunk> {
    if (!this.gemini) throw new Error('Gemini not configured');

    const systemMessage = messages.find((m) => m.role === 'system');
    const conversationMessages = messages.filter((m) => m.role !== 'system');

    const contents = conversationMessages.map((m) => ({
      role: m.role === 'assistant' ? 'model' : 'user',
      parts: [{ text: m.content }],
    }));

    const stream = await this.gemini.models.generateContentStream({
      model: options?.model || 'gemini-3.0-pro',
      contents,
      systemInstruction: systemMessage?.content,
      generationConfig: {
        temperature: options?.temperature || 0.7,
        maxOutputTokens: options?.maxTokens || 2000,
      },
    });

    for await (const chunk of stream) {
      const text = chunk.text;
      if (text) {
        yield { content: text, done: false };
      }
    }

    yield { content: '', done: true };
  }

  isProviderConfigured(provider: AIProvider): boolean {
    switch (provider) {
      case 'openai':
        return !!this.openai;
      case 'claude':
        return !!this.claude;
      case 'gemini':
        return !!this.gemini;
      default:
        return false;
    }
  }

  getConfiguredProviders(): AIProvider[] {
    const providers: AIProvider[] = [];
    if (this.openai) providers.push('openai');
    if (this.claude) providers.push('claude');
    if (this.gemini) providers.push('gemini');
    return providers;
  }
}
