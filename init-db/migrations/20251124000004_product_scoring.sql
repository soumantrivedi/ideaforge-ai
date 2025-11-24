-- Product Idea Scoring and Multi-Session Support
-- Migration: 20251124000004

-- Product Idea Scores Table
CREATE TABLE IF NOT EXISTS product_idea_scores (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  product_id uuid NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  tenant_id uuid, -- For tenant-level visibility
  overall_score numeric(5,2) CHECK (overall_score >= 0 AND overall_score <= 100),
  success_probability numeric(5,2) CHECK (success_probability >= 0 AND success_probability <= 100),
  scoring_data jsonb NOT NULL DEFAULT '{}', -- Full scoring breakdown
  recommendations jsonb DEFAULT '[]', -- Array of recommendations
  success_factors jsonb DEFAULT '[]', -- Array of success factors
  risk_factors jsonb DEFAULT '[]', -- Array of risk factors
  scoring_criteria jsonb DEFAULT '{}', -- Criteria used for scoring
  created_by uuid REFERENCES user_profiles(id) ON DELETE SET NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(product_id, created_at) -- One score per product per timestamp
);

-- Index for tenant-level queries
CREATE INDEX IF NOT EXISTS idx_product_idea_scores_tenant ON product_idea_scores(tenant_id);
CREATE INDEX IF NOT EXISTS idx_product_idea_scores_product ON product_idea_scores(product_id);
CREATE INDEX IF NOT EXISTS idx_product_idea_scores_created_at ON product_idea_scores(created_at DESC);

-- Product Summaries Table (from multiple sessions)
CREATE TABLE IF NOT EXISTS product_summaries (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  product_id uuid NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  tenant_id uuid, -- For tenant-level visibility
  summary_type text DEFAULT 'multi_session' CHECK (summary_type IN ('single_session', 'multi_session', 'product_overview')),
  session_ids uuid[] DEFAULT '{}', -- Array of session IDs included
  summary_content text NOT NULL,
  summary_metadata jsonb DEFAULT '{}', -- Participants, dates, etc.
  created_by uuid REFERENCES user_profiles(id) ON DELETE SET NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Index for tenant-level queries
CREATE INDEX IF NOT EXISTS idx_product_summaries_tenant ON product_summaries(tenant_id);
CREATE INDEX IF NOT EXISTS idx_product_summaries_product ON product_summaries(product_id);
CREATE INDEX IF NOT EXISTS idx_product_summaries_session_ids ON product_summaries USING GIN(session_ids);

-- Product PRD Documents (enhanced with industry standards)
CREATE TABLE IF NOT EXISTS product_prd_documents (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  product_id uuid NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  tenant_id uuid,
  version integer DEFAULT 1,
  prd_template text DEFAULT 'industry_standard', -- Template used
  standards jsonb DEFAULT '["BCS", "ICAgile", "AIPMM", "Pragmatic Institute"]',
  prd_content jsonb NOT NULL DEFAULT '{}', -- Structured PRD content
  summary_id uuid REFERENCES product_summaries(id) ON DELETE SET NULL,
  score_id uuid REFERENCES product_idea_scores(id) ON DELETE SET NULL,
  status text DEFAULT 'draft' CHECK (status IN ('draft', 'in_review', 'approved', 'published')),
  created_by uuid REFERENCES user_profiles(id) ON DELETE SET NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Index for tenant-level queries
CREATE INDEX IF NOT EXISTS idx_product_prd_documents_tenant ON product_prd_documents(tenant_id);
CREATE INDEX IF NOT EXISTS idx_product_prd_documents_product ON product_prd_documents(product_id);

-- Session Selection Tracking (for multi-user collaboration)
CREATE TABLE IF NOT EXISTS session_selections (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  product_id uuid NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  selected_session_ids uuid[] NOT NULL DEFAULT '{}',
  selection_purpose text, -- e.g., 'summary', 'scoring', 'prd_generation'
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_session_selections_product ON session_selections(product_id);
CREATE INDEX IF NOT EXISTS idx_session_selections_user ON session_selections(user_id);

-- Add tenant_id to products table if not exists
DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'products' AND column_name = 'tenant_id'
  ) THEN
    ALTER TABLE products ADD COLUMN tenant_id uuid;
    CREATE INDEX IF NOT EXISTS idx_products_tenant ON products(tenant_id);
  END IF;
END $$;

-- Add tenant_id to conversation_sessions if not exists
DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'conversation_sessions' AND column_name = 'tenant_id'
  ) THEN
    ALTER TABLE conversation_sessions ADD COLUMN tenant_id uuid;
    CREATE INDEX IF NOT EXISTS idx_conversation_sessions_tenant ON conversation_sessions(tenant_id);
  END IF;
END $$;

-- Comments for documentation
COMMENT ON TABLE product_idea_scores IS 'Stores product idea scores with detailed breakdown following industry standards';
COMMENT ON TABLE product_summaries IS 'Stores summaries from single or multiple conversation sessions';
COMMENT ON TABLE product_prd_documents IS 'Stores PRD documents following industry-standard templates';
COMMENT ON TABLE session_selections IS 'Tracks which sessions users select for multi-session operations';

