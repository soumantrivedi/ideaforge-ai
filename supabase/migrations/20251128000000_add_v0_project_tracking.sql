-- Add V0 project tracking fields to design_mockups table
-- This allows tracking V0 chat_id/project_id and status to prevent duplicate projects

-- Add new columns for V0 project tracking
ALTER TABLE design_mockups 
ADD COLUMN IF NOT EXISTS v0_chat_id text,
ADD COLUMN IF NOT EXISTS v0_project_id text,
ADD COLUMN IF NOT EXISTS project_status text DEFAULT 'pending' CHECK (project_status IN ('pending', 'in_progress', 'completed', 'failed', 'timeout')),
ADD COLUMN IF NOT EXISTS project_url text;

-- Create index for faster lookups by product and status
CREATE INDEX IF NOT EXISTS idx_design_mockups_product_status ON design_mockups(product_id, project_status);
CREATE INDEX IF NOT EXISTS idx_design_mockups_v0_chat_id ON design_mockups(v0_chat_id) WHERE v0_chat_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_design_mockups_user_product ON design_mockups(user_id, product_id);

-- Add comment for documentation
COMMENT ON COLUMN design_mockups.v0_chat_id IS 'V0 API chat_id for tracking and status polling';
COMMENT ON COLUMN design_mockups.v0_project_id IS 'V0 API project_id if different from chat_id';
COMMENT ON COLUMN design_mockups.project_status IS 'Status of prototype generation: pending, in_progress, completed, failed, timeout';
COMMENT ON COLUMN design_mockups.project_url IS 'Main prototype URL (demo_url, web_url, or chat_url)';

