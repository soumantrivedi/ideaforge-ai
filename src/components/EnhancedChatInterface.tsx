import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, Sparkles, Users, Zap, Download, FileText, Paperclip, X, Eye, ArrowUp } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { MultiAgentMessage, CoordinationMode } from '../agents/multi-agent-system';
import { ContentFormatter } from '../lib/content-formatter';
import { AgentMetadataPanel } from './AgentMetadataPanel';
import { AgentStatusPanel } from './AgentStatusPanel';
import { HorizontalAgentStatus } from './HorizontalAgentStatus';
import { useAuth } from '../contexts/AuthContext';
import { getValidatedApiUrl } from '../lib/runtime-config';

const API_URL = getValidatedApiUrl();

interface LifecyclePhase {
  id: string;
  phase_name: string;
  phase_order: number;
  description: string;
  icon: string;
}

interface EnhancedChatInterfaceProps {
  messages: MultiAgentMessage[];
  onSendMessage: (content: string) => Promise<void>;
  isLoading: boolean;
  coordinationMode: CoordinationMode;
  onCoordinationModeChange: (mode: CoordinationMode) => void;
  activeAgents?: string[];
  productId?: string;
  onExport?: () => void;
  streamingMessage?: MultiAgentMessage | null;
  currentAgent?: string | null;
  streamingProgress?: number;
  useStreaming?: boolean;
  onStreamingToggle?: (enabled: boolean) => void;
  phases?: LifecyclePhase[];
  agentStatuses?: any[];
  agentInteractions?: any[];
  onPhaseSelect?: (phase: LifecyclePhase) => void;
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
  streamingMessage = null,
  currentAgent = null,
  streamingProgress = 0,
  useStreaming = true,
  onStreamingToggle,
  phases = [],
  agentStatuses = [],
  agentInteractions = [],
  onPhaseSelect,
}: EnhancedChatInterfaceProps) {
  // Calculate if last message is streaming
  const isLastMessageStreaming = isLoading && (streamingMessage !== null && streamingMessage !== undefined);
  const [input, setInput] = useState('');
  const [showFileUpload, setShowFileUpload] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const [expandedMetadataIndex, setExpandedMetadataIndex] = useState<number | null>(null);
  const [productName, setProductName] = useState<string>('');
  const [showScrollToTop, setShowScrollToTop] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { token } = useAuth();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const scrollToTop = () => {
    messagesContainerRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Smooth scroll during streaming - use requestAnimationFrame and debounce
  useEffect(() => {
    if (isLastMessageStreaming) {
      // During streaming, scroll smoothly with requestAnimationFrame
      const scrollId = requestAnimationFrame(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
      });
      return () => cancelAnimationFrame(scrollId);
    } else {
      // When not streaming, scroll immediately
      scrollToBottom();
    }
  }, [messages, isLastMessageStreaming]);

  // Show/hide scroll to top button based on scroll position
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const scrollTop = container.scrollTop;
      setShowScrollToTop(scrollTop > 300); // Show button after scrolling 300px
    };

    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, []);

  // Fetch product name when productId changes
  useEffect(() => {
    if (productId && token) {
      fetchProductName();
    } else {
      setProductName('');
    }
  }, [productId, token]);

  const fetchProductName = async () => {
    if (!productId || !token) return;
    
    try {
      const response = await fetch(`${API_URL}/api/products/${productId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setProductName(data.name || '');
      }
    } catch (error) {
      console.error('Error fetching product name:', error);
    }
  };

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

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    setAttachedFiles(prev => [...prev, ...files]);
    setShowFileUpload(false);
  };

  const handleRemoveFile = (index: number) => {
    setAttachedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if ((input.trim() || attachedFiles.length > 0) && !isLoading) {
      // Include file information in message
      const messageContent = input.trim();
      const fileInfo = attachedFiles.length > 0 
        ? `\n[Attached ${attachedFiles.length} file(s): ${attachedFiles.map(f => f.name).join(', ')}]`
        : '';
      await onSendMessage(messageContent + fileInfo);
      setInput('');
      setAttachedFiles([]);
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
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
    <div className="flex flex-col h-full bg-white rounded-2xl shadow-xl border border-gray-100 relative z-0">
      <div className="p-6 border-b border-gray-100 bg-gradient-to-r from-slate-50 to-gray-50">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl">
              <Users className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900">
                {productName || 'Chat with Agents'}
              </h2>
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

      <div ref={messagesContainerRef} className="flex-1 overflow-y-auto px-4 sm:px-6 md:px-8 lg:px-12 py-6 space-y-8 relative">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <div className="w-20 h-20 bg-gradient-to-br from-blue-100 to-purple-100 rounded-full flex items-center justify-center mb-4">
              <Bot className="w-10 h-10 text-blue-600" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">
              {productName ? `Start working on ${productName}` : 'Start a Product Conversation'}
            </h3>
            <p className="text-gray-600 max-w-md mb-6">
              {phases.length > 0 
                ? 'Select a product lifecycle phase to begin. Our AI agents will help you complete each phase.'
                : 'Ask questions and watch multiple AI agents collaborate to provide comprehensive answers.'}
            </p>
            {phases.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-left max-w-2xl w-full">
                {phases
                  .sort((a, b) => a.phase_order - b.phase_order)
                  .map((phase) => (
                    <button
                      key={phase.id}
                      onClick={() => {
                        // Always send to chatbot instead of opening modal
                        // Build comprehensive prompt with all phase questions
                        const phaseQuestions = phase.template_prompts || [];
                        const phaseFields = phase.required_fields || [];
                        
                        let prompt = `I want to work on the **${phase.phase_name}** phase.\n\n`;
                        prompt += `${phase.description || ''}\n\n`;
                        
                        if (phaseQuestions.length > 0) {
                          prompt += `Please guide me through the following questions step by step:\n\n`;
                          phaseQuestions.forEach((question, index) => {
                            const fieldName = phaseFields[index] || `Question ${index + 1}`;
                            // Skip design_mockups field as it's auto-generated
                            if (fieldName !== 'design_mockups') {
                              prompt += `${index + 1}. ${question}\n`;
                            }
                          });
                          prompt += `\nPlease ask me these questions one at a time, wait for my response, and then move to the next question. After collecting all answers, help me refine and complete this phase.`;
                        } else {
                          prompt += `Please help me complete this phase by asking relevant questions and guiding me through the process.`;
                        }
                        
                        onSendMessage(prompt);
                      }}
                      className="p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all text-left group cursor-pointer"
                    >
                      <div className="flex items-center gap-3 mb-2">
                        <span className="text-2xl">{phase.icon || '📋'}</span>
                        <div className="font-semibold text-sm text-gray-900 group-hover:text-blue-900">
                          {phase.phase_name}
                        </div>
                      </div>
                      {phase.description && (
                        <div className="text-xs text-gray-600 group-hover:text-gray-700 ml-11">
                          {phase.description}
                        </div>
                      )}
                    </button>
                  ))}
              </div>
            ) : (
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
            )}
          </div>
        ) : (
          (Array.isArray(messages) ? messages : [])
            .filter((msg) => !msg.isInternal)
            .map((message, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.05 }}
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
                  className={`flex flex-col w-full max-w-[85%] sm:max-w-[90%] md:max-w-[92%] ${
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
                      {message.metadata && (message.metadata.system_context || message.metadata.system_prompt || message.metadata.user_prompt || message.metadata.rag_context) && (
                        <button
                          onClick={() => setExpandedMetadataIndex(expandedMetadataIndex === index ? null : index)}
                          className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1 transition-colors"
                          title="View agent details"
                        >
                          <Eye className="w-3 h-3" />
                          Details
                        </button>
                      )}
                    </div>
                  )}

                  <div
                    className={`px-6 py-4 rounded-2xl shadow-sm ${
                      message.role === 'user'
                        ? 'bg-gradient-to-r from-blue-600 to-blue-500 text-white'
                        : 'bg-white text-gray-900 border border-gray-200 shadow-sm'
                    }`}
                  >
                    {message.role === 'user' ? (
                      // Format user messages if they contain markdown/HTML, otherwise display as plain text
                      (message.content.includes('##') || message.content.includes('###') || message.content.includes('**') || message.content.includes('<') || message.content.includes('`')) ? (
                        <div className="chat-message-content prose prose-base max-w-none break-words">
                          <div
                            className="text-base leading-[1.75] font-normal transition-all duration-75 ease-out"
                            dangerouslySetInnerHTML={{
                              __html: ContentFormatter.markdownToHtml(message.content),
                            }}
                          />
                        </div>
                      ) : (
                        <div className="whitespace-pre-wrap break-words text-base leading-[1.75] font-normal">
                          {message.content}
                        </div>
                      )
                    ) : (
                      <div className="chat-message-content prose prose-base max-w-none break-words">
                        <div
                          className="text-base leading-[1.75] font-normal transition-all duration-75 ease-out"
                          dangerouslySetInnerHTML={{
                            __html: ContentFormatter.markdownToHtml(message.content),
                          }}
                        />
                        {isLastMessageStreaming && index === messages.length - 1 && (
                          <span className="inline-block w-2 h-5 ml-1 bg-purple-500 animate-pulse rounded-sm" />
                        )}
                      </div>
                    )}
                  </div>

                  {message.timestamp && (
                    <span className="text-xs text-gray-400 mt-1 px-1">
                      {new Date(message.timestamp).toLocaleTimeString()}
                    </span>
                  )}
                  
                  {/* Agent Metadata Panel */}
                  {expandedMetadataIndex === index && message.metadata && message.role === 'assistant' && (
                    <AgentMetadataPanel
                      agentName={message.agentName || 'Assistant'}
                      metadata={message.metadata}
                      onClose={() => setExpandedMetadataIndex(null)}
                    />
                  )}
                </div>

                       {message.role === 'user' && (
                         <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-blue-500 flex items-center justify-center text-white shadow-lg">
                           <User className="w-5 h-5" />
                         </div>
                       )}
                     </motion.div>
                   ))
        )}

        {isLoading && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex gap-4 justify-start"
          >
            <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white shadow-lg">
              <Bot className="w-5 h-5" />
            </div>
            <div className="flex flex-col items-start">
              <span className="text-xs font-semibold text-gray-700 mb-1">
                {currentAgent ? `${currentAgent} thinking...` : 'Agents thinking...'}
              </span>
              <div className="px-5 py-3 rounded-2xl bg-gray-50 border border-gray-100">
                <div className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                  <span className="text-sm text-gray-600">
                    {currentAgent ? `Processing with ${currentAgent}` : 'Processing with multiple agents'}
                  </span>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* File attachments display */}
      {attachedFiles.length > 0 && (
        <div className="px-6 py-2 border-t border-gray-100 bg-gray-50">
          <div className="flex items-center gap-2 flex-wrap">
            {attachedFiles.map((file, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 border border-blue-200 rounded-lg"
              >
                <FileText className="w-4 h-4 text-blue-600" />
                <span className="text-sm text-blue-900 truncate max-w-[200px]">{file.name}</span>
                <button
                  onClick={() => handleRemoveFile(index)}
                  className="p-0.5 hover:bg-blue-100 rounded"
                >
                  <X className="w-3 h-3 text-blue-600" />
                </button>
              </motion.div>
            ))}
          </div>
        </div>
      )}

        <form onSubmit={handleSubmit} className="px-4 sm:px-6 md:px-8 lg:px-12 py-4 border-t border-gray-200 bg-white flex items-end gap-3">
        <input
          ref={fileInputRef}
          type="file"
          multiple
          onChange={handleFileSelect}
          className="hidden"
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="flex-shrink-0 p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition"
          title="Attach file"
        >
          <Paperclip className="w-5 h-5" />
        </button>
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything... Multiple agents will collaborate on your question"
          className="flex-1 resize-none overflow-y-auto px-5 py-3 bg-white rounded-xl border border-gray-300 text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm text-base leading-relaxed font-normal"
          rows={1}
          disabled={isLoading}
        />
        <button
          type="submit"
          className="flex items-center justify-center w-10 h-10 rounded-xl bg-blue-600 text-white hover:bg-blue-700 transition disabled:bg-blue-300 disabled:cursor-not-allowed shadow-md"
          disabled={(!input.trim() && attachedFiles.length === 0) || isLoading}
        >
          {isLoading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
        </button>
      </form>
      
      {/* Agent Status Panel - Footer */}
      <div className="px-4 sm:px-6 md:px-8 lg:px-12 py-3 border-t border-gray-100 bg-gray-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-gray-600">Active Agents:</span>
            <HorizontalAgentStatus
              agents={agentStatuses || []}
              agentInteractions={agentInteractions || []}
            />
          </div>
          {agentStatuses.length === 0 && agentInteractions.length === 0 && (
            <span className="text-xs text-gray-400">No agents active</span>
          )}
        </div>
      </div>
      
      {/* Scroll to Top Button - Bottom Right */}
      {showScrollToTop && (
        <button
          onClick={scrollToTop}
          className="absolute bottom-20 right-6 p-2.5 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 transition-all z-20 opacity-90 hover:opacity-100"
          title="Go to top"
          aria-label="Scroll to top"
        >
          <ArrowUp className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
