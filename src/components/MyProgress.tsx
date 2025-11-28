import { useState, useEffect } from 'react';
import { FileText, Download, Loader2, FileDown } from 'lucide-react';
import { ProgressReportModal } from './ProgressReportModal';
import { getValidatedApiUrl } from '../lib/runtime-config';
import { useAuth } from '../contexts/AuthContext';
import { ContentFormatter } from '../lib/content-formatter';

const API_URL = getValidatedApiUrl();

interface MyProgressProps {
  productId: string;
  onNavigateToPhase?: (phaseId: string) => void;
}

interface ProgressReport {
  id: string;
  overall_score: number;
  status: 'ready' | 'needs_attention' | 'in_progress';
  phase_scores: Array<{
    phase_name: string;
    phase_id: string;
    score: number;
    status: 'complete' | 'incomplete' | 'missing';
  }>;
  missing_sections: Array<{
    section: string;
    phase_name?: string;
    phase_id?: string;
    importance: string;
    recommendation: string;
    score: number;
  }>;
  recommendations: string[];
  summary: string;
  created_at?: string;
  updated_at?: string;
}

export function MyProgress({ productId, onNavigateToPhase }: MyProgressProps) {
  const { token } = useAuth();
  const [isGenerating, setIsGenerating] = useState(false);
  const [report, setReport] = useState<ProgressReport | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (productId && token) {
      loadProgressReport();
    }
  }, [productId, token]);

  const loadProgressReport = async () => {
    if (!productId || !token) return;
    
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/products/${productId}/progress-report`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        if (data.exists) {
          setReport(data);
        } else {
          setReport(null);
        }
      }
    } catch (error) {
      console.error('Error loading progress report:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateReport = async () => {
    if (!productId || !token) return;
    
    setIsGenerating(true);
    try {
      const response = await fetch(`${API_URL}/api/products/${productId}/generate-progress-report`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setReport(data);
        setIsModalOpen(true);
      } else {
        const errorText = await response.text();
        alert(`Failed to generate progress report: ${errorText}`);
      }
    } catch (error) {
      console.error('Error generating progress report:', error);
      alert('Failed to generate progress report. Please try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleExportHTML = () => {
    if (!report) return;
    
    const htmlContent = generateReportHTML(report);
    const blob = new Blob([htmlContent], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `progress-report-${productId.substring(0, 8)}-${new Date().toISOString().split('T')[0]}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleExportPDF = async () => {
    if (!report) return;
    
    try {
      const htmlContent = generateReportHTML(report);
      const printWindow = window.open('', '_blank');
      if (printWindow) {
        printWindow.document.write(htmlContent);
        printWindow.document.close();
        printWindow.onload = () => {
          printWindow.print();
        };
      }
    } catch (error) {
      console.error('Error exporting PDF:', error);
      alert('Failed to export PDF. Please try printing the HTML version instead.');
    }
  };

  const generateReportHTML = (report: ProgressReport): string => {
    const phaseScoresHTML = report.phase_scores?.map(phase => `
      <div style="margin-bottom: 1rem; padding: 1rem; background: #f9fafb; border-radius: 8px;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
          <h4 style="font-weight: 600; color: #111827;">${ContentFormatter.escapeHtml(phase.phase_name)}</h4>
          <span style="font-weight: 700; color: ${phase.score >= 80 ? '#10b981' : phase.score >= 60 ? '#f59e0b' : '#ef4444'};">
            ${phase.score}%
          </span>
        </div>
        <div style="height: 8px; background: #e5e7eb; border-radius: 4px; overflow: hidden;">
          <div style="height: 100%; width: ${phase.score}%; background: ${phase.score >= 80 ? '#10b981' : phase.score >= 60 ? '#f59e0b' : '#ef4444'};"></div>
        </div>
        <p style="font-size: 0.875rem; color: #6b7280; margin-top: 0.5rem;">
          Status: ${ContentFormatter.escapeHtml(phase.status)}
        </p>
      </div>
    `).join('') || '';

    const missingSectionsHTML = report.missing_sections?.map(section => `
      <div style="margin-bottom: 1rem; padding: 1rem; background: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 4px;">
        <h4 style="font-weight: 600; color: #92400e; margin-bottom: 0.5rem;">${ContentFormatter.escapeHtml(section.section)}</h4>
        <p style="font-size: 0.875rem; color: #78350f; margin-bottom: 0.5rem;">${ContentFormatter.escapeHtml(section.importance)}</p>
        <p style="font-size: 0.875rem; color: #92400e; font-weight: 500;">💡 ${ContentFormatter.escapeHtml(section.recommendation)}</p>
      </div>
    `).join('') || '';

    const recommendationsHTML = report.recommendations?.map(rec => `
      <li style="margin-bottom: 0.5rem; color: #374151;">${ContentFormatter.escapeHtml(rec)}</li>
    `).join('') || '';

    // Create proper HTML document directly (not through markdown conversion)
    const summaryHTML = report.summary ? `<h3 style="font-size: 1.25em; margin-top: 1.5em; margin-bottom: 0.75em; color: #111827;">Summary</h3><p style="margin-bottom: 1em; text-align: justify;">${ContentFormatter.escapeHtml(report.summary)}</p>` : '';
    
    const missingSectionsSection = report.missing_sections && report.missing_sections.length > 0 
      ? `<h2 style="font-size: 1.5em; border-bottom: 2px solid #e5e7eb; padding-bottom: 0.3em; margin-top: 2em; margin-bottom: 1em; color: #111827;">Areas for Improvement</h2>${missingSectionsHTML}` 
      : '';
    
    const recommendationsSection = report.recommendations && report.recommendations.length > 0 
      ? `<h2 style="font-size: 1.5em; border-bottom: 2px solid #e5e7eb; padding-bottom: 0.3em; margin-top: 2em; margin-bottom: 1em; color: #111827;">Recommendations</h2><ul style="margin: 1em 0 1em 2em;">${recommendationsHTML}</ul>` 
      : '';

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Progress Report</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      line-height: 1.6;
      color: #1f2937;
      max-width: 800px;
      margin: 0 auto;
      padding: 40px 20px;
      background: white;
    }
    h1 {
      font-size: 2em;
      border-bottom: 3px solid #3b82f6;
      padding-bottom: 0.3em;
      margin-bottom: 1em;
      color: #111827;
    }
    h2 {
      font-size: 1.5em;
      border-bottom: 2px solid #e5e7eb;
      padding-bottom: 0.3em;
      margin-top: 2em;
      margin-bottom: 1em;
      color: #111827;
    }
    h3 {
      font-size: 1.25em;
      margin-top: 1.5em;
      margin-bottom: 0.75em;
      color: #111827;
    }
    p {
      margin-bottom: 1em;
      text-align: justify;
    }
    ul {
      margin: 1em 0 1em 2em;
    }
    li {
      margin-bottom: 0.5em;
    }
    hr {
      border: none;
      border-top: 2px solid #e5e7eb;
      margin: 2em 0;
    }
    @media print {
      body {
        max-width: 100%;
        padding: 20px;
      }
      h1, h2, h3 {
        page-break-after: avoid;
      }
    }
  </style>
</head>
<body>
  <h1>Progress Report</h1>
  <h2>Overall Score: ${report.overall_score}%</h2>
  <p><strong>Status:</strong> ${ContentFormatter.escapeHtml(report.status)}</p>
  ${summaryHTML}
  <h2>Phase Scores</h2>
  ${phaseScoresHTML}
  ${missingSectionsSection}
  ${recommendationsSection}
  <hr>
  <p style="text-align: center; color: #6b7280; font-size: 0.875em; margin-top: 3em;">
    Generated by IdeaForge AI • ${new Date(report.updated_at || report.created_at || Date.now()).toLocaleString()}
  </p>
</body>
</html>`;
  };

  return (
    <>
      <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-4">
        <button
          onClick={handleGenerateReport}
          disabled={isGenerating || loading}
          className="w-full bg-gradient-to-r from-purple-600 to-pink-600 text-white px-4 py-3 rounded-xl font-semibold shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
        >
          {isGenerating ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Generating Report...
            </>
          ) : (
            <>
              <FileText className="w-5 h-5" />
              Review Progress
            </>
          )}
        </button>

        {report && (
          <div className="mt-3 flex gap-2">
            <button
              onClick={() => setIsModalOpen(true)}
              className="flex-1 px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg font-medium text-sm transition-colors flex items-center justify-center gap-2"
            >
              <FileText className="w-4 h-4" />
              View
            </button>
            <button
              onClick={handleExportHTML}
              className="flex-1 px-3 py-2 bg-blue-100 hover:bg-blue-200 text-blue-700 rounded-lg font-medium text-sm transition-colors flex items-center justify-center gap-2"
            >
              <Download className="w-4 h-4" />
              HTML
            </button>
            <button
              onClick={handleExportPDF}
              className="flex-1 px-3 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-lg font-medium text-sm transition-colors flex items-center justify-center gap-2"
            >
              <FileDown className="w-4 h-4" />
              PDF
            </button>
          </div>
        )}
      </div>

      {report && (
        <ProgressReportModal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          report={report}
          onNavigateToPhase={onNavigateToPhase}
        />
      )}
    </>
  );
}
