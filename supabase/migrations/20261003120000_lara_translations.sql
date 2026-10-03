-- Lara meaning translations cache and support event telemetry (PR 3)

alter table public.journal_entries
  add column if not exists meaning_translations_cache jsonb not null default '{}'::jsonb;

comment on column public.journal_entries.meaning_translations_cache is
  'Per-part Lara/Gemini meaning translations keyed by part (original, rewrite, note:<id>)';

create table if not exists public.support_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  entry_id uuid references public.journal_entries(id) on delete set null,
  l2 text,
  immersion_level smallint,
  kind text not null,
  created_at timestamptz not null default now(),
  constraint support_events_kind_check
    check (kind in ('reveal_meaning', 'rescue_note', 'reveal_rewrite_gloss', 'reveal_example'))
);

create index if not exists idx_support_events_user_created
  on public.support_events (user_id, created_at desc);

alter table public.support_events enable row level security;

create policy "support_events_select_own"
  on public.support_events for select
  using (auth.uid() = user_id);

create policy "support_events_insert_own"
  on public.support_events for insert
  with check (auth.uid() = user_id);
