import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase environment variables');
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

export interface Project {
  id: string;
  user_id?: string;
  title: string;
  description: string;
  status: 'draft' | 'researching' | 'analyzing' | 'writing' | 'completed';
  created_at: string;
  updated_at: string;
}

export interface AgentInteraction {
  id: string;
  project_id: string;
  agent_name: 'research' | 'analysis' | 'prd_writer' | 'validator';
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  error?: string;
  created_at: string;
  completed_at?: string;
}

export interface PRD {
  id: string;
  project_id: string;
  content: Record<string, unknown>;
  version: number;
  is_current: boolean;
  created_at: string;
}

export interface MarketResearch {
  id: string;
  project_id: string;
  research_type: 'competitor' | 'market_trend' | 'user_need' | 'technology';
  findings: Record<string, unknown>;
  sources: string[];
  created_at: string;
}
