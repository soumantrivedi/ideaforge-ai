import { Bot, Search, Code, Palette, BarChart3, Database, Zap } from 'lucide-react';
import type { AgentRole } from '../agents/chatbot-agents';

interface AgentSelectorProps {
  selectedAgent: AgentRole;
  onSelectAgent: (agent: AgentRole) => void;
  agentStats?: Record<AgentRole, { messagesCount: number; avgResponseTime: number }>;
}

const AGENT_INFO: Record<
  AgentRole,
  { icon: React.ComponentType<{ className?: string }>; color: string; description: string }
> = {
  general: {
    icon: Bot,
    color: 'from-blue-500 to-blue-600',
    description: 'General purpose assistant for everyday tasks',
  },
  research: {
    icon: Search,
    color: 'from-green-500 to-green-600',
    description: 'Deep research and information gathering',
  },
  coding: {
    icon: Code,
    color: 'from-purple-500 to-purple-600',
    description: 'Code generation, debugging, and optimization',
  },
  creative: {
    icon: Palette,
    color: 'from-pink-500 to-pink-600',
    description: 'Creative writing and content generation',
  },
  analysis: {
    icon: BarChart3,
    color: 'from-orange-500 to-orange-600',
    description: 'Data analysis and business insights',
  },
  rag: {
    icon: Database,
    color: 'from-cyan-500 to-cyan-600',
    description: 'Knowledge base powered responses',
  },
};

export function AgentSelector({
  selectedAgent,
  onSelectAgent,
  agentStats,
}: AgentSelectorProps) {
  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <div className="flex items-center gap-2 mb-6">
        <Zap className="w-5 h-5 text-blue-600" />
        <h3 className="text-lg font-bold text-gray-900">AI Agents</h3>
      </div>

      <div className="space-y-3">
        {(Object.entries(AGENT_INFO) as [AgentRole, typeof AGENT_INFO[AgentRole]][]).map(
          ([role, info]) => {
            const Icon = info.icon;
            const isSelected = selectedAgent === role;
            const stats = agentStats?.[role];

            return (
              <button
                key={role}
                onClick={() => onSelectAgent(role)}
                className={`w-full text-left p-4 rounded-lg transition ${
                  isSelected
                    ? 'bg-blue-50 border-2 border-blue-500 shadow-sm'
                    : 'border-2 border-transparent hover:bg-gray-50'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div
                    className={`flex-shrink-0 w-10 h-10 rounded-lg bg-gradient-to-br ${info.color} flex items-center justify-center`}
                  >
                    <Icon className="w-5 h-5 text-white" />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <h4 className="font-semibold text-gray-900 capitalize">
                        {role === 'rag' ? 'RAG Agent' : `${role} Agent`}
                      </h4>
                      {isSelected && (
                        <span className="px-2 py-1 text-xs font-medium bg-blue-600 text-white rounded-full">
                          Active
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-600 mt-1">{info.description}</p>

                    {stats && stats.messagesCount > 0 && (
                      <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                        <span>{stats.messagesCount} messages</span>
                        <span>•</span>
                        <span>{stats.avgResponseTime}ms avg</span>
                      </div>
                    )}
                  </div>
                </div>
              </button>
            );
          }
        )}
      </div>

      <div className="mt-6 p-4 bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg">
        <div className="flex items-start gap-2">
          <Zap className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-blue-900 mb-1">Smart Routing</p>
            <p className="text-xs text-blue-700">
              Messages are automatically routed to the best agent based on content analysis
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
