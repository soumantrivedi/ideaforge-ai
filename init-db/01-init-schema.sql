-- Initialize database schema for IdeaForge AI
-- This script runs automatically when the PostgreSQL container is first created

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- User Profiles Table (simplified - no auth.users dependency)
CREATE TABLE IF NOT EXISTS user_profiles (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  email text UNIQUE NOT NULL,
  full_name text,
  persona text DEFAULT 'product_manager' CHECK (persona IN ('product_manager', 'leadership', 'tech_lead')),
  preferences jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Products Table
CREATE TABLE IF NOT EXISTS products (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  name text NOT NULL,
  description text,
  status text DEFAULT 'ideation' CHECK (status IN ('ideation', 'build', 'operate', 'learn', 'govern', 'sunset')),
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- PRD Documents Table
CREATE TABLE IF NOT EXISTS prd_documents (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  product_id uuid NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  title text NOT NULL,
  content jsonb NOT NULL DEFAULT '{}',
  version integer DEFAULT 1,
  status text DEFAULT 'draft' CHECK (status IN ('draft', 'in_review', 'approved', 'published')),
  created_by uuid NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Conversation Sessions Table
CREATE TABLE IF NOT EXISTS conversation_sessions (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  product_id uuid REFERENCES products(id) ON DELETE SET NULL,
  title text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Agent Messages Table
CREATE TABLE IF NOT EXISTS agent_messages (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id uuid NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
  role text NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content text NOT NULL,
  agent_role text,
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now()
);

-- Knowledge Articles Table (with vector embeddings)
CREATE TABLE IF NOT EXISTS knowledge_articles (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  product_id uuid NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  title text NOT NULL,
  content text NOT NULL,
  source text NOT NULL,
  embedding vector(1536),
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now()
);

-- Agent Activity Log Table
CREATE TABLE IF NOT EXISTS agent_activity_log (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  product_id uuid REFERENCES products(id) ON DELETE SET NULL,
  agent_type text NOT NULL,
  action text NOT NULL,
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now()
);

-- Feedback Entries Table
CREATE TABLE IF NOT EXISTS feedback_entries (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  product_id uuid NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  agent_type text NOT NULL,
  user_feedback text NOT NULL,
  rating integer CHECK (rating >= 1 AND rating <= 5),
  context jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now()
);

-- Product Lifecycle Phases Table
CREATE TABLE IF NOT EXISTS product_lifecycle_phases (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  phase_name text NOT NULL UNIQUE,
  phase_order integer NOT NULL,
  description text NOT NULL,
  icon text DEFAULT '📋',
  required_fields jsonb DEFAULT '[]',
  template_prompts jsonb DEFAULT '[]',
  created_at timestamptz DEFAULT now()
);

-- Phase Submissions Table
CREATE TABLE IF NOT EXISTS phase_submissions (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  product_id uuid NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  phase_id uuid NOT NULL REFERENCES product_lifecycle_phases(id) ON DELETE CASCADE,
  user_id uuid NOT NULL,
  form_data jsonb NOT NULL DEFAULT '{}',
  generated_content text,
  status text DEFAULT 'draft' CHECK (status IN ('draft', 'in_progress', 'completed', 'reviewed')),
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(product_id, phase_id)
);

-- Conversation History Table
CREATE TABLE IF NOT EXISTS conversation_history (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id uuid NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
  product_id uuid REFERENCES products(id) ON DELETE SET NULL,
  phase_id uuid REFERENCES product_lifecycle_phases(id) ON DELETE SET NULL,
  message_type text NOT NULL CHECK (message_type IN ('user', 'agent', 'system')),
  agent_name text,
  agent_role text,
  content text NOT NULL,
  formatted_content text,
  parent_message_id uuid REFERENCES conversation_history(id) ON DELETE SET NULL,
  interaction_metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now()
);

-- Exported Documents Table
CREATE TABLE IF NOT EXISTS exported_documents (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  product_id uuid NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  user_id uuid NOT NULL,
  document_type text NOT NULL CHECK (document_type IN ('prd', 'summary', 'full_lifecycle', 'phase_report')),
  title text NOT NULL,
  content text NOT NULL,
  formatted_html text,
  pdf_url text,
  version integer DEFAULT 1,
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_products_user_id ON products(user_id);
CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);
CREATE INDEX IF NOT EXISTS idx_prd_documents_product_id ON prd_documents(product_id);
CREATE INDEX IF NOT EXISTS idx_agent_messages_session_id ON agent_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_articles_product_id ON knowledge_articles(product_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_articles_embedding ON knowledge_articles USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_phase_submissions_product_id ON phase_submissions(product_id);
CREATE INDEX IF NOT EXISTS idx_phase_submissions_phase_id ON phase_submissions(phase_id);
CREATE INDEX IF NOT EXISTS idx_conversation_history_session_id ON conversation_history(session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_history_product_id ON conversation_history(product_id);
CREATE INDEX IF NOT EXISTS idx_conversation_history_created_at ON conversation_history(created_at DESC);

-- Create function for vector similarity search
CREATE OR REPLACE FUNCTION search_knowledge_articles(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.7,
  match_count int DEFAULT 5,
  filter_product_id uuid DEFAULT NULL
)
RETURNS TABLE (
  id uuid,
  product_id uuid,
  title text,
  content text,
  source text,
  metadata jsonb,
  created_at timestamptz,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    ka.id,
    ka.product_id,
    ka.title,
    ka.content,
    ka.source,
    ka.metadata,
    ka.created_at,
    1 - (ka.embedding <=> query_embedding) AS similarity
  FROM knowledge_articles ka
  WHERE 
    (filter_product_id IS NULL OR ka.product_id = filter_product_id)
    AND ka.embedding IS NOT NULL
    AND 1 - (ka.embedding <=> query_embedding) > match_threshold
  ORDER BY ka.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Insert default lifecycle phases
INSERT INTO product_lifecycle_phases (phase_name, phase_order, description, icon, required_fields, template_prompts)
VALUES
  ('Ideation', 1, 'Initial product concept and idea generation', '💡', 
   '["problem_statement", "target_audience", "value_proposition"]'::jsonb,
   '["What problem are you solving?", "Who is your target customer?", "What makes your solution unique?"]'::jsonb),
  
  ('Market Research', 2, 'Competitive analysis and market validation', '🔍',
   '["market_size", "competitors", "market_trends"]'::jsonb,
   '["What is the market size?", "Who are your main competitors?", "What are current market trends?"]'::jsonb),
  
  ('Requirements', 3, 'Define product requirements and specifications', '📋',
   '["functional_requirements", "non_functional_requirements", "constraints"]'::jsonb,
   '["What are the core features?", "What are the performance requirements?", "What are the constraints?"]'::jsonb),
  
  ('Design', 4, 'Product design and architecture planning', '🎨',
   '["user_experience", "technical_architecture", "design_mockups"]'::jsonb,
   '["Describe the user experience", "What is the technical architecture?", "Share design mockups"]'::jsonb),
  
  ('Development Planning', 5, 'Development roadmap and sprint planning', '⚙️',
   '["milestones", "timeline", "resources"]'::jsonb,
   '["What are the key milestones?", "What is the timeline?", "What resources are needed?"]'::jsonb),
  
  ('Go-to-Market', 6, 'Launch strategy and marketing plan', '🚀',
   '["launch_strategy", "marketing_channels", "success_metrics"]'::jsonb,
   '["What is your launch strategy?", "Which marketing channels?", "How do you measure success?"]'::jsonb)
ON CONFLICT (phase_name) DO NOTHING;

-- Create default user profile for anonymous access
INSERT INTO user_profiles (id, email, full_name, persona)
VALUES ('00000000-0000-0000-0000-000000000000', 'anonymous@ideaforge.ai', 'Anonymous User', 'product_manager')
ON CONFLICT (id) DO NOTHING;

