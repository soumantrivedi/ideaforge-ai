import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, Sparkles, Users, Zap, Download, FileText } from 'lucide-react';
import type { MultiAgentMessage, CoordinationMode } from '../agents/multi-agent-system';
import { ContentFormatter } from '../lib/content-formatter';

interface EnhancedChatInterfaceProps {
  messages: MultiAgentMessage[];
  onSendMessage: (content: string) => Promise<void>;
  isLoading: boolean;
  coordinationMode: CoordinationMode;
  onCoordinationModeChange: (mode: CoordinationMode) => void;
  activeAgents?: string[];
  productId?: string;
  onExport?: () => void;
}

export function EnhancedChatInterface({
  messages = [],
  onSendMessage,
  isLoading,
  coordinationMode,
  onCoordinationModeChange,
  activeAgents = [],
  productId,
  onExport,
}: EnhancedChatInterfaceProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Listen for focus chat input event (from Save to Chat)
  useEffect(() => {
    const handleFocusChatInput = (event: Event) => {
      const customEvent = event as CustomEvent;
      if (customEvent.detail && customEvent.detail.productId === productId) {
        // Focus the textarea after a short delay to ensure it's rendered
        setTimeout(() => {
          if (textareaRef.current) {
            textareaRef.current.focus();
            textareaRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          }
        }, 150);
      }
    };

    window.addEventListener('focusChatInput', handleFocusChatInput);
    return () => {
      window.removeEventListener('focusChatInput', handleFocusChatInput);
    };
  }, [productId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      await onSendMessage(input);
      setInput('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as any);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`;
  };

  const getAgentColor = (agentName?: string) => {
    const colors: Record<string, string> = {
      'General Assistant': 'from-blue-500 to-cyan-500',
      'Research Specialist': 'from-green-500 to-emerald-500',
      'Code Expert': 'from-orange-500 to-amber-500',
      'Creative Writer': 'from-pink-500 to-rose-500',
      'Data Analyst': 'from-purple-500 to-violet-500',
      'Knowledge Retrieval Agent': 'from-teal-500 to-cyan-500',
    };
    return colors[agentName || ''] || 'from-gray-500 to-slate-500';
  };

  const getAgentIcon = (agentName?: string) => {
    if (agentName?.includes('Code')) return '💻';
    if (agentName?.includes('Research')) return '🔬';
    if (agentName?.includes('Creative')) return '✨';
    if (agentName?.includes('Data')) return '📊';
    if (agentName?.includes('Knowledge')) return '📚';
    return '🤖';
  };

  const modeConfig = {
    sequential: {
      label: 'Sequential',
      description: 'Agents work one after another',
      icon: '📋',
      color: 'bg-blue-100 text-blue-700 border-blue-200',
    },
    parallel: {
      label: 'Parallel',
      description: 'All agents respond simultaneously',
      icon: '⚡',
      color: 'bg-purple-100 text-purple-700 border-purple-200',
    },
    collaborative: {
      label: 'Collaborative',
      description: 'Agents consult each other',
      icon: '🤝',
      color: 'bg-green-100 text-green-700 border-green-200',
    },
    debate: {
      label: 'Debate',
      description: 'Multiple perspectives, then synthesis',
      icon: '⚖️',
      color: 'bg-orange-100 text-orange-700 border-orange-200',
    },
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-2xl shadow-xl border border-gray-100">
      <div className="p-6 border-b border-gray-100 bg-gradient-to-r from-slate-50 to-gray-50">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl">
              <Users className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900">Multi-Agent Collaboration</h2>
              <p className="text-sm text-gray-600">
                {activeAgents.length > 0 ? `${activeAgents.length} agents active` : 'AI-powered conversation'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {onExport && (
              <button
                onClick={onExport}
                className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition"
                title="Export PRD"
              >
                <Download className="w-4 h-4" />
                Export PRD
              </button>
            )}
          </div>
        </div>

        {coordinationMode && (
          <p className="text-xs text-gray-500 mt-2 pl-1">
            {modeConfig[coordinationMode].description}
          </p>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <div className="w-20 h-20 bg-gradient-to-br from-blue-100 to-purple-100 rounded-full flex items-center justify-center mb-4">
              <Bot className="w-10 h-10 text-blue-600" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">
              Start a Multi-Agent Conversation
            </h3>
            <p className="text-gray-600 max-w-md mb-6">
              Ask questions and watch multiple AI agents collaborate to provide comprehensive answers.
            </p>
            <div className="grid grid-cols-2 gap-3 text-left max-w-lg">
              <div className="p-3 bg-blue-50 rounded-lg">
                <div className="font-semibold text-sm text-blue-900 mb-1">💻 Code</div>
                <div className="text-xs text-blue-700">Get expert coding help</div>
              </div>
              <div className="p-3 bg-green-50 rounded-lg">
                <div className="font-semibold text-sm text-green-900 mb-1">🔬 Research</div>
                <div className="text-xs text-green-700">Deep analysis & insights</div>
              </div>
              <div className="p-3 bg-pink-50 rounded-lg">
                <div className="font-semibold text-sm text-pink-900 mb-1">✨ Creative</div>
                <div className="text-xs text-pink-700">Stories & imagination</div>
              </div>
              <div className="p-3 bg-purple-50 rounded-lg">
                <div className="font-semibold text-sm text-purple-900 mb-1">📊 Analysis</div>
                <div className="text-xs text-purple-700">Data-driven decisions</div>
              </div>
            </div>
          </div>
        ) : (
          (Array.isArray(messages) ? messages : [])
            .filter((msg) => !msg.isInternal)
            .map((message, index) => (
              <div
                key={index}
                className={`flex gap-4 ${
                  message.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                {message.role === 'assistant' && (
                  <div className={`flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br ${getAgentColor(message.agentName)} flex items-center justify-center text-white font-bold shadow-lg`}>
                    {getAgentIcon(message.agentName)}
                  </div>
                )}

                <div
                  className={`flex flex-col max-w-[70%] ${
                    message.role === 'user' ? 'items-end' : 'items-start'
                  }`}
                >
                  {message.role === 'assistant' && message.agentName && (
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-semibold text-gray-700">
                        {message.agentName}
                      </span>
                      {message.interactions && Array.isArray(message.interactions) && message.interactions.length > 0 && (
                        <span className="text-xs text-gray-500 flex items-center gap-1">
                          <Zap className="w-3 h-3" />
                          {message.interactions.length} interactions
                        </span>
                      )}
                    </div>
                  )}

                  <div
                    className={`px-5 py-3 rounded-2xl shadow-sm ${
                      message.role === 'user'
                        ? 'bg-gradient-to-r from-blue-600 to-blue-500 text-white'
                        : 'bg-gray-50 text-gray-900 border border-gray-100'
                    }`}
                  >
                    {message.role === 'user' ? (
                      <div className="whitespace-pre-wrap break-words text-sm leading-relaxed">
                        {message.content}
                      </div>
                    ) : (
                      <div
                        className="prose prose-sm max-w-none break-words text-sm leading-relaxed"
                        dangerouslySetInnerHTML={{
                          __html: ContentFormatter.markdownToHtml(message.content),
                        }}
                      />
                    )}
                  </div>

                  {message.timestamp && (
                    <span className="text-xs text-gray-400 mt-1 px-1">
                      {new Date(message.timestamp).toLocaleTimeString()}
                    </span>
                  )}
                </div>

                {message.role === 'user' && (
                  <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-blue-500 flex items-center justify-center text-white shadow-lg">
                    <User className="w-5 h-5" />
                  </div>
                )}
              </div>
            ))
        )}

        {isLoading && (
          <div className="flex gap-4 justify-start">
            <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white shadow-lg">
              <Bot className="w-5 h-5" />
            </div>
            <div className="flex flex-col items-start">
              <span className="text-xs font-semibold text-gray-700 mb-1">
                Agents thinking...
              </span>
              <div className="px-5 py-3 rounded-2xl bg-gray-50 border border-gray-100">
                <div className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                  <span className="text-sm text-gray-600">Processing with multiple agents</span>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="p-6 border-t border-gray-100 bg-gray-50">
        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything... Multiple agents will collaborate on your question"
              className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none bg-white text-sm"
              rows={1}
              style={{ maxHeight: '200px' }}
            />
          </div>
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="px-5 py-3 bg-gradient-to-r from-blue-600 to-blue-500 text-white rounded-xl hover:from-blue-700 hover:to-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-lg hover:shadow-xl font-medium flex items-center gap-2"
          >
            <Send className="w-4 h-4" />
            Send
          </button>
        </div>
        <div className="mt-2 text-xs text-gray-500 px-1">
          Press Enter to send, Shift+Enter for new line
        </div>
      </form>
    </div>
  );
}
