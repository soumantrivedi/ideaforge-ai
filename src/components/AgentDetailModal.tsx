import { createPortal } from 'react-dom';
import { X, Bot, FileText, MessageSquare, Database, Sparkles } from 'lucide-react';

interface AgentInteraction {
  from_agent: string;
  to_agent: string;
  query: string;
  response: string;
  timestamp: string;
  metadata?: {
    system_context?: string;
    system_prompt?: string;
    rag_context?: string;
    user_prompt?: string;
    [key: string]: any;
  };
}

interface AgentDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  agentName: string;
  agentRole: string;
  interaction?: AgentInteraction;
}

export function AgentDetailModal({
  isOpen,
  onClose,
  agentName,
  agentRole,
  interaction,
}: AgentDetailModalProps) {
  if (!isOpen) return null;

  const metadata = interaction?.metadata || {};
  const systemContext = metadata.system_context || 'Not available';
  const systemPrompt = metadata.system_prompt || 'Not available';
  const ragContext = metadata.rag_context || 'No RAG context retrieved';
  const userPrompt = metadata.user_prompt || interaction?.query || 'Not available';
  const response = interaction?.response || 'Not available';

  // Use React Portal to render at document root, avoiding z-index stacking context issues
  const modalContent = (
    <div className="fixed inset-0 z-[99999]" style={{ isolation: 'isolate' }}>
      <div 
        className="fixed inset-0 bg-black bg-opacity-50"
        onClick={onClose}
      />
      <div 
        className="fixed inset-0 flex items-center justify-center p-4 pointer-events-none"
        onClick={(e) => e.stopPropagation()}
      >
        <div 
          className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col pointer-events-auto"
          onClick={(e) => e.stopPropagation()}
        >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-purple-500 to-pink-600 rounded-xl">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">{agentName}</h2>
              <p className="text-sm text-gray-600 capitalize">{agentRole.replace('_', ' ')}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-600" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* System Context */}
          <div className="bg-blue-50 rounded-xl p-4 border border-blue-100">
            <div className="flex items-center gap-2 mb-2">
              <FileText className="w-5 h-5 text-blue-600" />
              <h3 className="font-semibold text-blue-900">System Context</h3>
            </div>
            <p className="text-sm text-blue-800 whitespace-pre-wrap">{systemContext}</p>
          </div>

          {/* System Prompt */}
          <div className="bg-purple-50 rounded-xl p-4 border border-purple-100">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-5 h-5 text-purple-600" />
              <h3 className="font-semibold text-purple-900">System Prompt</h3>
            </div>
            <p className="text-sm text-purple-800 whitespace-pre-wrap">{systemPrompt}</p>
          </div>

          {/* RAG Context */}
          <div className="bg-teal-50 rounded-xl p-4 border border-teal-100">
            <div className="flex items-center gap-2 mb-2">
              <Database className="w-5 h-5 text-teal-600" />
              <h3 className="font-semibold text-teal-900">RAG Context</h3>
            </div>
            <p className="text-sm text-teal-800 whitespace-pre-wrap">{ragContext}</p>
          </div>

          {/* User Prompt */}
          <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
            <div className="flex items-center gap-2 mb-2">
              <MessageSquare className="w-5 h-5 text-gray-600" />
              <h3 className="font-semibold text-gray-900">User Prompt</h3>
            </div>
            <p className="text-sm text-gray-700 whitespace-pre-wrap">{userPrompt}</p>
          </div>

          {/* Response */}
          <div className="bg-green-50 rounded-xl p-4 border border-green-100">
            <div className="flex items-center gap-2 mb-2">
              <Bot className="w-5 h-5 text-green-600" />
              <h3 className="font-semibold text-green-900">Agent Response</h3>
            </div>
            <div className="text-sm text-green-800 whitespace-pre-wrap prose prose-sm max-w-none">
              {response}
            </div>
          </div>

          {/* Timestamp */}
          {interaction?.timestamp && (
            <div className="text-xs text-gray-500 text-center pt-2">
              Processed at: {new Date(interaction.timestamp).toLocaleString()}
            </div>
          )}
        </div>
        </div>
      </div>
    </div>
  );

  // Render modal using portal at document body level
  return typeof document !== 'undefined' 
    ? createPortal(modalContent, document.body)
    : null;
}

