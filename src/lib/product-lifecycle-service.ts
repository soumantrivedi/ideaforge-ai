// Using backend API instead of Supabase
import { apiFetch } from './api-client';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface LifecyclePhase {
  id: string;
  phase_name: string;
  phase_order: number;
  description: string;
  icon: string;
  required_fields: string[];
  template_prompts: string[];
  created_at: string;
}

export interface PhaseSubmission {
  id: string;
  product_id: string;
  phase_id: string;
  user_id: string;
  form_data: Record<string, any>;
  generated_content?: string;
  status: 'draft' | 'in_progress' | 'completed' | 'reviewed';
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface ConversationHistoryEntry {
  id: string;
  session_id: string;
  product_id?: string;
  phase_id?: string;
  message_type: 'user' | 'agent' | 'system';
  agent_name?: string;
  agent_role?: string;
  content: string;
  formatted_content?: string;
  parent_message_id?: string;
  interaction_metadata: Record<string, any>;
  created_at: string;
}

export interface ExportedDocument {
  id: string;
  product_id: string;
  user_id: string;
  document_type: 'prd' | 'summary' | 'full_lifecycle' | 'phase_report';
  title: string;
  content: string;
  formatted_html?: string;
  pdf_url?: string;
  version: number;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export class ProductLifecycleService {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
  }

  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };
    // Get token from localStorage if not set (apiFetch will also check, but we set it here for consistency)
    const token = this.token || localStorage.getItem('auth_token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  }

  // Lifecycle Phases
  async getAllPhases(): Promise<LifecyclePhase[]> {
    try {
      const response = await apiFetch('/api/db/phases', {
        headers: this.getHeaders(),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const result = await response.json();
      return result.phases || [];
    } catch (error) {
      console.error('Error loading phases:', error);
      return [];
    }
  }

  async getPhaseById(phaseId: string): Promise<LifecyclePhase | null> {
    try {
      const phases = await this.getAllPhases();
      return phases.find(p => p.id === phaseId) || null;
    } catch (error) {
      console.error('Error loading phase:', error);
      return null;
    }
  }

  // Phase Submissions
  async getPhaseSubmissions(productId: string): Promise<PhaseSubmission[]> {
    try {
      const response = await apiFetch(`/api/db/phase-submissions?product_id=${productId}`, {
        headers: this.getHeaders(),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const result = await response.json();
      return result.submissions || [];
    } catch (error) {
      console.error('Error loading submissions:', error);
      return [];
    }
  }

  async getPhaseSubmission(
    productId: string,
    phaseId: string
  ): Promise<PhaseSubmission | null> {
    try {
      const response = await apiFetch(`/api/db/phase-submissions/${productId}/${phaseId}`, {
        headers: this.getHeaders(),
      });
      
      if (!response.ok) {
        if (response.status === 404) {
          return null; // No submission found
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      
      if (!result) {
        return null;
      }
      
      return {
        id: result.id,
        product_id: result.product_id,
        phase_id: result.phase_id,
        user_id: result.user_id,
        form_data: result.form_data || {},
        generated_content: result.generated_content,
        status: result.status,
        metadata: result.metadata || {},
        created_at: result.created_at,
        updated_at: result.updated_at,
      };
    } catch (error) {
      console.error('Error loading phase submission:', error);
      return null;
    }
  }

  async createPhaseSubmission(
    productId: string,
    phaseId: string,
    userId: string,
    formData: Record<string, any>
  ): Promise<PhaseSubmission> {
    try {
      const response = await apiFetch('/api/db/phase-submissions', {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({
          product_id: productId,
          phase_id: phaseId,
          user_id: userId,
          form_data: formData,
          status: 'draft',
        }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      return {
        id: result.id,
        product_id: productId,
        phase_id: phaseId,
        user_id: userId,
        form_data: formData,
        generated_content: null,
        status: 'draft',
        metadata: {},
        created_at: result.created_at || new Date().toISOString(),
        updated_at: result.updated_at || new Date().toISOString(),
      };
    } catch (error) {
      console.error('Error creating phase submission:', error);
      throw error;
    }
  }

  async updatePhaseSubmission(
    submissionId: string,
    updates: Partial<PhaseSubmission>
  ): Promise<PhaseSubmission> {
    try {
      const response = await apiFetch(`/api/db/phase-submissions/${submissionId}`, {
        method: 'PUT',
        headers: this.getHeaders(),
        body: JSON.stringify(updates),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      return result;
    } catch (error) {
      console.error('Error updating phase submission:', error);
      throw error;
    }
  }

  async updatePhaseContent(
    submissionId: string,
    generatedContent: string,
    status: PhaseSubmission['status'] = 'completed',
    metadata?: Record<string, any>
  ): Promise<PhaseSubmission> {
    const updates: any = {
      generated_content: generatedContent,
      status,
    };
    if (metadata) {
      updates.metadata = metadata;
    }
    return this.updatePhaseSubmission(submissionId, updates as Partial<PhaseSubmission>);
  }

  // Alias for submitPhaseData - creates or updates a phase submission
  async submitPhaseData(
    productId: string,
    phaseId: string,
    formData: Record<string, any>,
    userId?: string
  ): Promise<PhaseSubmission> {
    try {
      // Get userId if not provided
      if (!userId) {
        // Try to get from localStorage (auth_token stores user info separately)
        const storedUserId = localStorage.getItem('user_id');
        if (storedUserId) {
          userId = storedUserId;
        } else {
          throw new Error('User ID is required for creating phase submission');
        }
      }

      // First, try to get existing submission
      const existing = await this.getPhaseSubmission(productId, phaseId);
      
      if (existing) {
        // Update existing submission
        return await this.updatePhaseSubmission(existing.id, {
          form_data: formData,
          status: 'in_progress',
        } as Partial<PhaseSubmission>);
      } else {
        // Create new submission
        return await this.createPhaseSubmission(productId, phaseId, userId, formData);
      }
    } catch (error) {
      console.error('Error submitting phase data:', error);
      throw error;
    }
  }

  // Conversation History
  async saveConversationMessage(
    sessionId: string,
    messageType: 'user' | 'agent' | 'system',
    content: string,
    options?: {
      productId?: string;
      phaseId?: string;
      agentName?: string;
      agentRole?: string;
      formattedContent?: string;
      parentMessageId?: string;
      metadata?: Record<string, any>;
    }
  ): Promise<ConversationHistoryEntry | null> {
    try {
      const response = await apiFetch('/api/db/conversation-history', {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({
          session_id: sessionId,
          message_type: messageType,
          content,
          product_id: options?.productId,
          phase_id: options?.phaseId,
          agent_name: options?.agentName,
          agent_role: options?.agentRole,
          formatted_content: options?.formattedContent,
          parent_message_id: options?.parentMessageId,
          interaction_metadata: options?.metadata || {},
        }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      return {
        id: result.id,
        session_id: sessionId,
        product_id: options?.productId,
        phase_id: options?.phaseId,
        message_type: messageType,
        agent_name: options?.agentName,
        agent_role: options?.agentRole,
        content,
        formatted_content: options?.formattedContent,
        parent_message_id: options?.parentMessageId,
        interaction_metadata: options?.metadata || {},
        created_at: result.created_at || new Date().toISOString(),
      };
    } catch (error) {
      console.error('Error saving conversation message:', error);
      return null;
    }
  }

  async getConversationHistory(
    sessionId: string,
    options?: {
      productId?: string;
      phaseId?: string;
      limit?: number;
    }
  ): Promise<ConversationHistoryEntry[]> {
    try {
      const params = new URLSearchParams({
        session_id: sessionId,
        limit: String(options?.limit || 100),
      });
      
      if (options?.productId) {
        params.append('product_id', options.productId);
      }
      
      const response = await apiFetch(`/api/db/conversation-history?${params}`, {
        headers: this.getHeaders(),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      return result.messages || [];
    } catch (error) {
      console.error('Error loading conversation history:', error);
      return [];
    }
  }

  async getProductConversationHistory(
    productId: string
  ): Promise<ConversationHistoryEntry[]> {
    try {
      const response = await apiFetch(`/api/db/conversation-history?product_id=${productId}`, {
        headers: this.getHeaders(),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      return result.messages || [];
    } catch (error) {
      console.error('Error loading product conversation history:', error);
      return [];
    }
  }

  // Exported Documents
  async createExportedDocument(
    productId: string,
    userId: string,
    documentType: ExportedDocument['document_type'],
    title: string,
    content: string,
    options?: {
      formattedHtml?: string;
      metadata?: Record<string, any>;
    }
  ): Promise<ExportedDocument> {
    // TODO: Implement backend API endpoint for exported documents
    // For now, return a mock document
    return {
      id: crypto.randomUUID(),
      product_id: productId,
      user_id: userId,
      document_type: documentType,
      title,
      content,
      formatted_html: options?.formattedHtml,
      pdf_url: null,
      version: 1,
      metadata: options?.metadata || {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
  }

  async getExportedDocuments(
    productId: string,
    documentType?: ExportedDocument['document_type']
  ): Promise<ExportedDocument[]> {
    // TODO: Implement backend API endpoint for exported documents
    return [];
  }

  async getLatestDocument(
    productId: string,
    documentType: ExportedDocument['document_type']
  ): Promise<ExportedDocument | null> {
    // TODO: Implement backend API endpoint for exported documents
    return null;
  }

  // Product Progress
  async getProductProgress(productId: string): Promise<{
    totalPhases: number;
    completedPhases: number;
    currentPhase?: LifecyclePhase;
    submissions: PhaseSubmission[];
  }> {
    const [phases, submissions] = await Promise.all([
      this.getAllPhases(),
      this.getPhaseSubmissions(productId),
    ]);

    const completedSubmissions = submissions.filter(
      (s) => s.status === 'completed' || s.status === 'reviewed'
    );

    const nextIncompletePhase = phases.find(
      (phase) =>
        !completedSubmissions.some((sub) => sub.phase_id === phase.id)
    );

    return {
      totalPhases: phases.length,
      completedPhases: completedSubmissions.length,
      currentPhase: nextIncompletePhase,
      submissions,
    };
  }
}

export const lifecycleService = new ProductLifecycleService();
