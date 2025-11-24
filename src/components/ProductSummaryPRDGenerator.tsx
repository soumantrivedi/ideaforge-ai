import { useState, useEffect } from 'react';
import { FileText, BarChart3, Sparkles, CheckCircle2, Loader2 } from 'lucide-react';
import { SessionSelector } from './SessionSelector';
import { useAuth } from '../contexts/AuthContext';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface ProductSummaryPRDGeneratorProps {
  productId: string;
  onSummaryGenerated?: (summaryId: string) => void;
  onPRDGenerated?: (prdId: string) => void;
  onScoreGenerated?: (scoreId: string) => void;
  canEdit?: boolean; // Permission check
}

export function ProductSummaryPRDGenerator({
  productId,
  onSummaryGenerated,
  onPRDGenerated,
  onScoreGenerated,
  canEdit: initialCanEdit = false,
}: ProductSummaryPRDGeneratorProps) {
  const { token } = useAuth();
  const [selectedSessions, setSelectedSessions] = useState<string[]>([]);
  const [step, setStep] = useState<'select' | 'summary' | 'score' | 'prd' | 'complete'>('select');
  const [loading, setLoading] = useState(false);
  const [summaryId, setSummaryId] = useState<string | null>(null);
  const [scoreId, setScoreId] = useState<string | null>(null);
  const [prdId, setPrdId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [canEdit, setCanEdit] = useState(initialCanEdit);
  const [checkingPermission, setCheckingPermission] = useState(true);

  // Check permission on mount
  useEffect(() => {
    checkPermission();
  }, [productId, token]);

  const checkPermission = async () => {
    if (!token || !productId) {
      setCanEdit(false);
      setCheckingPermission(false);
      return;
    }

    try {
      // Get product details which includes access_level
      const response = await fetch(`${API_URL}/api/products`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        const product = data.products?.find((p: any) => p.id === productId);
        if (product) {
          // Check if user has edit or admin access
          const hasEditAccess = ['owner', 'admin', 'edit'].includes(product.access_level);
          setCanEdit(hasEditAccess);
        }
      }
    } catch (error) {
      console.error('Error checking permission:', error);
      setCanEdit(false);
    } finally {
      setCheckingPermission(false);
    }
  };

  const handleGenerateSummary = async () => {
    if (selectedSessions.length === 0) {
      setError('Please select at least one session');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_URL}/api/products/${productId}/summarize`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          session_ids: selectedSessions,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to generate summary');
      }

      const data = await response.json();
      setSummaryId(data.summary_id);
      setStep('summary');
      onSummaryGenerated?.(data.summary_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate summary');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateScore = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_URL}/api/products/${productId}/score`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          summary_id: summaryId,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to generate score');
      }

      const data = await response.json();
      setScoreId(data.score_id);
      setStep('score');
      onScoreGenerated?.(data.score_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate score');
    } finally {
      setLoading(false);
    }
  };

  const handleGeneratePRD = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_URL}/api/products/${productId}/generate-prd`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          summary_id: summaryId,
          score_id: scoreId,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to generate PRD');
      }

      const data = await response.json();
      setPrdId(data.prd_id);
      setStep('complete');
      onPRDGenerated?.(data.prd_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate PRD');
    } finally {
      setLoading(false);
    }
  };

  const handleCompleteWorkflow = async () => {
    // Generate summary -> score -> PRD in sequence
    await handleGenerateSummary();
    if (summaryId) {
      await handleGenerateScore();
      if (scoreId) {
        await handleGeneratePRD();
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Step Indicator */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
            step === 'select' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600'
          }`}>
            1
          </div>
          <div className="h-1 w-12 bg-gray-200" />
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
            step === 'summary' ? 'bg-blue-600 text-white' : step === 'select' ? 'bg-gray-200 text-gray-600' : 'bg-green-500 text-white'
          }`}>
            {step !== 'select' ? <CheckCircle2 className="w-5 h-5" /> : '2'}
          </div>
          <div className="h-1 w-12 bg-gray-200" />
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
            step === 'score' ? 'bg-blue-600 text-white' : ['summary', 'prd', 'complete'].includes(step) ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-600'
          }`}>
            {['summary', 'prd', 'complete'].includes(step) ? <CheckCircle2 className="w-5 h-5" /> : '3'}
          </div>
          <div className="h-1 w-12 bg-gray-200" />
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
            step === 'prd' ? 'bg-blue-600 text-white' : step === 'complete' ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-600'
          }`}>
            {step === 'complete' ? <CheckCircle2 className="w-5 h-5" /> : '4'}
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* Step 1: Select Sessions */}
      {step === 'select' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">Step 1: Select Conversation Sessions</h3>
            <button
              onClick={handleCompleteWorkflow}
              disabled={selectedSessions.length === 0 || loading}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  Generate All (Summary → Score → PRD)
                </>
              )}
            </button>
          </div>

          <SessionSelector
            productId={productId}
            selectedSessions={selectedSessions}
            onSelectionChange={setSelectedSessions}
            token={token}
            multiSelect={true}
          />

          <div className="flex justify-end">
            <button
              onClick={handleGenerateSummary}
              disabled={selectedSessions.length === 0 || loading}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Generate Summary
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Summary Generated */}
      {step === 'summary' && (
        <div className="space-y-4">
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 className="w-5 h-5 text-green-600" />
              <h3 className="font-semibold text-green-900">Summary Generated Successfully</h3>
            </div>
            <p className="text-sm text-green-700">Summary ID: {summaryId}</p>
          </div>

          <div className="flex justify-end gap-2">
            <button
              onClick={() => setStep('select')}
              className="px-4 py-2 bg-gray-200 text-gray-700 text-sm rounded-lg hover:bg-gray-300 transition font-medium"
            >
              Back
            </button>
            <button
              onClick={handleGenerateScore}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Scoring...
                </>
              ) : (
                <>
                  <BarChart3 className="w-4 h-4" />
                  Generate Score
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Score Generated */}
      {step === 'score' && (
        <div className="space-y-4">
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 className="w-5 h-5 text-green-600" />
              <h3 className="font-semibold text-green-900">Score Generated Successfully</h3>
            </div>
            <p className="text-sm text-green-700">Score ID: {scoreId}</p>
          </div>

          <div className="flex justify-end gap-2">
            <button
              onClick={() => setStep('summary')}
              className="px-4 py-2 bg-gray-200 text-gray-700 text-sm rounded-lg hover:bg-gray-300 transition font-medium"
            >
              Back
            </button>
            <button
              onClick={handleGeneratePRD}
              disabled={loading || !canEdit}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Generating PRD...
                </>
              ) : (
                <>
                  <FileText className="w-4 h-4" />
                  Generate PRD
                </>
              )}
            </button>
          </div>

          {!canEdit && (
            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <p className="text-sm text-yellow-800">
                You need edit or admin permissions to generate PRD documents.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Step 4: PRD Generated */}
      {step === 'complete' && (
        <div className="space-y-4">
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 className="w-5 h-5 text-green-600" />
              <h3 className="font-semibold text-green-900">PRD Generated Successfully</h3>
            </div>
            <p className="text-sm text-green-700 mb-2">PRD ID: {prdId}</p>
            <p className="text-sm text-green-700">
              The PRD follows industry standards (BCS, ICAgile, AIPMM, Pragmatic Institute)
            </p>
          </div>

          {canEdit && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-800 mb-2">
                <strong>Next Steps:</strong> You can now refine the product using the product lifecycle agents.
              </p>
              <button
                onClick={() => {
                  // Navigate to product lifecycle view
                  window.location.href = `#/chat?productId=${productId}`;
                }}
                className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition font-medium"
              >
                Open Product Lifecycle
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

