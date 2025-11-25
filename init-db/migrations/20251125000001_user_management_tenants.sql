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
-- 3. PRODUCT SHARES TABLE (for collaboration)
-- ========================================
CREATE TABLE IF NOT EXISTS product_shares (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  product_id uuid NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  shared_with_user_id uuid NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  shared_by_user_id uuid NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  permission text DEFAULT 'view' CHECK (permission IN ('view', 'edit', 'admin')),
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(product_id, shared_with_user_id)
);

CREATE INDEX IF NOT EXISTS idx_product_shares_product_id ON product_shares(product_id);
CREATE INDEX IF NOT EXISTS idx_product_shares_shared_with_user_id ON product_shares(shared_with_user_id);
CREATE INDEX IF NOT EXISTS idx_product_shares_shared_by_user_id ON product_shares(shared_by_user_id);

-- ========================================
-- 4. UPDATE PRODUCTS TABLE
-- ========================================
-- Add tenant_id to products for tenant isolation
ALTER TABLE products 
  ADD COLUMN IF NOT EXISTS tenant_id uuid REFERENCES tenants(id) ON DELETE RESTRICT;

-- Update existing products to have tenant_id (set to default tenant)
DO $$
DECLARE
  default_tenant_id uuid;
BEGIN
  -- Get default tenant ID
  SELECT id INTO default_tenant_id FROM tenants WHERE slug = 'default' LIMIT 1;
  
  -- Update existing products
  UPDATE products SET tenant_id = default_tenant_id WHERE tenant_id IS NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_products_tenant_id ON products(tenant_id);

-- ========================================
-- 5. CREATE DEFAULT TENANTS AND USERS
-- ========================================
-- Create default tenant
INSERT INTO tenants (id, name, slug, description)
VALUES 
  ('00000000-0000-0000-0000-000000000001', 'Default Tenant', 'default', 'Default tenant for existing data')
ON CONFLICT (id) DO NOTHING;

-- Create default admin user (password is 'password123')
-- Password hash generated with: python3 -c "import bcrypt; password = 'password123'.encode('utf-8'); salt = bcrypt.gensalt(rounds=12); hashed = bcrypt.hashpw(password, salt); print(hashed.decode('utf-8'))"
-- Note: Each hash is unique due to salt, but any valid bcrypt hash for 'password123' will work
INSERT INTO user_profiles (id, email, full_name, tenant_id, password_hash, is_active, persona)
VALUES
  ('00000000-0000-0000-0000-000000000001', 'admin@ideaforge.ai', 'Admin User', '00000000-0000-0000-0000-000000000001', '$2b$12$eTMKjfsd8Hi2uERGM8/LZed4I0LlacMvnLx/9Xg9Mbu8NYqfaGNo.', true, 'product_manager')
ON CONFLICT (id) DO UPDATE SET
  tenant_id = EXCLUDED.tenant_id,
  password_hash = EXCLUDED.password_hash,
  is_active = EXCLUDED.is_active;

-- Update existing users to have default tenant if they don't have one
UPDATE user_profiles 
SET tenant_id = '00000000-0000-0000-0000-000000000001'
WHERE tenant_id IS NULL;

-- ========================================
-- 6. USER PREFERENCES TABLE
-- ========================================
CREATE TABLE IF NOT EXISTS user_preferences (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL UNIQUE REFERENCES user_profiles(id) ON DELETE CASCADE,
  theme text DEFAULT 'light' CHECK (theme IN ('light', 'dark', 'retro')),
  language text DEFAULT 'en',
  notifications_enabled boolean DEFAULT true,
  email_notifications boolean DEFAULT false,
  preferences jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);

-- ========================================
-- 7. UPDATE CONVERSATION_HISTORY TABLE
-- ========================================
-- Add tenant_id to conversation_history for tenant isolation
ALTER TABLE conversation_history
  ADD COLUMN IF NOT EXISTS tenant_id uuid REFERENCES tenants(id) ON DELETE RESTRICT;

-- Update existing conversation_history to have default tenant
UPDATE conversation_history 
SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default' LIMIT 1)
WHERE tenant_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_conversation_history_tenant_id ON conversation_history(tenant_id);

-- ========================================
-- 8. UPDATE PHASE_SUBMISSIONS TABLE
-- ========================================
-- Add tenant_id to phase_submissions for tenant isolation
ALTER TABLE phase_submissions
  ADD COLUMN IF NOT EXISTS tenant_id uuid REFERENCES tenants(id) ON DELETE RESTRICT;

-- Update existing phase_submissions to have default tenant
UPDATE phase_submissions 
SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default' LIMIT 1)
WHERE tenant_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_phase_submissions_tenant_id ON phase_submissions(tenant_id);

