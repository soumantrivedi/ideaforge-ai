import { useState, useEffect } from 'react';
import { EnhancedChatInterface } from './EnhancedChatInterface';
import type { MultiAgentMessage, CoordinationMode } from '../agents/multi-agent-system';
import { useAuth } from '../contexts/AuthContext';
import { saveChatSession, loadChatSession, clearProductSession } from '../lib/session-storage';

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
  const [agentInteractions, setAgentInteractions] = useState<any[]>([]);

  // Save to sessionStorage whenever messages, interactions, or agents change
  useEffect(() => {
    if (productId && messages.length > 0) {
      saveChatSession(productId, {
        messages,
        agentInteractions,
        activeAgents,
        coordinationMode,
      });
    }
  }, [messages, agentInteractions, activeAgents, coordinationMode, productId]);

  // Cleanup: clear session when component unmounts (if needed)
  useEffect(() => {
    return () => {
      // Don't clear on unmount - we want to keep it for refresh
      // Only clear on explicit logout
    };
  }, [productId]);

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
          const updatedMessages = [...prev, assistantMessage];
          // Save to sessionStorage
          saveChatSession(productId, {
            messages: updatedMessages,
            agentInteractions: agentInteractions,
            activeAgents: activeAgents,
            coordinationMode: coordinationMode,
          });
          return updatedMessages;
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

    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    // Save to sessionStorage immediately
    saveChatSession(productId, {
      messages: updatedMessages,
      agentInteractions: agentInteractions,
      activeAgents: activeAgents,
      coordinationMode: coordinationMode,
    });
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
          interactions: data.agent_interactions || [],
        };
        const updatedMessages = [...messages, assistantMessage];
        setMessages(updatedMessages);
        
        // Extract active agents from interactions
        const interactions = data.agent_interactions || [];
        const uniqueAgents = new Set<string>();
        interactions.forEach((interaction: any) => {
          if (interaction.to_agent) uniqueAgents.add(interaction.to_agent);
          if (interaction.from_agent) uniqueAgents.add(interaction.from_agent);
        });
        if (data.primary_agent) uniqueAgents.add(data.primary_agent);
        const activeAgentsArray = Array.from(uniqueAgents);
        setActiveAgents(activeAgentsArray);
        setAgentInteractions(interactions);
        
        // Save to sessionStorage
        saveChatSession(productId, {
          messages: updatedMessages,
          agentInteractions: interactions,
          activeAgents: activeAgentsArray,
          coordinationMode: coordinationMode,
        });
        
        // Dispatch event to update agent panel
        window.dispatchEvent(new CustomEvent('agentInteractionsUpdated', {
          detail: { interactions, activeAgents: activeAgentsArray }
        }));
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
      const updatedMessages = [...messages, errorMessage];
      setMessages(updatedMessages);
      // Save to sessionStorage
      saveChatSession(productId, {
        messages: updatedMessages,
        agentInteractions: agentInteractions,
        activeAgents: activeAgents,
        coordinationMode: coordinationMode,
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Helper function to merge messages (avoid duplicates, keep latest)
  const mergeMessages = (sessionMessages: MultiAgentMessage[], backendMessages: MultiAgentMessage[]): MultiAgentMessage[] => {
    const messageMap = new Map<string, MultiAgentMessage>();
    
    // Add backend messages first
    backendMessages.forEach(msg => {
      const key = `${msg.role}_${msg.timestamp}_${msg.content.substring(0, 50)}`;
      messageMap.set(key, msg);
    });
    
    // Add session messages (they might be newer)
    sessionMessages.forEach(msg => {
      const key = `${msg.role}_${msg.timestamp}_${msg.content.substring(0, 50)}`;
      const existing = messageMap.get(key);
      if (!existing || new Date(msg.timestamp) > new Date(existing.timestamp)) {
        messageMap.set(key, msg);
      }
    });
    
    // Sort by timestamp
    return Array.from(messageMap.values()).sort((a, b) => 
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
  };

  // Load conversation history on mount - first from sessionStorage, then from backend
  useEffect(() => {
    const loadConversationHistory = async () => {
      if (!token || !productId) return;
      
      // First, try to load from sessionStorage (fast, instant restore)
      const sessionData = loadChatSession(productId);
      if (sessionData && sessionData.messages && sessionData.messages.length > 0) {
        console.log('ProductChatInterface: Loading from sessionStorage', {
          messageCount: sessionData.messages.length,
          hasInteractions: sessionData.agentInteractions.length > 0
        });
        setMessages(sessionData.messages);
        setAgentInteractions(sessionData.agentInteractions || []);
        if (sessionData.activeAgents && sessionData.activeAgents.length > 0) {
          setActiveAgents(sessionData.activeAgents);
        }
        if (sessionData.coordinationMode) {
          setCoordinationMode(sessionData.coordinationMode as CoordinationMode);
        }
      }
      
      // Then load from backend to ensure we have the latest data
      try {
        const response = await fetch(`${API_URL}/api/conversations/history?product_id=${productId}&limit=100`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          credentials: 'include',
        });
        
        if (response.ok) {
          const data = await response.json();
          if (data.conversations && Array.isArray(data.conversations)) {
            // Convert conversation history to MultiAgentMessage format
            const historyMessages: MultiAgentMessage[] = data.conversations
              .reverse() // Reverse to get chronological order
              .map((conv: any) => ({
                role: conv.message_type === 'user' ? 'user' : 'assistant',
                content: conv.content || conv.formatted_content || '',
                agentName: conv.agent_name || 'Assistant',
                timestamp: conv.created_at || new Date().toISOString(),
              }));
            
            // Merge with sessionStorage data (sessionStorage might have newer messages)
            const sessionMessages = sessionData?.messages || [];
            const mergedMessages = mergeMessages(sessionMessages, historyMessages);
            
            setMessages(mergedMessages);
            
            // Extract agent interactions from history
            const interactions: any[] = [];
            mergedMessages.forEach((msg) => {
              if (msg.interactions && Array.isArray(msg.interactions)) {
                interactions.push(...msg.interactions);
              }
            });
            // Also include sessionStorage interactions
            if (sessionData?.agentInteractions) {
              interactions.push(...sessionData.agentInteractions);
            }
            setAgentInteractions(interactions);
            
            // Save merged data back to sessionStorage
            saveChatSession(productId, {
              messages: mergedMessages,
              agentInteractions: interactions,
              activeAgents: activeAgents,
              coordinationMode: coordinationMode,
            });
          }
        }
      } catch (error) {
        console.error('Error loading conversation history:', error);
        // If backend fails, at least we have sessionStorage data
      }
    };
    
    loadConversationHistory();
  }, [token, productId]);

  const handleExport = async () => {
    if (!token || !productId) return;
    
    try {
      // Get all conversation messages for export
      const conversationText = messages
        .map((msg) => `${msg.role === 'user' ? 'User' : 'Assistant'}: ${msg.content}`)
        .join('\n\n');
      
      // Call export endpoint
      const response = await fetch(`${API_URL}/api/products/${productId}/export-prd`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          conversation_history: messages,
          format: 'html', // Request HTML format
        }),
      });
      
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `PRD_${productId}_${new Date().toISOString().split('T')[0]}.html`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to export PRD');
      }
    } catch (error) {
      console.error('Export error:', error);
      alert(`Failed to export PRD: ${error instanceof Error ? error.message : 'Unknown error'}`);
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
      productId={productId}
      onExport={handleExport}
    />
  );
}

