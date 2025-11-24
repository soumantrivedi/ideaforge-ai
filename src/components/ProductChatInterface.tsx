import { useState, useEffect } from 'react';
import { EnhancedChatInterface } from './EnhancedChatInterface';
import type { MultiAgentMessage, CoordinationMode } from '../agents/multi-agent-system';
import { useAuth } from '../contexts/AuthContext';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface ProductChatInterfaceProps {
  productId: string;
  sessionId: string;
}

export function ProductChatInterface({ productId, sessionId }: ProductChatInterfaceProps) {
  const { token } = useAuth();
  const [messages, setMessages] = useState<MultiAgentMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [coordinationMode, setCoordinationMode] = useState<CoordinationMode>('collaborative');
  const [activeAgents, setActiveAgents] = useState<string[]>([]);

  const handleSendMessage = async (content: string) => {
    if (!token || !productId) return;

    const userMessage: MultiAgentMessage = {
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/multi-agent/process`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          user_id: '00000000-0000-0000-0000-000000000000', // Will be set by backend from token
          product_id: productId,
          coordination_mode: coordinationMode,
          messages: [
            ...(Array.isArray(messages) ? messages.map((m) => ({
              role: m.role,
              content: m.content,
            })) : []),
            {
              role: 'user',
              content,
            },
          ],
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const assistantMessage: MultiAgentMessage = {
          role: 'assistant',
          content: data.response || 'No response',
          agentName: data.primary_agent || 'Assistant',
          timestamp: new Date().toISOString(),
          interactions: data.interactions || [],
        };
        setMessages((prev) => [...prev, assistantMessage]);
        setActiveAgents(data.active_agents || []);
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to get response');
      }
    } catch (error) {
      const errorMessage: MultiAgentMessage = {
        role: 'assistant',
        content: `Error: ${error instanceof Error ? error.message : 'Failed to send message'}`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <EnhancedChatInterface
      messages={messages}
      onSendMessage={handleSendMessage}
      isLoading={isLoading}
      coordinationMode={coordinationMode}
      onCoordinationModeChange={setCoordinationMode}
      activeAgents={activeAgents}
    />
  );
}

