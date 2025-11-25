-- User Management and Tenant System Migration
-- This migration adds tenant-based multi-user support with authentication

-- ========================================
-- 1. TENANTS TABLE
-- ========================================
CREATE TABLE IF NOT EXISTS tenants (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  name text NOT NULL UNIQUE,
  slug text NOT NULL UNIQUE,
  description text,
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tenants_slug ON tenants(slug);

-- ========================================
-- 2. UPDATE USER_PROFILES TABLE
-- ========================================
-- Add authentication fields and tenant_id
ALTER TABLE user_profiles 
  ADD COLUMN IF NOT EXISTS password_hash text,
  ADD COLUMN IF NOT EXISTS tenant_id uuid REFERENCES tenants(id) ON DELETE RESTRICT,
  ADD COLUMN IF NOT EXISTS is_active boolean DEFAULT true,
  ADD COLUMN IF NOT EXISTS last_login_at timestamptz,
  ADD COLUMN IF NOT EXISTS auth_provider text DEFAULT 'local' CHECK (auth_provider IN ('local', 'github', 'okta', 'oauth')),
  ADD COLUMN IF NOT EXISTS external_id text, -- For OAuth providers
  ADD COLUMN IF NOT EXISTS avatar_url text;

CREATE INDEX IF NOT EXISTS idx_user_profiles_tenant_id ON user_profiles(tenant_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON user_profiles(email);
CREATE INDEX IF NOT EXISTS idx_user_profiles_external_id ON user_profiles(external_id) WHERE external_id IS NOT NULL;

-- ========================================
-- 3. CREATE DEFAULT TENANTS AND USERS
-- ========================================
-- Create default tenant
INSERT INTO tenants (id, name, slug, description)
VALUES 
  ('00000000-0000-0000-0000-000000000001', 'Default Tenant', 'default', 'Default tenant for existing data')
ON CONFLICT (id) DO NOTHING;

-- Create default admin user (password is 'password123')
-- Password hash for 'password123': $2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW
INSERT INTO user_profiles (id, email, full_name, tenant_id, password_hash, is_active, persona)
VALUES
  ('00000000-0000-0000-0000-000000000001', 'admin@ideaforge.ai', 'Admin User', '00000000-0000-0000-0000-000000000001', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', true, 'product_manager')
ON CONFLICT (id) DO UPDATE SET
  tenant_id = EXCLUDED.tenant_id,
  password_hash = EXCLUDED.password_hash,
  is_active = EXCLUDED.is_active;

-- Update existing users to have default tenant if they don't have one
UPDATE user_profiles 
SET tenant_id = '00000000-0000-0000-0000-000000000001'
WHERE tenant_id IS NULL;

