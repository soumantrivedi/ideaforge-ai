import { useState, useEffect } from 'react';
import { MessageSquare, Settings, Database } from 'lucide-react';
import { EnhancedChatInterface } from './components/EnhancedChatInterface';
import { AgentStatusPanel } from './components/AgentStatusPanel';
import { ProviderConfig } from './components/ProviderConfig';
import { KnowledgeBaseManager } from './components/KnowledgeBaseManager';
import { AIProviderManager, type AIProvider } from './lib/ai-providers';
import { RAGSystem, type Document } from './lib/rag-system';
import { CollaborativeOrchestrator, type MultiAgentMessage, type CoordinationMode } from './agents/multi-agent-system';
import { type AgentRole } from './agents/chatbot-agents';
import { v4 as uuidv4 } from 'uuid';

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
  const [conversationId] = useState(uuidv4());
  const [configuredProviders, setConfiguredProviders] = useState<AIProvider[]>([]);

  useEffect(() => {
    const savedConfig = {
      openaiKey: localStorage.getItem('openai_api_key') || undefined,
      claudeKey: localStorage.getItem('claude_api_key') || undefined,
      geminiKey: localStorage.getItem('gemini_api_key') || undefined,
    };

    if (savedConfig.openaiKey || savedConfig.claudeKey || savedConfig.geminiKey) {
      initializeSystem(savedConfig);
    }
  }, []);

  useEffect(() => {
    if (ragSystem) {
      loadDocuments();
    }
  }, [ragSystem]);

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
      const responses = await orchestrator.processMessage(content, messages);

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
      await ragSystem.addDocument(title, content);
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
      const results = await ragSystem.searchSimilar(query, 10);
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
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-50">
      <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-50 backdrop-blur-lg bg-opacity-90">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-gradient-to-br from-blue-500 via-purple-600 to-pink-500 rounded-xl shadow-lg">
                <MessageSquare className="w-7 h-7 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">IdeaForge AI</h1>
                <p className="text-sm text-gray-600 font-medium">Multi-Agent Collaboration System</p>
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
                Knowledge Base
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
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {view === 'settings' && (
          <div className="max-w-2xl mx-auto">
            <ProviderConfig
              onSaveConfig={handleSaveConfig}
              configuredProviders={configuredProviders}
            />
          </div>
        )}

        {view === 'chat' && orchestrator && (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            <div className="lg:col-span-1">
              <AgentStatusPanel
                agents={agentStatuses}
                onAgentSelect={setSelectedAgent}
                selectedAgent={selectedAgent}
              />
            </div>
            <div className="lg:col-span-3 h-[calc(100vh-200px)]">
              <EnhancedChatInterface
                messages={messages}
                onSendMessage={handleSendMessage}
                isLoading={isLoading}
                coordinationMode={coordinationMode}
                onCoordinationModeChange={handleCoordinationModeChange}
                activeAgents={agentStatuses.filter(a => a.isActive).map(a => a.name)}
              />
            </div>
          </div>
        )}

        {view === 'knowledge' && ragSystem && (
          <div className="max-w-4xl mx-auto">
            <KnowledgeBaseManager
              documents={documents}
              onAddDocument={handleAddDocument}
              onDeleteDocument={handleDeleteDocument}
              onSearch={handleSearchDocuments}
            />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
