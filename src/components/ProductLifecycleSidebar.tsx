import { useState, useEffect } from 'react';
import { CheckCircle2, Circle, Lock, ChevronRight, Star, Lightbulb, Search, FileText, Palette, Settings, Rocket } from 'lucide-react';
import type { LifecyclePhase, PhaseSubmission } from '../lib/product-lifecycle-service';
import { getValidatedApiUrl } from '../lib/runtime-config';
import { useAuth } from '../contexts/AuthContext';

const API_URL = getValidatedApiUrl();

interface ProductLifecycleSidebarProps {
  phases: LifecyclePhase[];
  submissions: PhaseSubmission[];
  currentPhaseId?: string;
  onPhaseSelect: (phase: LifecyclePhase) => void;
  productId?: string;
  phasesLoading?: boolean;
}

interface PhaseScore {
  phase_name: string;
  phase_id: string;
  score: number;
  status: 'complete' | 'incomplete' | 'missing';
}

export function ProductLifecycleSidebar({
  phases = [],
  submissions = [],
  currentPhaseId,
  onPhaseSelect,
  productId,
  phasesLoading = false,
}: ProductLifecycleSidebarProps) {
  const { token } = useAuth();
  const [currentPhase, setCurrentPhase] = useState<string | null>(currentPhaseId || null);
  const [completedPhases, setCompletedPhases] = useState<Set<string>>(new Set());
  const [inProgressPhases, setInProgressPhases] = useState<Set<string>>(new Set());
  const [phaseScores, setPhaseScores] = useState<Map<string, PhaseScore>>(new Map());

  useEffect(() => {
    const completed = new Set<string>();
    const inProgress = new Set<string>();

    if (Array.isArray(submissions)) {
      submissions.forEach((sub) => {
        if (sub.status === 'completed' || sub.status === 'reviewed') {
          completed.add(sub.phase_id);
        } else if (sub.status === 'in_progress') {
          inProgress.add(sub.phase_id);
        }
      });
    }

    setCompletedPhases(completed);
    setInProgressPhases(inProgress);
  }, [submissions]);

  // Load phase scores from progress report
  useEffect(() => {
    if (productId && token) {
      loadPhaseScores();
    }
  }, [productId, token]);

  const loadPhaseScores = async () => {
    if (!productId || !token) return;
    
    try {
      const response = await fetch(`${API_URL}/api/products/${productId}/progress-report`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        if (data.exists && data.phase_scores) {
          const scoresMap = new Map<string, PhaseScore>();
          data.phase_scores.forEach((score: PhaseScore) => {
            scoresMap.set(score.phase_id, score);
          });
          setPhaseScores(scoresMap);
        }
      }
    } catch (error) {
      console.error('Error loading phase scores:', error);
    }
  };

  const getPhaseStatus = (phase: LifecyclePhase, index: number) => {
    // All phases are now available - no sequential locking
    if (completedPhases.has(phase.id)) {
      return 'completed';
    }
    if (inProgressPhases.has(phase.id)) {
      return 'in_progress';
    }
    // All phases are available regardless of previous phase completion
    return 'available';
  };

  const getStatusIcon = (status: string, isActive: boolean) => {
    if (status === 'completed') {
      return <CheckCircle2 className={`w-5 h-5 ${isActive ? 'text-white' : 'text-green-500'}`} />;
    }
    if (status === 'in_progress') {
      return (
        <div className={`w-5 h-5 rounded-full border-2 ${isActive ? 'border-white' : 'border-blue-500'} flex items-center justify-center`}>
          <div className={`w-2 h-2 rounded-full ${isActive ? 'bg-white' : 'bg-blue-500'}`} />
        </div>
      );
    }
    if (status === 'locked') {
      return <Lock className={`w-5 h-5 ${isActive ? 'text-white' : 'text-gray-400'}`} />;
    }
    return <Circle className={`w-5 h-5 ${isActive ? 'text-white' : 'text-gray-400'}`} />;
  };

  const getPhaseIcon = (phaseName: string, isActive: boolean) => {
    const iconMap: Record<string, React.ReactNode> = {
      'Ideation': <Lightbulb className={`w-5 h-5 ${isActive ? 'text-white' : 'text-yellow-500'}`} />,
      'Market Research': <Search className={`w-5 h-5 ${isActive ? 'text-white' : 'text-blue-500'}`} />,
      'Requirements': <FileText className={`w-5 h-5 ${isActive ? 'text-white' : 'text-indigo-500'}`} />,
      'Design': <Palette className={`w-5 h-5 ${isActive ? 'text-white' : 'text-pink-500'}`} />,
      'Development Planning': <Settings className={`w-5 h-5 ${isActive ? 'text-white' : 'text-gray-500'}`} />,
      'Go-to-Market': <Rocket className={`w-5 h-5 ${isActive ? 'text-white' : 'text-green-500'}`} />,
    };
    return iconMap[phaseName] || <Circle className={`w-5 h-5 ${isActive ? 'text-white' : 'text-gray-400'}`} />;
  };

  const getStatusColor = (status: string, isActive: boolean) => {
    if (isActive) {
      return 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg';
    }
    if (status === 'completed') {
      return 'bg-green-50 text-green-900 border-green-200 hover:bg-green-100';
    }
    if (status === 'in_progress') {
      return 'bg-blue-50 text-blue-900 border-blue-200 hover:bg-blue-100';
    }
    if (status === 'locked') {
      return 'bg-gray-50 text-gray-400 border-gray-200 cursor-not-allowed';
    }
    return 'bg-white text-gray-900 border-gray-200 hover:bg-gray-50';
  };

  const progress = phases.length > 0
    ? (completedPhases.size / phases.length) * 100
    : 0;

  return (
    <div className="h-full max-h-[calc(100vh-8rem)] bg-white border-r border-gray-200 flex flex-col">
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-lg font-bold text-gray-900 mb-2">Product Lifecycle</h2>
        <p className="text-sm text-gray-600 mb-4">
          Access any phase to build your product. Phases are not locked - work in any order.
        </p>

        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Progress</span>
            <span className="font-semibold text-gray-900">
              {completedPhases.size} / {phases.length}
            </span>
          </div>
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-purple-600 transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {phasesLoading ? (
          <div className="text-center py-8" style={{ color: 'var(--text-secondary)' }}>
            <p className="text-sm">Loading phases...</p>
          </div>
        ) : !Array.isArray(phases) || phases.length === 0 ? (
          <div className="text-center py-8" style={{ color: 'var(--text-secondary)' }}>
            <p className="text-sm">
              {!productId 
                ? "No lifecycle phases available. Please select a product first."
                : "No lifecycle phases available."}
            </p>
          </div>
        ) : (
          phases.map((phase, index) => {
          const status = getPhaseStatus(phase, index);
          const isActive = phase.id === currentPhaseId;
          const isLocked = status === 'locked';

          return (
            <button
              key={phase.id}
              onClick={() => onPhaseSelect(phase)}
              className={`w-full p-4 rounded-xl border-2 transition text-left ${getStatusColor(
                status,
                isActive
              )}`}
            >
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-0.5">
                  {getStatusIcon(status, isActive)}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    {getPhaseIcon(phase.phase_name, isActive)}
                    <h3 className="font-semibold text-sm truncate">
                      {phase.phase_name}
                    </h3>
                  </div>
                  <p className={`text-xs leading-relaxed ${isActive ? 'text-white/90' : 'text-gray-600'}`}>
                    {phase.description}
                  </p>

                  {(() => {
                    const submission = submissions.find(s => s.phase_id === phase.id);
                    const reviewScore = phaseScores.get(phase.id);
                    const hasCompletedOnce = status === 'completed' || status === 'reviewed';
                    
                    return (
                      <>
                        {hasCompletedOnce && reviewScore && (
                          <div className="mt-3 space-y-2">
                            <div className="flex items-center justify-between">
                              <span className={`text-xs font-medium ${isActive ? 'text-white/90' : 'text-gray-700'}`}>
                                Quality Score
                              </span>
                              <span className={`text-xs font-bold ${
                                reviewScore.score >= 80 ? 'text-green-600' :
                                reviewScore.score >= 60 ? 'text-yellow-600' :
                                'text-orange-600'
                              }`}>
                                {reviewScore.score}%
                              </span>
                            </div>
                            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                              <div 
                                className={`h-full rounded-full transition-all ${
                                  reviewScore.score >= 80 ? 'bg-gradient-to-r from-green-500 to-emerald-500' :
                                  reviewScore.score >= 60 ? 'bg-gradient-to-r from-yellow-500 to-amber-500' :
                                  'bg-gradient-to-r from-orange-500 to-red-500'
                                }`}
                                style={{ width: `${reviewScore.score}%` }}
                              />
                            </div>
                          </div>
                        )}
                        {status === 'completed' && !isActive && !reviewScore && (
                          <div className="mt-2 text-xs text-green-600 font-medium">
                            ✓ Completed
                          </div>
                        )}
                        {status === 'in_progress' && !isActive && (
                          <div className="mt-2 text-xs text-blue-600 font-medium">
                            ⚡ In Progress
                          </div>
                        )}
                      </>
                    );
                  })()}
                </div>

                <ChevronRight className={`w-5 h-5 flex-shrink-0 ${isActive ? 'text-white' : 'text-gray-400'}`} />
              </div>
            </button>
          );
        })
        )}
      </div>

    </div>
  );
}
