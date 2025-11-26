import { useState, useEffect } from 'react';
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
  missing_sections: Array<{
    section: string;
    importance: string;
    recommendation: string;
  }>;
  summary: string;
}

export function ExportPRDModal({ productId, isOpen, onClose, onExportComplete, token, conversationHistory }: ExportPRDModalProps) {
  const [showChatExport, setShowChatExport] = useState(false);
  const [format, setFormat] = useState<'html' | 'markdown'>('html');
  const [overrideMissing, setOverrideMissing] = useState(false);
  const [isReviewing, setIsReviewing] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [reviewResult, setReviewResult] = useState<ReviewResult | null>(null);
  const [showConfluence, setShowConfluence] = useState(false);
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
          format,
          override_missing: overrideMissing,
        }),
      });

      if (response.ok) {
        if (format === 'markdown') {
          const text = await response.text();
          const blob = new Blob([text], { type: 'text/markdown' });
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `PRD_${productId}_${new Date().toISOString().split('T')[0]}.md`;
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);
        } else {
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
        onClose();
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

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">Export Product Requirements Document</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="p-6 space-y-6">
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
              <div className="space-y-3">
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
                      <div className="ml-7 space-y-2">
                        {reviewResult.missing_sections.map((section, idx) => (
                          <div key={idx} className="text-sm">
                            <div className="font-medium text-gray-900">{section.section}</div>
                            <div className="text-gray-600 text-xs mt-1">{section.importance}</div>
                            <div className="text-blue-600 text-xs mt-1">{section.recommendation}</div>
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
              <label className="block text-sm font-medium text-gray-700 mb-2">Export Format</label>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    value="html"
                    checked={format === 'html'}
                    onChange={(e) => setFormat(e.target.value as 'html' | 'markdown')}
                    className="w-4 h-4 text-blue-600"
                  />
                  <span>HTML</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    value="markdown"
                    checked={format === 'markdown'}
                    onChange={(e) => setFormat(e.target.value as 'html' | 'markdown')}
                    className="w-4 h-4 text-blue-600"
                  />
                  <span>Markdown</span>
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
            <button
              onClick={handleExport}
              disabled={isExporting}
              className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isExporting ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Exporting...</span>
                </>
              ) : (
                <>
                  <Download className="w-5 h-5" />
                  <span>Export PRD ({format.toUpperCase()})</span>
                </>
              )}
            </button>
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

          {/* Confluence Publishing */}
          <div className="border-t border-gray-200 pt-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <BookOpen className="w-5 h-5" />
                Publish to Confluence
              </h3>
              <button
                onClick={() => setShowConfluence(!showConfluence)}
                className="text-sm text-blue-600 hover:text-blue-700 font-medium"
              >
                {showConfluence ? 'Hide' : 'Show'}
              </button>
            </div>

            {showConfluence && (
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
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
                    onClick={handlePublishToConfluence}
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
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

