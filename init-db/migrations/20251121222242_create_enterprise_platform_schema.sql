/*
  # Enterprise Agentic PM Platform - Database Schema

  1. New Tables
    - `user_profiles`
      - `id` (uuid, primary key, references auth.users)
      - `email` (text, unique, not null)
      - `full_name` (text)
      - `persona` (text, default 'product_manager')
      - `preferences` (jsonb, default '{}')
      - `created_at` (timestamptz, default now())
      - `updated_at` (timestamptz, default now())
    
    - `products`
      - `id` (uuid, primary key)
      - `user_id` (uuid, references user_profiles, not null)
      - `name` (text, not null)
      - `description` (text)
      - `status` (text, default 'ideation')
      - `metadata` (jsonb, default '{}')
      - `created_at` (timestamptz, default now())
      - `updated_at` (timestamptz, default now())
    
    - `prd_documents`
      - `id` (uuid, primary key)
      - `product_id` (uuid, references products, not null)
      - `title` (text, not null)
      - `content` (jsonb, not null)
      - `version` (integer, default 1)
      - `status` (text, default 'draft')
      - `created_by` (uuid, references user_profiles, not null)
      - `created_at` (timestamptz, default now())
      - `updated_at` (timestamptz, default now())
    
    - `conversation_sessions`
      - `id` (uuid, primary key)
      - `user_id` (uuid, references user_profiles, not null)
      - `product_id` (uuid, references products)
      - `title` (text)
      - `created_at` (timestamptz, default now())
      - `updated_at` (timestamptz, default now())
    
    - `agent_messages`
      - `id` (uuid, primary key)
      - `session_id` (uuid, references conversation_sessions, not null)
      - `role` (text, not null)
      - `content` (text, not null)
      - `agent_role` (text)
      - `metadata` (jsonb, default '{}')
      - `created_at` (timestamptz, default now())
    
    - `knowledge_articles`
      - `id` (uuid, primary key)
      - `product_id` (uuid, references products, not null)
      - `title` (text, not null)
      - `content` (text, not null)
      - `source` (text, not null)
      - `embedding` (vector(1536))
      - `metadata` (jsonb, default '{}')
      - `created_at` (timestamptz, default now())
    
    - `agent_activity_log`
      - `id` (uuid, primary key)
      - `user_id` (uuid, references user_profiles, not null)
      - `product_id` (uuid, references products)
      - `agent_type` (text, not null)
      - `action` (text, not null)
      - `metadata` (jsonb, default '{}')
      - `created_at` (timestamptz, default now())
    
    - `feedback_entries`
      - `id` (uuid, primary key)
      - `product_id` (uuid, references products, not null)
      - `agent_type` (text, not null)
      - `user_feedback` (text, not null)
      - `rating` (integer, check rating >= 1 and rating <= 5)
      - `context` (jsonb, default '{}')
      - `created_at` (timestamptz, default now())

  2. Security
    - Enable RLS on all tables
    - Add policies for authenticated users to access their own data
    - Add policies for team collaboration

  3. Indexes
    - Add indexes for frequently queried columns
    - Add vector similarity search index
*/

-- Enable pgvector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- User Profiles Table
CREATE TABLE IF NOT EXISTS user_profiles (
  id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email text UNIQUE NOT NULL,
  full_name text,
  persona text DEFAULT 'product_manager' CHECK (persona IN ('product_manager', 'leadership', 'tech_lead')),
  preferences jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile"
  ON user_profiles FOR SELECT
  TO authenticated
  USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
  ON user_profiles FOR UPDATE
  TO authenticated
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
  ON user_profiles FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = id);

-- Products Table
CREATE TABLE IF NOT EXISTS products (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  name text NOT NULL,
  description text,
  status text DEFAULT 'ideation' CHECK (status IN ('ideation', 'build', 'operate', 'learn', 'govern', 'sunset')),
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE products ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own products"
  ON products FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create own products"
  ON products FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own products"
  ON products FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own products"
  ON products FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- PRD Documents Table
CREATE TABLE IF NOT EXISTS prd_documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  title text NOT NULL,
  content jsonb NOT NULL DEFAULT '{}',
  version integer DEFAULT 1,
  status text DEFAULT 'draft' CHECK (status IN ('draft', 'in_review', 'approved', 'published')),
  created_by uuid NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE prd_documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view PRDs for own products"
  ON prd_documents FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM products
      WHERE products.id = prd_documents.product_id
      AND products.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can create PRDs for own products"
  ON prd_documents FOR INSERT
  TO authenticated
  WITH CHECK (
    auth.uid() = created_by AND
    EXISTS (
      SELECT 1 FROM products
      WHERE products.id = prd_documents.product_id
      AND products.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can update PRDs for own products"
  ON prd_documents FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM products
      WHERE products.id = prd_documents.product_id
      AND products.user_id = auth.uid()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM products
      WHERE products.id = prd_documents.product_id
      AND products.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can delete PRDs for own products"
  ON prd_documents FOR DELETE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM products
      WHERE products.id = prd_documents.product_id
      AND products.user_id = auth.uid()
    )
  );

-- Conversation Sessions Table
CREATE TABLE IF NOT EXISTS conversation_sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  product_id uuid REFERENCES products(id) ON DELETE CASCADE,
  title text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE conversation_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own conversation sessions"
  ON conversation_sessions FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create own conversation sessions"
  ON conversation_sessions FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own conversation sessions"
  ON conversation_sessions FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own conversation sessions"
  ON conversation_sessions FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- Agent Messages Table
CREATE TABLE IF NOT EXISTS agent_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
  role text NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content text NOT NULL,
  agent_role text,
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now()
);

