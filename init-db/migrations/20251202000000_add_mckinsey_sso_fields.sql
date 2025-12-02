-- Migration: Add McKinsey SSO fields to user_profiles
-- Date: 2025-12-02
-- Description: Add columns to support McKinsey Single Sign-On (SSO) authentication
--              using mckinsey.id as the OIDC provider (Keycloak-based)

-- Add McKinsey SSO columns to user_profiles table
-- Core McKinsey SSO fields

-- mckinsey_subject: Unique user identifier from the 'sub' claim in ID token
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS mckinsey_subject VARCHAR(255);
COMMENT ON COLUMN user_profiles.mckinsey_subject IS 'Unique McKinsey user identifier from OIDC sub claim';

-- mckinsey_email: Email address from the ID token
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS mckinsey_email VARCHAR(255);
COMMENT ON COLUMN user_profiles.mckinsey_email IS 'McKinsey email address from OIDC email claim';

-- mckinsey_refresh_token_encrypted: Encrypted refresh token for token refresh
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS mckinsey_refresh_token_encrypted TEXT;
COMMENT ON COLUMN user_profiles.mckinsey_refresh_token_encrypted IS 'Encrypted McKinsey refresh token (Fernet encryption)';

-- mckinsey_token_expires_at: Token expiration timestamp
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS mckinsey_token_expires_at TIMESTAMP;
COMMENT ON COLUMN user_profiles.mckinsey_token_expires_at IS 'McKinsey access token expiration timestamp';

-- McKinsey-specific fields from Keycloak token structure

-- mckinsey_fmno: Firm member number (employee ID)
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS mckinsey_fmno VARCHAR(100);
COMMENT ON COLUMN user_profiles.mckinsey_fmno IS 'McKinsey firm member number (employee ID) from fmno claim';

-- mckinsey_preferred_username: Preferred username from token
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS mckinsey_preferred_username VARCHAR(255);
COMMENT ON COLUMN user_profiles.mckinsey_preferred_username IS 'McKinsey preferred username from preferred_username claim';

-- mckinsey_session_state: Keycloak session state
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS mckinsey_session_state VARCHAR(255);
COMMENT ON COLUMN user_profiles.mckinsey_session_state IS 'Keycloak session state from session_state claim';

-- Create indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_user_profiles_mckinsey_subject 
ON user_profiles(mckinsey_subject) 
WHERE mckinsey_subject IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_user_profiles_mckinsey_email 
ON user_profiles(mckinsey_email) 
WHERE mckinsey_email IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_user_profiles_mckinsey_fmno 
ON user_profiles(mckinsey_fmno) 
WHERE mckinsey_fmno IS NOT NULL;

-- Add index comment
COMMENT ON INDEX idx_user_profiles_mckinsey_subject IS 'Index for McKinsey SSO user lookup by subject (sub claim)';
COMMENT ON INDEX idx_user_profiles_mckinsey_email IS 'Index for McKinsey SSO user lookup by email';
COMMENT ON INDEX idx_user_profiles_mckinsey_fmno IS 'Index for McKinsey SSO user lookup by firm member number';
