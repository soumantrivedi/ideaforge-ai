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
-- 3. USER PREFERENCES TABLE
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
-- 4. PRODUCT SHARES TABLE (for collaboration)
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
-- 5. UPDATE PRODUCTS TABLE
-- ========================================
-- Add tenant_id to products for tenant isolation
ALTER TABLE products 
  ADD COLUMN IF NOT EXISTS tenant_id uuid REFERENCES tenants(id) ON DELETE RESTRICT;

-- Update existing products to have tenant_id (set to default tenant)
DO $$
DECLARE
  default_tenant_id uuid;
BEGIN
  -- Create default tenant if it doesn't exist
  INSERT INTO tenants (id, name, slug, description)
  VALUES ('00000000-0000-0000-0000-000000000001', 'Default Tenant', 'default', 'Default tenant for existing data')
  ON CONFLICT (id) DO NOTHING
  RETURNING id INTO default_tenant_id;
  
  IF default_tenant_id IS NULL THEN
    SELECT id INTO default_tenant_id FROM tenants WHERE slug = 'default';
  END IF;
  
  -- Update existing products
  UPDATE products SET tenant_id = default_tenant_id WHERE tenant_id IS NULL;
  
  -- Update existing users
  UPDATE user_profiles SET tenant_id = default_tenant_id WHERE tenant_id IS NULL;
END $$;

ALTER TABLE products ALTER COLUMN tenant_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_products_tenant_id ON products(tenant_id);

-- ========================================
-- 6. CONVERSATION HISTORY - Add tenant tracking
-- ========================================
ALTER TABLE conversation_history
  ADD COLUMN IF NOT EXISTS tenant_id uuid REFERENCES tenants(id) ON DELETE RESTRICT;

-- Update existing conversation history
UPDATE conversation_history ch
SET tenant_id = (
  SELECT p.tenant_id 
  FROM conversation_sessions cs
  JOIN products p ON cs.product_id = p.id
  WHERE cs.id = ch.session_id
  LIMIT 1
)
WHERE tenant_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_conversation_history_tenant_id ON conversation_history(tenant_id);

-- ========================================
-- 7. PHASE SUBMISSIONS - Add tenant tracking
-- ========================================
ALTER TABLE phase_submissions
  ADD COLUMN IF NOT EXISTS tenant_id uuid REFERENCES tenants(id) ON DELETE RESTRICT;

-- Update existing phase submissions
UPDATE phase_submissions ps
SET tenant_id = (
  SELECT p.tenant_id 
  FROM products p
  WHERE p.id = ps.product_id
  LIMIT 1
)
WHERE tenant_id IS NULL;

ALTER TABLE phase_submissions ALTER COLUMN tenant_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_phase_submissions_tenant_id ON phase_submissions(tenant_id);

-- ========================================
-- 8. DESIGN MOCKUPS - Add tenant tracking
-- ========================================
ALTER TABLE design_mockups
  ADD COLUMN IF NOT EXISTS tenant_id uuid REFERENCES tenants(id) ON DELETE RESTRICT;

-- Update existing design mockups
UPDATE design_mockups dm
SET tenant_id = (
  SELECT p.tenant_id 
  FROM products p
  WHERE p.id = dm.product_id
  LIMIT 1
)
WHERE tenant_id IS NULL;

ALTER TABLE design_mockups ALTER COLUMN tenant_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_design_mockups_tenant_id ON design_mockups(tenant_id);

-- ========================================
-- 9. CREATE DEFAULT TENANTS AND USERS
-- ========================================
-- Create default tenant
INSERT INTO tenants (id, name, slug, description)
VALUES 
  ('00000000-0000-0000-0000-000000000001', 'Default Tenant', 'default', 'Default tenant for existing data'),
  ('00000000-0000-0000-0000-000000000002', 'Acme Corp', 'acme-corp', 'Acme Corporation tenant'),
  ('00000000-0000-0000-0000-000000000003', 'TechStart Inc', 'techstart', 'TechStart Inc tenant')
ON CONFLICT (id) DO NOTHING;