ALTER TABLE agent_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view messages in own sessions"
  ON agent_messages FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM conversation_sessions
      WHERE conversation_sessions.id = agent_messages.session_id
      AND conversation_sessions.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can create messages in own sessions"
  ON agent_messages FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM conversation_sessions
      WHERE conversation_sessions.id = agent_messages.session_id
      AND conversation_sessions.user_id = auth.uid()
    )
  );

-- Knowledge Articles Table
CREATE TABLE IF NOT EXISTS knowledge_articles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  title text NOT NULL,
  content text NOT NULL,
  source text NOT NULL CHECK (source IN ('manual', 'jira', 'confluence', 'github')),
  embedding vector(1536),
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now()
);

ALTER TABLE knowledge_articles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view knowledge for own products"
  ON knowledge_articles FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM products
      WHERE products.id = knowledge_articles.product_id
      AND products.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can create knowledge for own products"
  ON knowledge_articles FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM products
      WHERE products.id = knowledge_articles.product_id
      AND products.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can delete knowledge for own products"
  ON knowledge_articles FOR DELETE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM products
      WHERE products.id = knowledge_articles.product_id
      AND products.user_id = auth.uid()
    )
  );

-- Agent Activity Log Table
CREATE TABLE IF NOT EXISTS agent_activity_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  product_id uuid REFERENCES products(id) ON DELETE CASCADE,
  agent_type text NOT NULL,
  action text NOT NULL,
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now()
);

ALTER TABLE agent_activity_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own activity log"
  ON agent_activity_log FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "System can insert activity log"
  ON agent_activity_log FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

-- Feedback Entries Table
CREATE TABLE IF NOT EXISTS feedback_entries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id uuid NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  agent_type text NOT NULL,
  user_feedback text NOT NULL,
  rating integer NOT NULL CHECK (rating >= 1 AND rating <= 5),
  context jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now()
);

ALTER TABLE feedback_entries ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view feedback for own products"
  ON feedback_entries FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM products
      WHERE products.id = feedback_entries.product_id
      AND products.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can create feedback for own products"
  ON feedback_entries FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM products
      WHERE products.id = feedback_entries.product_id
      AND products.user_id = auth.uid()
    )
  );

-- Indexes
CREATE INDEX IF NOT EXISTS idx_products_user_id ON products(user_id);
CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);
CREATE INDEX IF NOT EXISTS idx_prd_documents_product_id ON prd_documents(product_id);
CREATE INDEX IF NOT EXISTS idx_prd_documents_status ON prd_documents(status);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_user_id ON conversation_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_product_id ON conversation_sessions(product_id);
CREATE INDEX IF NOT EXISTS idx_agent_messages_session_id ON agent_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_articles_product_id ON knowledge_articles(product_id);
CREATE INDEX IF NOT EXISTS idx_agent_activity_log_user_id ON agent_activity_log(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_activity_log_product_id ON agent_activity_log(product_id);
CREATE INDEX IF NOT EXISTS idx_feedback_entries_product_id ON feedback_entries(product_id);

-- Vector similarity search index
CREATE INDEX IF NOT EXISTS idx_knowledge_articles_embedding 
  ON knowledge_articles 
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- Vector similarity search function
CREATE OR REPLACE FUNCTION search_knowledge_articles(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.7,
  match_count int DEFAULT 5,
  filter_product_id uuid DEFAULT NULL
)
RETURNS TABLE (
  id uuid,
  product_id uuid,
  title text,
  content text,
  source text,
  similarity float,
  metadata jsonb
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    knowledge_articles.id,
    knowledge_articles.product_id,
    knowledge_articles.title,
    knowledge_articles.content,
    knowledge_articles.source,
    1 - (knowledge_articles.embedding <=> query_embedding) AS similarity,
    knowledge_articles.metadata
  FROM knowledge_articles
  WHERE 
    (filter_product_id IS NULL OR knowledge_articles.product_id = filter_product_id)
    AND 1 - (knowledge_articles.embedding <=> query_embedding) > match_threshold
  ORDER BY knowledge_articles.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Updated timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers
CREATE TRIGGER update_user_profiles_updated_at
  BEFORE UPDATE ON user_profiles
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_products_updated_at
  BEFORE UPDATE ON products
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_prd_documents_updated_at
  BEFORE UPDATE ON prd_documents
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversation_sessions_updated_at
  BEFORE UPDATE ON conversation_sessions
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();
