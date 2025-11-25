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

  // Listen for phase form generation events
  useEffect(() => {
    const handlePhaseFormGenerated = (event: Event) => {
      const customEvent = event as CustomEvent;
      if (customEvent.detail && customEvent.detail.productId === productId && customEvent.detail.message) {
        console.log('ProductChatInterface: Received phaseFormGenerated event', {
          productId: customEvent.detail.productId,
          messageLength: customEvent.detail.message?.length || 0
        });
        
        // Add the generated message to chat
        const assistantMessage: MultiAgentMessage = {
          role: 'assistant',
          content: customEvent.detail.message,
          agentName: 'Multi-Agent System',
          timestamp: new Date().toISOString(),
        };
        
        setMessages((prev) => {
          // Avoid duplicates by checking last message
          const lastMessage = prev[prev.length - 1];
          if (lastMessage && lastMessage.content === assistantMessage.content) {
            console.log('ProductChatInterface: Duplicate message detected, skipping');
            return prev;
          }
          console.log('ProductChatInterface: Adding message to chat', {
            totalMessages: prev.length + 1
          });
          return [...prev, assistantMessage];
        });
      } else {
        console.warn('ProductChatInterface: Invalid phaseFormGenerated event', {
          hasDetail: !!customEvent.detail,
          productIdMatch: customEvent.detail?.productId === productId,
          hasMessage: !!customEvent.detail?.message
        });
      }
    };

    window.addEventListener('phaseFormGenerated', handlePhaseFormGenerated);
    return () => {
      window.removeEventListener('phaseFormGenerated', handlePhaseFormGenerated);
    };
  }, [productId]);

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
      // Build query from message history and current message
      const messageHistory = Array.isArray(messages) ? messages.map((m) => `${m.role}: ${m.content}`).join('\n') : '';
      const fullQuery = messageHistory ? `${messageHistory}\nuser: ${content}` : content;

      // Always include RAG agent for knowledge base context
      // Determine supporting agents based on query content
      let supportingAgents: string[] = ['rag']; // RAG is always first
      
      const queryLower = fullQuery.toLowerCase();
      if (queryLower.includes('research') || queryLower.includes('market') || queryLower.includes('competitive')) {
        supportingAgents.push('research');
      }
      if (queryLower.includes('analyze') || queryLower.includes('swot') || queryLower.includes('feasibility')) {
        supportingAgents.push('analysis');
      }
      if (queryLower.includes('idea') || queryLower.includes('brainstorm') || queryLower.includes('feature')) {
        supportingAgents.push('ideation');
      }
      if (queryLower.includes('prd') || queryLower.includes('requirement') || queryLower.includes('document')) {
        supportingAgents.push('prd_authoring');
      }
      
      // If no specific agents matched, add default ones
      if (supportingAgents.length === 1) {
        supportingAgents.push('research', 'analysis');
      }

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
          query: fullQuery,
          coordination_mode: 'enhanced_collaborative', // Always use enhanced collaborative for RAG integration
          supporting_agents: supportingAgents, // Always include RAG
          context: {
            product_id: productId,
            session_id: sessionId,
            message_history: messages,
            always_use_rag: true, // Flag to ensure RAG is always considered
          },
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