-- Create 10 static users (password is 'password123' for all users)
-- Note: In production, run scripts/generate_password_hash.py to generate proper hashes
-- For now using placeholder - will be updated on first run
-- Password hash for 'password123': Run: python scripts/generate_password_hash.py
INSERT INTO user_profiles (id, email, full_name, tenant_id, password_hash, is_active, persona)
VALUES
  -- Default Tenant Users
  ('00000000-0000-0000-0000-000000000001', 'admin@ideaforge.ai', 'Admin User', '00000000-0000-0000-0000-000000000001', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', true, 'product_manager'),
  ('00000000-0000-0000-0000-000000000002', 'user1@ideaforge.ai', 'User One', '00000000-0000-0000-0000-000000000001', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', true, 'product_manager'),
  ('00000000-0000-0000-0000-000000000003', 'user2@ideaforge.ai', 'User Two', '00000000-0000-0000-0000-000000000001', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', true, 'leadership'),
  
  -- Acme Corp Users
  ('00000000-0000-0000-0000-000000000004', 'alice@acme.com', 'Alice Johnson', '00000000-0000-0000-0000-000000000002', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', true, 'product_manager'),
  ('00000000-0000-0000-0000-000000000005', 'bob@acme.com', 'Bob Smith', '00000000-0000-0000-0000-000000000002', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', true, 'tech_lead'),
  ('00000000-0000-0000-0000-000000000006', 'carol@acme.com', 'Carol Williams', '00000000-0000-0000-0000-000000000002', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', true, 'leadership'),
  
  -- TechStart Inc Users
  ('00000000-0000-0000-0000-000000000007', 'dave@techstart.com', 'Dave Brown', '00000000-0000-0000-0000-000000000003', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', true, 'product_manager'),
  ('00000000-0000-0000-0000-000000000008', 'eve@techstart.com', 'Eve Davis', '00000000-0000-0000-0000-000000000003', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', true, 'product_manager'),
  ('00000000-0000-0000-0000-000000000009', 'frank@techstart.com', 'Frank Miller', '00000000-0000-0000-0000-000000000003', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', true, 'tech_lead'),
  ('00000000-0000-0000-0000-000000000010', 'grace@techstart.com', 'Grace Wilson', '00000000-0000-0000-0000-000000000003', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', true, 'leadership')
ON CONFLICT (id) DO NOTHING;

-- Create default preferences for users
INSERT INTO user_preferences (user_id, theme, language, notifications_enabled)
SELECT id, 'light', 'en', true
FROM user_profiles
WHERE id NOT IN (SELECT user_id FROM user_preferences)
ON CONFLICT (user_id) DO NOTHING;

-- ========================================
-- 10. ROW LEVEL SECURITY POLICIES
-- ========================================

-- TENANTS: Users can only view their own tenant
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own tenant"
  ON tenants FOR SELECT
  TO anon, authenticated
  USING (
    id IN (
      SELECT tenant_id FROM user_profiles 
      WHERE id = current_setting('app.current_user_id', true)::uuid
    )
  );

-- USER_PROFILES: Users can view users in same tenant
DROP POLICY IF EXISTS "Users can view own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can insert own profile" ON user_profiles;
DROP POLICY IF EXISTS "Allow anonymous access to user_profiles" ON user_profiles;

CREATE POLICY "Users can view same tenant profiles"
  ON user_profiles FOR SELECT
  TO anon, authenticated
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles 
      WHERE id = current_setting('app.current_user_id', true)::uuid
    )
  );

CREATE POLICY "Users can update own profile"
  ON user_profiles FOR UPDATE
  TO anon, authenticated
  USING (id = current_setting('app.current_user_id', true)::uuid)
  WITH CHECK (id = current_setting('app.current_user_id', true)::uuid);

-- PRODUCTS: Tenant isolation + sharing
DROP POLICY IF EXISTS "Users can view own products" ON products;
DROP POLICY IF EXISTS "Users can create own products" ON products;
DROP POLICY IF EXISTS "Users can update own products" ON products;
DROP POLICY IF EXISTS "Users can delete own products" ON products;
DROP POLICY IF EXISTS "Allow anonymous access to products" ON products;

CREATE POLICY "Users can view tenant products"
  ON products FOR SELECT
  TO anon, authenticated
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles 
      WHERE id = current_setting('app.current_user_id', true)::uuid
    )
    AND (
      user_id = current_setting('app.current_user_id', true)::uuid
      OR id IN (
        SELECT product_id FROM product_shares 
        WHERE shared_with_user_id = current_setting('app.current_user_id', true)::uuid
      )
    )
  );

CREATE POLICY "Users can create products in own tenant"
  ON products FOR INSERT
  TO anon, authenticated
  WITH CHECK (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles 
      WHERE id = current_setting('app.current_user_id', true)::uuid
    )
    AND user_id = current_setting('app.current_user_id', true)::uuid
  );

CREATE POLICY "Users can update own or shared products"
  ON products FOR UPDATE
  TO anon, authenticated
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles 
      WHERE id = current_setting('app.current_user_id', true)::uuid
    )
    AND (
      user_id = current_setting('app.current_user_id', true)::uuid
      OR id IN (
        SELECT product_id FROM product_shares 
        WHERE shared_with_user_id = current_setting('app.current_user_id', true)::uuid
        AND permission IN ('edit', 'admin')
      )
    )
  )
  WITH CHECK (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles 
      WHERE id = current_setting('app.current_user_id', true)::uuid
    )
  );

-- PRODUCT_SHARES: Tenant isolation
ALTER TABLE product_shares ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view shares in same tenant"
  ON product_shares FOR SELECT
  TO anon, authenticated
  USING (
    product_id IN (
      SELECT p.id FROM products p
      JOIN user_profiles up ON p.tenant_id = up.tenant_id
      WHERE up.id = current_setting('app.current_user_id', true)::uuid
    )
  );

CREATE POLICY "Users can create shares within tenant"
  ON product_shares FOR INSERT
  TO anon, authenticated
  WITH CHECK (
    product_id IN (
      SELECT id FROM products 
      WHERE user_id = current_setting('app.current_user_id', true)::uuid
      AND tenant_id IN (
        SELECT tenant_id FROM user_profiles 
        WHERE id = current_setting('app.current_user_id', true)::uuid
      )
    )
    AND shared_with_user_id IN (
      SELECT id FROM user_profiles 
      WHERE tenant_id IN (
        SELECT tenant_id FROM user_profiles 
        WHERE id = current_setting('app.current_user_id', true)::uuid
      )
    )
  );

-- USER_PREFERENCES: Users can only access own preferences
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own preferences"
  ON user_preferences FOR SELECT
  TO anon, authenticated
  USING (user_id = current_setting('app.current_user_id', true)::uuid);

CREATE POLICY "Users can update own preferences"
  ON user_preferences FOR UPDATE
  TO anon, authenticated
  USING (user_id = current_setting('app.current_user_id', true)::uuid)
  WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);

CREATE POLICY "Users can insert own preferences"
  ON user_preferences FOR INSERT
  TO anon, authenticated
  WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);

-- ========================================
-- 11. HELPER FUNCTIONS
-- ========================================

-- Function to get current user's tenant_id
CREATE OR REPLACE FUNCTION get_current_user_tenant_id()
RETURNS uuid AS $$
BEGIN
  RETURN (
    SELECT tenant_id FROM user_profiles 
    WHERE id = current_setting('app.current_user_id', true)::uuid
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to check if user can access product
CREATE OR REPLACE FUNCTION can_user_access_product(product_uuid uuid, user_uuid uuid)
RETURNS boolean AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM products p
    WHERE p.id = product_uuid
    AND (
      p.user_id = user_uuid
      OR p.id IN (
        SELECT product_id FROM product_shares 
        WHERE shared_with_user_id = user_uuid
      )
    )
    AND p.tenant_id = (
      SELECT tenant_id FROM user_profiles WHERE id = user_uuid
    )
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ========================================
-- 12. TRIGGERS
-- ========================================

-- Update triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_tenants_updated_at
  BEFORE UPDATE ON tenants
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_product_shares_updated_at
  BEFORE UPDATE ON product_shares
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_preferences_updated_at
  BEFORE UPDATE ON user_preferences
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

