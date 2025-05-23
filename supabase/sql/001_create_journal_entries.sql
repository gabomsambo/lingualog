-- 001_create_journal_entries.sql
-- Migration for creating the journal_entries table with basic RLS policies
--
-- To apply this migration, run:
--   supabase db push --file supabase/sql/001_create_journal_entries.sql

create table if not exists journal_entries (
  id uuid primary key default gen_random_uuid(),
  user_id text,
  original_text text,
  corrected text,
  rewrite text,
  score int,
  tone text,
  translation text,
  created_at timestamp with time zone default now()
);

alter table journal_entries enable row level security;

create policy "public insert" on journal_entries
  for insert with check (true);

create policy "public select" on journal_entries
  for select using (true); 