import { useState, useEffect } from 'react';
import { MessageSquare, Settings, Database, FileText, Download, LayoutDashboard, Folder, History, User, LogOut, ChevronLeft, ChevronRight, BarChart3, Star } from 'lucide-react';
import { ProductChatInterface } from './ProductChatInterface';
import { AgentStatusPanel } from './AgentStatusPanel';
import { ProductLifecycleSidebar } from './ProductLifecycleSidebar';
import { PhaseFormModal } from './PhaseFormModal';
import { ValidationModal } from './ValidationModal';
import { EnhancedSettings } from './EnhancedSettings';
import { KnowledgeBaseManagerWrapper } from './KnowledgeBaseManagerWrapper';
import { ProductsDashboard } from './ProductsDashboard';
import { PortfolioView } from './PortfolioView';
import { ConversationHistory } from './ConversationHistory';
import { UserProfile } from './UserProfile';
import { IdeaScoreDashboard } from './IdeaScoreDashboard';
import { ProductSummaryPRDGenerator } from './ProductSummaryPRDGenerator';
import { getValidatedApiUrl } from '../lib/runtime-config';

const API_URL = getValidatedApiUrl();
import { useAuth } from '../contexts/AuthContext';
import { lifecycleService, type LifecyclePhase, type PhaseSubmission } from '../lib/product-lifecycle-service';
import { saveAppState, loadAppState, resetProductState, clearAppState } from '../lib/session-storage';

type View = 'dashboard' | 'chat' | 'settings' | 'knowledge' | 'portfolio' | 'history' | 'profile' | 'scoring';

