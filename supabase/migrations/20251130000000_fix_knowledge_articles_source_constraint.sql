-- Migration: Fix knowledge_articles source check constraint to allow 'local_upload'
-- This fixes the error when uploading local files to knowledge base

-- Drop the existing constraint
ALTER TABLE knowledge_articles DROP CONSTRAINT IF EXISTS knowledge_articles_source_check;

-- Add new constraint with 'local_upload' included
ALTER TABLE knowledge_articles 
ADD CONSTRAINT knowledge_articles_source_check 
CHECK (source IN ('manual', 'jira', 'confluence', 'github', 'local_upload'));

