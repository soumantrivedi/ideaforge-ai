import { Bot, Activity, Zap, CheckCircle2, Circle } from 'lucide-react';
import type { AgentRole } from '../agents/chatbot-agents';

interface AgentStatus {
  role: AgentRole;
  name: string;
  isActive: boolean;
  confidence?: number;
  lastActivity?: string;
  interactions?: number;
}

interface AgentStatusPanelProps {
  agents: AgentStatus[];
  onAgentSelect?: (role: AgentRole) => void;
  selectedAgent?: AgentRole;
}

export function AgentStatusPanel({
  agents,
  onAgentSelect,
  selectedAgent,
}: AgentStatusPanelProps) {
  const getAgentIcon = (role: AgentRole) => {
    const icons: Record<AgentRole, string> = {
      general: '🤖',
      research: '🔬',
      coding: '💻',
      creative: '✨',
      analysis: '📊',
      rag: '📚',
    };
    return icons[role];
  };

  const getAgentColor = (role: AgentRole) => {
    const colors: Record<AgentRole, string> = {
      general: 'from-blue-500 to-cyan-500',
      research: 'from-green-500 to-emerald-500',
      coding: 'from-orange-500 to-amber-500',
      creative: 'from-pink-500 to-rose-500',
      analysis: 'from-purple-500 to-violet-500',
      rag: 'from-teal-500 to-cyan-500',
    };
    return colors[role];
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
          agents.map((agent) => (
          <button
            key={agent.role}
            onClick={() => onAgentSelect?.(agent.role)}
            className={`w-full p-4 rounded-xl border-2 transition hover:shadow-md ${
              selectedAgent === agent.role
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
        ))
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
