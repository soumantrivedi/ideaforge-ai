import { useState } from 'react';
import { Plus, Trash2, Search, BookOpen, Upload } from 'lucide-react';
import type { Document } from '../lib/rag-system';

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

  const displayDocuments = searchQuery.trim() ? searchResults : documents;

  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-blue-600" />
          <h3 className="text-lg font-bold text-gray-900">Knowledge Base</h3>
          <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded-full">
            {documents.length} docs
          </span>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition flex items-center gap-2"
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
              className="px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition"
            >
              <Upload className="w-4 h-4 inline mr-2" />
              Add to Knowledge Base
            </button>
            <button
              type="button"
              onClick={() => {
                setShowAddForm(false);
                setTitle('');
                setContent('');
              }}
              className="px-4 py-2 bg-gray-200 text-gray-700 font-medium rounded-lg hover:bg-gray-300 transition"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      <form onSubmit={handleSearch} className="mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search knowledge base..."
            className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </form>

      <div className="space-y-3 max-h-96 overflow-y-auto">
        {displayDocuments.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <BookOpen className="w-12 h-12 mx-auto mb-4 text-gray-300" />
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
                  <h4 className="font-semibold text-gray-900 mb-2">{doc.title}</h4>
                  <p className="text-sm text-gray-600 line-clamp-2">{doc.content}</p>
                  <p className="text-xs text-gray-400 mt-2">
                    {new Date(doc.created_at).toLocaleDateString()}
                  </p>
                </div>
                <button
                  onClick={() => onDeleteDocument(doc.id)}
                  className="ml-4 p-2 text-red-600 hover:bg-red-50 rounded-lg transition"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
