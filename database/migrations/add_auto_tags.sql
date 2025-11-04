-- Migration: Add Auto-Tagging Support to Quotes
-- Run this in your Supabase SQL Editor

-- Add auto_tags column to store automatically generated tags
ALTER TABLE public.cms_quotes
ADD COLUMN IF NOT EXISTS auto_tags text[] DEFAULT '{}';

-- Add removed_auto_tags column to track user-removed auto tags
ALTER TABLE public.cms_quotes
ADD COLUMN IF NOT EXISTS removed_auto_tags text[] DEFAULT '{}';

-- Add index for faster tag searches on auto_tags
CREATE INDEX IF NOT EXISTS idx_cms_quotes_auto_tags
ON public.cms_quotes USING GIN (auto_tags);

-- Add comment for documentation
COMMENT ON COLUMN public.cms_quotes.auto_tags IS 'Automatically generated tags based on keyword matching';
COMMENT ON COLUMN public.cms_quotes.removed_auto_tags IS 'Auto-tags that user manually removed (will not be reapplied)';
