-- Migration: Fix missing tables and columns
-- Date: 2025-11-26
-- Description: Add missing phase_submissions, conversation_history, conversation_sessions tables
--              and metadata column to user_api_keys

-- 1. Add metadata column to user_api_keys if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_api_keys' AND column_name = 'metadata'
    ) THEN
        ALTER TABLE user_api_keys ADD COLUMN metadata jsonb DEFAULT '{}';
        CREATE INDEX IF NOT EXISTS idx_user_api_keys_metadata ON user_api_keys USING gin(metadata);
    END IF;
END $$;

-- 2. Create conversation_sessions table if it doesn't exist
CREATE TABLE IF NOT EXISTS conversation_sessions (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  product_id uuid REFERENCES products(id) ON DELETE SET NULL,
  tenant_id uuid REFERENCES tenants(id) ON DELETE SET NULL,
  title text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Add tenant_id if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'conversation_sessions' AND column_name = 'tenant_id'
    ) THEN
        ALTER TABLE conversation_sessions ADD COLUMN tenant_id uuid REFERENCES tenants(id) ON DELETE SET NULL;
        -- Set default tenant for existing rows
        UPDATE conversation_sessions SET tenant_id = (SELECT id FROM tenants LIMIT 1) WHERE tenant_id IS NULL;
        CREATE INDEX IF NOT EXISTS idx_conversation_sessions_tenant_id ON conversation_sessions(tenant_id);
    END IF;
END $$;

-- 3. Create phase_submissions table if it doesn't exist
CREATE TABLE IF NOT EXISTS phase_submissions (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  product_id uuid NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  phase_id uuid NOT NULL REFERENCES product_lifecycle_phases(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  tenant_id uuid REFERENCES tenants(id) ON DELETE SET NULL,
  form_data jsonb NOT NULL DEFAULT '{}',
  generated_content text,
  status text DEFAULT 'draft' CHECK (status IN ('draft', 'in_progress', 'completed', 'reviewed')),
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(product_id, phase_id)
);

-- Add tenant_id if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'phase_submissions' AND column_name = 'tenant_id'
    ) THEN
        ALTER TABLE phase_submissions ADD COLUMN tenant_id uuid REFERENCES tenants(id) ON DELETE SET NULL;
        -- Set default tenant for existing rows
        UPDATE phase_submissions SET tenant_id = (SELECT id FROM tenants LIMIT 1) WHERE tenant_id IS NULL;
        CREATE INDEX IF NOT EXISTS idx_phase_submissions_tenant_id ON phase_submissions(tenant_id);
    END IF;
END $$;

-- 4. Create conversation_history table if it doesn't exist
CREATE TABLE IF NOT EXISTS conversation_history (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id uuid NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
  product_id uuid REFERENCES products(id) ON DELETE SET NULL,
  tenant_id uuid REFERENCES tenants(id) ON DELETE SET NULL,
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

-- Add tenant_id if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'conversation_history' AND column_name = 'tenant_id'
    ) THEN
        ALTER TABLE conversation_history ADD COLUMN tenant_id uuid REFERENCES tenants(id) ON DELETE SET NULL;
        -- Set default tenant for existing rows
        UPDATE conversation_history SET tenant_id = (SELECT id FROM tenants LIMIT 1) WHERE tenant_id IS NULL;
        CREATE INDEX IF NOT EXISTS idx_conversation_history_tenant_id ON conversation_history(tenant_id);
    END IF;
END $$;

-- 5. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_phase_submissions_product_id ON phase_submissions(product_id);
CREATE INDEX IF NOT EXISTS idx_phase_submissions_phase_id ON phase_submissions(phase_id);
CREATE INDEX IF NOT EXISTS idx_phase_submissions_user_id ON phase_submissions(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_history_session_id ON conversation_history(session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_history_product_id ON conversation_history(product_id);
CREATE INDEX IF NOT EXISTS idx_conversation_history_created_at ON conversation_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_user_id ON conversation_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_product_id ON conversation_sessions(product_id);

-- 6. Create function for updated_at triggers if it doesn't exist
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 7. Create triggers for updated_at
DROP TRIGGER IF EXISTS update_phase_submissions_updated_at ON phase_submissions;
CREATE TRIGGER update_phase_submissions_updated_at
  BEFORE UPDATE ON phase_submissions
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_conversation_sessions_updated_at ON conversation_sessions;
CREATE TRIGGER update_conversation_sessions_updated_at
  BEFORE UPDATE ON conversation_sessions
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