export function MainApp() {
  const { user, logout, token } = useAuth();
  
  // Load app state from sessionStorage on mount
  const savedState = loadAppState();
  const [view, setView] = useState<View>((savedState?.view as View) || 'dashboard');
  const [productId, setProductId] = useState<string>(savedState?.productId || '');
  const [phases, setPhases] = useState<LifecyclePhase[]>([]);
  const [submissions, setSubmissions] = useState<PhaseSubmission[]>([]);
  const [currentPhase, setCurrentPhase] = useState<LifecyclePhase | null>(null);
  const [savedPhaseId, setSavedPhaseId] = useState<string | undefined>(savedState?.currentPhaseId);
  const [isFormModalOpen, setIsFormModalOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [activeAgents, setActiveAgents] = useState<any[]>([]);
  const [agentInteractions, setAgentInteractions] = useState<any[]>([]);
  const [validationModalOpen, setValidationModalOpen] = useState(false);
  const [validationData, setValidationData] = useState<{
    generatedContent: string;
    phaseName: string;
    formData: Record<string, string>;
    previousQuestions: Array<{ question: string; answer: string }>;
    agentInteractions: any[];
    submissionId?: string;
  } | null>(null);

  useEffect(() => {
    if (token) {
      lifecycleService.setToken(token);
      loadPhases();
    }
  }, [token]);

  // Listen for agent interactions updates
  useEffect(() => {
    const handleAgentInteractionsUpdate = (event: Event) => {
      const customEvent = event as CustomEvent;
      if (customEvent.detail) {
        const { interactions, activeAgents: agents } = customEvent.detail;
        
        // Convert active agents to AgentStatus format
        const agentStatuses = agents.map((agentName: string) => {
          const role = agentName.toLowerCase().replace(/\s+/g, '_');
          const latestInteraction = interactions
            .filter((i: any) => i.to_agent === agentName || i.from_agent === agentName)
            .sort((a: any, b: any) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())[0];
          
          return {
            role,
            name: agentName,
            isActive: true,
            lastActivity: latestInteraction ? new Date(latestInteraction.timestamp).toLocaleString() : undefined,
            interactions: interactions.filter((i: any) => i.to_agent === agentName || i.from_agent === agentName).length,
            latestInteraction,
          };
        });
        
        setActiveAgents(agentStatuses);
        setAgentInteractions(interactions);
      }
    };

    window.addEventListener('agentInteractionsUpdated', handleAgentInteractionsUpdate);
    return () => {
      window.removeEventListener('agentInteractionsUpdated', handleAgentInteractionsUpdate);
    };
  }, []);

  // Save app state to sessionStorage whenever it changes
  useEffect(() => {
    saveAppState({
      productId,
      currentPhaseId: currentPhase?.id,
      view,
      // Don't save phases/submissions - they should be loaded fresh from backend
    });
  }, [productId, currentPhase, view]);

  useEffect(() => {
    if (productId && token) {
      console.log('MainApp: Loading data for productId:', productId);
      lifecycleService.setToken(token);
      loadSubmissions();
      // Also reload phases when product changes to ensure fresh data
      loadPhases();
      
      // Reset any corrupted state when switching products
      // This ensures clean state for each product
      const prevProductId = savedState?.productId;
      if (prevProductId && prevProductId !== productId) {
        console.log('MainApp: Product changed, resetting previous product state');
        resetProductState(prevProductId);
      }
    } else {
      console.log('MainApp: Skipping data load', { productId, hasToken: !!token });
    }
  }, [productId, token]);

  // Load agents for current phase
  useEffect(() => {
    const loadAgentsForPhase = async () => {
      if (!currentPhase || !token) {
        // If no phase selected, clear agents or show default
        setActiveAgents([]);
        return;
      }

      try {
        const response = await fetch(
          `${API_URL}/api/agents/by-phase?phase_name=${encodeURIComponent(currentPhase.phase_name)}`,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
            credentials: 'include',
          }
        );

        if (response.ok) {
          const data = await response.json();
          // Convert backend agent format to frontend AgentStatus format
          const agentStatuses = data.agents.map((agent: any) => ({
            role: agent.role,
            name: agent.name,
            isActive: agent.isActive,
            lastActivity: undefined,
            interactions: 0,
            latestInteraction: undefined,
          }));
          setActiveAgents(agentStatuses);
        } else {
          console.error('Failed to load agents for phase:', response.status);
          setActiveAgents([]);
        }
      } catch (error) {
        console.error('Error loading agents for phase:', error);
        setActiveAgents([]);
      }
    };

    loadAgentsForPhase();
  }, [currentPhase, token]);

  const loadPhases = async () => {
    try {
      const loadedPhases = await lifecycleService.getAllPhases();
      const phasesArray = Array.isArray(loadedPhases) ? loadedPhases : [];
      setPhases(phasesArray);
      
      // Restore current phase from saved state if available
      if (savedPhaseId && phasesArray.length > 0) {
        const phase = phasesArray.find(p => p.id === savedPhaseId);
        if (phase) {
          setCurrentPhase(phase);
          setSavedPhaseId(undefined); // Clear after restoring
        }
      }
    } catch (error) {
      console.error('Error loading phases:', error);
      setPhases([]);
    }
  };

  const loadSubmissions = async () => {
    if (!productId) {
      console.log('loadSubmissions: No productId, skipping');
      setSubmissions([]);
      return;
    }
    try {
      console.log('loadSubmissions: Loading submissions for productId:', productId);
      const loadedSubmissions = await lifecycleService.getPhaseSubmissions(productId);
      console.log('loadSubmissions: Loaded', loadedSubmissions?.length || 0, 'submissions');
      setSubmissions(Array.isArray(loadedSubmissions) ? loadedSubmissions : []);
    } catch (error) {
      console.error('Error loading submissions:', error);
      setSubmissions([]);
    }
  };

  // Helper function to reset state when switching products
  const handleProductChange = (newProductId: string) => {
    const prevProductId = productId;
    
    // If switching to a different product, reset previous product's state
    if (prevProductId && prevProductId !== newProductId) {
      console.log('MainApp: Switching products, resetting state', { from: prevProductId, to: newProductId });
      resetProductState(prevProductId);
    }
    
    // Reset UI state for new product
    setProductId(newProductId);
    setCurrentPhase(null);
    setSubmissions([]);
    setActiveAgents([]);
    setAgentInteractions([]);
    setValidationModalOpen(false);
    setValidationData(null);
    setIsFormModalOpen(false);
    
    // Reload data for new product
    if (newProductId && token) {
      lifecycleService.setToken(token);
      loadSubmissions();
      loadPhases();
    }
  };

  const handleFormSubmit = async (formData: Record<string, string>) => {
    if (!productId || !currentPhase || !user || !token) return;
    
    const isDesignPhase = currentPhase.phase_name.toLowerCase() === 'design';
    
    try {
      // First, save the form data
      await lifecycleService.submitPhaseData(productId, currentPhase.id, formData, user.id);
      
      // For Design phase, skip multi-agent generation - just save prompts
      // User will save prompts to chatbot separately with scoring
      if (isDesignPhase) {
        // Get submission to store prompts
        const submission = await lifecycleService.getPhaseSubmission(productId, currentPhase.id);
        
        // Close the form modal - prompts are saved, user can now save to chatbot
        setIsFormModalOpen(false);
        
        // Reload submissions to update UI
        await loadSubmissions();
        
        // Reset any corrupted UI state after design phase completion
        // This prevents UI distortion issues
        setTimeout(() => {
          // Force a UI refresh by resetting current phase state
          const currentPhaseId = currentPhase.id;
          setCurrentPhase(null);
          setTimeout(() => {
            const phase = phases.find(p => p.id === currentPhaseId);
            if (phase) {
              setCurrentPhase(phase);
            }
          }, 100);
        }, 500);
        
        return; // Don't proceed with multi-agent generation
      }
      
      // Build a comprehensive query for agent processing
      const formDataSummary = Object.entries(formData)
        .map(([key, value]) => `${key.replace(/_/g, ' ')}: ${value}`)
        .join('\n');
      
      const query = `Generate comprehensive content for the ${currentPhase.phase_name} phase based on the following information:\n\n${formDataSummary}\n\nPlease provide a detailed, well-structured response that synthesizes this information and adds valuable insights using knowledge from the RAG knowledge base, research findings, and analysis from relevant agents.`;
      
      // Determine appropriate agents based on phase
      let primaryAgent = 'ideation';
      let supportingAgents: string[] = ['rag', 'research'];
      
      if (currentPhase.phase_name.toLowerCase().includes('research')) {
        primaryAgent = 'research';
        supportingAgents = ['rag', 'analysis'];
      } else if (currentPhase.phase_name.toLowerCase().includes('requirement')) {
        primaryAgent = 'analysis';
        supportingAgents = ['rag', 'research'];
      } else if (currentPhase.phase_name.toLowerCase().includes('development')) {
        primaryAgent = 'prd_authoring';
        supportingAgents = ['rag', 'analysis'];
      } else if (currentPhase.phase_name.toLowerCase().includes('market')) {
        primaryAgent = 'research';
        supportingAgents = ['rag', 'analysis'];
      }
      
      // Use async job processing to avoid Cloudflare timeout
      const { processAsyncJob } = await import('../utils/asyncJobProcessor');
      
      const requestData = {
        user_id: user.id,
        product_id: productId,
        query: query,
        coordination_mode: 'enhanced_collaborative',
        primary_agent: primaryAgent,
        supporting_agents: supportingAgents,
        context: {
          product_id: productId,
          phase_id: currentPhase.id,
          phase_name: currentPhase.phase_name,
          form_data: formData,
        },
      };

      // Show loading indicator
      setLoading(true);
      let progressMessage = 'Submitting request...';

      try {
        const data = await processAsyncJob(requestData, {
          apiUrl: API_URL,
          token,
          onProgress: (status) => {
            progressMessage = status.message || `Processing... ${Math.round((status.progress || 0) * 100)}%`;
            console.log('Job progress:', status);
            // You could update UI here with progress
          },
          pollInterval: 2000, // Poll every 2 seconds
          maxPollAttempts: 150, // 5 minutes max
          timeout: 300000, // 5 minutes timeout
        });
        console.log('Multi-agent response received:', {
          hasResponse: !!data.response,
          responseLength: data.response?.length || 0,
          primaryAgent: data.primary_agent,
          metadata: data.metadata
        });
        
        const generatedContent = data.response || '';
        const agentInteractions = data.agent_interactions || [];
      
        if (!generatedContent) {
          console.warn('Generated content is empty');
          alert('AI generated an empty response. Please try again or check your AI provider configuration.');
          setLoading(false);
          return;
        }
        
        // Continue with existing logic...
        // Extract previous questions and answers from form data
        const previousQuestions: Array<{ question: string; answer: string }> = [];
        if (currentPhase.required_fields && currentPhase.template_prompts) {
          currentPhase.required_fields.forEach((field, idx) => {
            const prompt = currentPhase.template_prompts?.[idx] || field;
            const answer = formData[field] || '';
            if (answer) {
              previousQuestions.push({
                question: prompt,
                answer: answer,
              });
            }
          });
        }
        
        // Get submission ID for updating later
        const submission = await lifecycleService.getPhaseSubmission(productId, currentPhase.id);
        
        // Show validation modal
        setValidationData({
          generatedContent,
          phaseName: currentPhase.phase_name,
          formData,
          previousQuestions,
          agentInteractions,
          submissionId: submission?.id,
        });
        setValidationModalOpen(true);
        setLoading(false);
      } catch (error) {
        console.error('Error submitting form:', error);
        setLoading(false);
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        
        // Check if error is about missing AI provider
        if (errorMessage.includes('No AI provider') || errorMessage.includes('configure at least one AI provider')) {
          const shouldGoToSettings = confirm(
            `${errorMessage}\n\nWould you like to go to Settings to configure an AI provider now?`
          );
          if (shouldGoToSettings) {
            setView('settings');
          }
          return; // Don't show alert, user chose to go to Settings or dismissed
        }
        
        alert(`Failed to process form: ${errorMessage}`);
      }
    } catch (error) {
      console.error('Error in handleFormSubmit:', error);
      setLoading(false);
      alert(`Failed to submit form: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleValidationAccept = async (score: number, feedback?: string) => {
    if (!validationData || !productId || !currentPhase || !token) return;
    
    try {
      // Update phase submission with generated content and score
      const submission = await lifecycleService.getPhaseSubmission(productId, currentPhase.id);
      if (submission) {
        // Store score in metadata
        const metadata = {
          ...(submission.metadata || {}),
          validation_score: score,
          validation_feedback: feedback || '',
          validated_at: new Date().toISOString(),
        };
        
        await lifecycleService.updatePhaseContent(
          submission.id,
          validationData.generatedContent,
          'completed',
          metadata
        );
      }
      
      // Reload submissions to update UI
      await loadSubmissions();
      
      // Close modals
      setIsFormModalOpen(false);
      setValidationModalOpen(false);
      
      // Send to chatbot with score
      const chatbotMessage = `Generated content for ${currentPhase.phase_name} phase (Score: ${score}/5):\n\n${validationData.generatedContent}`;
      
      window.dispatchEvent(new CustomEvent('phaseFormGenerated', {
        detail: {
          message: chatbotMessage,
          productId,
        }
      }));
      
      console.log('Form submission completed with score:', score);
    } catch (error) {
      console.error('Error accepting validation:', error);
      alert(`Failed to save validation: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleValidationRefine = async (refinementFeedback: string) => {
    if (!validationData || !productId || !currentPhase || !user || !token) return;
    
    try {
      
      // Refine the response
      const refinedResponse = await fetch(`${API_URL}/api/multi-agent/process`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          user_id: user.id,
          product_id: productId,
          query: `Refine this response based on user feedback:\n\nOriginal Response:\n${validationData.generatedContent}\n\nUser Feedback:\n${refinementFeedback}`,
          coordination_mode: 'enhanced_collaborative',
          primary_agent: 'ideation', // Use appropriate agent based on phase
          supporting_agents: ['rag', 'validation'],
          context: {
            product_id: productId,
            phase_id: currentPhase.id,
            phase_name: currentPhase.phase_name,
            form_data: validationData.formData,
            original_content: validationData.generatedContent,
            refinement_feedback: refinementFeedback,
          },
        }),
      });
      
      if (refinedResponse.ok) {
        const refinedData = await refinedResponse.json();
        const refinedContent = refinedData.response || validationData.generatedContent;
        
        // Update validation data with refined content
        setValidationData({
          ...validationData,
          generatedContent: refinedContent,
        });
        
        // Show validation modal again with refined content
        // (modal will stay open, just update the content)
        console.log('Response refined, showing validation modal again');
      } else {
        throw new Error('Failed to refine response');
      }
    } catch (error) {
      console.error('Error refining response:', error);
      alert(`Failed to refine response: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleLogout = async () => {
    await logout();
    window.location.reload();
  };

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--bg-secondary)' }}>
      {/* Header */}
      <header className="border-b" style={{ backgroundColor: 'var(--card-bg)', borderColor: 'var(--border-color)' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <h1 className="text-lg font-semibold text-gray-900 tracking-tight">IdeaForge AI</h1>
              <div className="h-4 w-px bg-gray-300"></div>
              <div className="text-sm text-gray-500">
                {user?.tenant_name && (
                  <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs font-medium">
                    {user.tenant_name}
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 text-sm" style={{ color: 'var(--text-primary)' }}>
                {user?.avatar_url ? (
                  <img src={user.avatar_url} alt={user.full_name || user.email} className="w-8 h-8 rounded-full" />
                ) : (
                  <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold" style={{ backgroundColor: 'var(--accent-color)', color: 'var(--button-primary-text)' }}>
                    {user?.email?.charAt(0).toUpperCase()}
                  </div>
                )}
                <span>{user?.full_name || user?.email}</span>
              </div>
              <button
                onClick={handleLogout}
                className="p-2 rounded-lg transition"
                style={{ color: 'var(--text-secondary)' }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = 'var(--text-primary)';
                  e.currentTarget.style.backgroundColor = 'var(--bg-tertiary)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = 'var(--text-secondary)';
                  e.currentTarget.style.backgroundColor = 'transparent';
                }}
                title="Logout"
              >
                <LogOut className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="flex relative">
        {/* Sidebar Navigation */}
        <aside 
          className={`${isSidebarCollapsed ? 'w-0' : 'w-64'} transition-all duration-300 overflow-hidden border-r min-h-[calc(100vh-4rem)]`} 
          style={{ backgroundColor: 'var(--card-bg)', borderColor: 'var(--border-color)' }}
        >
          <nav className="p-4 space-y-2">
              <button
                onClick={() => setView('dashboard')}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-md transition font-medium"
                style={{
                  backgroundColor: view === 'dashboard' ? 'var(--bg-tertiary)' : 'transparent',
                  color: view === 'dashboard' ? 'var(--text-primary)' : 'var(--text-secondary)'
                }}
                onMouseEnter={(e) => {
                  if (view !== 'dashboard') {
                    e.currentTarget.style.backgroundColor = 'var(--bg-tertiary)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (view !== 'dashboard') {
                    e.currentTarget.style.backgroundColor = 'transparent';
                  }
                }}
              >
              <LayoutDashboard className="w-5 h-5" />
              <span>Dashboard</span>
            </button>
            {(['portfolio', 'chat', 'history', 'profile', 'settings', 'knowledge', 'scoring'] as View[]).map((viewName) => {
              const icons = {
                portfolio: Folder,
                chat: MessageSquare,
                history: History,
                profile: User,
                settings: Settings,
                knowledge: Database,
                scoring: BarChart3,
              };
              const labels = {
                portfolio: 'Portfolio',
                chat: 'Chat',
                history: 'History',
                profile: 'Profile',
                settings: 'Settings',
                knowledge: 'Knowledge Base',
                scoring: 'Idea Scoring',
              };
              const Icon = icons[viewName];
              return (
                <button
                  key={viewName}
                  onClick={() => {
                    setView(viewName);
                    // Preserve productId when navigating - don't clear it
                    // If productId is needed but missing, the view will show product selector
                  }}
                  className="w-full flex items-center gap-3 px-4 py-3 rounded-md transition font-medium"
                  style={{
                    backgroundColor: view === viewName ? 'var(--bg-tertiary)' : 'transparent',
                    color: view === viewName ? 'var(--text-primary)' : 'var(--text-secondary)'
                  }}
                  onMouseEnter={(e) => {
                    if (view !== viewName) {
                      e.currentTarget.style.backgroundColor = 'var(--bg-tertiary)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (view !== viewName) {
                      e.currentTarget.style.backgroundColor = 'transparent';
                    }
                  }}
                >
                  <Icon className="w-5 h-5" />
                  <span>{labels[viewName]}</span>
                </button>
              );
            })}
          </nav>
        </aside>
        
        {/* Sidebar Toggle Button */}
        <button
          onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
          className={`absolute ${isSidebarCollapsed ? 'left-0' : 'left-64'} top-1/2 -translate-y-1/2 z-10 p-2 rounded-r-lg transition-all duration-300`}
          style={{ 
            backgroundColor: 'var(--card-bg)', 
            borderColor: 'var(--border-color)',
            borderLeft: 'none',
            borderTop: '1px solid var(--border-color)',
            borderRight: '1px solid var(--border-color)',
            borderBottom: '1px solid var(--border-color)',
            boxShadow: '2px 0 4px rgba(0,0,0,0.1)'
          }}
          title={isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isSidebarCollapsed ? (
            <ChevronRight className="w-5 h-5" style={{ color: 'var(--text-primary)' }} />
          ) : (
            <ChevronLeft className="w-5 h-5" style={{ color: 'var(--text-primary)' }} />
          )}
        </button>

        {/* Main Content */}
        <main className="flex-1 p-6">
          {view === 'dashboard' && (
            <ProductsDashboard
              onProductSelect={(id) => {
                console.log('Dashboard: Product selected:', id);
                if (id) {
                  handleProductChange(id);
                  setView('chat');
                } else {
                  console.error('Dashboard: Invalid product ID received:', id);
                }
              }}
            />
          )}
          {view === 'portfolio' && (
            <PortfolioView
              onProductSelect={(id) => {
                console.log('PortfolioView onProductSelect called with:', id);
                if (id) {
                  handleProductChange(id);
                  setView('chat');
                } else {
                  console.error('PortfolioView onProductSelect received invalid id:', id);
                }
              }}
            />
          )}
          {view === 'chat' && (
            <div className="flex gap-6 h-[calc(100vh-8rem)] relative">
              <div className="flex-1">
                {productId ? (
                  <div className="sticky top-0 h-[calc(100vh-8rem)] overflow-y-auto">
                  <ProductLifecycleSidebar
                    phases={phases || []}
                    submissions={submissions || []}
                    currentPhaseId={currentPhase?.id}
                    onPhaseSelect={(phase) => {
                      setCurrentPhase(phase);
                      setIsFormModalOpen(true);
                    }}
                    productId={productId}
                  />
                  </div>
                ) : (
                  <div className="h-full flex items-center justify-center rounded-xl border" style={{ backgroundColor: 'var(--card-bg)', borderColor: 'var(--border-color)' }}>
                    <div className="text-center p-8 w-full max-w-2xl">
                      <p className="mb-4 text-lg font-medium" style={{ color: 'var(--text-primary)' }}>Select a product to view lifecycle phases</p>
                      <div className="mt-6">
                        <ProductsDashboard
                          onProductSelect={(id) => {
                            console.log('Chat view (left): Product selected:', id);
                            if (id) {
                              handleProductChange(id);
                            } else {
                              console.error('Chat view (left): Invalid product ID received:', id);
                            }
                          }}
                          compact={true}
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>
              <div className="flex-1 overflow-y-auto">
                {productId ? (
                  <ProductChatInterface
                    productId={productId}
                    sessionId={productId}
                  />
                ) : (
                  <div className="h-full flex items-center justify-center rounded-xl border" style={{ backgroundColor: 'var(--card-bg)', borderColor: 'var(--border-color)' }}>
                    <div className="text-center p-8 w-full max-w-2xl">
                      <p className="mb-4 text-lg font-medium" style={{ color: 'var(--text-primary)' }}>Select a product to start chatting</p>
                      <div className="mt-6">
                        <ProductsDashboard
                          onProductSelect={(id) => {
                            console.log('Chat view (right): Product selected:', id);
                            if (id) {
                              handleProductChange(id);
                            } else {
                              console.error('Chat view (right): Invalid product ID received:', id);
                            }
                          }}
                          compact={true}
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>
              <div className="w-64">
                <div className="sticky top-0 h-[calc(100vh-8rem)] overflow-y-auto">
                <AgentStatusPanel 
                  agents={activeAgents} 
                  agentInteractions={agentInteractions}
                />
                </div>
              </div>
            </div>
          )}
          {view === 'history' && (
            <ConversationHistory />
          )}
          {view === 'profile' && (
            <UserProfile />
          )}
          {view === 'settings' && (
            <EnhancedSettings />
          )}
          {view === 'knowledge' && (
            <div className="space-y-6">
              {!productId && (
                <div className="mb-4 p-4 rounded-md border" style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)' }}>
                  <p className="text-sm mb-4" style={{ color: 'var(--text-primary)' }}>
                    <strong>Select a product:</strong> Choose a product to manage product-specific knowledge articles, or work with general knowledge articles below.
                  </p>
                  <ProductsDashboard
                    onProductSelect={(id) => {
                      console.log('Knowledge Base view: Product selected:', id);
                      if (id) {
                        handleProductChange(id);
                      } else {
                        console.error('Knowledge Base view: Invalid product ID received:', id);
                      }
                    }}
                    compact={true}
                  />
                </div>
              )}
              <KnowledgeBaseManagerWrapper productId={productId || undefined} />
            </div>
          )}
          {view === 'scoring' && (
            <div className="space-y-6">
              <div className="mb-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Idea Score Dashboard</h2>
                <p className="text-gray-600">
                  View product idea scores, generate summaries, and create standardized PRDs from conversation sessions.
                </p>
              </div>
              
              {!productId ? (
                <div className="space-y-4">
                  <div className="p-4 rounded-md border" style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)' }}>
                    <p className="text-sm mb-4" style={{ color: 'var(--text-primary)' }}>
                      <strong>Select a product:</strong> Choose a product to view scores or generate summaries and PRDs.
                    </p>
                    <ProductsDashboard
                      onProductSelect={(id) => {
                        console.log('Scoring view: Product selected:', id);
                        if (id) {
                          handleProductChange(id);
                        }
                      }}
                      compact={true}
                    />
                  </div>
                  
                  {user?.tenant_id && (
                    <div className="mt-6">
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">Tenant-Level Scores</h3>
                      <IdeaScoreDashboard
                        tenantId={user.tenant_id}
                        onProductSelect={(id) => {
                          handleProductChange(id);
                          setView('scoring');
                        }}
                      />
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <button
                        onClick={() => setProductId('')}
                        className="text-sm text-blue-600 hover:text-blue-700 mb-2"
                      >
                        ← Back to all products
                      </button>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">Generate Summary & PRD</h3>
                      <ProductSummaryPRDGenerator
                        productId={productId}
                        canEdit={true} // Will be checked internally
                        onSummaryGenerated={(summaryId) => {
                          console.log('Summary generated:', summaryId);
                        }}
                        onPRDGenerated={(prdId) => {
                          console.log('PRD generated:', prdId);
                        }}
                        onScoreGenerated={(scoreId) => {
                          console.log('Score generated:', scoreId);
                          // Reload scores after generation
                          window.dispatchEvent(new Event('scores-updated'));
                        }}
                      />
                    </div>
                    
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">Product Scores</h3>
                      <IdeaScoreDashboard
                        productId={productId}
                        onProductSelect={(id) => {
                          handleProductChange(id);
                        }}
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </main>
      </div>

      {/* Phase Form Modal */}
      {currentPhase && (
        <PhaseFormModal
          phase={currentPhase}
          isOpen={isFormModalOpen}
          onClose={() => setIsFormModalOpen(false)}
          onSubmit={handleFormSubmit}
          existingData={submissions.find(s => s.phase_id === currentPhase.id)?.form_data}
          productId={productId}
          sessionId={productId}
          onNavigateToSettings={() => {
            setIsFormModalOpen(false);
            setView('settings');
          }}
        />
      )}
      
      {/* Validation Modal */}
      {validationData && (
        <ValidationModal
          isOpen={validationModalOpen}
          onClose={() => {
            setValidationModalOpen(false);
            setValidationData(null);
          }}
          onAccept={handleValidationAccept}
          onRefine={handleValidationRefine}
          generatedContent={validationData.generatedContent}
          phaseName={validationData.phaseName}
          formData={validationData.formData}
          previousQuestions={validationData.previousQuestions}
          agentInteractions={validationData.agentInteractions}
        />
      )}
    </div>
  );
}

