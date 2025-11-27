/*
  # Product Lifecycle and Conversation History System

  1. New Tables
    - `product_lifecycle_phases` - Product development phases
    - `phase_submissions` - User inputs for each phase
    - `conversation_history` - Full conversation tracking
    - `exported_documents` - PDF exports and document versions
    
  2. Updates
    - Enhanced conversation tracking
    - Phase-based workflow management
    
  3. Security
    - Enable RLS on all tables
    - Secure policies for authenticated and anonymous users
*/

-- Product Lifecycle Phases (predefined)
CREATE TABLE IF NOT EXISTS product_lifecycle_phases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  phase_name text NOT NULL UNIQUE,
  phase_order integer NOT NULL,
  description text NOT NULL,
  icon text DEFAULT '📋',
  required_fields jsonb DEFAULT '[]',
  template_prompts jsonb DEFAULT '[]',
  created_at timestamptz DEFAULT now()
);

-- User Phase Submissions
CREATE TABLE IF NOT EXISTS phase_submissions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
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

-- Conversation History (comprehensive tracking)
CREATE TABLE IF NOT EXISTS conversation_history (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
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

-- Exported Documents
CREATE TABLE IF NOT EXISTS exported_documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
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

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_phase_submissions_product_id ON phase_submissions(product_id);
CREATE INDEX IF NOT EXISTS idx_phase_submissions_phase_id ON phase_submissions(phase_id);
CREATE INDEX IF NOT EXISTS idx_phase_submissions_user_id ON phase_submissions(user_id);
CREATE INDEX IF NOT EXISTS idx_phase_submissions_status ON phase_submissions(status);
CREATE INDEX IF NOT EXISTS idx_conversation_history_session_id ON conversation_history(session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_history_product_id ON conversation_history(product_id);
CREATE INDEX IF NOT EXISTS idx_conversation_history_phase_id ON conversation_history(phase_id);
CREATE INDEX IF NOT EXISTS idx_conversation_history_created_at ON conversation_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_exported_documents_product_id ON exported_documents(product_id);
CREATE INDEX IF NOT EXISTS idx_exported_documents_user_id ON exported_documents(user_id);

-- Enable RLS
ALTER TABLE product_lifecycle_phases ENABLE ROW LEVEL SECURITY;
ALTER TABLE phase_submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE exported_documents ENABLE ROW LEVEL SECURITY;

-- RLS Policies for product_lifecycle_phases (public read)
CREATE POLICY "Anyone can view lifecycle phases"
  ON product_lifecycle_phases FOR SELECT
  TO public
  USING (true);

-- RLS Policies for phase_submissions
CREATE POLICY "Users can view own phase submissions"
  ON phase_submissions FOR SELECT
  TO authenticated
  USING ((select auth.uid()) = user_id);

CREATE POLICY "Users can create own phase submissions"
  ON phase_submissions FOR INSERT
  TO authenticated
  WITH CHECK ((select auth.uid()) = user_id);

CREATE POLICY "Users can update own phase submissions"
  ON phase_submissions FOR UPDATE
  TO authenticated
  USING ((select auth.uid()) = user_id)
  WITH CHECK ((select auth.uid()) = user_id);

CREATE POLICY "Users can delete own phase submissions"
  ON phase_submissions FOR DELETE
  TO authenticated
  USING ((select auth.uid()) = user_id);

-- Anonymous policies for phase_submissions
CREATE POLICY "Allow anonymous read phase submissions"
  ON phase_submissions FOR SELECT
  TO anon
  USING (true);

CREATE POLICY "Allow anonymous insert phase submissions"
  ON phase_submissions FOR INSERT
  TO anon
  WITH CHECK (true);

CREATE POLICY "Allow anonymous update phase submissions"
  ON phase_submissions FOR UPDATE
  TO anon
  USING (true)
  WITH CHECK (true);

-- RLS Policies for conversation_history
CREATE POLICY "Users can view own conversation history"
  ON conversation_history FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM conversation_sessions
      WHERE conversation_sessions.id = conversation_history.session_id
      AND conversation_sessions.user_id = (select auth.uid())
    )
  );

CREATE POLICY "Users can create own conversation history"
  ON conversation_history FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM conversation_sessions
      WHERE conversation_sessions.id = conversation_history.session_id
      AND conversation_sessions.user_id = (select auth.uid())
    )
  );

-- Anonymous policies for conversation_history
CREATE POLICY "Allow anonymous read conversation history"
  ON conversation_history FOR SELECT
  TO anon
  USING (true);

CREATE POLICY "Allow anonymous insert conversation history"
  ON conversation_history FOR INSERT
  TO anon
  WITH CHECK (true);

-- RLS Policies for exported_documents
CREATE POLICY "Users can view own exported documents"
  ON exported_documents FOR SELECT
  TO authenticated
  USING ((select auth.uid()) = user_id);

CREATE POLICY "Users can create own exported documents"
  ON exported_documents FOR INSERT
  TO authenticated
  WITH CHECK ((select auth.uid()) = user_id);

CREATE POLICY "Users can update own exported documents"
  ON exported_documents FOR UPDATE
  TO authenticated
  USING ((select auth.uid()) = user_id)
  WITH CHECK ((select auth.uid()) = user_id);

CREATE POLICY "Users can delete own exported documents"
  ON exported_documents FOR DELETE
  TO authenticated
  USING ((select auth.uid()) = user_id);

-- Anonymous policies for exported_documents
CREATE POLICY "Allow anonymous read exported documents"
  ON exported_documents FOR SELECT
  TO anon
  USING (true);

CREATE POLICY "Allow anonymous insert exported documents"
  ON exported_documents FOR INSERT
  TO anon
  WITH CHECK (true);

CREATE POLICY "Allow anonymous update exported documents"
  ON exported_documents FOR UPDATE
  TO anon
  USING (true)
  WITH CHECK (true);

-- Add triggers
CREATE TRIGGER update_phase_submissions_updated_at
  BEFORE UPDATE ON phase_submissions
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_exported_documents_updated_at
  BEFORE UPDATE ON exported_documents
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Insert default product lifecycle phases
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

-- Grant permissions
GRANT SELECT ON product_lifecycle_phases TO public;
GRANT SELECT, INSERT, UPDATE, DELETE ON phase_submissions TO authenticated, anon;
GRANT SELECT, INSERT ON conversation_history TO authenticated, anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON exported_documents TO authenticated, anon;
