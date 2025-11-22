import { useState, useEffect } from 'react';
import { MessageSquare, Settings, Database, FileText, Download } from 'lucide-react';
import { EnhancedChatInterface } from './components/EnhancedChatInterface';
import { AgentStatusPanel } from './components/AgentStatusPanel';
import { ProductLifecycleSidebar } from './components/ProductLifecycleSidebar';
import { PhaseFormModal } from './components/PhaseFormModal';
import { ProviderConfig } from './components/ProviderConfig';
import { KnowledgeBaseManager } from './components/KnowledgeBaseManager';
import { AIProviderManager, type AIProvider } from './lib/ai-providers';
import { RAGSystem, type Document } from './lib/rag-system';
import { CollaborativeOrchestrator, type MultiAgentMessage, type CoordinationMode } from './agents/multi-agent-system';
import { type AgentRole } from './agents/chatbot-agents';
import { lifecycleService, type LifecyclePhase, type PhaseSubmission } from './lib/product-lifecycle-service';
import { ContentFormatter } from './lib/content-formatter';
import { v4 as uuidv4 } from 'uuid';
import { supabase } from './lib/supabase';

type View = 'chat' | 'settings' | 'knowledge';

function App() {
  const [view, setView] = useState<View>('settings');
  const [aiManager, setAiManager] = useState<AIProviderManager | null>(null);
  const [ragSystem, setRagSystem] = useState<RAGSystem | null>(null);
  const [orchestrator, setOrchestrator] = useState<CollaborativeOrchestrator | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<AgentRole>('general');
  const [messages, setMessages] = useState<MultiAgentMessage[]>([]);
  const [coordinationMode, setCoordinationMode] = useState<CoordinationMode>('collaborative');
  const [agentStatuses, setAgentStatuses] = useState<Array<{role: AgentRole; name: string; isActive: boolean; confidence?: number}>>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [sessionId] = useState(uuidv4());
  const [productId, setProductId] = useState<string>('');
  const [configuredProviders, setConfiguredProviders] = useState<AIProvider[]>([]);

  // Lifecycle states
  const [phases, setPhases] = useState<LifecyclePhase[]>([]);
  const [submissions, setSubmissions] = useState<PhaseSubmission[]>([]);
  const [currentPhase, setCurrentPhase] = useState<LifecyclePhase | null>(null);
  const [isFormModalOpen, setIsFormModalOpen] = useState(false);

  useEffect(() => {
    const savedConfig = {
      openaiKey: localStorage.getItem('openai_api_key') || undefined,
      claudeKey: localStorage.getItem('claude_api_key') || undefined,
      geminiKey: localStorage.getItem('gemini_api_key') || undefined,
    };

    if (savedConfig.openaiKey || savedConfig.claudeKey || savedConfig.geminiKey) {
      initializeSystem(savedConfig);
    }

    loadPhases();
  }, []);

  useEffect(() => {
    if (ragSystem) {
      loadDocuments();
    }
  }, [ragSystem]);

  useEffect(() => {
    if (productId) {
      loadSubmissions();
    }
  }, [productId]);

  const initializeSystem = (config: {
    openaiKey?: string;
    claudeKey?: string;
    geminiKey?: string;
  }) => {
    const manager = new AIProviderManager(config);
    setAiManager(manager);
    setConfiguredProviders(manager.getConfiguredProviders());

    if (config.openaiKey) {
      const rag = new RAGSystem(config.openaiKey);
      setRagSystem(rag);

      const orch = new CollaborativeOrchestrator(manager, rag, coordinationMode);
      setOrchestrator(orch);
      updateAgentStatuses(orch);
    } else if (manager.getConfiguredProviders().length > 0) {
      const orch = new CollaborativeOrchestrator(manager, undefined, coordinationMode);
      setOrchestrator(orch);
      updateAgentStatuses(orch);
    }

    setView('chat');
  };

  const loadPhases = async () => {
    try {
      const loadedPhases = await lifecycleService.getAllPhases();
      setPhases(loadedPhases);
    } catch (error) {
      console.error('Error loading phases:', error);
    }
  };

  const loadSubmissions = async () => {
    if (!productId) return;
    try {
      const loadedSubmissions = await lifecycleService.getPhaseSubmissions(productId);
      setSubmissions(loadedSubmissions);
    } catch (error) {
      console.error('Error loading submissions:', error);
    }
  };

  const handleSaveConfig = (config: {
    openaiKey?: string;
    claudeKey?: string;
    geminiKey?: string;
  }) => {
    if (config.openaiKey) localStorage.setItem('openai_api_key', config.openaiKey);
    if (config.claudeKey) localStorage.setItem('claude_api_key', config.claudeKey);
    if (config.geminiKey) localStorage.setItem('gemini_api_key', config.geminiKey);

    initializeSystem(config);
  };

  const updateAgentStatuses = (orch: CollaborativeOrchestrator) => {
    const agents = orch.getAllAgents();
    setAgentStatuses(
      agents.map((agent) => ({
        role: agent.config.role,
        name: agent.config.name,
        isActive: true,
        confidence: 0.8,
      }))
    );
  };

  const handlePhaseSelect = (phase: LifecyclePhase) => {
    setCurrentPhase(phase);

    // Create product if it doesn't exist
    if (!productId) {
      const newProductId = uuidv4();
      setProductId(newProductId);
      createProduct(newProductId);
    }

    setIsFormModalOpen(true);
  };

  const createProduct = async (id: string) => {
    try {
      await supabase.from('products').insert({
        id,
        user_id: 'anonymous-user',
        name: `Product ${id.substring(0, 8)}`,
        description: 'Product created via lifecycle wizard',
      });
    } catch (error) {
      console.error('Error creating product:', error);
    }
  };

  const handleFormSubmit = async (formData: Record<string, string>) => {
    if (!currentPhase || !productId || !orchestrator) return;

    try {
      setIsLoading(true);

      // Save or update submission
      const existingSubmission = await lifecycleService.getPhaseSubmission(productId, currentPhase.id);

      let submission: PhaseSubmission;
      if (existingSubmission) {
        submission = await lifecycleService.updatePhaseSubmission(existingSubmission.id, {
          form_data: formData,
          status: 'in_progress',
        });
      } else {
        submission = await lifecycleService.createPhaseSubmission(
          productId,
          currentPhase.id,
          'anonymous-user',
          formData
        );
      }

      // Build comprehensive prompt for agents
      const promptParts = [
        `I'm working on the "${currentPhase.phase_name}" phase of my product lifecycle.`,
        `Here is the information I've provided:`,
        '',
      ];

      Object.entries(formData).forEach(([key, value]) => {
        const fieldName = key.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
        promptParts.push(`**${fieldName}:**`);
        promptParts.push(value);
        promptParts.push('');
      });

      promptParts.push(`Please help me create a comprehensive ${currentPhase.phase_name} document based on this information. Include detailed sections, actionable insights, and professional formatting.`);

      const prompt = promptParts.join('\n');

      // Save conversation to history
      await lifecycleService.saveConversationMessage(sessionId, 'user', prompt, {
        productId,
        phaseId: currentPhase.id,
        metadata: { formData, phaseName: currentPhase.phase_name },
      });

      // Send to multi-agent system
      const userMessage: MultiAgentMessage = {
        role: 'user',
        content: prompt,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMessage]);

      // Process with agents
      const responses = await orchestrator.processMessage(prompt, messages);

      // Combine all agent responses
      const combinedContent = responses
        .filter(r => !r.isInternal)
        .map(r => r.content)
        .join('\n\n');

      // Format the content
      const formattedHtml = ContentFormatter.markdownToHtml(combinedContent);

      // Update submission with generated content
      await lifecycleService.updatePhaseContent(submission.id, combinedContent, 'completed');

      // Save to conversation history
      for (const response of responses.filter(r => !r.isInternal)) {
        await lifecycleService.saveConversationMessage(sessionId, 'agent', response.content, {
          productId,
          phaseId: currentPhase.id,
          agentName: response.agentName,
          agentRole: response.agentType,
          formattedContent: formattedHtml,
        });
      }

      // Update messages
      setMessages((prev) => [...prev, ...responses]);

      // Reload submissions
      await loadSubmissions();

      // Update agent statuses
      const { agent, allAgents } = await orchestrator.routeMessage(prompt, messages);
      if (allAgents) {
        setAgentStatuses(
          allAgents.map((a) => ({
            role: a.config.role,
            name: a.config.name,
            isActive: true,
            confidence: a.getConfidence(prompt),
            interactions: a.getInteractions().length,
          }))
        );
      }

    } catch (error) {
      console.error('Error processing phase:', error);
      const errorMessage: MultiAgentMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your phase information. Please try again.',
        agentName: 'System',
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = async (content: string) => {
    if (!orchestrator || !aiManager) return;

    const userMessage: MultiAgentMessage = {
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // Save to history
      await lifecycleService.saveConversationMessage(sessionId, 'user', content, {
        productId: productId || undefined,
        phaseId: currentPhase?.id,
      });

      const responses = await orchestrator.processMessage(content, messages);

      // Save responses to history
      for (const response of responses.filter(r => !r.isInternal)) {
        const formattedHtml = ContentFormatter.markdownToHtml(response.content);
        await lifecycleService.saveConversationMessage(sessionId, 'agent', response.content, {
          productId: productId || undefined,
          phaseId: currentPhase?.id,
          agentName: response.agentName,
          agentRole: response.agentType,
          formattedContent: formattedHtml,
        });
      }

      setMessages((prev) => [...prev, ...responses]);

      if (responses.length > 0 && responses[responses.length - 1].agentType) {
        setSelectedAgent(responses[responses.length - 1].agentType!);
      }

      const { agent, allAgents } = await orchestrator.routeMessage(content, messages);
      if (allAgents) {
        setAgentStatuses(
          allAgents.map((a) => ({
            role: a.config.role,
            name: a.config.name,
            isActive: true,
            confidence: a.getConfidence(content),
            interactions: a.getInteractions().length,
          }))
        );
      }
    } catch (error) {
      console.error('Error generating response:', error);
      const errorMessage: MultiAgentMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        agentName: 'System',
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCoordinationModeChange = (mode: CoordinationMode) => {
    setCoordinationMode(mode);
    if (orchestrator) {
      orchestrator.setCoordinationMode(mode);
    }
  };

  const handleExportPDF = async () => {
    if (!productId) return;

    try {
      const history = await lifecycleService.getProductConversationHistory(productId);
      const content = history
        .filter(h => h.message_type === 'agent')
        .map(h => h.content)
        .join('\n\n---\n\n');

      const html = ContentFormatter.toPdfHtml(content, 'Product Lifecycle Document');

      // Create exported document record
      await lifecycleService.createExportedDocument(
        productId,
        'anonymous-user',
        'full_lifecycle',
        'Full Product Lifecycle',
        content,
        { formattedHtml: html }
      );

      // Create download
      const blob = new Blob([html], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `product-lifecycle-${productId.substring(0, 8)}.html`;
      a.click();
      URL.revokeObjectURL(url);

      alert('Document exported successfully! You can open the HTML file in your browser and print to PDF.');
    } catch (error) {
      console.error('Error exporting PDF:', error);
      alert('Failed to export document.');
    }
  };

  const loadDocuments = async () => {
    if (!ragSystem) return;
    try {
      const docs = await ragSystem.getAllDocuments();
      setDocuments(docs);
    } catch (error) {
      console.error('Error loading documents:', error);
    }
  };

  const handleAddDocument = async (title: string, content: string) => {
    if (!ragSystem) return;
    try {
      await ragSystem.addDocument(title, content, productId);
      await loadDocuments();
    } catch (error) {
      console.error('Error adding document:', error);
    }
  };

  const handleDeleteDocument = async (id: string) => {
    if (!ragSystem) return;
    try {
      await ragSystem.deleteDocument(id);
      await loadDocuments();
    } catch (error) {
      console.error('Error deleting document:', error);
    }
  };

  const handleSearchDocuments = async (query: string) => {
    if (!ragSystem) return [];
    try {
      const results = await ragSystem.searchSimilar(query, 10, productId);
      return results.map((r) => r.document);
    } catch (error) {
      console.error('Error searching documents:', error);
      return [];
    }
  };

  if (!aiManager && view !== 'settings') {
    setView('settings');
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-50 flex flex-col">
      <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-50 backdrop-blur-lg bg-opacity-90">
        <div className="max-w-full mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-gradient-to-br from-blue-500 via-purple-600 to-pink-500 rounded-xl shadow-lg">
                <MessageSquare className="w-7 h-7 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
                  IdeaForge AI
                </h1>
                <p className="text-sm text-gray-600 font-medium">Product Lifecycle Management</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setView('chat')}
                disabled={!orchestrator}
                className={`px-4 py-2 rounded-lg font-medium transition ${
                  view === 'chat'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                <MessageSquare className="w-4 h-4 inline mr-2" />
                Chat
              </button>
              <button
                onClick={() => setView('knowledge')}
                disabled={!ragSystem}
                className={`px-4 py-2 rounded-lg font-medium transition ${
                  view === 'knowledge'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                <Database className="w-4 h-4 inline mr-2" />
                Knowledge
              </button>
              <button
                onClick={() => setView('settings')}
                className={`px-4 py-2 rounded-lg font-medium transition ${
                  view === 'settings'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <Settings className="w-4 h-4 inline mr-2" />
                Settings
              </button>
              {productId && view === 'chat' && (
                <button
                  onClick={handleExportPDF}
                  className="px-4 py-2 rounded-lg font-medium bg-gradient-to-r from-green-600 to-emerald-600 text-white hover:from-green-700 hover:to-emerald-700 transition shadow-lg"
                >
                  <Download className="w-4 h-4 inline mr-2" />
                  Export
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 flex overflow-hidden">
        {view === 'settings' && (
          <div className="flex-1 flex items-center justify-center p-8">
            <div className="max-w-2xl w-full">
              <ProviderConfig
                onSaveConfig={handleSaveConfig}
                configuredProviders={configuredProviders}
              />
            </div>
          </div>
        )}

        {view === 'chat' && orchestrator && (
          <>
            <div className="w-80 flex-shrink-0">
              <ProductLifecycleSidebar
                phases={phases}
                submissions={submissions}
                currentPhaseId={currentPhase?.id}
                onPhaseSelect={handlePhaseSelect}
                productId={productId}
              />
            </div>

            <div className="flex-1 p-6">
              <EnhancedChatInterface
                messages={messages}
                onSendMessage={handleSendMessage}
                isLoading={isLoading}
                coordinationMode={coordinationMode}
                onCoordinationModeChange={handleCoordinationModeChange}
                activeAgents={agentStatuses.filter(a => a.isActive).map(a => a.name)}
              />
            </div>

            <div className="w-80 flex-shrink-0">
              <AgentStatusPanel
                agents={agentStatuses}
                onAgentSelect={setSelectedAgent}
                selectedAgent={selectedAgent}
              />
            </div>
          </>
        )}

        {view === 'knowledge' && ragSystem && (
          <div className="flex-1 p-8">
            <div className="max-w-4xl mx-auto">
              <KnowledgeBaseManager
                documents={documents}
                onAddDocument={handleAddDocument}
                onDeleteDocument={handleDeleteDocument}
                onSearch={handleSearchDocuments}
              />
            </div>
          </div>
        )}
      </main>

      {currentPhase && (
        <PhaseFormModal
          phase={currentPhase}
          isOpen={isFormModalOpen}
          onClose={() => setIsFormModalOpen(false)}
          onSubmit={handleFormSubmit}
          existingData={submissions.find(s => s.phase_id === currentPhase.id)?.form_data}
        />
      )}
    </div>
  );
}

export default App;
