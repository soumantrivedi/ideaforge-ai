/*
  # Add Agent-to-Agent Interaction Support

  1. New Tables
    - `agent_interactions` - Tracks agent-to-agent communications
    - `multi_agent_sessions` - Manages collaborative agent sessions
    
  2. Updates
    - Add agent_type and parent_message_id to agent_messages
    - Add interaction metadata for tracking agent collaboration
    
  3. Security
    - Enable RLS on new tables
    - Add policies for authenticated users
*/

-- Add agent interaction tracking
CREATE TABLE IF NOT EXISTS agent_interactions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
  source_agent text NOT NULL,
  target_agent text NOT NULL,
  interaction_type text NOT NULL CHECK (interaction_type IN ('request', 'response', 'consultation', 'delegation')),
  message_id uuid REFERENCES agent_messages(id) ON DELETE CASCADE,
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now()
);

-- Add multi-agent session management
CREATE TABLE IF NOT EXISTS multi_agent_sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id uuid NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
  active_agents text[] NOT NULL DEFAULT '{}',
  coordination_mode text NOT NULL CHECK (coordination_mode IN ('sequential', 'parallel', 'collaborative', 'debate')),
  current_phase text DEFAULT 'ideation',
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Add columns to agent_messages for better agent tracking
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'agent_messages' AND column_name = 'agent_type'
  ) THEN
    ALTER TABLE agent_messages ADD COLUMN agent_type text;
  END IF;
  
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'agent_messages' AND column_name = 'parent_message_id'
  ) THEN
    ALTER TABLE agent_messages ADD COLUMN parent_message_id uuid REFERENCES agent_messages(id) ON DELETE SET NULL;
  END IF;
  
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'agent_messages' AND column_name = 'is_internal'
  ) THEN
    ALTER TABLE agent_messages ADD COLUMN is_internal boolean DEFAULT false;
  END IF;
  
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'agent_messages' AND column_name = 'target_agent'
  ) THEN
    ALTER TABLE agent_messages ADD COLUMN target_agent text;
  END IF;
END $$;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_agent_interactions_session_id ON agent_interactions(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_interactions_source_agent ON agent_interactions(source_agent);
CREATE INDEX IF NOT EXISTS idx_agent_interactions_target_agent ON agent_interactions(target_agent);
CREATE INDEX IF NOT EXISTS idx_multi_agent_sessions_conversation_id ON multi_agent_sessions(conversation_id);
CREATE INDEX IF NOT EXISTS idx_agent_messages_parent_message_id ON agent_messages(parent_message_id);
CREATE INDEX IF NOT EXISTS idx_agent_messages_agent_type ON agent_messages(agent_type);

-- Enable RLS
ALTER TABLE agent_interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE multi_agent_sessions ENABLE ROW LEVEL SECURITY;

-- RLS Policies for agent_interactions
CREATE POLICY "Users can view interactions in own sessions"
  ON agent_interactions FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM conversation_sessions
      WHERE conversation_sessions.id = agent_interactions.session_id
      AND conversation_sessions.user_id = (select auth.uid())
    )
  );

CREATE POLICY "Users can create interactions in own sessions"
  ON agent_interactions FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM conversation_sessions
      WHERE conversation_sessions.id = agent_interactions.session_id
      AND conversation_sessions.user_id = (select auth.uid())
    )
  );

-- Allow anonymous access for testing
CREATE POLICY "Allow anonymous read access to agent interactions"
  ON agent_interactions FOR SELECT
  TO anon
  USING (true);

CREATE POLICY "Allow anonymous insert to agent interactions"
  ON agent_interactions FOR INSERT
  TO anon
  WITH CHECK (true);

-- RLS Policies for multi_agent_sessions
CREATE POLICY "Users can view own multi-agent sessions"
  ON multi_agent_sessions FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM conversation_sessions
      WHERE conversation_sessions.id = multi_agent_sessions.conversation_id
      AND conversation_sessions.user_id = (select auth.uid())
    )
  );

CREATE POLICY "Users can create own multi-agent sessions"
  ON multi_agent_sessions FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM conversation_sessions
      WHERE conversation_sessions.id = multi_agent_sessions.conversation_id
      AND conversation_sessions.user_id = (select auth.uid())
    )
  );

CREATE POLICY "Users can update own multi-agent sessions"
  ON multi_agent_sessions FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM conversation_sessions
      WHERE conversation_sessions.id = multi_agent_sessions.conversation_id
      AND conversation_sessions.user_id = (select auth.uid())
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM conversation_sessions
      WHERE conversation_sessions.id = multi_agent_sessions.conversation_id
      AND conversation_sessions.user_id = (select auth.uid())
    )
  );

-- Allow anonymous access for testing
CREATE POLICY "Allow anonymous read access to multi-agent sessions"
  ON multi_agent_sessions FOR SELECT
  TO anon
  USING (true);

CREATE POLICY "Allow anonymous insert to multi-agent sessions"
  ON multi_agent_sessions FOR INSERT
  TO anon
  WITH CHECK (true);

CREATE POLICY "Allow anonymous update to multi-agent sessions"
  ON multi_agent_sessions FOR UPDATE
  TO anon
  USING (true)
  WITH CHECK (true);

-- Add trigger for updated_at
CREATE TRIGGER update_multi_agent_sessions_updated_at
  BEFORE UPDATE ON multi_agent_sessions
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions
GRANT SELECT, INSERT ON agent_interactions TO authenticated, anon;
GRANT SELECT, INSERT, UPDATE ON multi_agent_sessions TO authenticated, anon;
