-- Fix RLS Policies: Remove role references (policies apply to all users)
-- This migration fixes policies that reference non-existent 'anon' and 'authenticated' roles
-- by removing the role specification (policies will apply to all users)

-- ========================================
-- TENANTS POLICIES
-- ========================================
DROP POLICY IF EXISTS "Users can view own tenant" ON tenants;
CREATE POLICY "Users can view own tenant"
  ON tenants FOR SELECT
  USING (
    id IN (
      SELECT tenant_id FROM user_profiles 
      WHERE id = current_setting('app.current_user_id', true)::uuid
    )
  );

-- ========================================
-- USER_PROFILES POLICIES
-- ========================================
DROP POLICY IF EXISTS "Users can view same tenant profiles" ON user_profiles;
CREATE POLICY "Users can view same tenant profiles"
  ON user_profiles FOR SELECT
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles 
      WHERE id = current_setting('app.current_user_id', true)::uuid
    )
  );

DROP POLICY IF EXISTS "Users can update own profile" ON user_profiles;
CREATE POLICY "Users can update own profile"
  ON user_profiles FOR UPDATE
  USING (id = current_setting('app.current_user_id', true)::uuid)
  WITH CHECK (id = current_setting('app.current_user_id', true)::uuid);

-- ========================================
-- PRODUCTS POLICIES
-- ========================================
DROP POLICY IF EXISTS "Users can view tenant products" ON products;
CREATE POLICY "Users can view tenant products"
  ON products FOR SELECT
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

DROP POLICY IF EXISTS "Users can create products in own tenant" ON products;
CREATE POLICY "Users can create products in own tenant"
  ON products FOR INSERT
  WITH CHECK (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles 
      WHERE id = current_setting('app.current_user_id', true)::uuid
    )
    AND user_id = current_setting('app.current_user_id', true)::uuid
  );

DROP POLICY IF EXISTS "Users can update own or shared products" ON products;
CREATE POLICY "Users can update own or shared products"
  ON products FOR UPDATE
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
    AND (
      user_id = current_setting('app.current_user_id', true)::uuid
      OR id IN (
        SELECT product_id FROM product_shares 
        WHERE shared_with_user_id = current_setting('app.current_user_id', true)::uuid
        AND permission IN ('edit', 'admin')
      )
    )
  );

DROP POLICY IF EXISTS "Users can delete own products" ON products;
CREATE POLICY "Users can delete own products"
  ON products FOR DELETE
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles 
      WHERE id = current_setting('app.current_user_id', true)::uuid
    )
    AND user_id = current_setting('app.current_user_id', true)::uuid
  );

-- ========================================
-- PRODUCT_SHARES POLICIES
-- ========================================
DROP POLICY IF EXISTS "Users can view shares for accessible products" ON product_shares;
CREATE POLICY "Users can view shares for accessible products"
  ON product_shares FOR SELECT
  USING (
    product_id IN (
      SELECT id FROM products 
      WHERE tenant_id IN (
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
    )
  );

DROP POLICY IF EXISTS "Users can create shares within tenant" ON product_shares;
CREATE POLICY "Users can create shares within tenant"
  ON product_shares FOR INSERT
  WITH CHECK (
    product_id IN (
      SELECT id FROM products 
      WHERE tenant_id IN (
        SELECT tenant_id FROM user_profiles 
        WHERE id = current_setting('app.current_user_id', true)::uuid
      )
      AND user_id = current_setting('app.current_user_id', true)::uuid
    )
    AND shared_with_user_id IN (
      SELECT id FROM user_profiles 
      WHERE tenant_id IN (
        SELECT tenant_id FROM user_profiles 
        WHERE id = current_setting('app.current_user_id', true)::uuid
      )
    )
  );

DROP POLICY IF EXISTS "Users can delete own shares" ON product_shares;
CREATE POLICY "Users can delete own shares"
  ON product_shares FOR DELETE
  USING (
    product_id IN (
      SELECT id FROM products 
      WHERE user_id = current_setting('app.current_user_id', true)::uuid
    )
  );

-- ========================================
-- PHASE_SUBMISSIONS POLICIES
-- ========================================
DROP POLICY IF EXISTS "Users can view tenant phase submissions" ON phase_submissions;
CREATE POLICY "Users can view tenant phase submissions"
  ON phase_submissions FOR SELECT
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles 
      WHERE id = current_setting('app.current_user_id', true)::uuid
    )
    AND (
      user_id = current_setting('app.current_user_id', true)::uuid
      OR product_id IN (
        SELECT product_id FROM product_shares 
        WHERE shared_with_user_id = current_setting('app.current_user_id', true)::uuid
      )
    )
  );

