import { useState, useEffect, useMemo } from 'react';
import { MessageSquare, Filter, Calendar, User, Bot, Search, X } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { HorizontalAgentStatus } from './HorizontalAgentStatus';

import { getValidatedApiUrl } from '../lib/runtime-config';
const API_URL = getValidatedApiUrl();

interface Conversation {
  id: string;
  message_type: string;
  agent_name?: string;
  agent_role?: string;
  content: string;
  formatted_content?: string;
  created_at: string;
  session_title?: string;
  product_id?: string;
  product_name?: string;
  interaction_metadata?: any;
}

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

interface Product {
  id: string;
  name: string;
}

export function ConversationHistory() {
  const { token } = useAuth();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [productFilter, setProductFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [dateFilter, setDateFilter] = useState<string>('all');

  const [allConversations, setAllConversations] = useState<Conversation[]>([]);
  const [agentInteractions, setAgentInteractions] = useState<AgentInteraction[]>([]);
  const [agentStatuses, setAgentStatuses] = useState<any[]>([]);

  // Load products and conversations on mount
  useEffect(() => {
    if (token) {
      loadProducts();
      loadAllConversations();
    }
  }, [token]);
  
  // Load ALL products the user has access to
  const loadProducts = async () => {
    if (!token) return;

    try {
      const response = await fetch(`${API_URL}/api/products`, {
        headers: { 'Authorization': `Bearer ${token}` },
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        const allProducts = data.products || [];
        setProducts(allProducts.map((p: any) => ({
          id: p.id,
          name: p.name,
        })));
      }
    } catch (error) {
      console.error('Failed to load products:', error);
    }
  };
  
  // Load ALL conversations
  const loadAllConversations = async () => {
    if (!token) return;

    setIsLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/conversations/history`, {
        headers: { 'Authorization': `Bearer ${token}` },
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        const loadedConversations = data.conversations || [];
        setAllConversations(loadedConversations);
      }
    } catch (error) {
      console.error('Failed to load all conversations:', error);
    } finally {
      setIsLoading(false);
    }
  };
  
  // Filter conversations client-side based on productFilter
  useEffect(() => {
    if (productFilter === 'all') {
      setConversations(allConversations);
    } else {
      setConversations(allConversations.filter(conv => conv.product_id === productFilter));
    }
  }, [allConversations, productFilter]);
  
  // Extract agent interactions and statuses from conversations
  useEffect(() => {
    const interactions: AgentInteraction[] = [];
    const agentMap = new Map<string, any>();
    
    conversations.forEach(conv => {
      // Extract agent interactions from metadata
      if (conv.interaction_metadata) {
        try {
          const metadata = typeof conv.interaction_metadata === 'string' 
            ? JSON.parse(conv.interaction_metadata) 
            : conv.interaction_metadata;
          
          if (metadata.agent_interactions && Array.isArray(metadata.agent_interactions)) {
            metadata.agent_interactions.forEach((interaction: any) => {
              interactions.push({
                from_agent: interaction.from_agent || '',
                to_agent: interaction.to_agent || conv.agent_name || '',
                query: interaction.query || metadata.user_prompt || conv.content,
                response: interaction.response || conv.content,
                timestamp: conv.created_at,
                metadata: {
                  ...metadata,
                  ...(interaction.metadata || {}),
                },
              });
            });
          } else if (metadata.from_agent || metadata.to_agent || conv.agent_name) {
            interactions.push({
              from_agent: metadata.from_agent || '',
              to_agent: metadata.to_agent || conv.agent_name || '',
              query: metadata.user_prompt || metadata.query || conv.content,
              response: metadata.response || conv.content,
              timestamp: conv.created_at,
              metadata: metadata,
            });
          }
        } catch (e) {
          // Ignore parsing errors
        }
      }
      
      // Build agent statuses from agent messages
      if (conv.agent_name && conv.agent_role) {
        const role = conv.agent_role.toLowerCase().replace(/\s+/g, '_');
        if (!agentMap.has(role)) {
          const metadata = conv.interaction_metadata 
            ? (typeof conv.interaction_metadata === 'string' 
                ? JSON.parse(conv.interaction_metadata) 
                : conv.interaction_metadata)
            : {};
          
          agentMap.set(role, {
            role,
            name: conv.agent_name,
            isActive: true,
            lastActivity: conv.created_at,
            latestInteraction: {
              from_agent: metadata.from_agent || '',
              to_agent: conv.agent_name,
              query: metadata.user_prompt || conv.content.substring(0, 100),
              response: conv.content,
              timestamp: conv.created_at,
              metadata: {
                system_context: metadata.system_context,
                system_prompt: metadata.system_prompt,
                rag_context: metadata.rag_context,
                user_prompt: metadata.user_prompt || conv.content,
                ...metadata,
              },
            },
          });
        }
      }
    });
    
    setAgentInteractions(interactions);
    setAgentStatuses(Array.from(agentMap.values()));
  }, [conversations]);

  // Filter and search conversations
  const filteredConversations = useMemo(() => {
    let filtered = conversations;
    
    // Search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(conv => 
        conv.content.toLowerCase().includes(query) ||
        conv.agent_name?.toLowerCase().includes(query) ||
        conv.product_name?.toLowerCase().includes(query)
      );
    }
    
    // Date filter
    if (dateFilter !== 'all') {
      const now = new Date();
      const filterDate = new Date();
      
      switch (dateFilter) {
        case 'today':
          filterDate.setHours(0, 0, 0, 0);
          filtered = filtered.filter(conv => new Date(conv.created_at) >= filterDate);
          break;
        case 'week':
          filterDate.setDate(now.getDate() - 7);
          filtered = filtered.filter(conv => new Date(conv.created_at) >= filterDate);
          break;
        case 'month':
          filterDate.setMonth(now.getMonth() - 1);
          filtered = filtered.filter(conv => new Date(conv.created_at) >= filterDate);
          break;
      }
    }
    
    return filtered;
  }, [conversations, searchQuery, dateFilter]);

  const groupedConversations = Array.isArray(filteredConversations) ? filteredConversations.reduce((acc, conv) => {
    const date = new Date(conv.created_at).toLocaleDateString();
    if (!acc[date]) {
      acc[date] = [];
    }
    acc[date].push(conv);
    return acc;
  }, {} as Record<string, Conversation[]>) : {};

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-gray-500">Loading conversation history...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Conversation History</h2>
            <p className="text-gray-600 mt-1">View all your past conversations</p>
          </div>
        </div>

        {/* Search and Filters */}
        <div className="flex items-center gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search conversations..."
              className="w-full pl-10 pr-10 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-gray-100 rounded"
              >
                <X className="w-4 h-4 text-gray-400" />
              </button>
            )}
          </div>

          {/* Date Filter */}
          <select
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Time</option>
            <option value="today">Today</option>
            <option value="week">Last Week</option>
            <option value="month">Last Month</option>
          </select>

          {/* Product Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-5 h-5 text-gray-500" />
            <select
              value={productFilter}
              onChange={(e) => setProductFilter(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent min-w-[200px]"
            >
              <option value="all">All Products</option>
              {products.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Results count */}
        {searchQuery && (
          <div className="text-sm text-gray-600">
            Found {filteredConversations.length} conversation{filteredConversations.length !== 1 ? 's' : ''}
          </div>
        )}
      </div>

      {filteredConversations.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl shadow">
          <MessageSquare className="w-16 h-16 mx-auto text-gray-400 mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No conversations yet</h3>
          <p className="text-gray-600">Start chatting to see your conversation history</p>
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(groupedConversations).map(([date, convs]) => (
            <div key={date} className="bg-white rounded-xl shadow-lg p-6">
              <div className="flex items-center gap-2 mb-4 pb-4 border-b">
                <Calendar className="w-5 h-5 text-gray-500" />
                <h3 className="font-semibold text-gray-900">{date}</h3>
                <span className="text-sm text-gray-500">({convs.length} messages)</span>
              </div>

              <div className="space-y-4">
                {convs.map((conv) => (
                  <div
                    key={conv.id}
                    className={`p-4 rounded-lg ${
                      conv.message_type === 'user'
                        ? 'bg-blue-50 border-l-4 border-blue-500'
                        : 'bg-gray-50 border-l-4 border-gray-300'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      {conv.message_type === 'user' ? (
                        <User className="w-5 h-5 text-blue-600 mt-1 flex-shrink-0" />
                      ) : (
                        <Bot className="w-5 h-5 text-gray-600 mt-1 flex-shrink-0" />
                      )}
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="font-medium text-gray-900">
                            {conv.message_type === 'user'
                              ? 'You'
                              : conv.agent_name || 'Assistant'}
                          </span>
                          {conv.agent_role && (
                            <span className="text-xs px-2 py-1 bg-gray-200 text-gray-700 rounded">
                              {conv.agent_role}
                            </span>
                          )}
                          {conv.product_name && (
                            <span className="text-xs px-2 py-1 bg-purple-100 text-purple-700 rounded">
                              {conv.product_name}
                            </span>
                          )}
                          <span className="text-xs text-gray-500 ml-auto">
                            {new Date(conv.created_at).toLocaleTimeString()}
                          </span>
                        </div>
                        <div className="text-gray-700 whitespace-pre-wrap">
                          {conv.formatted_content || conv.content}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
      
      {/* Agent Status Panel - Footer */}
      {(agentStatuses.length > 0 || agentInteractions.length > 0) && (
        <div className="mt-6 p-4 border-t border-gray-200 bg-gray-50 rounded-xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-gray-600">Agents Used in History:</span>
              <HorizontalAgentStatus
                agents={agentStatuses}
                agentInteractions={agentInteractions}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

