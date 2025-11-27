import { useState, useEffect } from 'react';
import { CheckCircle2, Circle, Lock, ChevronRight, Star, Lightbulb, Search, FileText, Palette, Settings, Rocket } from 'lucide-react';
import type { LifecyclePhase, PhaseSubmission } from '../lib/product-lifecycle-service';

interface ProductLifecycleSidebarProps {
  phases: LifecyclePhase[];
  submissions: PhaseSubmission[];
  currentPhaseId?: string;
  onPhaseSelect: (phase: LifecyclePhase) => void;
  productId?: string;
}

export function ProductLifecycleSidebar({
  phases = [],
  submissions = [],
  currentPhaseId,
  onPhaseSelect,
  productId,
}: ProductLifecycleSidebarProps) {
  const [currentPhase, setCurrentPhase] = useState<string | null>(currentPhaseId || null);
  const [completedPhases, setCompletedPhases] = useState<Set<string>>(new Set());
  const [inProgressPhases, setInProgressPhases] = useState<Set<string>>(new Set());

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
        {!Array.isArray(phases) || phases.length === 0 ? (
          <div className="text-center py-8" style={{ color: 'var(--text-secondary)' }}>
            <p className="text-sm">No lifecycle phases available. Please select a product first.</p>
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
                    const score = submission?.metadata?.validation_score;
                    
                    return (
                      <>
                        {status === 'completed' && !isActive && (
                          <div className="mt-2 flex items-center gap-2">
                            <span className="text-xs text-green-600 font-medium">
                              ✓ Completed
                            </span>
                            {score !== undefined && (
                              <div className="flex items-center gap-1 px-2 py-0.5 bg-yellow-50 rounded-full">
                                <Star className={`w-3 h-3 ${score >= 4 ? 'text-yellow-500 fill-yellow-500' : score >= 3 ? 'text-yellow-400 fill-yellow-400' : 'text-yellow-300 fill-yellow-300'}`} />
                                <span className="text-xs font-semibold text-yellow-700">{score}/5</span>
                              </div>
                            )}
                          </div>
                        )}
                        {status === 'in_progress' && !isActive && (
                          <div className="mt-2 text-xs text-blue-600 font-medium">
                            ⚡ In Progress
                          </div>
                        )}
                        {isActive && score !== undefined && (
                          <div className="mt-2 flex items-center gap-1">
                            <Star className="w-3 h-3 text-yellow-300 fill-yellow-300" />
                            <span className="text-xs font-semibold text-white">Score: {score}/5</span>
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

      {productId && (
        <div className="p-4 border-t border-gray-200 bg-gradient-to-r from-blue-50 to-purple-50">
          <div className="text-xs text-gray-600 mb-2">Current Product</div>
          <div className="text-sm font-semibold text-gray-900 truncate">
            {productId.substring(0, 8)}...
          </div>
        </div>
      )}
    </div>
  );
}
