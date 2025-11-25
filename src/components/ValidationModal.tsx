import { useState, useEffect } from 'react';
import { X, Star, CheckCircle2, AlertCircle, MessageSquare, Bot } from 'lucide-react';

interface ValidationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAccept: (score: number, feedback?: string) => void;
  onRefine: (feedback: string) => void;
  generatedContent: string;
  phaseName: string;
  formData: Record<string, string>;
  previousQuestions: Array<{ question: string; answer: string }>;
  agentInteractions?: Array<{
    from_agent: string;
    to_agent: string;
    query: string;
    response: string;
    metadata?: any;
  }>;
}

export function ValidationModal({
  isOpen,
  onClose,
  onAccept,
  onRefine,
  generatedContent,
  phaseName,
  formData,
  previousQuestions,
  agentInteractions = [],
}: ValidationModalProps) {
  const [score, setScore] = useState(5);
  const [feedback, setFeedback] = useState('');
  const [showRefinement, setShowRefinement] = useState(false);
  const [refinementFeedback, setRefinementFeedback] = useState('');

  useEffect(() => {
    if (isOpen) {
      setScore(5);
      setFeedback('');
      setShowRefinement(false);
      setRefinementFeedback('');
    }
  }, [isOpen]);

  if (!isOpen) return null;

  // Extract unique agents from interactions
  const activeAgents = new Set<string>();
  agentInteractions.forEach(interaction => {
    if (interaction.from_agent) activeAgents.add(interaction.from_agent);
    if (interaction.to_agent) activeAgents.add(interaction.to_agent);
  });

  const getAgentIcon = (role: string) => {
    const icons: Record<string, string> = {
      research: '🔬',
      analysis: '📊',
      ideation: '💡',
      prd_authoring: '📝',
      summary: '📄',
      scoring: '⭐',
      validation: '✅',
      export: '📤',
      rag: '📚',
      v0: '🎨',
      lovable: '🎭',
      github_mcp: '🐙',
      atlassian_mcp: '🔷',
    };
    return icons[role] || '🤖';
  };

  const getScoreColor = (score: number) => {
    if (score >= 4) return 'text-green-500';
    if (score >= 3) return 'text-yellow-500';
    return 'text-red-500';
  };

  const getScoreLabel = (score: number) => {
    if (score >= 4.5) return 'Excellent';
    if (score >= 4) return 'Very Good';
    if (score >= 3) return 'Good';
    if (score >= 2) return 'Fair';
    return 'Needs Improvement';
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-6 h-6" />
            <div>
              <h2 className="text-xl font-bold">Validate Generated Response</h2>
              <p className="text-sm text-blue-100">Phase: {phaseName}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-white hover:bg-white/20 rounded-full p-2 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Active Agents */}
          {activeAgents.size > 0 && (
            <div className="bg-gray-50 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                <Bot className="w-4 h-4" />
                Active Agents Used
              </h3>
              <div className="flex flex-wrap gap-2">
                {Array.from(activeAgents).map(agent => (
                  <span
                    key={agent}
                    className="inline-flex items-center gap-1 px-3 py-1 bg-white rounded-full text-sm border border-gray-200"
                  >
                    <span>{getAgentIcon(agent)}</span>
                    <span className="capitalize">{agent.replace('_', ' ')}</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Context: Previous Questions & Answers */}
          {previousQuestions.length > 0 && (
            <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
              <h3 className="text-sm font-semibold text-blue-900 mb-3 flex items-center gap-2">
                <MessageSquare className="w-4 h-4" />
                Context: Previous Questions & Answers
              </h3>
              <div className="space-y-3 max-h-48 overflow-y-auto">
                {previousQuestions.map((qa, idx) => (
                  <div key={idx} className="bg-white rounded p-3 border border-blue-100">
                    <p className="text-xs font-medium text-blue-700 mb-1">Q{idx + 1}: {qa.question}</p>
                    <p className="text-sm text-gray-700">{qa.answer}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Generated Content */}
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Generated Response</h3>
            <div className="bg-white rounded p-4 max-h-64 overflow-y-auto border border-gray-200">
              <pre className="whitespace-pre-wrap text-sm text-gray-800 font-sans">
                {generatedContent}
              </pre>
            </div>
          </div>

          {/* Scoring Section */}
          <div className="bg-yellow-50 rounded-lg p-4 border border-yellow-200">
            <h3 className="text-sm font-semibold text-yellow-900 mb-3">
              Rate the Quality of This Response
            </h3>
            <div className="flex items-center gap-4 mb-3">
              <div className="flex items-center gap-1">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    type="button"
                    onClick={() => setScore(star)}
                    className={`transition ${
                      star <= score
                        ? 'text-yellow-500 hover:text-yellow-600'
                        : 'text-gray-300 hover:text-yellow-400'
                    }`}
                  >
                    <Star
                      className={`w-8 h-8 ${star <= score ? 'fill-current' : ''}`}
                    />
                  </button>
                ))}
              </div>
              <div className="flex-1">
                <div className={`text-lg font-bold ${getScoreColor(score)}`}>
                  {score} / 5 - {getScoreLabel(score)}
                </div>
                <div className="text-xs text-gray-600 mt-1">
                  {score >= 4
                    ? '✅ High quality - Ready to use'
                    : score >= 3
                    ? '⚠️ Acceptable - Minor improvements possible'
                    : '❌ Needs refinement - Significant improvements needed'}
                </div>
              </div>
            </div>
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="Optional: Add feedback or comments about this response..."
              className="w-full p-3 border border-yellow-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-yellow-500"
              rows={2}
            />
          </div>

          {/* Refinement Section */}
          {score < 4 && (
            <div className="bg-red-50 rounded-lg p-4 border border-red-200">
              <div className="flex items-center gap-2 mb-2">
                <AlertCircle className="w-5 h-5 text-red-600" />
                <h3 className="text-sm font-semibold text-red-900">
                  Response Quality Below Threshold
                </h3>
              </div>
              <p className="text-xs text-red-700 mb-3">
                The response scored below 4/5. Would you like to refine it?
              </p>
              <button
                type="button"
                onClick={() => setShowRefinement(!showRefinement)}
                className="text-sm text-red-700 hover:text-red-900 underline"
              >
                {showRefinement ? 'Hide' : 'Show'} Refinement Options
              </button>
              {showRefinement && (
                <div className="mt-3 space-y-3">
                  <textarea
                    value={refinementFeedback}
                    onChange={(e) => setRefinementFeedback(e.target.value)}
                    placeholder="Describe what you'd like to improve in the response..."
                    className="w-full p-3 border border-red-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
                    rows={3}
                  />
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="border-t border-gray-200 p-4 bg-gray-50 flex items-center justify-between gap-4">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition"
          >
            Cancel
          </button>
          <div className="flex gap-3">
            {score < 4 && showRefinement && refinementFeedback && (
              <button
                type="button"
                onClick={() => {
                  onRefine(refinementFeedback);
                  onClose();
                }}
                className="px-6 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition flex items-center gap-2"
              >
                <AlertCircle className="w-4 h-4" />
                Refine Response
              </button>
            )}
            <button
              type="button"
              onClick={() => {
                onAccept(score, feedback);
                onClose();
              }}
              className={`px-6 py-2 text-white rounded-lg transition flex items-center gap-2 ${
                score >= 4
                  ? 'bg-green-600 hover:bg-green-700'
                  : 'bg-yellow-600 hover:bg-yellow-700'
              }`}
            >
              <CheckCircle2 className="w-4 h-4" />
              Accept & Continue {score < 4 && '(Low Score)'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

