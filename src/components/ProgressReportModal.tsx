import { X, TrendingUp, CheckCircle2, AlertCircle, Clock, ArrowRight, Star, Target, Award, Lightbulb, FileText } from 'lucide-react';

interface PhaseScore {
  phase_name: string;
  phase_id: string;
  score: number;
  status: 'complete' | 'incomplete' | 'missing';
}

interface MissingSection {
  section: string;
  phase_name?: string;
  phase_id?: string;
  importance: string;
  recommendation: string;
  score: number;
}

interface ProgressReport {
  id: string;
  overall_score: number;
  status: 'ready' | 'needs_attention' | 'in_progress';
  phase_scores: PhaseScore[];
  missing_sections: MissingSection[];
  recommendations: string[];
  summary: string;
  created_at?: string;
  updated_at?: string;
}

interface ProgressReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  report: ProgressReport;
  onNavigateToPhase?: (phaseId: string) => void;
}

export function ProgressReportModal({ isOpen, onClose, report, onNavigateToPhase }: ProgressReportModalProps) {
  if (!isOpen) return null;

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-orange-600';
  };

  const getScoreBgColor = (score: number) => {
    if (score >= 80) return 'bg-green-50 border-green-200';
    if (score >= 60) return 'bg-yellow-50 border-yellow-200';
    return 'bg-orange-50 border-orange-200';
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'complete':
        return <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-medium rounded-full">Complete</span>;
      case 'incomplete':
        return <span className="px-2 py-0.5 bg-yellow-100 text-yellow-700 text-xs font-medium rounded-full">In Progress</span>;
      case 'missing':
        return <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs font-medium rounded-full">Missing</span>;
      default:
        return null;
    }
  };

  const handlePhaseClick = (phaseId: string) => {
    if (onNavigateToPhase && phaseId) {
      onNavigateToPhase(phaseId);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-purple-600 via-pink-600 to-rose-600 p-6 text-white relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -mr-32 -mt-32"></div>
          <div className="absolute bottom-0 left-0 w-48 h-48 bg-white/10 rounded-full -ml-24 -mb-24"></div>
          
          <div className="relative z-10 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-white/20 backdrop-blur-sm rounded-xl">
                <TrendingUp className="w-6 h-6" />
              </div>
              <div>
                <h2 className="text-2xl font-bold">Progress Report</h2>
                <p className="text-purple-100 text-sm">Comprehensive quality assessment</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/20 rounded-lg transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Overall Score */}
          <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border border-purple-100">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-gradient-to-br from-purple-500 to-pink-600 rounded-xl">
                  <Award className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-gray-900">Overall Score</h3>
                  <p className="text-sm text-gray-600">Product completion & quality</p>
                </div>
              </div>
              <div className="text-right">
                <div className={`text-4xl font-bold ${getScoreColor(report.overall_score)}`}>
                  {report.overall_score}%
                </div>
                <div className="text-sm text-gray-600 mt-1">
                  {report.status === 'ready' && '🎉 Excellent!'}
                  {report.status === 'needs_attention' && '⚠️ Needs Improvement'}
                  {report.status === 'in_progress' && '🚀 In Progress'}
                </div>
              </div>
            </div>
            
            {/* Progress Bar */}
            <div className="relative h-4 bg-gray-200 rounded-full overflow-hidden">
              <div 
                className={`absolute inset-y-0 left-0 rounded-full transition-all duration-1000 ${
                  report.overall_score >= 80 ? 'bg-gradient-to-r from-green-500 to-emerald-500' :
                  report.overall_score >= 60 ? 'bg-gradient-to-r from-yellow-500 to-amber-500' :
                  'bg-gradient-to-r from-orange-500 to-red-500'
                }`}
                style={{ width: `${report.overall_score}%` }}
              >
                <div className="absolute inset-0 bg-white/30 animate-pulse"></div>
              </div>
            </div>
          </div>

          {/* Summary */}
          {report.summary && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
              <div className="flex items-start gap-3">
                <FileText className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold text-blue-900 mb-1">Summary</h4>
                  <p className="text-sm text-blue-800 leading-relaxed">{report.summary}</p>
                </div>
              </div>
            </div>
          )}

          {/* Phase Scores */}
          {report.phase_scores && report.phase_scores.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Target className="w-5 h-5 text-purple-600" />
                <h3 className="text-lg font-bold text-gray-900">Phase Scores</h3>
              </div>
              <div className="space-y-3">
                {report.phase_scores.map((phase, idx) => (
                  <div
                    key={idx}
                    className={`${getScoreBgColor(phase.score)} border-2 rounded-xl p-4 transition-all hover:shadow-md ${
                      onNavigateToPhase && phase.phase_id ? 'cursor-pointer hover:scale-[1.02]' : ''
                    }`}
                    onClick={() => phase.phase_id && handlePhaseClick(phase.phase_id)}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3 flex-1">
                        <div className="flex items-center gap-2 flex-1">
                          <span className="font-semibold text-gray-900">{phase.phase_name}</span>
                          {getStatusBadge(phase.status)}
                        </div>
                        {onNavigateToPhase && phase.phase_id && (
                          <ArrowRight className="w-4 h-4 text-purple-600 flex-shrink-0" />
                        )}
                      </div>
                      <div className={`text-2xl font-bold ${getScoreColor(phase.score)}`}>
                        {phase.score}%
                      </div>
                    </div>
                    
                    {/* Progress Bar */}
                    <div className="relative h-2.5 bg-white rounded-full overflow-hidden">
                      <div 
                        className={`absolute inset-y-0 left-0 rounded-full transition-all duration-1000 ${
                          phase.score >= 80 ? 'bg-gradient-to-r from-green-500 to-emerald-500' :
                          phase.score >= 60 ? 'bg-gradient-to-r from-yellow-500 to-amber-500' :
                          'bg-gradient-to-r from-orange-500 to-red-500'
                        }`}
                        style={{ width: `${phase.score}%` }}
                      />
                    </div>
                    
                    {onNavigateToPhase && phase.phase_id && (
                      <p className="text-xs text-purple-600 mt-2 flex items-center gap-1">
                        Click to improve this phase <ArrowRight className="w-3 h-3" />
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Missing Sections */}
          {report.missing_sections && report.missing_sections.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-4">
                <AlertCircle className="w-5 h-5 text-orange-600" />
                <h3 className="text-lg font-bold text-gray-900">Areas for Improvement</h3>
              </div>
              <div className="space-y-3">
                {report.missing_sections.map((section, idx) => (
                  <div
                    key={idx}
                    className="bg-orange-50 border border-orange-200 rounded-xl p-4"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <h4 className="font-semibold text-orange-900 mb-1">{section.section}</h4>
                        {section.phase_name && (
                          <p className="text-xs text-orange-700 mb-2">
                            Related to: {section.phase_name}
                          </p>
                        )}
                        <p className="text-sm text-orange-800 mb-2">{section.importance}</p>
                        <p className="text-sm font-medium text-orange-900">
                          💡 {section.recommendation}
                        </p>
                      </div>
                      {section.phase_id && onNavigateToPhase && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handlePhaseClick(section.phase_id!);
                          }}
                          className="ml-4 p-2 bg-orange-100 hover:bg-orange-200 rounded-lg transition-colors flex-shrink-0"
                          title="Go to phase"
                        >
                          <ArrowRight className="w-4 h-4 text-orange-700" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {report.recommendations && report.recommendations.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Lightbulb className="w-5 h-5 text-yellow-600" />
                <h3 className="text-lg font-bold text-gray-900">Recommendations</h3>
              </div>
              <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 space-y-2">
                {report.recommendations.map((rec, idx) => (
                  <div key={idx} className="flex items-start gap-2">
                    <Star className="w-4 h-4 text-yellow-600 mt-0.5 flex-shrink-0" />
                    <p className="text-sm text-yellow-900">{rec}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 p-4 bg-gray-50 flex items-center justify-between">
          <p className="text-xs text-gray-500">
            {report.updated_at && `Last updated: ${new Date(report.updated_at).toLocaleString()}`}
          </p>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

