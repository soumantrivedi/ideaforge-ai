import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, Download, FileText, AlertCircle, CheckCircle, Loader2, BookOpen, ExternalLink } from 'lucide-react';
import { getValidatedApiUrl } from '../lib/runtime-config';

interface ExportPRDModalProps {
  productId: string;
  isOpen: boolean;
  onClose: () => void;
  onExportComplete?: () => void;
  token: string | null;
  conversationHistory?: Array<{ role: string; content: string; timestamp?: string }>;
}

interface ReviewResult {
  status: 'ready' | 'needs_attention';
  score?: number; // Overall score as percentage
  missing_sections: Array<{
    section: string;
    phase_name?: string;
    phase_id?: string;
    importance: string;
    recommendation: string;
    score?: number; // Section-specific score
  }>;
  summary: string;
  phase_scores?: Array<{
    phase_name: string;
    phase_id: string;
    score: number;
    status: 'complete' | 'incomplete' | 'missing';
  }>;
}

export function ExportPRDModal({ productId, isOpen, onClose, onExportComplete, token, conversationHistory }: ExportPRDModalProps) {
  const [showChatExport, setShowChatExport] = useState(false);
  const [exportType, setExportType] = useState<'html' | 'pdf' | 'confluence'>('html');
  const [overrideMissing, setOverrideMissing] = useState(false);
  const [isReviewing, setIsReviewing] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [reviewResult, setReviewResult] = useState<ReviewResult | null>(null);
  const [confluenceSpaceKey, setConfluenceSpaceKey] = useState('');
  const [isPublishing, setIsPublishing] = useState(false);
  const [publishResult, setPublishResult] = useState<{ url?: string; page_id?: string; title?: string } | null>(null);

  const API_URL = getValidatedApiUrl();

  useEffect(() => {
    if (isOpen && productId) {
      // Auto-review when modal opens
      handleReview();
    }
  }, [isOpen, productId]);

  // Handle Escape key to close modal
  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isExporting && !isPublishing && !isReviewing) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    // Prevent body scroll when modal is open
    document.body.style.overflow = 'hidden';

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = '';
    };
  }, [isOpen, isExporting, isPublishing, isReviewing, onClose]);

  const handleReview = async () => {
    if (!token || !productId) return;

    setIsReviewing(true);
    setReviewResult(null);

    try {
      const response = await fetch(`${API_URL}/api/products/${productId}/review-prd`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({}),
      });

      if (response.ok) {
        const result = await response.json();
        setReviewResult(result);
      } else {
        const errorData = await response.json();
        console.error('Review error:', errorData);
        // Continue with export even if review fails
      }
    } catch (error) {
      console.error('Review error:', error);
      // Continue with export even if review fails
    } finally {
      setIsReviewing(false);
    }
  };

  const handleExport = async () => {
    if (!token || !productId) return;

    // Handle Confluence publish separately
    if (exportType === 'confluence') {
      handlePublishToConfluence();
      return;
    }

    setIsExporting(true);

    try {
      const response = await fetch(`${API_URL}/api/products/${productId}/export-prd`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          format: 'html', // Always get HTML from backend
          override_missing: overrideMissing,
        }),
      });

      if (response.ok) {
        if (exportType === 'pdf') {
          // For PDF, get HTML and convert to PDF using browser print
          const htmlBlob = await response.blob();
          const htmlText = await htmlBlob.text();
          
          // Create a new window with the HTML content
          const printWindow = window.open('', '_blank');
          if (printWindow) {
            printWindow.document.write(htmlText);
            printWindow.document.close();
            // Wait for content to load, then trigger print
            printWindow.onload = () => {
              setTimeout(() => {
                printWindow.print();
              }, 250);
            };
          } else {
            // Fallback: download HTML if popup blocked
            const blob = new Blob([htmlText], { type: 'text/html' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `PRD_${productId}_${new Date().toISOString().split('T')[0]}.html`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            alert('Popup blocked. HTML file downloaded instead. You can print it to PDF from your browser.');
          }
        } else {
          // HTML export
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `PRD_${productId}_${new Date().toISOString().split('T')[0]}.html`;
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);
        }

        if (onExportComplete) {
          onExportComplete();
        }
        if (exportType !== 'pdf') {
          onClose();
        }
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to export PRD');
      }
    } catch (error) {
      console.error('Export error:', error);
      alert(`Failed to export PRD: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsExporting(false);
    }
  };

  const handlePublishToConfluence = async () => {
    if (!token || !productId || !confluenceSpaceKey.trim()) {
      alert('Please enter a Confluence space key');
      return;
    }

    setIsPublishing(true);
    setPublishResult(null);

    try {
      const response = await fetch(`${API_URL}/api/products/${productId}/publish-to-confluence`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          space_key: confluenceSpaceKey.trim(),
          override_missing: overrideMissing,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        setPublishResult(result);
        if (onExportComplete) {
          onExportComplete();
        }
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to publish to Confluence');
      }
    } catch (error) {
      console.error('Publish error:', error);
      alert(`Failed to publish to Confluence: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsPublishing(false);
    }
  };

  if (!isOpen) return null;

  // Use React Portal to render at document root, avoiding z-index stacking context issues
  const modalContent = (
    <div 
      className="fixed inset-0 z-[9999]" 
      style={{ isolation: 'isolate' }}
      onClick={(e) => {
        // Close on backdrop click (but not on modal content click)
        if (e.target === e.currentTarget && !isExporting && !isPublishing && !isReviewing) {
          onClose();
        }
      }}
    >
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm" />
      
      {/* Modal Content */}
      <div className="fixed inset-0 flex items-center justify-center p-4 pointer-events-none">
        <div 
          className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col pointer-events-auto"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between z-10">
            <h2 className="text-2xl font-bold text-gray-900">Export Product Requirements Document</h2>
            <button
              onClick={onClose}
              disabled={isExporting || isPublishing || isReviewing}
              className="text-gray-400 hover:text-gray-600 transition disabled:opacity-50 disabled:cursor-not-allowed"
              title="Close (Esc)"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          <div className="p-6 space-y-6 overflow-y-auto flex-1">
          {/* Review Section */}
          <div className="bg-blue-50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <FileText className="w-5 h-5" />
                Content Review
              </h3>
              <button
                onClick={handleReview}
                disabled={isReviewing}
                className="text-sm text-blue-600 hover:text-blue-700 font-medium disabled:opacity-50"
              >
                {isReviewing ? 'Reviewing...' : 'Refresh Review'}
              </button>
            </div>

            {isReviewing ? (
              <div className="flex items-center gap-2 text-gray-600">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Reviewing PRD content...</span>
              </div>
            ) : reviewResult ? (
              <div className="space-y-4">
                {/* Overall Score */}
                {reviewResult.score !== undefined && (
                  <div className="bg-white rounded-lg p-4 border-2 border-blue-200">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-700">Overall PRD Completeness</span>
                      <span className="text-2xl font-bold text-blue-600">{reviewResult.score}%</span>
                    </div>
                    <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all ${
                          reviewResult.score >= 80 ? 'bg-green-500' :
                          reviewResult.score >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${reviewResult.score}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Phase Scores */}
                {reviewResult.phase_scores && reviewResult.phase_scores.length > 0 && (
                  <div className="bg-white rounded-lg p-4 border border-gray-200">
                    <h4 className="text-sm font-semibold text-gray-900 mb-3">Phase Scores</h4>
                    <div className="space-y-2">
                      {reviewResult.phase_scores.map((phase, idx) => (
                        <div key={idx} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                          <span className="text-sm text-gray-700">{phase.phase_name}</span>
                          <div className="flex items-center gap-2">
                            <span className={`text-sm font-medium ${
                              phase.score >= 80 ? 'text-green-600' :
                              phase.score >= 60 ? 'text-yellow-600' : 'text-red-600'
                            }`}>
                              {phase.score}%
                            </span>
                            <span className={`text-xs px-2 py-1 rounded ${
                              phase.status === 'complete' ? 'bg-green-100 text-green-700' :
                              phase.status === 'incomplete' ? 'bg-yellow-100 text-yellow-700' :
                              'bg-red-100 text-red-700'
                            }`}>
                              {phase.status}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {reviewResult.status === 'ready' ? (
                  <div className="flex items-center gap-2 text-green-700">
                    <CheckCircle className="w-5 h-5" />
                    <span className="font-medium">PRD is ready for export</span>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-amber-700">
                      <AlertCircle className="w-5 h-5" />
                      <span className="font-medium">PRD needs attention</span>
                    </div>
                    {reviewResult.missing_sections.length > 0 && (
                      <div className="ml-7 space-y-3">
                        {reviewResult.missing_sections.map((section, idx) => (
                          <div key={idx} className="text-sm p-3 bg-amber-50 rounded-lg border border-amber-200">
                            <div className="flex items-center justify-between mb-2">
                              <div className="font-medium text-gray-900">{section.section}</div>
                              {section.score !== undefined && (
                                <span className={`text-xs font-medium px-2 py-1 rounded ${
                                  section.score >= 80 ? 'bg-green-100 text-green-700' :
                                  section.score >= 60 ? 'bg-yellow-100 text-yellow-700' :
                                  'bg-red-100 text-red-700'
                                }`}>
                                  {section.score}%
                                </span>
                              )}
                            </div>
                            <div className="text-gray-600 text-xs mt-1">{section.importance}</div>
                            <div className="text-blue-600 text-xs mt-1">{section.recommendation}</div>
                            {section.phase_id && (
                              <button
                                onClick={() => {
                                  // Dispatch event to navigate to phase
                                  window.dispatchEvent(new CustomEvent('navigateToPhase', {
                                    detail: { phaseId: section.phase_id, phaseName: section.phase_name }
                                  }));
                                  onClose();
                                }}
                                className="mt-2 text-xs text-blue-600 hover:text-blue-700 font-medium underline"
                              >
                                Navigate to {section.phase_name || section.section}
                              </button>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
                {reviewResult.summary && (
                  <div className="text-sm text-gray-700 mt-3 p-3 bg-white rounded border border-gray-200">
                    {reviewResult.summary}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-sm text-gray-600">Click "Refresh Review" to check PRD completeness</div>
            )}
          </div>

          {/* Export Options */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Export Options</label>
              <div className="grid grid-cols-3 gap-3">
                <label className="flex flex-col items-center gap-2 p-4 border-2 rounded-lg cursor-pointer transition hover:bg-gray-50 border-gray-200 hover:border-blue-300">
                  <input
                    type="radio"
                    value="html"
                    checked={exportType === 'html'}
                    onChange={(e) => setExportType(e.target.value as 'html' | 'pdf' | 'confluence')}
                    className="w-4 h-4 text-blue-600"
                  />
                  <FileText className="w-6 h-6 text-blue-600" />
                  <span className="text-sm font-medium">HTML</span>
                </label>
                <label className="flex flex-col items-center gap-2 p-4 border-2 rounded-lg cursor-pointer transition hover:bg-gray-50 border-gray-200 hover:border-red-300">
                  <input
                    type="radio"
                    value="pdf"
                    checked={exportType === 'pdf'}
                    onChange={(e) => setExportType(e.target.value as 'html' | 'pdf' | 'confluence')}
                    className="w-4 h-4 text-red-600"
                  />
                  <FileText className="w-6 h-6 text-red-600" />
                  <span className="text-sm font-medium">PDF</span>
                </label>
                <label className="flex flex-col items-center gap-2 p-4 border-2 rounded-lg cursor-pointer transition hover:bg-gray-50 border-gray-200 hover:border-green-300">
                  <input
                    type="radio"
                    value="confluence"
                    checked={exportType === 'confluence'}
                    onChange={(e) => setExportType(e.target.value as 'html' | 'pdf' | 'confluence')}
                    className="w-4 h-4 text-green-600"
                  />
                  <BookOpen className="w-6 h-6 text-green-600" />
                  <span className="text-sm font-medium">Confluence</span>
                </label>
              </div>
            </div>

            {reviewResult?.status === 'needs_attention' && reviewResult.missing_sections.length > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={overrideMissing}
                    onChange={(e) => setOverrideMissing(e.target.checked)}
                    className="w-4 h-4 text-amber-600"
                  />
                  <span className="text-sm text-gray-700">
                    Export anyway with missing sections marked as "TO BE DEFINED"
                  </span>
                </label>
              </div>
            )}

            {/* Export Button */}
            {exportType === 'confluence' ? (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Confluence Space Key
                  </label>
                  <input
                    type="text"
                    value={confluenceSpaceKey}
                    onChange={(e) => setConfluenceSpaceKey(e.target.value)}
                    placeholder="e.g., IDEA"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Enter the space key where the PRD should be published
                  </p>
                </div>
                {publishResult ? (
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-green-700 mb-2">
                      <CheckCircle className="w-5 h-5" />
                      <span className="font-medium">Published successfully!</span>
                    </div>
                    {publishResult.url && (
                      <a
                        href={publishResult.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
                      >
                        <ExternalLink className="w-4 h-4" />
                        View in Confluence
                      </a>
                    )}
                  </div>
                ) : (
                  <button
                    onClick={handleExport}
                    disabled={isPublishing || !confluenceSpaceKey.trim()}
                    className="w-full bg-green-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-green-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {isPublishing ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        <span>Publishing...</span>
                      </>
                    ) : (
                      <>
                        <BookOpen className="w-5 h-5" />
                        <span>Publish to Confluence</span>
                      </>
                    )}
                  </button>
                )}
              </div>
            ) : (
              <button
                onClick={handleExport}
                disabled={isExporting}
                className={`w-full text-white py-3 px-4 rounded-lg font-medium transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 ${
                  exportType === 'pdf' 
                    ? 'bg-red-600 hover:bg-red-700' 
                    : 'bg-blue-600 hover:bg-blue-700'
                }`}
              >
                {isExporting ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Exporting...</span>
                  </>
                ) : (
                  <>
                    <Download className="w-5 h-5" />
                    <span>Export as {exportType.toUpperCase()}</span>
                  </>
                )}
              </button>
            )}
          </div>

          {/* Chat Export */}
          {conversationHistory && conversationHistory.length > 0 && (
            <div className="border-t border-gray-200 pt-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <FileText className="w-5 h-5" />
                  Export Chat Conversation
                </h3>
                <button
                  onClick={() => setShowChatExport(!showChatExport)}
                  className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                >
                  {showChatExport ? 'Hide' : 'Show'}
                </button>
              </div>

              {showChatExport && (
                <div className="space-y-4">
                  <button
                    onClick={() => {
                      const chatText = conversationHistory
                        .map((msg) => `${msg.role === 'user' ? 'User' : 'Assistant'}: ${msg.content}`)
                        .join('\n\n');
                      const blob = new Blob([chatText], { type: 'text/plain' });
                      const url = window.URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = `Chat_${productId}_${new Date().toISOString().split('T')[0]}.txt`;
                      document.body.appendChild(a);
                      a.click();
                      window.URL.revokeObjectURL(url);
                      document.body.removeChild(a);
                    }}
                    className="w-full bg-gray-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-gray-700 transition flex items-center justify-center gap-2"
                  >
                    <Download className="w-5 h-5" />
                    <span>Export Chat as Text</span>
                  </button>
                </div>
              )}
            </div>
          )}

          </div>
        </div>
      </div>
    </div>
  );

  // Render using React Portal to document body
  return createPortal(modalContent, document.body);
}

