-- Add design_mockups table for storing generated design prototypes
CREATE TABLE IF NOT EXISTS design_mockups (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  product_id uuid NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  phase_submission_id uuid REFERENCES phase_submissions(id) ON DELETE CASCADE,
  user_id uuid NOT NULL,
  provider text NOT NULL CHECK (provider IN ('v0', 'lovable')),
  prompt text NOT NULL,
  image_url text,
  thumbnail_url text,
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_design_mockups_product_id ON design_mockups(product_id);
CREATE INDEX IF NOT EXISTS idx_design_mockups_phase_submission_id ON design_mockups(phase_submission_id);
CREATE INDEX IF NOT EXISTS idx_design_mockups_provider ON design_mockups(provider);

-- Create trigger for updated_at (using existing function)
CREATE TRIGGER update_design_mockups_updated_at
  BEFORE UPDATE ON design_mockups
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Update Design phase to have 3 sections
UPDATE product_lifecycle_phases
SET 
  required_fields = '["user_experience", "v0_lovable_prompts", "design_mockups"]'::jsonb,
  template_prompts = '["Describe the user experience and key user flows", "Generate detailed prompts for V0 and Lovable (with Help with AI)", "View and select design mockups"]'::jsonb
WHERE phase_name = 'Design';

-- Add RLS policies for design_mockups
ALTER TABLE design_mockups ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anonymous access to design_mockups"
  ON design_mockups FOR ALL
  TO anon
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Allow authenticated access to design_mockups"
  ON design_mockups FOR ALL
  TO authenticated
  USING (true)
  WITH CHECK (true);

