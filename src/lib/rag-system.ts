import OpenAI from 'openai';
import { supabase } from './supabase';

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
    const embedding = await this.generateEmbedding(content);

    const { data, error } = await supabase
      .from('knowledge_articles')
      .insert({
        product_id: productId || '00000000-0000-0000-0000-000000000000',
        title,
        content,
        source: 'manual',
        embedding,
        metadata: metadata || {},
      })
      .select()
      .single();

    if (error) throw new Error(error.message);

    return data as Document;
  }

  async searchSimilar(query: string, limit: number = 5, productId?: string): Promise<SearchResult[]> {
    const queryEmbedding = await this.generateEmbedding(query);

    const { data, error } = await supabase.rpc('search_knowledge_articles', {
      query_embedding: queryEmbedding,
      match_threshold: 0.7,
      match_count: limit,
      filter_product_id: productId || null,
    });

    if (error) throw new Error(error.message);

    return (data || []).map((item: any) => ({
      document: {
        id: item.id,
        product_id: item.product_id,
        title: item.title,
        content: item.content,
        source: item.source,
        metadata: item.metadata,
        created_at: item.created_at,
      },
      similarity: item.similarity,
    }));
  }

  async searchByKeywords(keywords: string, limit: number = 5, productId?: string): Promise<Document[]> {
    let query = supabase
      .from('knowledge_articles')
      .select('*')
      .ilike('content', `%${keywords}%`)
      .limit(limit);

    if (productId) {
      query = query.eq('product_id', productId);
    }

    const { data, error } = await query;

    if (error) throw new Error(error.message);

    return data as Document[];
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
    const { error } = await supabase.from('knowledge_articles').delete().eq('id', id);

    if (error) throw new Error(error.message);
  }

  async getAllDocuments(productId?: string): Promise<Document[]> {
    let query = supabase
      .from('knowledge_articles')
      .select('*')
      .order('created_at', { ascending: false });

    if (productId) {
      query = query.eq('product_id', productId);
    }

    const { data, error } = await query;

    if (error) throw new Error(error.message);

    return data as Document[];
  }

  async updateDocument(
    id: string,
    updates: { title?: string; content?: string; metadata?: Record<string, unknown> }
  ): Promise<Document> {
    const updateData: any = { ...updates };

    if (updates.content) {
      updateData.embedding = await this.generateEmbedding(updates.content);
    }

    const { data, error } = await supabase
      .from('knowledge_articles')
      .update(updateData)
      .eq('id', id)
      .select()
      .single();

    if (error) throw new Error(error.message);

    return data as Document;
  }
}
