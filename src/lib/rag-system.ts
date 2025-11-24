import OpenAI from 'openai';
// Using backend API instead of Supabase
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface Document {
  id: string;
  product_id?: string;
  title: string;
  content: string;
  source?: string;
  embedding?: number[];
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface SearchResult {
  document: Document;
  similarity: number;
}

export class RAGSystem {
  private openai: OpenAI;

  constructor(apiKey: string) {
    this.openai = new OpenAI({ apiKey, dangerouslyAllowBrowser: true });
  }

  async generateEmbedding(text: string): Promise<number[]> {
    const response = await this.openai.embeddings.create({
      model: 'text-embedding-3-small',
      input: text,
    });

    return response.data[0].embedding;
  }

  async addDocument(title: string, content: string, metadata?: Record<string, unknown>, productId?: string): Promise<Document> {
    try {
      const embedding = await this.generateEmbedding(content);
      
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/db/knowledge-articles`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          product_id: productId || '00000000-0000-0000-0000-000000000000',
          title,
          content,
          source: 'manual',
          embedding: Array.from(embedding), // Convert to array for JSON
          metadata: metadata || {},
        }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      return {
        id: result.id,
        product_id: productId,
        title,
        content,
        source: 'manual',
        embedding,
        metadata: metadata || {},
        created_at: result.created_at || new Date().toISOString(),
      };
    } catch (error) {
      console.error('Error adding document:', error);
      throw error;
    }
  }

  async searchSimilar(query: string, limit: number = 5, productId?: string): Promise<SearchResult[]> {
    // TODO: Implement vector search via backend API
    // For now, fall back to keyword search
    return this.searchByKeywords(query, limit, productId).then(docs => 
      docs.map(doc => ({ document: doc, similarity: 0.8 }))
    );
  }

  async searchByKeywords(keywords: string, limit: number = 5, productId?: string): Promise<Document[]> {
    try {
      const params = new URLSearchParams({ limit: String(limit) });
      if (productId) {
        params.append('product_id', productId);
      }
      
      const response = await fetch(`${API_URL}/api/db/knowledge-articles?${params}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      const articles = result.articles || [];
      
      // Filter by keywords (client-side for now)
      const filtered = articles.filter((article: any) => 
        article.content.toLowerCase().includes(keywords.toLowerCase()) ||
        article.title.toLowerCase().includes(keywords.toLowerCase())
      ).slice(0, limit);
      
      return filtered.map((article: any) => ({
        id: article.id,
        product_id: article.product_id,
        title: article.title,
        content: article.content,
        source: article.source,
        metadata: article.metadata,
        created_at: article.created_at,
      }));
    } catch (error) {
      console.error('Error searching by keywords:', error);
      return [];
    }
  }

  async getRelevantContext(query: string, maxTokens: number = 2000): Promise<string> {
    const results = await this.searchSimilar(query, 5);

    if (results.length === 0) {
      return 'No relevant context found.';
    }

    let context = '## Relevant Knowledge Base Context:\n\n';
    let currentTokens = 0;

    for (const result of results) {
      const docText = `### ${result.document.title}\n${result.document.content}\n\n`;
      const estimatedTokens = Math.ceil(docText.length / 4);

      if (currentTokens + estimatedTokens > maxTokens) {
        break;
      }

      context += docText;
      currentTokens += estimatedTokens;
    }

    return context;
  }

  async deleteDocument(id: string): Promise<void> {
    // TODO: Implement backend API endpoint for deleting documents
    console.warn('Delete document API not yet implemented');
  }

  async getAllDocuments(productId?: string): Promise<Document[]> {
    try {
      const params = new URLSearchParams({ limit: '50' });
      if (productId) {
        params.append('product_id', productId);
      }
      
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/db/knowledge-articles?${params}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      return (result.articles || []).map((article: any) => ({
        id: article.id,
        product_id: article.product_id,
        title: article.title,
        content: article.content,
        source: article.source,
        metadata: article.metadata,
        created_at: article.created_at,
      }));
    } catch (error) {
      console.error('Error loading documents:', error);
      return [];
    }
  }

  async updateDocument(
    id: string,
    updates: { title?: string; content?: string; metadata?: Record<string, unknown> }
  ): Promise<Document> {
    // TODO: Implement backend API endpoint for updating documents
    throw new Error('Update document API not yet implemented');
  }
}
