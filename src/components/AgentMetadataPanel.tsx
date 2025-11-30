import { useState } from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown, ChevronUp, Code, FileText, MessageSquare, Brain, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface AgentMetadata {
  system_context?: string;
  system_prompt?: string;
  user_prompt?: string;
  rag_context?: string;
  [key: string]: any;
}

interface AgentMetadataPanelProps {
  agentName: string;
  metadata?: AgentMetadata;
  onClose?: () => void;
}

export function AgentMetadataPanel({ agentName, metadata, onClose }: AgentMetadataPanelProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['system_prompt', 'user_prompt']));

  const toggleSection = (section: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  };

  const sections = [
    {
      key: 'system_context',
      label: 'System Context',
      icon: <Brain className="w-4 h-4" />,
      content: metadata?.system_context,
    },
    {
      key: 'system_prompt',
      label: 'System Prompt',
      icon: <Code className="w-4 h-4" />,
      content: metadata?.system_prompt,
    },
    {
      key: 'user_prompt',
      label: 'User Prompt',
      icon: <MessageSquare className="w-4 h-4" />,
      content: metadata?.user_prompt,
    },
    {
      key: 'rag_context',
      label: 'RAG Context',
      icon: <FileText className="w-4 h-4" />,
      content: metadata?.rag_context,
    },
  ].filter(section => section.content && section.content !== 'N/A');

  if (!metadata || sections.length === 0) {
    return null;
  }

  // Use React Portal to render at document root, avoiding z-index stacking context issues
  const modalContent = (
    <div className="fixed inset-0 z-[99999]" style={{ isolation: 'isolate' }}>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black bg-opacity-50"
        onClick={onClose}
      />
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        onClick={(e) => e.stopPropagation()}
        className="fixed inset-0 flex items-center justify-center p-4 pointer-events-none"
      >
        <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col pointer-events-auto">
          <div className="px-6 py-4 bg-gradient-to-r from-blue-50 to-purple-50 border-b border-gray-200 flex items-center justify-between sticky top-0 z-10 bg-white">
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-blue-600" />
            <span className="text-lg font-semibold text-gray-900">
              {agentName} - Agent Details
            </span>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
              title="Close"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          )}
        </div>

        <div className="flex-1 overflow-y-auto divide-y divide-gray-200">
          {sections.map((section) => {
            const isExpanded = expandedSections.has(section.key);
            return (
              <div key={section.key}>
                <button
                  onClick={() => toggleSection(section.key)}
                  className="w-full px-6 py-3 flex items-center justify-between hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-gray-500">{section.icon}</span>
                    <span className="text-sm font-medium text-gray-700">{section.label}</span>
                  </div>
                  {isExpanded ? (
                    <ChevronUp className="w-5 h-5 text-gray-400" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-gray-400" />
                  )}
                </button>
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div className="px-6 pb-4">
                        <pre className="text-sm text-gray-700 whitespace-pre-wrap break-words font-mono bg-gray-50 p-4 rounded-lg border border-gray-200 max-h-96 overflow-y-auto">
                          {section.content}
                        </pre>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </div>
        </div>
      </motion.div>
    </div>
  );

  // Render modal using portal at document body level
  return typeof document !== 'undefined' 
    ? createPortal(modalContent, document.body)
    : null;
}

