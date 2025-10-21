-- SQL Migration for Chrome Extension Quote Capture
-- Run this in your Supabase SQL Editor

-- Create extension tokens table
CREATE TABLE IF NOT EXISTS public.cms_extension_tokens (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  token text NOT NULL UNIQUE,
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at timestamp with time zone DEFAULT now(),
  expires_at timestamp with time zone DEFAULT (now() + interval '7 days')
);

-- Add index for faster token lookups
CREATE INDEX IF NOT EXISTS idx_extension_tokens_token ON public.cms_extension_tokens(token);
CREATE INDEX IF NOT EXISTS idx_extension_tokens_user_id ON public.cms_extension_tokens(user_id);

-- Add RLS (Row Level Security) policies
ALTER TABLE public.cms_extension_tokens ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own tokens
CREATE POLICY "Users can view their own tokens"
  ON public.cms_extension_tokens
  FOR SELECT
  USING (auth.uid() = user_id);

-- Policy: Users can create their own tokens
CREATE POLICY "Users can create their own tokens"
  ON public.cms_extension_tokens
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Policy: Users can delete their own tokens
CREATE POLICY "Users can delete their own tokens"
  ON public.cms_extension_tokens
  FOR DELETE
  USING (auth.uid() = user_id);

-- Grant necessary permissions
GRANT SELECT, INSERT, DELETE ON public.cms_extension_tokens TO authenticated;
GRANT USAGE ON SCHEMA public TO authenticated;

-- Optional: Create a function to clean up expired tokens
CREATE OR REPLACE FUNCTION clean_expired_extension_tokens()
RETURNS void AS $$
BEGIN
  DELETE FROM public.cms_extension_tokens
  WHERE expires_at < now();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Optional: Create a scheduled job to clean expired tokens (requires pg_cron extension)
-- You can run this manually or set up a cron job in Supabase Dashboard
-- SELECT cron.schedule('clean-expired-tokens', '0 0 * * *', 'SELECT clean_expired_extension_tokens();');
