/*
  # Review Reports Table
  
  Stores review agent reports for products with phase scores and recommendations.
  Allows users to track progress and quality across all lifecycle phases.
*/

CREATE TABLE IF NOT EXISTS review_reports (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  user_id uuid NOT NULL,
  overall_score integer CHECK (overall_score >= 0 AND overall_score <= 100),
  status text DEFAULT 'ready' CHECK (status IN ('ready', 'needs_attention', 'in_progress')),
  phase_scores jsonb DEFAULT '[]', -- Array of {phase_name, phase_id, score, status}
  missing_sections jsonb DEFAULT '[]', -- Array of missing sections with recommendations
  recommendations jsonb DEFAULT '[]', -- General recommendations
  summary text,
  report_data jsonb DEFAULT '{}', -- Full report data from review agent
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(product_id, user_id) -- One report per product per user (latest)
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_review_reports_product_id ON review_reports(product_id);
CREATE INDEX IF NOT EXISTS idx_review_reports_user_id ON review_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_review_reports_created_at ON review_reports(created_at DESC);

-- Enable RLS
ALTER TABLE review_reports ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view their own reports
CREATE POLICY "Users can view their own review reports"
  ON review_reports
  FOR SELECT
  USING (auth.uid() = user_id);

-- Policy: Users can create their own reports
CREATE POLICY "Users can create their own review reports"
  ON review_reports
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Policy: Users can update their own reports
CREATE POLICY "Users can update their own review reports"
  ON review_reports
  FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Policy: Users can delete their own reports
CREATE POLICY "Users can delete their own review reports"
  ON review_reports
  FOR DELETE
  USING (auth.uid() = user_id);

