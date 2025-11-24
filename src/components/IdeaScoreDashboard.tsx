import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Target, AlertCircle, CheckCircle2, XCircle, BarChart3, Lightbulb, AlertTriangle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface ScoreDimension {
  score: number;
  rationale: string;
  sub_scores?: Record<string, number>;
}

interface Recommendation {
  dimension: string;
  priority: 'high' | 'medium' | 'low';
  recommendation: string;
  expected_impact: string;
}

interface ProductScore {
  id: string;
  product_id: string;
  product_name: string;
  overall_score: number;
  success_probability: number;
  dimensions: Record<string, ScoreDimension>;
  recommendations: Recommendation[];
  success_factors: string[];
  risk_factors: string[];
  created_at: string;
  updated_at: string;
}

interface IdeaScoreDashboardProps {
  tenantId?: string;
  productId?: string;
  onProductSelect?: (productId: string) => void;
}

export function IdeaScoreDashboard({ tenantId, productId, onProductSelect }: IdeaScoreDashboardProps) {
  const [scores, setScores] = useState<ProductScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedScore, setSelectedScore] = useState<ProductScore | null>(null);
  const { token } = useAuth();

  useEffect(() => {
    if (token) {
      loadScores();
    }
  }, [token, tenantId, productId]);

  const loadScores = async () => {
    try {
      setLoading(true);
      let url = '';
      if (productId) {
        url = `${API_URL}/api/products/${productId}/scores`;
      } else if (tenantId) {
        url = `${API_URL}/api/products/tenant/${tenantId}/scores`;
      } else {
        return;
      }

      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) throw new Error('Failed to load scores');

      const data = await response.json();
      setScores(data.scores || []);
      if (data.scores && data.scores.length > 0) {
        setSelectedScore(data.scores[0]); // Select most recent
      }
    } catch (error) {
      console.error('Error loading scores:', error);
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getScoreBgColor = (score: number) => {
    if (score >= 80) return 'bg-green-100';
    if (score >= 60) return 'bg-yellow-100';
    return 'bg-red-100';
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'text-red-600 bg-red-50 border-red-200';
      case 'medium': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'low': return 'text-blue-600 bg-blue-50 border-blue-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-gray-500">Loading scores...</div>
      </div>
    );
  }

  if (scores.length === 0) {
    return (
      <div className="p-8 text-center">
        <BarChart3 className="w-12 h-12 mx-auto text-gray-400 mb-4" />
        <p className="text-gray-500">No scores available yet. Generate a score for a product to see it here.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Score List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {scores.map((score) => (
          <div
            key={score.id}
            onClick={() => setSelectedScore(score)}
            className={`p-4 rounded-lg border-2 cursor-pointer transition ${
              selectedScore?.id === score.id
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 bg-white hover:border-gray-300'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-gray-900 truncate">{score.product_name}</h3>
              {onProductSelect && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onProductSelect(score.product_id);
                  }}
                  className="text-xs text-blue-600 hover:text-blue-700"
                >
                  View
                </button>
              )}
            </div>
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <div className="text-sm text-gray-600 mb-1">Overall Score</div>
                <div className={`text-2xl font-bold ${getScoreColor(score.overall_score)}`}>
                  {score.overall_score.toFixed(1)}
                </div>
              </div>
              <div className="flex-1">
                <div className="text-sm text-gray-600 mb-1">Success Probability</div>
                <div className={`text-2xl font-bold ${getScoreColor(score.success_probability)}`}>
                  {score.success_probability.toFixed(1)}%
                </div>
              </div>
            </div>
            <div className="mt-2 text-xs text-gray-500">
              {new Date(score.created_at).toLocaleDateString()}
            </div>
          </div>
        ))}
      </div>

      {/* Detailed Score View */}
      {selectedScore && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold text-gray-900">{selectedScore.product_name}</h2>
            <div className="flex items-center gap-4">
              <div className="text-center">
                <div className="text-sm text-gray-600">Overall Score</div>
                <div className={`text-3xl font-bold ${getScoreColor(selectedScore.overall_score)}`}>
                  {selectedScore.overall_score.toFixed(1)}
                </div>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-600">Success</div>
                <div className={`text-3xl font-bold ${getScoreColor(selectedScore.success_probability)}`}>
                  {selectedScore.success_probability.toFixed(0)}%
                </div>
              </div>
            </div>
          </div>

          {/* Score Dimensions */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <BarChart3 className="w-5 h-5" />
              Scoring Dimensions
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(selectedScore.dimensions || {}).map(([dimension, data]) => (
                <div key={dimension} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-semibold text-gray-900 capitalize">
                      {dimension.replace(/_/g, ' ')}
                    </h4>
                    <div className={`px-3 py-1 rounded-full text-sm font-semibold ${getScoreBgColor(data.score)} ${getScoreColor(data.score)}`}>
                      {data.score.toFixed(1)}
                    </div>
                  </div>
                  <p className="text-sm text-gray-600 mb-3">{data.rationale}</p>
                  {data.sub_scores && (
                    <div className="space-y-2">
                      {Object.entries(data.sub_scores).map(([sub, score]) => (
                        <div key={sub} className="flex items-center justify-between text-xs">
                          <span className="text-gray-600 capitalize">{sub.replace(/_/g, ' ')}</span>
                          <span className="font-medium">{score.toFixed(1)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Recommendations */}
          {selectedScore.recommendations && selectedScore.recommendations.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Lightbulb className="w-5 h-5" />
                Recommendations to Improve Score
              </h3>
              <div className="space-y-3">
                {selectedScore.recommendations.map((rec, idx) => (
                  <div
                    key={idx}
                    className={`border-2 rounded-lg p-4 ${getPriorityColor(rec.priority)}`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold capitalize">{rec.dimension.replace(/_/g, ' ')}</span>
                      <span className="text-xs font-medium px-2 py-1 rounded capitalize bg-white/50">
                        {rec.priority} Priority
                      </span>
                    </div>
                    <p className="text-sm mb-2">{rec.recommendation}</p>
                    {rec.expected_impact && (
                      <p className="text-xs opacity-75">Expected Impact: {rec.expected_impact}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Success Factors */}
          {selectedScore.success_factors && selectedScore.success_factors.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-green-600" />
                Success Factors
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {selectedScore.success_factors.map((factor, idx) => (
                  <div key={idx} className="flex items-start gap-2 p-3 bg-green-50 rounded-lg border border-green-200">
                    <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-gray-700">{factor}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Risk Factors */}
          {selectedScore.risk_factors && selectedScore.risk_factors.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-yellow-600" />
                Risk Factors
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {selectedScore.risk_factors.map((risk, idx) => (
                  <div key={idx} className="flex items-start gap-2 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                    <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-gray-700">{risk}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Scoring Criteria */}
          <div className="border-t pt-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Scoring Standards</h3>
            <div className="flex flex-wrap gap-2">
              {['BCS', 'ICAgile', 'AIPMM', 'Pragmatic Institute'].map((standard) => (
                <span
                  key={standard}
                  className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-medium"
                >
                  {standard}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