DROP POLICY IF EXISTS "Users can create phase submissions" ON phase_submissions;
CREATE POLICY "Users can create phase submissions"
  ON phase_submissions FOR INSERT
  WITH CHECK (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles 
      WHERE id = current_setting('app.current_user_id', true)::uuid
    )
    AND (
      user_id = current_setting('app.current_user_id', true)::uuid
      OR product_id IN (
        SELECT product_id FROM product_shares 
        WHERE shared_with_user_id = current_setting('app.current_user_id', true)::uuid
        AND permission IN ('edit', 'admin')
      )
    )
  );

DROP POLICY IF EXISTS "Users can update phase submissions" ON phase_submissions;
CREATE POLICY "Users can update phase submissions"
  ON phase_submissions FOR UPDATE
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_profiles 
      WHERE id = current_setting('app.current_user_id', true)::uuid
    )
    AND (
      user_id = current_setting('app.current_user_id', true)::uuid
      OR product_id IN (
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
    AND (
      user_id = current_setting('app.current_user_id', true)::uuid
      OR product_id IN (
        SELECT product_id FROM product_shares 
        WHERE shared_with_user_id = current_setting('app.current_user_id', true)::uuid
        AND permission IN ('edit', 'admin')
      )
    )
  );

-- ========================================
-- CONVERSATION_SESSIONS POLICIES
-- ========================================
-- Only create policies if tenant_id column exists
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'conversation_sessions' 
    AND column_name = 'tenant_id'
  ) THEN
    DROP POLICY IF EXISTS "Users can view tenant conversation sessions" ON conversation_sessions;
    EXECUTE 'CREATE POLICY "Users can view tenant conversation sessions"
      ON conversation_sessions FOR SELECT
      USING (
        tenant_id IN (
          SELECT tenant_id FROM user_profiles 
          WHERE id = current_setting(''app.current_user_id'', true)::uuid
        )
        AND (
          user_id = current_setting(''app.current_user_id'', true)::uuid
          OR product_id IN (
            SELECT product_id FROM product_shares 
            WHERE shared_with_user_id = current_setting(''app.current_user_id'', true)::uuid
          )
        )
      )';

    DROP POLICY IF EXISTS "Users can create conversation sessions" ON conversation_sessions;
    EXECUTE 'CREATE POLICY "Users can create conversation sessions"
      ON conversation_sessions FOR INSERT
      WITH CHECK (
        tenant_id IN (
          SELECT tenant_id FROM user_profiles 
          WHERE id = current_setting(''app.current_user_id'', true)::uuid
        )
        AND user_id = current_setting(''app.current_user_id'', true)::uuid
      )';
  END IF;
END $$;

-- ========================================
-- DESIGN_MOCKUPS POLICIES
-- ========================================
-- Only create policies if table exists
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_name = 'design_mockups'
  ) THEN
    DROP POLICY IF EXISTS "Users can view tenant design mockups" ON design_mockups;
    EXECUTE 'CREATE POLICY "Users can view tenant design mockups"
      ON design_mockups FOR SELECT
      USING (
        tenant_id IN (
          SELECT tenant_id FROM user_profiles 
          WHERE id = current_setting(''app.current_user_id'', true)::uuid
        )
        AND (
          user_id = current_setting(''app.current_user_id'', true)::uuid
          OR product_id IN (
            SELECT product_id FROM product_shares 
            WHERE shared_with_user_id = current_setting(''app.current_user_id'', true)::uuid
          )
        )
      )';

    DROP POLICY IF EXISTS "Users can create design mockups" ON design_mockups;
    EXECUTE 'CREATE POLICY "Users can create design mockups"
      ON design_mockups FOR INSERT
      WITH CHECK (
        tenant_id IN (
          SELECT tenant_id FROM user_profiles 
          WHERE id = current_setting(''app.current_user_id'', true)::uuid
        )
        AND user_id = current_setting(''app.current_user_id'', true)::uuid
      )';
  END IF;
END $$;

-- ========================================
-- USER_PREFERENCES POLICIES
-- ========================================
DROP POLICY IF EXISTS "Users can view own preferences" ON user_preferences;
CREATE POLICY "Users can view own preferences"
  ON user_preferences FOR SELECT
  USING (user_id = current_setting('app.current_user_id', true)::uuid);

DROP POLICY IF EXISTS "Users can update own preferences" ON user_preferences;
CREATE POLICY "Users can update own preferences"
  ON user_preferences FOR UPDATE
  USING (user_id = current_setting('app.current_user_id', true)::uuid)
  WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);

DROP POLICY IF EXISTS "Users can insert own preferences" ON user_preferences;
CREATE POLICY "Users can insert own preferences"
  ON user_preferences FOR INSERT
  WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);

