-- A dismissed level suggestion stays hidden until snoozed_until.
-- Accepting a suggestion does not write here; it updates user_language_profiles.

create table if not exists public.level_suggestion_snoozes (
  user_id uuid not null references auth.users(id) on delete cascade,
  l2 text not null,
  snoozed_until timestamptz not null,
  created_at timestamptz not null default now(),
  primary key (user_id, l2),
  constraint level_suggestion_snoozes_l2_format
    check (l2 ~ '^[a-z]{2}(-[A-Z]{2})?$')
);

comment on table public.level_suggestion_snoozes is
  'Hides the immersion-level suggestion for one target language until snoozed_until.';

alter table public.level_suggestion_snoozes enable row level security;

create policy "level_suggestion_snoozes_select_own"
  on public.level_suggestion_snoozes for select
  using (auth.uid() = user_id);

create policy "level_suggestion_snoozes_insert_own"
  on public.level_suggestion_snoozes for insert
  with check (auth.uid() = user_id);

create policy "level_suggestion_snoozes_update_own"
  on public.level_suggestion_snoozes for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "level_suggestion_snoozes_delete_own"
  on public.level_suggestion_snoozes for delete
  using (auth.uid() = user_id);
