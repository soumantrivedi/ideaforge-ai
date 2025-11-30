import { useState, useRef } from 'react';
import { Upload, File, Link, BookOpen, X, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

import { getValidatedApiUrl } from '../lib/runtime-config';
const API_URL = getValidatedApiUrl();

interface DocumentUploaderProps {
  productId?: string;
  onUploadComplete?: (documentId: string) => void;
}

type UploadSource = 'local' | 'confluence';

interface UploadStatus {
  status: 'idle' | 'uploading' | 'success' | 'error';
  message?: string;
}

export function DocumentUploader({ productId, onUploadComplete }: DocumentUploaderProps) {
  const [uploadSource, setUploadSource] = useState<UploadSource>('local');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [confluenceUrl, setConfluenceUrl] = useState('');
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>({ status: 'idle' });
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { token } = useAuth();

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setUploadStatus({ status: 'idle' });
    }
  };

  const handleLocalUpload = async () => {
    if (!selectedFile || !token) {
      setUploadStatus({ status: 'error', message: 'Please select a file and ensure you are logged in.' });
      return;
    }

    setIsUploading(true);
    setUploadStatus({ status: 'uploading', message: 'Uploading file...' });

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      if (productId) {
        formData.append('product_id', productId);
      }

      const response = await fetch(`${API_URL}/api/documents/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        credentials: 'include',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to upload file');
      }

      const result = await response.json();
      setUploadStatus({ status: 'success', message: 'File uploaded successfully!' });
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      
      if (onUploadComplete) {
        onUploadComplete(result.document_id);
      }
    } catch (error) {
      setUploadStatus({
        status: 'error',
        message: error instanceof Error ? error.message : 'Failed to upload file'
      });
    } finally {
      setIsUploading(false);
    }
  };


  const handleConfluenceUpload = async () => {
    if (!confluenceUrl.trim() || !token) {
      setUploadStatus({ status: 'error', message: 'Please enter a Confluence URL or page ID.' });
      return;
    }

    setIsUploading(true);
    setUploadStatus({ status: 'uploading', message: 'Fetching from Confluence...' });

    try {
      const response = await fetch(`${API_URL}/api/documents/upload-from-confluence`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          confluence_url: confluenceUrl.trim(),
          product_id: productId,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to fetch from Confluence');
      }

      const result = await response.json();
      setUploadStatus({ status: 'success', message: 'Document fetched from Confluence successfully!' });
      setConfluenceUrl('');
      
      if (onUploadComplete) {
        onUploadComplete(result.document_id);
      }
    } catch (error) {
      setUploadStatus({
        status: 'error',
        message: error instanceof Error ? error.message : 'Failed to fetch from Confluence'
      });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <div className="flex items-center gap-3 mb-6">
        <Upload className="w-6 h-6 text-blue-600" />
        <div>
          <h3 className="text-lg font-bold text-gray-900">Upload Documents</h3>
          <p className="text-sm text-gray-500">Upload from local files, GitHub, or Confluence</p>
        </div>
      </div>

      {/* Source Selection */}
      <div className="mb-6">
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={() => setUploadSource('local')}
            className={`p-4 rounded-lg border-2 transition ${
              uploadSource === 'local'
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <File className="w-6 h-6 mx-auto mb-2 text-gray-600" />
            <p className="text-sm font-medium">Local File</p>
          </button>
          <button
            onClick={() => setUploadSource('confluence')}
            className={`p-4 rounded-lg border-2 transition ${
              uploadSource === 'confluence'
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <BookOpen className="w-6 h-6 mx-auto mb-2 text-gray-600" />
            <p className="text-sm font-medium">Confluence</p>
          </button>
        </div>
      </div>

      {/* Upload Forms */}
      <div className="space-y-4">
        {uploadSource === 'local' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select File
            </label>
            <div className="flex items-center gap-3">
              <input
                ref={fileInputRef}
                type="file"
                onChange={handleFileSelect}
                className="hidden"
                id="file-upload"
                accept=".pdf,.md,.txt,.doc,.docx,.html"
              />
              <label
                htmlFor="file-upload"
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50 transition flex items-center gap-2"
              >
                <File className="w-4 h-4" />
                <span>{selectedFile ? selectedFile.name : 'Choose a file...'}</span>
              </label>
              {selectedFile && (
                <button
                  onClick={() => {
                    setSelectedFile(null);
                    if (fileInputRef.current) {
                      fileInputRef.current.value = '';
                    }
                  }}
                  className="p-2 text-gray-500 hover:text-gray-700"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
            <button
              onClick={handleLocalUpload}
              disabled={!selectedFile || isUploading}
              className="mt-3 w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  Upload File
                </>
              )}
            </button>
          </div>
        )}

        {uploadSource === 'confluence' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Confluence URL or Page ID
            </label>
            <input
              type="text"
              value={confluenceUrl}
              onChange={(e) => setConfluenceUrl(e.target.value)}
              placeholder="https://your-domain.atlassian.net/wiki/spaces/SPACE/pages/123456789/Page+Title or page ID: 123456789"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="text-xs text-gray-500 mt-1">
              Enter a Confluence page URL or page ID to fetch and add to knowledge base
            </p>
            <button
              onClick={handleConfluenceUpload}
              disabled={!confluenceUrl.trim() || isUploading}
              className="mt-3 w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Fetching...
                </>
              ) : (
                <>
                  <BookOpen className="w-4 h-4" />
                  Fetch from Confluence
                </>
              )}
            </button>
          </div>
        )}

        {/* Status Message */}
        {uploadStatus.status !== 'idle' && (
          <div
            className={`p-4 rounded-lg flex items-center gap-3 ${
              uploadStatus.status === 'success'
                ? 'bg-green-50 border border-green-200 text-green-700'
                : uploadStatus.status === 'error'
                ? 'bg-red-50 border border-red-200 text-red-700'
                : 'bg-blue-50 border border-blue-200 text-blue-700'
            }`}
          >
            {uploadStatus.status === 'success' ? (
              <CheckCircle2 className="w-5 h-5" />
            ) : uploadStatus.status === 'error' ? (
              <AlertCircle className="w-5 h-5" />
            ) : (
              <Loader2 className="w-5 h-5 animate-spin" />
            )}
            <p className="text-sm">{uploadStatus.message}</p>
          </div>
        )}
      </div>
    </div>
  );
}

