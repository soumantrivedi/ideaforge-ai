-- Add AI Gateway provider support to user_api_keys table
-- AI Gateway uses service account credentials (client_id and client_secret)
-- We'll store client_id in api_key_encrypted and client_secret in metadata

-- Update the provider check constraint to include 'ai_gateway'
ALTER TABLE user_api_keys 
DROP CONSTRAINT IF EXISTS user_api_keys_provider_check;

ALTER TABLE user_api_keys
ADD CONSTRAINT user_api_keys_provider_check 
CHECK (provider IN ('openai', 'anthropic', 'google', 'v0', 'lovable', 'github', 'atlassian', 'ai_gateway'));

-- Add comment explaining AI Gateway storage format
COMMENT ON COLUMN user_api_keys.api_key_encrypted IS 
'For AI Gateway: stores encrypted client_id. client_secret is stored in metadata.client_secret';

COMMENT ON COLUMN user_api_keys.metadata IS 
'For AI Gateway: stores JSON with client_secret and optionally base_url, default_model';

