import { supabase } from './supabase';

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
  // Lifecycle Phases
  async getAllPhases(): Promise<LifecyclePhase[]> {
    const { data, error } = await supabase
      .from('product_lifecycle_phases')
      .select('*')
      .order('phase_order', { ascending: true });

    if (error) throw error;
    return data || [];
  }

  async getPhaseById(phaseId: string): Promise<LifecyclePhase | null> {
    const { data, error } = await supabase
      .from('product_lifecycle_phases')
      .select('*')
      .eq('id', phaseId)
      .maybeSingle();

    if (error) throw error;
    return data;
  }

  // Phase Submissions
  async getPhaseSubmissions(productId: string): Promise<PhaseSubmission[]> {
    const { data, error } = await supabase
      .from('phase_submissions')
      .select('*')
      .eq('product_id', productId)
      .order('created_at', { ascending: true });

    if (error) throw error;
    return data || [];
  }

  async getPhaseSubmission(
    productId: string,
    phaseId: string
  ): Promise<PhaseSubmission | null> {
    const { data, error } = await supabase
      .from('phase_submissions')
      .select('*')
      .eq('product_id', productId)
      .eq('phase_id', phaseId)
      .maybeSingle();

    if (error) throw error;
    return data;
  }

  async createPhaseSubmission(
    productId: string,
    phaseId: string,
    userId: string,
    formData: Record<string, any>
  ): Promise<PhaseSubmission> {
    const { data, error } = await supabase
      .from('phase_submissions')
      .insert({
        product_id: productId,
        phase_id: phaseId,
        user_id: userId,
        form_data: formData,
        status: 'draft',
      })
      .select()
      .single();

    if (error) throw error;
    return data;
  }

  async updatePhaseSubmission(
    submissionId: string,
    updates: Partial<PhaseSubmission>
  ): Promise<PhaseSubmission> {
    const { data, error } = await supabase
      .from('phase_submissions')
      .update(updates)
      .eq('id', submissionId)
      .select()
      .single();

    if (error) throw error;
    return data;
  }

  async updatePhaseContent(
    submissionId: string,
    generatedContent: string,
    status: PhaseSubmission['status'] = 'completed'
  ): Promise<PhaseSubmission> {
    return this.updatePhaseSubmission(submissionId, {
      generated_content: generatedContent,
      status,
    });
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
  ): Promise<ConversationHistoryEntry> {
    const { data, error } = await supabase
      .from('conversation_history')
      .insert({
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
      })
      .select()
      .single();

    if (error) throw error;
    return data;
  }

  async getConversationHistory(
    sessionId: string,
    options?: {
      productId?: string;
      phaseId?: string;
      limit?: number;
    }
  ): Promise<ConversationHistoryEntry[]> {
    let query = supabase
      .from('conversation_history')
      .select('*')
      .eq('session_id', sessionId);

    if (options?.productId) {
      query = query.eq('product_id', options.productId);
    }

    if (options?.phaseId) {
      query = query.eq('phase_id', options.phaseId);
    }

    query = query.order('created_at', { ascending: true });

    if (options?.limit) {
      query = query.limit(options.limit);
    }

    const { data, error } = await query;

    if (error) throw error;
    return data || [];
  }

  async getProductConversationHistory(
    productId: string
  ): Promise<ConversationHistoryEntry[]> {
    const { data, error } = await supabase
      .from('conversation_history')
      .select('*')
      .eq('product_id', productId)
      .order('created_at', { ascending: true });

    if (error) throw error;
    return data || [];
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
    // Get current version
    const { data: existing } = await supabase
      .from('exported_documents')
      .select('version')
      .eq('product_id', productId)
      .eq('document_type', documentType)
      .order('version', { ascending: false })
      .limit(1)
      .maybeSingle();

    const version = existing ? existing.version + 1 : 1;

    const { data, error } = await supabase
      .from('exported_documents')
      .insert({
        product_id: productId,
        user_id: userId,
        document_type: documentType,
        title,
        content,
        formatted_html: options?.formattedHtml,
        version,
        metadata: options?.metadata || {},
      })
      .select()
      .single();

    if (error) throw error;
    return data;
  }

  async getExportedDocuments(
    productId: string,
    documentType?: ExportedDocument['document_type']
  ): Promise<ExportedDocument[]> {
    let query = supabase
      .from('exported_documents')
      .select('*')
      .eq('product_id', productId);

    if (documentType) {
      query = query.eq('document_type', documentType);
    }

    query = query.order('created_at', { ascending: false });

    const { data, error } = await query;

    if (error) throw error;
    return data || [];
  }

  async getLatestDocument(
    productId: string,
    documentType: ExportedDocument['document_type']
  ): Promise<ExportedDocument | null> {
    const { data, error } = await supabase
      .from('exported_documents')
      .select('*')
      .eq('product_id', productId)
      .eq('document_type', documentType)
      .order('version', { ascending: false })
      .limit(1)
      .maybeSingle();

    if (error) throw error;
    return data;
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
