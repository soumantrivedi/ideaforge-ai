/**
 * Enhanced Chat Interface with Streaming Support
 * Provides real-time streaming responses with smooth UI updates
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Bot, User, Loader2, Sparkles, Users, Zap, Download, FileText, Radio } from 'lucide-react';
import type { MultiAgentMessage, CoordinationMode } from '../agents/multi-agent-system';
import { ContentFormatter } from '../lib/content-formatter';
import { streamMultiAgentSSE, WebSocketStreamingClient, StreamingEvent } from '../lib/streaming-client';
import { getValidatedApiUrl } from '../lib/api-client';

const API_URL = getValidatedApiUrl();

interface StreamingChatInterfaceProps {
  messages: MultiAgentMessage[];
  onSendMessage: (content: string) => Promise<void>;
  isLoading: boolean;
  coordinationMode: CoordinationMode;
  onCoordinationModeChange: (mode: CoordinationMode) => void;
  activeAgents?: string[];
  productId?: string;
  onExport?: () => void;
  token?: string;
  useStreaming?: boolean; // Toggle for streaming vs regular
}

export function StreamingChatInterface({
  messages = [],
  onSendMessage,
  isLoading: externalIsLoading,
  coordinationMode,
  onCoordinationModeChange,
  activeAgents = [],
  productId,
  onExport,
  token,
  useStreaming = true,
}: StreamingChatInterfaceProps) {
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState<MultiAgentMessage | null>(null);
  const [currentAgent, setCurrentAgent] = useState<string | null>(null);
  const [streamingProgress, setStreamingProgress] = useState(0);
  const [streamingStatus, setStreamingStatus] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const wsClientRef = useRef<WebSocketStreamingClient | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingMessage]);

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (wsClientRef.current) {
        wsClientRef.current.disconnect();
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const handleStreamingResponse = useCallback(async (content: string) => {
    if (!token || !productId) return;

    const userMessage: MultiAgentMessage = {
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };

    const updatedMessages = [...messages, userMessage];
    onSendMessage(content); // Update parent state

    setIsStreaming(true);
    setStreamingMessage({
      role: 'assistant',
      content: '',
      agentName: 'Streaming...',
      timestamp: new Date().toISOString(),
      interactions: [],
    });

    try {
      // Determine supporting agents
      let supportingAgents: string[] = ['rag'];
      const queryLower = content.toLowerCase();
      if (queryLower.includes('research') || queryLower.includes('market')) {
        supportingAgents.push('research');
      }
      if (queryLower.includes('analyze') || queryLower.includes('swot')) {
        supportingAgents.push('analysis');
      }
      if (queryLower.includes('idea') || queryLower.includes('brainstorm')) {
        supportingAgents.push('ideation');
      }
      if (supportingAgents.length === 1) {
        supportingAgents.push('research', 'analysis');
      }

      const request = {
        user_id: '00000000-0000-0000-0000-000000000000',
        product_id: productId,
        query: content,
        coordination_mode: 'enhanced_collaborative',
        supporting_agents: supportingAgents,
        context: {
          product_id: productId,
          message_history: messages,
        },
      };

      if (useStreaming) {
        // Use SSE streaming
        abortControllerRef.current = new AbortController();
        let accumulatedContent = '';
        let interactions: any[] = [];

        const result = await streamMultiAgentSSE(request, token, API_URL, {
          onAgentStart: (agent) => {
            setCurrentAgent(agent);
            setStreamingStatus(`${agent} is processing...`);
          },
          onChunk: (chunk, agent) => {
            accumulatedContent += chunk;
            setStreamingMessage((prev) => ({
              ...prev!,
              content: accumulatedContent,
              agentName: agent,
            }));
            scrollToBottom();
          },
          onAgentComplete: (agent, response) => {
            setStreamingStatus(`${agent} completed`);
            accumulatedContent += response;
          },
          onProgress: (progress, message) => {
            setStreamingProgress(progress);
            setStreamingStatus(message);
          },
          onComplete: (response, agentInteractions, metadata) => {
            accumulatedContent = response;
            interactions = agentInteractions;
            setStreamingMessage((prev) => ({
              ...prev!,
              content: accumulatedContent,
              agentName: metadata?.primary_agent || 'Assistant',
              interactions: agentInteractions,
            }));
            setIsStreaming(false);
            setCurrentAgent(null);
            setStreamingProgress(1);
            setStreamingStatus('Complete');
            
            // Update parent with final message
            const finalMessage: MultiAgentMessage = {
              role: 'assistant',
              content: accumulatedContent,
              agentName: metadata?.primary_agent || 'Assistant',
              timestamp: new Date().toISOString(),
              interactions: agentInteractions,
            };
            onSendMessage(accumulatedContent);
          },
          onError: (error) => {
            console.error('Streaming error:', error);
            setIsStreaming(false);
            setStreamingStatus(`Error: ${error}`);
          },
        });

        // Final message update
        if (result.response) {
          const finalMessage: MultiAgentMessage = {
            role: 'assistant',
            content: result.response,
            agentName: 'Assistant',
            timestamp: new Date().toISOString(),
            interactions: result.interactions,
          };
          setStreamingMessage(null);
        }
      } else {
        // Fallback to regular non-streaming request
        const response = await fetch(`${API_URL}/api/multi-agent/process`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(request),
        });

        if (response.ok) {
          const data = await response.json();
          const assistantMessage: MultiAgentMessage = {
            role: 'assistant',
            content: data.response || 'No response',
            agentName: data.primary_agent || 'Assistant',
            timestamp: new Date().toISOString(),
            interactions: data.agent_interactions || [],
          };
          setStreamingMessage(null);
          onSendMessage(data.response);
        } else {
          throw new Error('Failed to get response');
        }
      }
    } catch (error) {
      console.error('Error in streaming:', error);
      setIsStreaming(false);
      setStreamingMessage(null);
      setStreamingStatus('Error occurred');
    }
  }, [token, productId, messages, useStreaming, onSendMessage]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isStreaming && !externalIsLoading) {
      const content = input;
      setInput('');
      await handleStreamingResponse(content);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as any);
    }
  };

  const displayMessages = [...messages];
  if (streamingMessage) {
    displayMessages.push(streamingMessage);
  }

  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      {/* Header with streaming indicator */}
      <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-purple-500" />
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            AI Assistant {useStreaming && <span className="text-xs text-purple-500">(Streaming)</span>}
          </h2>
        </div>
        {isStreaming && (
          <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>{streamingStatus || 'Processing...'}</span>
            {currentAgent && (
              <span className="px-2 py-1 bg-purple-100 dark:bg-purple-900 rounded text-purple-700 dark:text-purple-300">
                {currentAgent}
              </span>
            )}
            {streamingProgress > 0 && (
              <div className="w-24 h-1 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-purple-500 transition-all duration-300"
                  style={{ width: `${streamingProgress * 100}%` }}
                />
              </div>
            )}
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {displayMessages.map((message, idx) => (
          <div
            key={idx}
            className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {message.role === 'assistant' && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                <Bot className="w-5 h-5 text-white" />
              </div>
            )}
            <div
              className={`max-w-[80%] rounded-lg p-4 ${
                message.role === 'user'
                  ? 'bg-blue-500 text-white'
                  : 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-sm'
              }`}
            >
              {message.role === 'assistant' && message.agentName && (
                <div className="text-xs font-semibold mb-2 text-purple-600 dark:text-purple-400">
                  {message.agentName}
                </div>
              )}
              <div 
                className="prose prose-sm dark:prose-invert max-w-none"
                dangerouslySetInnerHTML={{
                  __html: ContentFormatter.markdownToHtml(message.content),
                }}
              />
              {message.role === 'assistant' && idx === displayMessages.length - 1 && isStreaming && (
                <span className="inline-block w-2 h-4 ml-1 bg-purple-500 animate-pulse" />
              )}
            </div>
            {message.role === 'user' && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                <User className="w-5 h-5 text-white" />
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message... (Shift+Enter for new line)"
            className="flex-1 min-h-[60px] max-h-[200px] p-3 border border-slate-300 dark:border-slate-600 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-purple-500 dark:bg-slate-700 dark:text-slate-100"
            disabled={isStreaming || externalIsLoading}
          />
          <button
            type="submit"
            disabled={!input.trim() || isStreaming || externalIsLoading}
            className="px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg hover:from-purple-600 hover:to-pink-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2"
          >
            {isStreaming ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

