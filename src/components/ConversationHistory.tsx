import { useState, useEffect } from 'react';
import { MessageSquare, Filter, Calendar, User, Bot } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

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
}

export function ConversationHistory() {
  const { token } = useAuth();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [productFilter, setProductFilter] = useState<string>('all');

  useEffect(() => {
    if (token) {
      loadConversations();
    }
  }, [token, productFilter]);

  const loadConversations = async () => {
    if (!token) return;

    setIsLoading(true);
    try {
      const url =
        productFilter === 'all'
          ? `${API_URL}/api/conversations/history`
          : `${API_URL}/api/conversations/history?product_id=${productFilter}`;

      const response = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` },
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        setConversations(data.conversations || []);
      }
    } catch (error) {
      console.error('Failed to load conversations:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const groupedConversations = Array.isArray(conversations) ? conversations.reduce((acc, conv) => {
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
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Conversation History</h2>
          <p className="text-gray-600 mt-1">View all your past conversations</p>
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-gray-500" />
          <select
            value={productFilter}
            onChange={(e) => setProductFilter(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Products</option>
            {/* Product options would be loaded from API */}
          </select>
        </div>
      </div>

      {conversations.length === 0 ? (
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
    </div>
  );
}

