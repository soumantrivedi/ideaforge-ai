import { useState, useEffect, useRef, useCallback } from 'react';
import { EnhancedChatInterface } from './EnhancedChatInterface';
import { ExportPRDModal } from './ExportPRDModal';
import { AgentStatusPanel } from './AgentStatusPanel';
import { CommandPalette } from './CommandPalette';
import { initKeyboardShortcuts, keyboardShortcutManager, CommandPaletteItem } from '../lib/keyboard-shortcuts';
import type { MultiAgentMessage, CoordinationMode } from '../agents/multi-agent-system';
import { useAuth } from '../contexts/AuthContext';
import { saveChatSession, loadChatSession, clearProductSession } from '../lib/session-storage';
import { ContentFormatter } from '../lib/content-formatter';
import { streamMultiAgentSSE } from '../lib/streaming-client';

import { getValidatedApiUrl } from '../lib/runtime-config';
const API_URL = getValidatedApiUrl();

import type { LifecyclePhase } from '../lib/product-lifecycle-service';

interface ProductChatInterfaceProps {
  productId: string;
  sessionId: string;
  phases?: LifecyclePhase[];
  onPhaseSelect?: (phase: LifecyclePhase) => void;
}

export function ProductChatInterface({ productId, sessionId, phases = [], onPhaseSelect }: ProductChatInterfaceProps) {
  const { token } = useAuth();
  const [messages, setMessages] = useState<MultiAgentMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [coordinationMode, setCoordinationMode] = useState<CoordinationMode>('collaborative');
  const [activeAgents, setActiveAgents] = useState<string[]>([]);
  const [agentInteractions, setAgentInteractions] = useState<any[]>([]);
  const [agentStatuses, setAgentStatuses] = useState<any[]>([]); // AgentStatus format for HorizontalAgentStatus
  const [agentMetadata, setAgentMetadata] = useState<Record<string, any>>({}); // Store metadata per agent
  const [showAgentPanel, setShowAgentPanel] = useState<boolean>(false); // Hide by default since MainApp has it

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
          messageLength: customEvent.detail.message?.length || 0,
          phaseName: customEvent.detail.phaseName,
          allFieldsCompleted: customEvent.detail.allFieldsCompleted
        });
        
        // Add the generated message to chat as user message (the phase content)
        const userMessage: MultiAgentMessage = {
          role: 'user',
          content: customEvent.detail.message,
          timestamp: new Date().toISOString(),
        };
        
        setMessages((prev) => {
          // Avoid duplicates by checking last message
          const lastMessage = prev[prev.length - 1];
          if (lastMessage && lastMessage.content === userMessage.content) {
            console.log('ProductChatInterface: Duplicate message detected, skipping');
            return prev;
          }
          console.log('ProductChatInterface: Adding phase content to chat', {
            totalMessages: prev.length + 1
          });
          const updatedMessages = [...prev, userMessage];
          // Save to sessionStorage
          saveChatSession(productId, {
            messages: updatedMessages,
            agentInteractions: agentInteractions,
            activeAgents: activeAgents,
            coordinationMode: coordinationMode,
          });
          return updatedMessages;
        });

        // Add follow-up question as assistant message asking if user wants to process the content
        // DO NOT auto-send - wait for user confirmation
        if (customEvent.detail.allFieldsCompleted && customEvent.detail.phaseName) {
          const phaseName = customEvent.detail.phaseName;
          // Map phase names to processing questions
          const processingQuestions: Record<string, string> = {
            'Ideation': 'Do you want me to create comprehensive ideation content using this information?',
            'Market Research': 'Do you want me to analyze and process this market research data?',
            'Requirements': 'Do you want me to process these requirements and create a requirements document?',
            'Design': 'Do you want me to process these design prompts and create design mockups?',
            'Development Planning': 'Do you want me to process this development planning information?',
            'Go-to-Market': 'Do you want me to process this go-to-market strategy?',
          };

          const followUpQuestion = processingQuestions[phaseName] || `Do you want me to process this ${phaseName} phase content?`;
          
          // Add the question as an assistant message (not auto-send as user message)
          // This way it appears in chat but doesn't trigger processing until user confirms
          setTimeout(() => {
            const assistantMessage: MultiAgentMessage = {
              role: 'assistant',
              content: followUpQuestion,
              timestamp: new Date().toISOString(),
            };
            
            setMessages((prev) => {
              // Avoid duplicates by checking last message
              const lastMessage = prev[prev.length - 1];
              if (lastMessage && lastMessage.content === assistantMessage.content) {
                console.log('ProductChatInterface: Duplicate assistant question detected, skipping');
                return prev;
              }
              console.log('ProductChatInterface: Adding assistant follow-up question', {
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
          }, 500);
        }
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
  }, [productId, agentInteractions, activeAgents, coordinationMode]);

  const [useStreaming, setUseStreaming] = useState(true); // Enable streaming by default
  const [streamingMessage, setStreamingMessage] = useState<MultiAgentMessage | null>(null);
  const [currentAgent, setCurrentAgent] = useState<string | null>(null);
  const [streamingProgress, setStreamingProgress] = useState(0);

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
    setStreamingMessage(null);
    setCurrentAgent(null);
    setStreamingProgress(0);

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

      // Detect current phase from recent messages (look for "## Phase Name Phase Content" pattern)
      let detectedPhaseName: string | null = null;
      const recentMessages = [...messages, userMessage].slice(-10).reverse(); // Check last 10 messages, most recent first
      for (const msg of recentMessages) {
        if (msg.role === 'user' && msg.content) {
          // Look for pattern like "## Ideation Phase Content" or "Ideation Phase Content"
          const phaseMatch = msg.content.match(/(?:##\s*)?([A-Za-z\s]+)\s+Phase\s+Content/i);
          if (phaseMatch) {
            detectedPhaseName = phaseMatch[1].trim();
            break;
          }
        }
      }

      // Build context with phase information if detected
      const requestContext: any = {
        product_id: productId,
        session_id: sessionId,
        message_history: messages,
        always_use_rag: true, // Flag to ensure RAG is always considered
      };
      
      // Add phase_name if detected from conversation
      if (detectedPhaseName) {
        requestContext.phase_name = detectedPhaseName;
      }

      const request = {
        user_id: '00000000-0000-0000-0000-000000000000', // Will be set by backend from token
        product_id: productId,
        query: fullQuery,
        coordination_mode: 'enhanced_collaborative', // Always use enhanced collaborative for RAG integration
        supporting_agents: supportingAgents, // Always include RAG
        context: requestContext,
      };

      let streamingSucceeded = false;
      
      if (useStreaming) {
        // Use streaming SSE with initial delay for thinking time
        try {
          // Show thinking indicator immediately
          setCurrentAgent('Agents');
          setIsLoading(true);
          
          // Wait 2 seconds before starting to stream (reduced thinking time for faster response)
          await new Promise(resolve => setTimeout(resolve, 2000));
          
          await streamMultiAgentSSE(request, token, API_URL, {
            onAgentStart: (agent) => {
              setCurrentAgent(agent);
            },
            onChunk: (chunk, agent) => {
              // Update streaming message with new chunk
              setStreamingMessage((prev) => ({
                role: 'assistant',
                content: (prev?.content || '') + chunk,
                agentName: agent,
                timestamp: prev?.timestamp || new Date().toISOString(),
                interactions: prev?.interactions || [],
                metadata: prev?.metadata || {},
              }));
            },
            onAgentComplete: (agent, response, metadata) => {
              setCurrentAgent(null);
              // Store metadata for this agent
              if (metadata && agent) {
                setAgentMetadata((prev) => ({
                  ...prev,
                  [agent]: metadata,
                }));
              }
              // Also update streaming message metadata
              if (metadata && streamingMessage) {
                setStreamingMessage((prev) => ({
                  ...prev!,
                  metadata: metadata,
                }));
              }
            },
            onInteraction: (from_agent, to_agent, query, response, metadata) => {
              // Store interaction with metadata
              const interaction = {
                from_agent,
                to_agent,
                query,
                response,
                metadata: metadata || {},
                timestamp: new Date().toISOString(),
              };
              setAgentInteractions((prev) => {
                // Avoid duplicates - check if interaction already exists
                const exists = prev.some(
                  (i: any) => 
                    i.from_agent === from_agent && 
                    i.to_agent === to_agent && 
                    i.query === query &&
                    Math.abs(new Date(i.timestamp).getTime() - new Date(interaction.timestamp).getTime()) < 1000
                );
                if (exists) return prev;
                return [...prev, interaction];
              });
              // Store metadata for the agent
              if (metadata && to_agent) {
                setAgentMetadata((prev) => ({
                  ...prev,
                  [to_agent]: metadata,
                }));
              }
            },
            onProgress: (progress, message) => {
              setStreamingProgress(progress);
            },
            onComplete: (response, agentInteractions, metadata) => {
              streamingSucceeded = true;
              
              // Merge agent metadata into interactions
              const enrichedInteractions = agentInteractions.map((interaction: any) => {
                const agentName = interaction.to_agent || interaction.from_agent;
                const agentMeta = agentMetadata[agentName] || {};
                return {
                  ...interaction,
                  metadata: {
                    ...agentMeta,
                    ...(interaction.metadata || {}),
                  },
                };
              });
              
              const assistantMessage: MultiAgentMessage = {
                role: 'assistant',
                content: response,
                agentName: metadata?.primary_agent || 'Assistant',
                timestamp: new Date().toISOString(),
                interactions: enrichedInteractions,
                metadata: metadata, // Include full metadata for transparency
              };
              
              const finalMessages = [...updatedMessages, assistantMessage];
              setMessages(finalMessages);
              setStreamingMessage(null);
              
              // Extract active agents
              const uniqueAgents = new Set<string>();
              enrichedInteractions.forEach((interaction: any) => {
                if (interaction.to_agent) uniqueAgents.add(interaction.to_agent);
                if (interaction.from_agent) uniqueAgents.add(interaction.from_agent);
              });
              if (metadata?.primary_agent) uniqueAgents.add(metadata.primary_agent);
              const activeAgentsArray = Array.from(uniqueAgents);
              setActiveAgents(activeAgentsArray);
              setAgentInteractions(enrichedInteractions);
              
              // Save to sessionStorage
              saveChatSession(productId, {
                messages: finalMessages,
                agentInteractions: enrichedInteractions,
                activeAgents: activeAgentsArray,
                coordinationMode: coordinationMode,
              });
              
              // Dispatch event with enriched interactions
              window.dispatchEvent(new CustomEvent('agentInteractionsUpdated', {
                detail: { interactions: enrichedInteractions, activeAgents: activeAgentsArray }
              }));
            },
            onError: (error) => {
              console.error('Streaming error:', error);
              
              // If we have a streaming message with content, treat it as partial success
              if (streamingMessage && streamingMessage.content && streamingMessage.content.length > 50) {
                console.warn('Streaming error but partial response available, using partial result');
                const partialMessage: MultiAgentMessage = {
                  role: 'assistant',
                  content: streamingMessage.content + `\n\n⚠️ *Note: Response was interrupted. Partial results shown.*`,
                  agentName: streamingMessage.agentName || 'Assistant',
                  timestamp: streamingMessage.timestamp || new Date().toISOString(),
                  interactions: streamingMessage.interactions || [],
                  metadata: { ...streamingMessage.metadata, partial: true, error: error },
                };
                setMessages((prev) => [...prev, partialMessage]);
                setStreamingMessage(null);
                setIsLoading(false);
                setCurrentAgent(null);
                return;
              }
              
              streamingSucceeded = false;
              setIsLoading(false);
              setCurrentAgent(null);
              setStreamingMessage(null);
              
              // Show user-friendly error message
              const errorMessage: MultiAgentMessage = {
                role: 'assistant',
                content: `⚠️ **Streaming Error**\n\n${error}\n\nPlease try again. If the problem persists, the system will automatically fall back to a regular request.`,
                timestamp: new Date().toISOString(),
              };
              setMessages((prev) => [...prev, errorMessage]);
            },
          });
          
          // If streaming completed successfully, we're done
          if (streamingSucceeded) {
            return;
          }
        } catch (streamError) {
          console.error('Streaming failed, falling back to regular request:', streamError);
          streamingSucceeded = false;
        }
      }

      // Fallback to regular non-streaming request if streaming failed or disabled
      if (!useStreaming || !streamingSucceeded) {
        // Show thinking indicator
        setCurrentAgent('Agents');
        setIsLoading(true);
        
        // Wait 2 seconds before starting to stream (reduced thinking time for faster response)
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        const response = await fetch(`${API_URL}/api/multi-agent/process`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify(request),
        });

        if (response.ok) {
          const data = await response.json();
          const fullResponse = data.response || 'No response';
          
          // Simulate streaming for non-streaming responses - faster, more interactive typing
          const chunkSize = 2; // Smaller chunks for character-by-character typing effect
          let streamedContent = '';
          
          // Initialize streaming message
          setStreamingMessage({
            role: 'assistant',
            content: '',
            agentName: data.primary_agent || 'Assistant',
            timestamp: new Date().toISOString(),
            interactions: data.agent_interactions || [],
          });
          
          // Stream the response character by character with faster typing effect
          for (let i = 0; i < fullResponse.length; i += chunkSize) {
            const chunk = fullResponse.slice(i, i + chunkSize);
            streamedContent += chunk;
            
            setStreamingMessage((prev) => ({
              role: 'assistant',
              content: streamedContent,
              agentName: data.primary_agent || 'Assistant',
              timestamp: prev?.timestamp || new Date().toISOString(),
              interactions: data.agent_interactions || [],
            }));
            
            // Faster delay for more interactive typing effect (8ms instead of 20ms)
            await new Promise(resolve => setTimeout(resolve, 8));
          }
          
          // Final message
          const assistantMessage: MultiAgentMessage = {
            role: 'assistant',
            content: fullResponse,
            agentName: data.primary_agent || 'Assistant',
            timestamp: new Date().toISOString(),
            interactions: data.agent_interactions || [],
          };
          const finalMessages = [...updatedMessages, assistantMessage];
          setMessages(finalMessages);
          setStreamingMessage(null);
          
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
            messages: finalMessages,
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
      }
    } catch (error) {
      const errorMessage: MultiAgentMessage = {
        role: 'assistant',
        content: `Error: ${error instanceof Error ? error.message : 'Failed to send message'}`,
        timestamp: new Date().toISOString(),
      };
      const updatedMessages = [...messages, errorMessage];
      setMessages(updatedMessages);
      setStreamingMessage(null);
      // Save to sessionStorage
      saveChatSession(productId, {
        messages: updatedMessages,
        agentInteractions: agentInteractions,
        activeAgents: activeAgents,
        coordinationMode: coordinationMode,
      });
    } finally {
      setIsLoading(false);
      setStreamingProgress(0);
      setCurrentAgent(null);
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

  const [showExportModal, setShowExportModal] = useState(false);

  const handleExport = () => {
    setShowExportModal(true);
  };

  // Combine messages with streaming message for display
  const displayMessages = [...messages];
  if (streamingMessage) {
    displayMessages.push(streamingMessage);
  }

  // Convert agentInteractions to format expected by AgentStatusPanel
  // Merge agent metadata from agent_complete events into interactions
  const formattedInteractions = agentInteractions.map((interaction: any) => {
    const toAgent = interaction.to_agent || interaction.fromAgent || '';
    const fromAgent = interaction.from_agent || interaction.fromAgent || '';
    const agentName = toAgent || fromAgent;
    
    // Merge metadata from agent_complete events if available
    const agentMeta = agentMetadata[agentName] || {};
    const interactionMeta = interaction.metadata || {};
    
    return {
      from_agent: fromAgent,
      to_agent: toAgent,
      query: interaction.query || '',
      response: interaction.response || '',
      timestamp: interaction.timestamp || new Date().toISOString(),
      metadata: {
        ...agentMeta,  // Metadata from agent_complete events
        ...interactionMeta,  // Metadata from interaction events (takes precedence)
      },
    };
  });

  // Update agent statuses from active agents and interactions
  useEffect(() => {
    if (activeAgents.length > 0 || agentInteractions.length > 0) {
      const statuses = activeAgents.map((agentName: string) => {
        const role = agentName.toLowerCase().replace(/\s+/g, '_');
        const latestInteraction = agentInteractions
          .filter((i: any) => i.to_agent === agentName || i.from_agent === agentName)
          .sort((a: any, b: any) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())[0];
        return {
          role,
          name: agentName,
          isActive: true,
          lastActivity: latestInteraction?.timestamp ? new Date(latestInteraction.timestamp).toLocaleString() : undefined,
          interactions: agentInteractions.filter((i: any) => i.to_agent === agentName || i.from_agent === agentName).length,
          latestInteraction,
        };
      });
      setAgentStatuses(statuses);
    } else {
      setAgentStatuses([]);
    }
  }, [activeAgents, agentInteractions]);

  return (
    <>
      <CommandPalette />
      <div className="flex gap-4 h-full">
        {/* Main Chat Interface */}
        <div className="flex-1 min-w-0">
          <EnhancedChatInterface
            messages={displayMessages}
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
            coordinationMode={coordinationMode}
            onCoordinationModeChange={setCoordinationMode}
            activeAgents={activeAgents}
            productId={productId}
            onExport={handleExport}
            streamingMessage={streamingMessage}
            currentAgent={currentAgent}
            streamingProgress={streamingProgress}
            useStreaming={useStreaming}
            onStreamingToggle={setUseStreaming}
            phases={phases}
            agentStatuses={agentStatuses}
            agentInteractions={agentInteractions}
          />
        </div>
      </div>
      {showExportModal && (
        <ExportPRDModal
          productId={productId || ''}
          isOpen={showExportModal}
          onClose={() => setShowExportModal(false)}
          token={token}
          conversationHistory={messages.map(msg => ({
            role: msg.role,
            content: msg.content,
            timestamp: msg.timestamp
          }))}
        />
      )}
    </>
  );
}

