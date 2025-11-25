-- Add demo accounts to existing database
-- This script adds demo accounts that don't already exist

-- Ensure default tenant exists
INSERT INTO tenants (id, name, slug, description)
VALUES 
  ('00000000-0000-0000-0000-000000000001', 'Default Tenant', 'default', 'Default tenant for existing data')
ON CONFLICT (id) DO NOTHING;

-- Add demo accounts (only if they don't exist)
INSERT INTO user_profiles (id, email, full_name, tenant_id, password_hash, is_active, persona)
VALUES
  -- Admin accounts
  ('00000000-0000-0000-0000-000000000001', 'admin@ideaforge.ai', 'Admin User', '00000000-0000-0000-0000-000000000001', '$2b$12$eTMKjfsd8Hi2uERGM8/LZed4I0LlacMvnLx/9Xg9Mbu8NYqfaGNo.', true, 'product_manager'),
  ('00000000-0000-0000-0000-000000000002', 'admin2@ideaforge.ai', 'Admin Two', '00000000-0000-0000-0000-000000000001', '$2b$12$eTMKjfsd8Hi2uERGM8/LZed4I0LlacMvnLx/9Xg9Mbu8NYqfaGNo.', true, 'leadership'),
  ('00000000-0000-0000-0000-000000000003', 'admin3@ideaforge.ai', 'Admin Three', '00000000-0000-0000-0000-000000000001', '$2b$12$eTMKjfsd8Hi2uERGM8/LZed4I0LlacMvnLx/9Xg9Mbu8NYqfaGNo.', true, 'tech_lead'),
  -- Demo user accounts
  ('00000000-0000-0000-0000-000000000004', 'user1@ideaforge.ai', 'User One', '00000000-0000-0000-0000-000000000001', '$2b$12$eTMKjfsd8Hi2uERGM8/LZed4I0LlacMvnLx/9Xg9Mbu8NYqfaGNo.', true, 'product_manager'),
  ('00000000-0000-0000-0000-000000000005', 'user2@ideaforge.ai', 'User Two', '00000000-0000-0000-0000-000000000001', '$2b$12$eTMKjfsd8Hi2uERGM8/LZed4I0LlacMvnLx/9Xg9Mbu8NYqfaGNo.', true, 'product_manager'),
  ('00000000-0000-0000-0000-000000000006', 'user3@ideaforge.ai', 'User Three', '00000000-0000-0000-0000-000000000001', '$2b$12$eTMKjfsd8Hi2uERGM8/LZed4I0LlacMvnLx/9Xg9Mbu8NYqfaGNo.', true, 'leadership'),
  ('00000000-0000-0000-0000-000000000007', 'user4@ideaforge.ai', 'User Four', '00000000-0000-0000-0000-000000000001', '$2b$12$eTMKjfsd8Hi2uERGM8/LZed4I0LlacMvnLx/9Xg9Mbu8NYqfaGNo.', true, 'tech_lead'),
  ('00000000-0000-0000-0000-000000000008', 'user5@ideaforge.ai', 'User Five', '00000000-0000-0000-0000-000000000001', '$2b$12$eTMKjfsd8Hi2uERGM8/LZed4I0LlacMvnLx/9Xg9Mbu8NYqfaGNo.', true, 'product_manager')
ON CONFLICT (id) DO UPDATE SET
  password_hash = EXCLUDED.password_hash,
  is_active = true,
  tenant_id = EXCLUDED.tenant_id;

-- Add user preferences for all demo accounts
INSERT INTO user_preferences (user_id, theme, language, notifications_enabled, email_notifications)
VALUES
  ('00000000-0000-0000-0000-000000000001', 'light', 'en', true, false),
  ('00000000-0000-0000-0000-000000000002', 'light', 'en', true, false),
  ('00000000-0000-0000-0000-000000000003', 'light', 'en', true, false),
  ('00000000-0000-0000-0000-000000000004', 'light', 'en', true, false),
  ('00000000-0000-0000-0000-000000000005', 'light', 'en', true, false),
  ('00000000-0000-0000-0000-000000000006', 'light', 'en', true, false),
  ('00000000-0000-0000-0000-000000000007', 'light', 'en', true, false),
  ('00000000-0000-0000-0000-000000000008', 'light', 'en', true, false)
ON CONFLICT (user_id) DO NOTHING;

-- Display summary
SELECT 
  (SELECT COUNT(*) FROM user_profiles) as total_users,
  (SELECT COUNT(*) FROM user_profiles WHERE email LIKE '%@ideaforge.ai') as demo_users;
