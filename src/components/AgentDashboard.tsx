import { useState, useEffect } from 'react';
import { Bot, TrendingUp, Activity, BarChart3, Zap, Clock, Database, X, Info } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { getValidatedApiUrl } from '../lib/runtime-config';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';

const API_URL = getValidatedApiUrl();

interface AgentUsage {
  agent_name: string;
  agent_role: string;
  usage_count: number;
  usage_percentage: number;
  last_used?: string;
  total_interactions: number;
  avg_processing_time?: number; // in seconds
  total_processing_time?: number; // in seconds
  cache_hit_rate?: number; // percentage
  total_tokens?: number;
}

interface AgentDashboardStats {
  total_agents: number;
  total_usage: number;
  agents: AgentUsage[];
  usage_by_phase: Record<string, number>;
  usage_trend: Array<{
    date: string;
    count: number;
  }>;
}

interface AgentCardProps {
  agent: AgentUsage;
  getAgentIcon: (role: string) => string;
  getAgentColor: (role: string) => string;
}

function AgentCard({ agent, getAgentIcon, getAgentColor }: AgentCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <>
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        whileHover={{ scale: 1.02 }}
        className="p-4 rounded-xl border-2 border-gray-200 hover:border-blue-400 transition-all cursor-pointer bg-white shadow-sm hover:shadow-md"
        onClick={() => setIsExpanded(true)}
      >
        <div className="flex flex-col items-center text-center mb-3">
          <div
            className={`w-16 h-16 rounded-xl bg-gradient-to-br ${getAgentColor(
              agent.agent_role
            )} flex items-center justify-center text-white text-2xl shadow-lg mb-3`}
          >
            {getAgentIcon(agent.agent_role)}
          </div>
          <h4 className="font-semibold text-gray-900 text-sm mb-1">{agent.agent_name}</h4>
          <p className="text-xs text-gray-600 capitalize mb-2">
            {agent.agent_role.replace(/_/g, ' ')}
          </p>
        </div>

        {/* Usage Percentage */}
        <div className="mb-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-gray-600">Usage</span>
            <span className="text-xs font-bold text-gray-900">
              {agent.usage_percentage.toFixed(1)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full bg-gradient-to-r ${getAgentColor(agent.agent_role)}`}
              style={{ width: `${Math.min(agent.usage_percentage, 100)}%` }}
            />
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="text-center">
            <p className="text-lg font-bold text-gray-900">{agent.usage_count}</p>
            <p className="text-gray-500">Uses</p>
          </div>
          {agent.avg_processing_time !== undefined && agent.avg_processing_time > 0 && (
            <div className="text-center">
              <p className="text-lg font-bold text-gray-900">
                {agent.avg_processing_time < 1 
                  ? `${(agent.avg_processing_time * 1000).toFixed(0)}ms`
                  : `${agent.avg_processing_time.toFixed(1)}s`}
              </p>
              <p className="text-gray-500">Avg Time</p>
            </div>
          )}
        </div>

        {/* Click indicator */}
        <div className="mt-3 pt-3 border-t border-gray-200 text-center">
          <p className="text-xs text-blue-600 flex items-center justify-center gap-1">
            <Info className="w-3 h-3" />
            Click for details
          </p>
        </div>
      </motion.div>

      {/* Expanded Detail Modal */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black bg-opacity-50 flex items-center justify-center p-4"
            onClick={() => setIsExpanded(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="sticky top-0 bg-white border-b border-gray-200 p-6 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div
                    className={`w-16 h-16 rounded-xl bg-gradient-to-br ${getAgentColor(
                      agent.agent_role
                    )} flex items-center justify-center text-white text-3xl shadow-lg`}
                  >
                    {getAgentIcon(agent.agent_role)}
                  </div>
                  <div>
                    <h3 className="text-2xl font-bold text-gray-900">{agent.agent_name}</h3>
                    <p className="text-sm text-gray-600 capitalize">
                      {agent.agent_role.replace(/_/g, ' ')}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setIsExpanded(false)}
                  className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <X className="w-5 h-5 text-gray-500" />
                </button>
              </div>

              <div className="p-6 space-y-6">
                {/* Usage Statistics */}
                <div>
                  <h4 className="text-lg font-semibold text-gray-900 mb-4">Usage Statistics</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-blue-50 rounded-lg">
                      <p className="text-sm text-gray-600">Total Uses</p>
                      <p className="text-2xl font-bold text-gray-900">{agent.usage_count}</p>
                    </div>
                    <div className="p-4 bg-green-50 rounded-lg">
                      <p className="text-sm text-gray-600">Usage Percentage</p>
                      <p className="text-2xl font-bold text-gray-900">{agent.usage_percentage.toFixed(1)}%</p>
                    </div>
                    <div className="p-4 bg-purple-50 rounded-lg">
                      <p className="text-sm text-gray-600">Total Interactions</p>
                      <p className="text-2xl font-bold text-gray-900">{agent.total_interactions}</p>
                    </div>
                    {agent.last_used && (
                      <div className="p-4 bg-orange-50 rounded-lg">
                        <p className="text-sm text-gray-600">Last Used</p>
                        <p className="text-lg font-bold text-gray-900">
                          {new Date(agent.last_used).toLocaleDateString()}
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Performance Metrics - Always show for all agents */}
                <div>
                  <h4 className="text-lg font-semibold text-gray-900 mb-4">Performance Metrics</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-blue-50 rounded-lg flex items-center gap-3">
                      <Clock className="w-8 h-8 text-blue-600" />
                      <div>
                        <p className="text-sm text-gray-600">Average Processing Time</p>
                        <p className="text-xl font-bold text-gray-900">
                          {agent.avg_processing_time !== undefined && agent.avg_processing_time > 0
                            ? (agent.avg_processing_time < 1 
                                ? `${(agent.avg_processing_time * 1000).toFixed(0)}ms`
                                : `${agent.avg_processing_time.toFixed(2)}s`)
                            : '0s'}
                        </p>
                      </div>
                    </div>
                    <div className="p-4 bg-indigo-50 rounded-lg flex items-center gap-3">
                      <Clock className="w-8 h-8 text-indigo-600" />
                      <div>
                        <p className="text-sm text-gray-600">Total Processing Time</p>
                        <p className="text-xl font-bold text-gray-900">
                          {agent.total_processing_time !== undefined && agent.total_processing_time > 0
                            ? (agent.total_processing_time < 60
                                ? `${agent.total_processing_time.toFixed(1)}s`
                                : `${(agent.total_processing_time / 60).toFixed(1)}m`)
                            : '0s'}
                        </p>
                      </div>
                    </div>
                    <div className="p-4 bg-green-50 rounded-lg flex items-center gap-3">
                      <Database className="w-8 h-8 text-green-600" />
                      <div>
                        <p className="text-sm text-gray-600">Cache Hit Rate</p>
                        <p className="text-xl font-bold text-gray-900">
                          {agent.cache_hit_rate !== undefined 
                            ? `${agent.cache_hit_rate.toFixed(1)}%`
                            : '0.0%'}
                        </p>
                      </div>
                    </div>
                    <div className="p-4 bg-purple-50 rounded-lg flex items-center gap-3">
                      <Zap className="w-8 h-8 text-purple-600" />
                      <div>
                        <p className="text-sm text-gray-600">Total Tokens</p>
                        <p className="text-xl font-bold text-gray-900">
                          {agent.total_tokens !== undefined && agent.total_tokens > 0
                            ? agent.total_tokens.toLocaleString()
                            : '0'}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Usage Percentage Visualization */}
                <div>
                  <h4 className="text-lg font-semibold text-gray-900 mb-4">Usage Distribution</h4>
                  <div className="w-full bg-gray-200 rounded-full h-4">
                    <div
                      className={`h-4 rounded-full bg-gradient-to-r ${getAgentColor(agent.agent_role)} flex items-center justify-end pr-2`}
                      style={{ width: `${Math.min(agent.usage_percentage, 100)}%` }}
                    >
                      <span className="text-xs font-bold text-white">
                        {agent.usage_percentage.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

export function AgentDashboard() {
  const { token } = useAuth();
  const [stats, setStats] = useState<AgentDashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (token) {
      loadAgentStats();
    }
  }, [token]);

  const loadAgentStats = async () => {
    if (!token) return;

    setIsLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/agents/usage-stats`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        setStats(data);
      } else {
        console.error('Failed to load agent stats:', response.status);
      }
    } catch (error) {
      console.error('Error loading agent stats:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getAgentIcon = (role: string) => {
    const icons: Record<string, string> = {
      research: '🔬',
      analysis: '📊',
      ideation: '💡',
      prd_authoring: '📝',
      summary: '📄',
      scoring: '⭐',
      strategy: '🎯',
      validation: '✅',
      export: '📤',
      v0: '🎨',
      lovable: '🎭',
      github_mcp: '🐙',
      atlassian_mcp: '🔷',
      rag: '📚',
    };
    return icons[role.toLowerCase()] || '🤖';
  };

  const getAgentColor = (role: string) => {
    const colors: Record<string, string> = {
      research: 'from-green-500 to-emerald-500',
      analysis: 'from-purple-500 to-violet-500',
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
      rag: 'from-teal-500 to-cyan-500',
    };
    return colors[role.toLowerCase()] || 'from-gray-500 to-slate-500';
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-gray-500">Loading agent statistics...</div>
      </div>
    );
  }

  if (!stats || stats.agents.length === 0) {
    return (
      <div className="text-center py-12 bg-white rounded-xl shadow">
        <Bot className="w-16 h-16 mx-auto text-gray-400 mb-4" />
        <h3 className="text-lg font-semibold text-gray-900 mb-2">No Agent Usage Yet</h3>
        <p className="text-gray-600">Start using agents in your conversations to see usage statistics</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Agent Dashboard</h2>
            <p className="text-gray-600 mt-1">Track agent usage and performance</p>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Bot className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Total Agents</p>
                <p className="text-2xl font-bold text-gray-900">{stats.total_agents}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 bg-green-100 rounded-lg">
                <Activity className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Total Usage</p>
                <p className="text-2xl font-bold text-gray-900">{stats.total_usage}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 bg-purple-100 rounded-lg">
                <TrendingUp className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Active Agents</p>
                <p className="text-2xl font-bold text-gray-900">
                  {stats.agents.filter(a => a.usage_count > 0).length}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Usage Trend Chart */}
        {stats.usage_trend && stats.usage_trend.length > 0 && (
          <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
            <div className="flex items-center gap-2 mb-6">
              <TrendingUp className="w-5 h-5 text-gray-600" />
              <h3 className="text-lg font-semibold text-gray-900">Usage Trend (Last 30 Days)</h3>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={stats.usage_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis 
                  dataKey="date" 
                  stroke="#6b7280"
                  tick={{ fill: '#6b7280', fontSize: 12 }}
                  tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                />
                <YAxis 
                  stroke="#6b7280"
                  tick={{ fill: '#6b7280', fontSize: 12 }}
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px' }}
                  labelFormatter={(value) => new Date(value).toLocaleDateString()}
                />
                <Legend />
                <Line 
                  type="monotone" 
                  dataKey="count" 
                  stroke="#3b82f6" 
                  strokeWidth={2}
                  name="Agent Usage"
                  dot={{ fill: '#3b82f6', r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Usage by Phase Chart */}
        {Object.keys(stats.usage_by_phase).length > 0 && (
          <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
            <div className="flex items-center gap-2 mb-6">
              <BarChart3 className="w-5 h-5 text-gray-600" />
              <h3 className="text-lg font-semibold text-gray-900">Usage by Product Phase</h3>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={Object.entries(stats.usage_by_phase)
                .sort(([, a], [, b]) => b - a)
                .map(([phase, count]) => ({
                  phase: phase.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
                  count,
                  percentage: ((count / stats.total_usage) * 100).toFixed(1)
                }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis 
                  dataKey="phase" 
                  stroke="#6b7280"
                  tick={{ fill: '#6b7280', fontSize: 12 }}
                  angle={-45}
                  textAnchor="end"
                  height={100}
                />
                <YAxis 
                  stroke="#6b7280"
                  tick={{ fill: '#6b7280', fontSize: 12 }}
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px' }}
                  formatter={(value: any, name: string, props: any) => [
                    `${value} uses (${props.payload.percentage}%)`,
                    'Usage'
                  ]}
                />
                <Bar dataKey="count" fill="#3b82f6" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Agent Grid with Performance Metrics */}
        <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
          <div className="flex items-center gap-2 mb-6">
            <BarChart3 className="w-5 h-5 text-gray-600" />
            <h3 className="text-lg font-semibold text-gray-900">All Agno Agents - Usage & Performance</h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {stats.agents
              .sort((a, b) => b.usage_count - a.usage_count)
              .map((agent) => (
                <AgentCard
                  key={agent.agent_role}
                  agent={agent}
                  getAgentIcon={getAgentIcon}
                  getAgentColor={getAgentColor}
                />
              ))}
          </div>
        </div>

        {/* Top Agents Performance Chart */}
        {stats.agents.filter(a => a.usage_count > 0 && a.avg_processing_time && a.avg_processing_time > 0).length > 0 && (
          <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
            <div className="flex items-center gap-2 mb-6">
              <Clock className="w-5 h-5 text-gray-600" />
              <h3 className="text-lg font-semibold text-gray-900">Average Processing Time by Agent</h3>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={stats.agents
                .filter(a => a.usage_count > 0 && a.avg_processing_time && a.avg_processing_time > 0)
                .sort((a, b) => (b.avg_processing_time || 0) - (a.avg_processing_time || 0))
                .slice(0, 10)
                .map(agent => ({
                  name: agent.agent_name.length > 15 ? agent.agent_name.substring(0, 15) + '...' : agent.agent_name,
                  time: agent.avg_processing_time || 0,
                  fullName: agent.agent_name
                }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis 
                  dataKey="name" 
                  stroke="#6b7280"
                  tick={{ fill: '#6b7280', fontSize: 12 }}
                  angle={-45}
                  textAnchor="end"
                  height={100}
                />
                <YAxis 
                  stroke="#6b7280"
                  tick={{ fill: '#6b7280', fontSize: 12 }}
                  label={{ value: 'Time (seconds)', angle: -90, position: 'insideLeft' }}
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px' }}
                  formatter={(value: any, name: string, props: any) => [
                    `${(value as number).toFixed(2)}s`,
                    'Avg Processing Time'
                  ]}
                  labelFormatter={(label, payload) => payload?.[0]?.payload?.fullName || label}
                />
                <Bar dataKey="time" fill="#10b981" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}

