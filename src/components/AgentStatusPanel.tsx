import { useState } from 'react';
import { Bot, Activity, Zap, CheckCircle2, Circle } from 'lucide-react';
import type { AgentRole } from '../agents/chatbot-agents';
import { AgentDetailModal } from './AgentDetailModal';

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

interface AgentStatus {
  role: string;
  name: string;
  isActive: boolean;
  confidence?: number;
  lastActivity?: string;
  interactions?: number;
  latestInteraction?: AgentInteraction;
}

interface AgentStatusPanelProps {
  agents: AgentStatus[];
  agentInteractions?: AgentInteraction[];
  onAgentSelect?: (role: string) => void;
  selectedAgent?: string;
}

export function AgentStatusPanel({
  agents,
  agentInteractions = [],
  onAgentSelect,
  selectedAgent,
}: AgentStatusPanelProps) {
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);

  const getAgentIcon = (role: string) => {
    const icons: Record<string, string> = {
      general: '🤖',
      research: '🔬',
      coding: '💻',
      creative: '✨',
      analysis: '📊',
      rag: '📚',
      ideation: '💡',
      prd_authoring: '📝',
      summary: '📄',
      scoring: '⭐',
      validation: '✅',
      export: '📤',
      v0: '🎨',
      lovable: '🎭',
      github_mcp: '🐙',
      atlassian_mcp: '🔷',
    };
    return icons[role] || '🤖';
  };

  const getAgentColor = (role: string) => {
    const colors: Record<string, string> = {
      general: 'from-blue-500 to-cyan-500',
      research: 'from-green-500 to-emerald-500',
      coding: 'from-orange-500 to-amber-500',
      creative: 'from-pink-500 to-rose-500',
      analysis: 'from-purple-500 to-violet-500',
      rag: 'from-teal-500 to-cyan-500',
      ideation: 'from-yellow-500 to-amber-500',
      prd_authoring: 'from-indigo-500 to-purple-500',
      summary: 'from-gray-500 to-slate-500',
      scoring: 'from-yellow-400 to-orange-500',
      validation: 'from-green-400 to-emerald-500',
      export: 'from-blue-400 to-cyan-500',
      v0: 'from-black to-gray-700',
      lovable: 'from-pink-400 to-rose-500',
      github_mcp: 'from-gray-700 to-gray-900',
      atlassian_mcp: 'from-blue-600 to-blue-800',
    };
    return colors[role] || 'from-gray-500 to-slate-500';
  };

  const handleAgentClick = (agent: AgentStatus) => {
    if (expandedAgent === agent.role) {
      setExpandedAgent(null);
    } else {
      setExpandedAgent(agent.role);
      onAgentSelect?.(agent.role);
    }
  };

  // Get latest interaction for an agent
  const getLatestInteraction = (agentRole: string): AgentInteraction | undefined => {
    return agentInteractions
      .filter(interaction => interaction.to_agent === agentRole || interaction.from_agent === agentRole)
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())[0];
  };

  return (
    <div className="bg-white rounded-2xl shadow-xl border border-gray-100 p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-gradient-to-br from-purple-500 to-pink-600 rounded-xl">
          <Activity className="w-5 h-5 text-white" />
        </div>
        <div>
          <h3 className="font-bold text-gray-900">Agent Network</h3>
          <p className="text-xs text-gray-600">
            {Array.isArray(agents) ? agents.filter((a) => a.isActive).length : 0} active
          </p>
        </div>
      </div>

      <div className="space-y-3">
        {!Array.isArray(agents) || agents.length === 0 ? (
          <div className="text-center py-8 text-gray-500 text-sm">
            <p>No active agents. Start a conversation to see agent activity.</p>
          </div>
        ) : (
          agents.map((agent) => {
            const latestInteraction = agent.latestInteraction || getLatestInteraction(agent.role);
            return (
              <div key={agent.role}>
                <button
                  onClick={() => handleAgentClick(agent)}
                  className={`w-full p-4 rounded-xl border-2 transition hover:shadow-md ${
                    expandedAgent === agent.role
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-100 bg-white hover:border-gray-200'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div
                      className={`w-12 h-12 rounded-xl bg-gradient-to-br ${getAgentColor(
                        agent.role
                      )} flex items-center justify-center text-white text-xl shadow-lg flex-shrink-0`}
                    >
                      {getAgentIcon(agent.role)}
                    </div>

                    <div className="flex-1 text-left min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <h4 className="font-semibold text-sm text-gray-900 truncate">
                          {agent.name}
                        </h4>
                        {agent.isActive ? (
                          <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
                        ) : (
                          <Circle className="w-4 h-4 text-gray-300 flex-shrink-0" />
                        )}
                      </div>

                      {agent.confidence !== undefined && (
                        <div className="mb-2">
                          <div className="flex items-center justify-between text-xs mb-1">
                            <span className="text-gray-600">Confidence</span>
                            <span className="font-medium text-gray-900">
                              {(agent.confidence * 100).toFixed(0)}%
                            </span>
                          </div>
                          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className={`h-full bg-gradient-to-r ${getAgentColor(
                                agent.role
                              )} transition-all`}
                              style={{ width: `${agent.confidence * 100}%` }}
                            />
                          </div>
                        </div>
                      )}

                      {agent.interactions !== undefined && agent.interactions > 0 && (
                        <div className="flex items-center gap-1 text-xs text-gray-600">
                          <Zap className="w-3 h-3" />
                          <span>{agent.interactions} interactions</span>
                        </div>
                      )}

                      {agent.lastActivity && (
                        <p className="text-xs text-gray-500 mt-1 truncate">
                          {agent.lastActivity}
                        </p>
                      )}
                    </div>
                  </div>
                </button>
                <AgentDetailModal
                  isOpen={expandedAgent === agent.role}
                  onClose={() => setExpandedAgent(null)}
                  agentName={agent.name}
                  agentRole={agent.role}
                  interaction={latestInteraction}
                />
              </div>
            );
          })
        )}
      </div>

      <div className="mt-6 p-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl border border-blue-100">
        <div className="flex items-start gap-3">
          <Bot className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div>
            <h4 className="font-semibold text-sm text-blue-900 mb-1">
              Multi-Agent System
            </h4>
            <p className="text-xs text-blue-700 leading-relaxed">
              Agents collaborate in real-time, consulting each other to provide
              comprehensive, accurate responses.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
