import { useState, useEffect } from 'react';
import { KnowledgeBaseManager } from './KnowledgeBaseManager';
import { DocumentUploader } from './DocumentUploader';
import { useAuth } from '../contexts/AuthContext';
import { RAGSystem } from '../lib/rag-system';
import type { Document } from '../lib/rag-system';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface KnowledgeBaseManagerWrapperProps {
  productId?: string;
}

export function KnowledgeBaseManagerWrapper({ productId }: KnowledgeBaseManagerWrapperProps) {
  const { token } = useAuth();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ragSystem, setRagSystem] = useState<RAGSystem | null>(null);

  useEffect(() => {
    loadDocuments();
  }, [productId, token]);

  const loadDocuments = async () => {
    if (!token) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/api/db/knowledge-articles${productId ? `?product_id=${productId}` : ''}`, {
        headers: { 'Authorization': `Bearer ${token}` },
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        const articles = Array.isArray(data.articles) ? data.articles : [];
        setDocuments(articles.map((article: any) => ({
          id: article.id || String(Date.now()),
          product_id: article.product_id,
          title: article.title || 'Untitled',
          content: article.content || '',
          source: article.source || 'manual',
          metadata: article.metadata || {},
          created_at: article.created_at || new Date().toISOString(),
        })));
      } else {
        setError('Failed to load documents');
      }
    } catch (err) {
      console.error('Error loading documents:', err);
      setError('Failed to load documents');
      setDocuments([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddDocument = async (title: string, content: string) => {
    if (!token) {
      setError('Authentication required');
      return;
    }

    try {
      const response = await fetch(`${API_URL}/api/db/knowledge-articles`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          product_id: productId || null,
          title,
          content,
          source: 'manual',
          metadata: {},
        }),
      });

      if (response.ok) {
        await loadDocuments();
      } else {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to add document');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add document');
      throw err;
    }
  };

  const handleDeleteDocument = async (id: string) => {
    if (!token) {
      setError('Authentication required');
      return;
    }

    try {
      const response = await fetch(`${API_URL}/api/db/knowledge-articles/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        credentials: 'include',
      });

      if (response.ok) {
        await loadDocuments();
      } else {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to delete document');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete document');
      throw err;
    }
  };

  const handleSearch = async (query: string): Promise<Document[]> => {
    if (!token) {
      return [];
    }

    try {
      const response = await fetch(`${API_URL}/api/db/knowledge-articles?search=${encodeURIComponent(query)}${productId ? `&product_id=${productId}` : ''}`, {
        headers: { 'Authorization': `Bearer ${token}` },
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        const articles = Array.isArray(data.articles) ? data.articles : [];
        return articles.map((article: any) => ({
          id: article.id || String(Date.now()),
          product_id: article.product_id,
          title: article.title || 'Untitled',
          content: article.content || '',
          source: article.source || 'manual',
          metadata: article.metadata || {},
          created_at: article.created_at || new Date().toISOString(),
        }));
      }
      return [];
    } catch (err) {
      console.error('Error searching documents:', err);
      return [];
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8" style={{ color: 'var(--text-secondary)' }}>
        <div>Loading knowledge base...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 rounded-xl border" style={{ backgroundColor: 'var(--card-bg)', borderColor: 'var(--border-color)' }}>
        <div className="text-center">
          <p className="mb-4" style={{ color: 'var(--text-primary)' }}>{error}</p>
          <button
            onClick={loadDocuments}
            className="px-4 py-2 rounded-md transition font-medium"
            style={{ 
              backgroundColor: 'var(--button-primary-bg)', 
              color: 'var(--button-primary-text)' 
            }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const handleUploadComplete = async (documentId: string) => {
    // Reload documents after upload
    await loadDocuments();
  };

  return (
    <div className="space-y-6">
      {!productId && (
        <div className="mb-4 p-4 rounded-md border" style={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-color)' }}>
          <p className="text-sm" style={{ color: 'var(--text-primary)' }}>
            <strong>Note:</strong> Select a product from Dashboard to manage product-specific knowledge articles, or add general knowledge articles here.
          </p>
        </div>
      )}
      <DocumentUploader
        productId={productId}
        onUploadComplete={handleUploadComplete}
      />
      <KnowledgeBaseManager
        documents={documents}
        onAddDocument={handleAddDocument}
        onDeleteDocument={handleDeleteDocument}
        onSearch={handleSearch}
      />
    </div>
  );
}

