import { useState, useEffect } from 'react';
import { Plus, Trash2, Search, BookOpen, Upload, X, Eye, EyeOff } from 'lucide-react';
import type { Document } from '../lib/rag-system';
import { ContentFormatter } from '../lib/content-formatter';

interface KnowledgeBaseManagerProps {
  documents: Document[];
  onAddDocument: (title: string, content: string) => Promise<void>;
  onDeleteDocument: (id: string) => Promise<void>;
  onSearch: (query: string) => Promise<Document[]>;
}

export function KnowledgeBaseManager({
  documents,
  onAddDocument,
  onDeleteDocument,
  onSearch,
}: KnowledgeBaseManagerProps) {
  const [showAddForm, setShowAddForm] = useState(false);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Document[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [previewedDocId, setPreviewedDocId] = useState<string | null>(null);

  const handleAddDocument = async (e: React.FormEvent) => {
    e.preventDefault();
    if (title.trim() && content.trim()) {
      await onAddDocument(title.trim(), content.trim());
      setTitle('');
      setContent('');
      setShowAddForm(false);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      setIsSearching(true);
      const results = await onSearch(searchQuery.trim());
      setSearchResults(results);
      setIsSearching(false);
    }
  };

  const displayDocuments = searchQuery.trim() ? (Array.isArray(searchResults) ? searchResults : []) : (Array.isArray(documents) ? documents : []);
  const documentsCount = Array.isArray(documents) ? documents.length : 0;

  // Handle keyboard shortcuts for preview
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Escape key to close preview
      if (e.key === 'Escape' && previewedDocId) {
        setPreviewedDocId(null);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [previewedDocId]);

  const togglePreview = (docId: string) => {
    if (previewedDocId === docId) {
      setPreviewedDocId(null);
    } else {
      setPreviewedDocId(docId);
    }
  };

  return (
    <div className="rounded-xl border p-6" style={{ backgroundColor: 'var(--card-bg)', borderColor: 'var(--border-color)' }}>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <BookOpen className="w-5 h-5" style={{ color: 'var(--text-primary)' }} />
          <h3 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Knowledge Base</h3>
          <span className="px-2 py-1 text-xs font-medium rounded-full" style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-primary)' }}>
            {documentsCount} docs
          </span>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="px-4 py-2 font-medium rounded-md transition flex items-center gap-2"
          style={{ 
            backgroundColor: 'var(--button-primary-bg)', 
            color: 'var(--button-primary-text)' 
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--button-primary-hover)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--button-primary-bg)';
          }}
        >
          <Plus className="w-4 h-4" />
          Add Document
        </button>
      </div>

      {showAddForm && (
        <form onSubmit={handleAddDocument} className="mb-6 p-4 bg-gray-50 rounded-lg space-y-4">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Document Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Enter document title..."
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Content
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Enter document content..."
              rows={6}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              required
            />
          </div>

          <div className="flex gap-3">
            <button
              type="submit"
              className="px-4 py-2 font-medium rounded-lg transition flex items-center gap-2"
              style={{ 
                backgroundColor: 'var(--button-primary-bg)', 
                color: 'var(--button-primary-text)' 
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--button-primary-hover)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--button-primary-bg)';
              }}
            >
              <Upload className="w-4 h-4" />
              Add to Knowledge Base
            </button>
            <button
              type="button"
              onClick={() => {
                setShowAddForm(false);
                setTitle('');
                setContent('');
              }}
              className="px-4 py-2 font-medium rounded-lg transition"
              style={{ 
                backgroundColor: 'var(--button-secondary-bg)', 
                color: 'var(--button-secondary-text)',
                borderColor: 'var(--border-color)'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--button-secondary-hover)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--button-secondary-bg)';
              }}
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      <form onSubmit={handleSearch} className="mb-6">
        <div className="relative flex gap-2">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: 'var(--text-tertiary)' }} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search knowledge base..."
              className="w-full pl-10 pr-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
              style={{ 
                backgroundColor: 'var(--input-bg)', 
                color: 'var(--text-primary)', 
                borderColor: 'var(--input-border)' 
              }}
            />
          </div>
          <button
            type="submit"
            disabled={!searchQuery.trim() || isSearching}
            className="px-6 py-3 font-medium rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            style={{ 
              backgroundColor: 'var(--button-primary-bg)', 
              color: 'var(--button-primary-text)' 
            }}
            onMouseEnter={(e) => {
              if (!e.currentTarget.disabled) {
                e.currentTarget.style.backgroundColor = 'var(--button-primary-hover)';
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--button-primary-bg)';
            }}
          >
            <Search className="w-4 h-4" />
            {isSearching ? 'Searching...' : 'Search'}
          </button>
        </div>
      </form>

      <div className="space-y-3 max-h-96 overflow-y-auto">
        {!Array.isArray(displayDocuments) || displayDocuments.length === 0 ? (
          <div className="text-center py-12" style={{ color: 'var(--text-secondary)' }}>
            <BookOpen className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--text-tertiary)' }} />
            <p>
              {searchQuery.trim()
                ? 'No documents found matching your search'
                : 'No documents yet. Add your first document to get started.'}
            </p>
          </div>
        ) : (
          displayDocuments.map((doc) => (
            <div
              key={doc.id}
              className="p-4 border border-gray-200 rounded-lg hover:border-gray-300 transition"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <h4 
                      className="font-semibold text-gray-900 cursor-pointer hover:text-blue-600 transition"
                      onClick={() => togglePreview(doc.id)}
                    >
                      {doc.title}
                    </h4>
                    <button
                      onClick={() => togglePreview(doc.id)}
                      className="p-1 text-gray-500 hover:text-blue-600 rounded transition"
                      title={previewedDocId === doc.id ? "Hide preview (Esc)" : "Show preview"}
                    >
                      {previewedDocId === doc.id ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                  {previewedDocId === doc.id ? (
                    <div className="relative mt-2 p-4 bg-gray-50 rounded-lg border border-gray-200 max-h-96 overflow-y-auto">
                      <button
                        onClick={() => setPreviewedDocId(null)}
                        className="absolute top-2 right-2 p-1 text-gray-500 hover:text-gray-700 rounded transition"
                        title="Close preview (Esc)"
                      >
                        <X className="w-4 h-4" />
                      </button>
                      <div 
                        className="prose prose-sm max-w-none"
                        dangerouslySetInnerHTML={{ 
                          __html: ContentFormatter.markdownToHtml(doc.content || '') 
                        }}
                      />
                    </div>
                  ) : (
                    <p className="text-sm text-gray-600 line-clamp-2">{doc.content}</p>
                  )}
                  <p className="text-xs text-gray-400 mt-2">
                    {new Date(doc.created_at).toLocaleDateString()}
                    {doc.source && (
                      <span className="ml-2 px-2 py-0.5 bg-gray-100 rounded text-gray-600">
                        {doc.source}
                      </span>
                    )}
                  </p>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <button
                    onClick={() => onDeleteDocument(doc.id)}
                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition"
                    title="Delete document"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
