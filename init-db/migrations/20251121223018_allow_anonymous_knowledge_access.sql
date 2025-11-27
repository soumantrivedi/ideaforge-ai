/*
  # Allow Anonymous Access to Knowledge Articles

  1. Changes
    - Add policy for anonymous users to read knowledge articles
    - Add policy for anonymous users to insert knowledge articles
    - This enables the chatbot to work without authentication during testing
  
  2. Security Notes
    - For production, implement proper authentication
    - These policies should be restricted once user auth is set up
*/

-- Allow anonymous users to read all knowledge articles
CREATE POLICY "Allow anonymous read access to knowledge articles"
  ON knowledge_articles FOR SELECT
  TO anon
  USING (true);

-- Allow anonymous users to insert knowledge articles (for testing)
CREATE POLICY "Allow anonymous insert to knowledge articles"
  ON knowledge_articles FOR INSERT
  TO anon
  WITH CHECK (true);

-- Allow anonymous users to delete knowledge articles (for testing)
CREATE POLICY "Allow anonymous delete from knowledge articles"
  ON knowledge_articles FOR DELETE
  TO anon
  USING (true);
