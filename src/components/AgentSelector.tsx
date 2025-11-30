import { Bot, Search, Code, Palette, BarChart3, Database, Zap } from 'lucide-react';
import type { AgentRole } from '../agents/chatbot-agents';

interface AgentSelectorProps {
  selectedAgent: AgentRole;
  onSelectAgent: (agent: AgentRole) => void;
  agentStats?: Record<AgentRole, { messagesCount: number; avgResponseTime: number }>;
}

const AGENT_INFO: Record<
  AgentRole,
  { 
    icon: React.ComponentType<{ className?: string }>; 
    color: string; 
    description: string;
    capabilities: string[];
    modelTier: 'fast' | 'standard' | 'premium';
  }
> = {
  general: {
    icon: Bot,
    color: 'from-blue-500 to-blue-600',
    description: 'General purpose assistant for everyday tasks',
    capabilities: ['General assistance', 'Question answering', 'Task coordination'],
    modelTier: 'fast',
  },
  research: {
    icon: Search,
    color: 'from-green-500 to-green-600',
    description: 'Deep research and information gathering',
    capabilities: ['Market research', 'Competitive analysis', 'Trend analysis', 'User research'],
    modelTier: 'fast',
  },
  coding: {
    icon: Code,
    color: 'from-purple-500 to-purple-600',
    description: 'Code generation, debugging, and optimization',
    capabilities: ['Code generation', 'Debugging', 'Code review', 'Documentation'],
    modelTier: 'fast',
  },
  creative: {
    icon: Palette,
    color: 'from-pink-500 to-pink-600',
    description: 'Creative writing and content generation',
    capabilities: ['Content creation', 'Creative writing', 'Brainstorming', 'Ideation'],
    modelTier: 'fast',
  },
  analysis: {
    icon: BarChart3,
    color: 'from-orange-500 to-orange-600',
    description: 'Data analysis and business insights',
    capabilities: ['SWOT analysis', 'Feasibility analysis', 'Risk analysis', 'Strategic analysis'],
    modelTier: 'fast',
  },
  rag: {
    icon: Database,
    color: 'from-cyan-500 to-cyan-600',
    description: 'Knowledge base powered responses',
    capabilities: ['Knowledge retrieval', 'Context-aware responses', 'Document search'],
    modelTier: 'fast',
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

                    {/* Capabilities */}
                    <div className="flex flex-wrap gap-1 mt-2">
                      {info.capabilities.slice(0, 3).map((cap, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-0.5 text-xs bg-gray-100 text-gray-700 rounded-full"
                        >
                          {cap}
                        </span>
                      ))}
                      {info.capabilities.length > 3 && (
                        <span className="px-2 py-0.5 text-xs text-gray-500">
                          +{info.capabilities.length - 3} more
                        </span>
                      )}
                    </div>

                    {/* Model Tier Badge */}
                    <div className="mt-2">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        info.modelTier === 'premium' 
                          ? 'bg-purple-100 text-purple-700'
                          : info.modelTier === 'standard'
                          ? 'bg-blue-100 text-blue-700'
                          : 'bg-green-100 text-green-700'
                      }`}>
                        {info.modelTier === 'premium' ? '⚡ Premium' : info.modelTier === 'standard' ? '⚙️ Standard' : '🚀 Fast'}
                      </span>
                    </div>

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
