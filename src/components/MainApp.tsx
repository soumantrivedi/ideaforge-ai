import { useState, useEffect } from 'react';
import { MessageSquare, Settings, Database, FileText, Download, LayoutDashboard, Folder, History, User, LogOut, ChevronLeft, ChevronRight } from 'lucide-react';
import { ProductChatInterface } from './ProductChatInterface';
import { AgentStatusPanel } from './AgentStatusPanel';
import { ProductLifecycleSidebar } from './ProductLifecycleSidebar';
import { PhaseFormModal } from './PhaseFormModal';
import { EnhancedSettings } from './EnhancedSettings';
import { KnowledgeBaseManagerWrapper } from './KnowledgeBaseManagerWrapper';
import { ProductsDashboard } from './ProductsDashboard';
import { PortfolioView } from './PortfolioView';
import { ConversationHistory } from './ConversationHistory';
import { UserProfile } from './UserProfile';
import { useAuth } from '../contexts/AuthContext';
import { lifecycleService, type LifecyclePhase, type PhaseSubmission } from '../lib/product-lifecycle-service';

type View = 'dashboard' | 'chat' | 'settings' | 'knowledge' | 'portfolio' | 'history' | 'profile';

export function MainApp() {
  const { user, logout, token } = useAuth();
  const [view, setView] = useState<View>('dashboard');
  const [productId, setProductId] = useState<string>('');
  const [phases, setPhases] = useState<LifecyclePhase[]>([]);
  const [submissions, setSubmissions] = useState<PhaseSubmission[]>([]);
  const [currentPhase, setCurrentPhase] = useState<LifecyclePhase | null>(null);
  const [isFormModalOpen, setIsFormModalOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  useEffect(() => {
    if (token) {
      lifecycleService.setToken(token);
      loadPhases();
    }
  }, [token]);

  useEffect(() => {
    if (productId && token) {
      console.log('MainApp: Loading data for productId:', productId);
      lifecycleService.setToken(token);
      loadSubmissions();
      // Also reload phases when product changes to ensure fresh data
      loadPhases();
    } else {
      console.log('MainApp: Skipping data load', { productId, hasToken: !!token });
    }
  }, [productId, token]);

  const loadPhases = async () => {
    try {
      const loadedPhases = await lifecycleService.getAllPhases();
      setPhases(Array.isArray(loadedPhases) ? loadedPhases : []);
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

  const handleFormSubmit = async (formData: Record<string, string>) => {
    if (!productId || !currentPhase) return;
    
    try {
      await lifecycleService.submitPhaseData(productId, currentPhase.id, formData);
      await loadSubmissions();
      setIsFormModalOpen(false);
    } catch (error) {
      console.error('Error submitting form:', error);
      alert('Failed to submit form data');
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
            {(['portfolio', 'chat', 'history', 'profile', 'settings', 'knowledge'] as View[]).map((viewName) => {
              const icons = {
                portfolio: Folder,
                chat: MessageSquare,
                history: History,
                profile: User,
                settings: Settings,
                knowledge: Database,
              };
              const labels = {
                portfolio: 'Portfolio',
                chat: 'Chat',
                history: 'History',
                profile: 'Profile',
                settings: 'Settings',
                knowledge: 'Knowledge Base',
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
                  setProductId(id);
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
                  setProductId(id);
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
                              setProductId(id);
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
                              setProductId(id);
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
                  <AgentStatusPanel agents={[]} />
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
                        setProductId(id);
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
    </div>
  );
}

