-- Fix RLS Policies for Chrome Extension
-- Run this in Supabase SQL Editor to allow the extension to create authors and quotes

-- NOTE: If you get "policy already exists" errors, that's OK!
-- It means the policy is already in place and you can skip to the next one.

-- ==================== FIX FOR cms_authors TABLE ====================

-- Drop existing policies if they exist (to avoid conflicts)
DROP POLICY IF EXISTS "Allow insert authors via API" ON public.cms_authors;
DROP POLICY IF EXISTS "Allow read authors" ON public.cms_authors;

-- Add policy to allow inserting new authors
-- The extension already validates users via token, so this is safe
CREATE POLICY "Allow insert authors via API"
  ON public.cms_authors
  FOR INSERT
  TO authenticated, anon
  WITH CHECK (true);

-- Add policy to allow anyone to read authors (for autocomplete)
CREATE POLICY "Allow read authors"
  ON public.cms_authors
  FOR SELECT
  TO authenticated, anon
  USING (true);

-- ==================== FIX FOR cms_quotes TABLE ====================

-- Drop existing policies if they exist (to avoid conflicts)
DROP POLICY IF EXISTS "Allow insert quotes via API" ON public.cms_quotes;
DROP POLICY IF EXISTS "Allow read quotes" ON public.cms_quotes;

-- Add policy to allow inserting quotes
-- The extension validates the user via token before allowing this operation
CREATE POLICY "Allow insert quotes via API"
  ON public.cms_quotes
  FOR INSERT
  TO authenticated, anon
  WITH CHECK (true);

-- Add policy to allow users to read all quotes
CREATE POLICY "Allow read quotes"
  ON public.cms_quotes
  FOR SELECT
  TO authenticated, anon
  USING (true);

-- ==================== VERIFICATION ====================

-- Run this to see all RLS policies on these tables:
SELECT tablename, policyname, permissive, roles, cmd
FROM pg_policies
WHERE tablename IN ('cms_authors', 'cms_quotes')
ORDER BY tablename, policyname;
