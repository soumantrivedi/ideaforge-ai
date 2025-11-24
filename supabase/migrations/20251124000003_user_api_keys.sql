-- User API Keys Migration
-- Store user-specific API keys securely in the database with encryption

CREATE TABLE IF NOT EXISTS user_api_keys (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  provider text NOT NULL CHECK (provider IN ('openai', 'anthropic', 'google', 'v0', 'lovable')),
  api_key_encrypted text NOT NULL,
  is_active boolean DEFAULT true,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(user_id, provider)
);

CREATE INDEX IF NOT EXISTS idx_user_api_keys_user_id ON user_api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_user_api_keys_provider ON user_api_keys(provider);

-- Update trigger for updated_at
CREATE OR REPLACE FUNCTION update_user_api_keys_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_user_api_keys_updated_at
  BEFORE UPDATE ON user_api_keys
  FOR EACH ROW
  EXECUTE FUNCTION update_user_api_keys_updated_at();

-- RLS Policies
ALTER TABLE user_api_keys ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "user_api_keys_select" ON user_api_keys;
DROP POLICY IF EXISTS "user_api_keys_insert" ON user_api_keys;
DROP POLICY IF EXISTS "user_api_keys_update" ON user_api_keys;
DROP POLICY IF EXISTS "user_api_keys_delete" ON user_api_keys;

CREATE POLICY "user_api_keys_select" ON user_api_keys
  FOR SELECT
  USING (
    user_id = (SELECT id FROM user_profiles WHERE id = current_setting('app.current_user_id', true)::uuid)
  );

CREATE POLICY "user_api_keys_insert" ON user_api_keys
  FOR INSERT
  WITH CHECK (
    user_id = (SELECT id FROM user_profiles WHERE id = current_setting('app.current_user_id', true)::uuid)
  );

CREATE POLICY "user_api_keys_update" ON user_api_keys
  FOR UPDATE
  USING (
    user_id = (SELECT id FROM user_profiles WHERE id = current_setting('app.current_user_id', true)::uuid)
  );

CREATE POLICY "user_api_keys_delete" ON user_api_keys
  FOR DELETE
  USING (
    user_id = (SELECT id FROM user_profiles WHERE id = current_setting('app.current_user_id', true)::uuid)
  );

