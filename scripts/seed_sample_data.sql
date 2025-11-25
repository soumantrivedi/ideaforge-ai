-- Seed Sample Data Script
-- Run this after database clean to restore sample products and data
-- Usage: docker-compose exec postgres psql -U agentic_pm -d agentic_pm_db -f /path/to/seed_sample_data.sql

-- Ensure default tenant exists
INSERT INTO tenants (id, name, slug, description)
VALUES 
  ('00000000-0000-0000-0000-000000000001', 'Default Tenant', 'default', 'Default tenant for existing data')
ON CONFLICT (id) DO NOTHING;

-- Ensure demo accounts exist with correct password (password123 for all)
-- Password hash for 'password123': $2b$12$eTMKjfsd8Hi2uERGM8/LZed4I0LlacMvnLx/9Xg9Mbu8NYqfaGNo.
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

-- Create sample products (if they don't exist)
-- All 9 products with fixed UUIDs for consistent seeding
INSERT INTO products (id, user_id, name, description, status, tenant_id, metadata)
VALUES
  ('b9e09ba1-e062-470e-aa8e-a9c98022dab2', '00000000-0000-0000-0000-000000000001', 'AI Product Manager Assistant', 'An intelligent assistant for product managers', 'ideation', '00000000-0000-0000-0000-000000000001', '{}'),
  ('fc184f51-14d5-43b5-b9d1-8f4833e8133a', '00000000-0000-0000-0000-000000000001', 'Smart Analytics Platform', 'Advanced analytics for product insights', 'build', '00000000-0000-0000-0000-000000000001', '{}'),
  ('a1b2c3d4-e5f6-4789-a012-345678901234', '00000000-0000-0000-0000-000000000001', 'Customer Feedback System', 'System for collecting and analyzing customer feedback', 'ideation', '00000000-0000-0000-0000-000000000001', '{}'),
  ('b2c3d4e5-f6a7-4890-b123-456789012345', '00000000-0000-0000-0000-000000000001', 'Product Roadmap Tool', 'Tool for managing product roadmaps', 'ideation', '00000000-0000-0000-0000-000000000001', '{}'),
  ('c3d4e5f6-a7b8-4901-c234-567890123456', '00000000-0000-0000-0000-000000000001', 'Feature Request Manager', 'Manage and prioritize feature requests', 'ideation', '00000000-0000-0000-0000-000000000001', '{}'),
  ('d4e5f6a7-b8c9-4012-d345-678901234567', '00000000-0000-0000-0000-000000000001', 'User Research Platform', 'Platform for conducting user research', 'ideation', '00000000-0000-0000-0000-000000000001', '{}'),
  ('e5f6a7b8-c9d0-4123-e456-789012345678', '00000000-0000-0000-0000-000000000001', 'A/B Testing Framework', 'Framework for running A/B tests', 'build', '00000000-0000-0000-0000-000000000001', '{}'),
  ('f6a7b8c9-d0e1-4234-f567-890123456789', '00000000-0000-0000-0000-000000000001', 'Product Metrics Dashboard', 'Dashboard for tracking product metrics', 'operate', '00000000-0000-0000-0000-000000000001', '{}'),
  ('a7b8c9d0-e1f2-4345-a678-901234567890', '00000000-0000-0000-0000-000000000001', 'Release Management System', 'System for managing product releases', 'operate', '00000000-0000-0000-0000-000000000001', '{}')
ON CONFLICT (id) DO NOTHING;

-- Create user preferences for all demo accounts
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
  (SELECT COUNT(*) FROM products) as total_products,
  (SELECT COUNT(*) FROM user_profiles) as total_users,
  (SELECT COUNT(*) FROM user_api_keys) as total_api_keys,
  (SELECT COUNT(*) FROM tenants) as total_tenants;

