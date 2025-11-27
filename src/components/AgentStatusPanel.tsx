import { useState, useEffect } from 'react';
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
  const [derivedAgents, setDerivedAgents] = useState<AgentStatus[]>([]);
  
  // Derive agents from interactions if agents list is empty
  useEffect(() => {
    if ((!agents || agents.length === 0) && agentInteractions.length > 0) {
      const uniqueAgents = new Set<string>();
      agentInteractions.forEach(interaction => {
        if (interaction.from_agent) uniqueAgents.add(interaction.from_agent);
        if (interaction.to_agent) uniqueAgents.add(interaction.to_agent);
      });
      
      const agentStatuses: AgentStatus[] = Array.from(uniqueAgents).map(agentName => {
        const role = agentName.toLowerCase().replace(/\s+/g, '_');
        const latestInteraction = agentInteractions
          .filter(i => {
            const toAgent = (i.to_agent || '').toLowerCase().replace(/\s+/g, '_');
            const fromAgent = (i.from_agent || '').toLowerCase().replace(/\s+/g, '_');
            return toAgent === role || fromAgent === role;
          })
          .sort((a, b) => {
            const timeA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
            const timeB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
            return timeB - timeA;
          })[0];
        
        return {
          role,
          name: agentName.charAt(0).toUpperCase() + agentName.slice(1).replace(/_/g, ' '),
          isActive: true,
          lastActivity: latestInteraction?.timestamp ? new Date(latestInteraction.timestamp).toLocaleString() : undefined,
          interactions: agentInteractions.filter(i => {
            const toAgent = (i.to_agent || '').toLowerCase().replace(/\s+/g, '_');
            const fromAgent = (i.from_agent || '').toLowerCase().replace(/\s+/g, '_');
            return toAgent === role || fromAgent === role;
          }).length,
          latestInteraction,
        };
      });
      
      setDerivedAgents(agentStatuses);
    } else {
      setDerivedAgents([]);
    }
  }, [agentInteractions, agents]);
  
  // Use derived agents if agents list is empty
  const displayAgents = (agents && agents.length > 0) ? agents : derivedAgents;

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
      .filter(interaction => {
        const toAgent = (interaction.to_agent || '').toLowerCase().replace(/\s+/g, '_');
        const fromAgent = (interaction.from_agent || '').toLowerCase().replace(/\s+/g, '_');
        return toAgent === agentRole || fromAgent === agentRole;
      })
      .sort((a, b) => {
        const timeA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
        const timeB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
        return timeB - timeA;
      })[0];
  };

  return (
    <div className="bg-white rounded-2xl shadow-xl border border-gray-100 p-4">
      <div className="flex items-center justify-center mb-4">
        <div className="p-2 bg-gradient-to-br from-purple-500 to-pink-600 rounded-xl">
          <Activity className="w-4 h-4 text-white" />
        </div>
      </div>

      <div className="flex flex-wrap gap-2 justify-center">
        {displayAgents.length === 0 ? (
          <div className="text-center py-4 text-gray-500 text-xs w-full">
            <p>No active agents</p>
          </div>
        ) : (
          displayAgents.map((agent) => {
            const latestInteraction = agent.latestInteraction || getLatestInteraction(agent.role);
            return (
              <div key={agent.role} className="relative group">
                <button
                  onClick={() => handleAgentClick(agent)}
                  className={`w-10 h-10 rounded-xl bg-gradient-to-br ${getAgentColor(
                    agent.role
                  )} flex items-center justify-center text-white text-lg shadow-lg hover:scale-110 transition-transform ${
                    expandedAgent === agent.role ? 'ring-2 ring-blue-500' : ''
                  }`}
                  title={agent.name}
                >
                  {getAgentIcon(agent.role)}
                  {agent.isActive && (
                    <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white"></div>
                  )}
                </button>
                <div className="absolute left-full ml-2 top-1/2 -translate-y-1/2 bg-gray-900 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-50 transition-opacity">
                  {agent.name}
                </div>
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
    </div>
  );
}
