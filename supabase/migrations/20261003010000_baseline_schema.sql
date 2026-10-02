create extension if not exists "pgcrypto";

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.users (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  username text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create trigger set_users_updated_at
before update on public.users
for each row
execute function public.set_updated_at();

create table if not exists public.user_settings (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references auth.users(id) on delete cascade,
  native_language text not null default 'en',
  target_languages text[] not null default array['es']::text[],
  email_notifications boolean not null default true,
  push_notifications boolean not null default true,
  daily_reminders boolean not null default true,
  weekly_progress boolean not null default true,
  reminder_time text not null default '09:00',
  theme text not null default 'system',
  app_language text not null default 'en',
  sound_effects boolean not null default true,
  animations boolean not null default true,
  difficulty_level text not null default 'intermediate',
  daily_goal integer not null default 100,
  weekly_goal integer not null default 700,
  auto_save boolean not null default true,
  show_hints boolean not null default true,
  public_profile boolean not null default false,
  share_progress boolean not null default false,
  analytics_opt_in boolean not null default true,
  interface_lang text not null default 'en',
  native_lang text not null default 'en',
  default_target_lang text default 'es',
  explanation_mode text not null default 'bilingual',
  immersion_level smallint not null default 1,
  strictness text not null default 'medium',
  formality text not null default 'neutral',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint user_settings_explanation_mode_check
    check (explanation_mode in ('native_only', 'target_only', 'bilingual', 'smart')),
  constraint user_settings_immersion_level_check
    check (immersion_level >= 0 and immersion_level <= 3),
  constraint user_settings_strictness_check
    check (strictness in ('gentle', 'medium', 'strict', 'pedantic')),
  constraint user_settings_formality_check
    check (formality in ('casual', 'neutral', 'formal', 'academic')),
  constraint chk_interface_lang_format
    check (interface_lang ~ '^[a-z]{2}(-[A-Z]{2})?$'),
  constraint chk_native_lang_format
    check (native_lang ~ '^[a-z]{2}(-[A-Z]{2})?$'),
  constraint chk_default_target_lang_format
    check (default_target_lang is null or default_target_lang ~ '^[a-z]{2}(-[A-Z]{2})?$')
);

create trigger set_user_settings_updated_at
before update on public.user_settings
for each row
execute function public.set_updated_at();

create table if not exists public.journal_entries (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title varchar(255),
  language text not null default 'en',
  original_text text not null,
  corrected text,
  rewrite text,
  score integer,
  tone text,
  translation text,
  explanation text,
  rubric jsonb,
  grammar_suggestions jsonb not null default '[]'::jsonb,
  new_words jsonb not null default '[]'::jsonb,
  target_language text not null default 'en',
  ui_language_snapshot text,
  explanation_language_snapshot text,
  translation_policy_snapshot text,
  proficiency_estimate text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint chk_target_language_format
    check (target_language ~ '^[a-z]{2}(-[A-Z]{2})?$'),
  constraint journal_entries_translation_policy_snapshot_check
    check (
      translation_policy_snapshot is null
      or translation_policy_snapshot in ('none', 'on_demand', 'automatic', 'smart', 'L2_to_L1', 'omit')
    ),
  constraint journal_entries_proficiency_estimate_check
    check (
      proficiency_estimate is null
      or proficiency_estimate in ('beginner', 'elementary', 'intermediate', 'advanced', 'native')
    )
);

create trigger set_journal_entries_updated_at
before update on public.journal_entries
for each row
execute function public.set_updated_at();

create table if not exists public.user_vocabulary (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  entry_id uuid references public.journal_entries(id) on delete set null,
  term text not null,
  language text not null,
  part_of_speech text,
  definition text,
  reading text,
  example_sentence text,
  status text not null default 'saved',
  ai_example_sentences jsonb,
  ai_definitions jsonb,
  ai_synonyms jsonb,
  ai_antonyms jsonb,
  ai_related_phrases jsonb,
  ai_conjugation_info jsonb,
  ai_cultural_note text,
  ai_pronunciation_guide text,
  ai_alternative_forms jsonb,
  ai_common_mistakes jsonb,
  emotion_tone text,
  mnemonic text,
  emoji text,
  source_model text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint unique_user_term_language unique (user_id, term, language),
  constraint user_vocabulary_status_check check (status in ('saved', 'learning', 'mastered'))
);

create trigger set_user_vocabulary_updated_at
before update on public.user_vocabulary
for each row
execute function public.set_updated_at();

create table if not exists public.word_ai_cache (
  id uuid primary key default gen_random_uuid(),
  word_vocabulary_id uuid not null references public.user_vocabulary(id) on delete cascade,
  language text not null,
  ai_example_sentences jsonb,
  synonyms_antonyms jsonb,
  related_phrases jsonb,
  cultural_note text,
  emotion_tone text,
  mnemonic text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  last_accessed_at timestamptz,
  constraint unique_word_ai_cache unique (word_vocabulary_id, language)
);

create trigger set_word_ai_cache_updated_at
before update on public.word_ai_cache
for each row
execute function public.set_updated_at();

create index if not exists idx_journal_entries_user_created_at
on public.journal_entries (user_id, created_at desc);

create index if not exists idx_journal_entries_target_language
on public.journal_entries (target_language);

create index if not exists idx_journal_entries_proficiency
on public.journal_entries (proficiency_estimate)
where proficiency_estimate is not null;

create index if not exists idx_user_vocabulary_user_created_at
on public.user_vocabulary (user_id, created_at desc);

create index if not exists idx_user_settings_languages
on public.user_settings (interface_lang, native_lang, default_target_lang);

alter table public.users enable row level security;
alter table public.user_settings enable row level security;
alter table public.journal_entries enable row level security;
alter table public.user_vocabulary enable row level security;
alter table public.word_ai_cache enable row level security;

create policy "users_select_own"
on public.users for select
using (auth.uid() = id);

create policy "users_insert_own"
on public.users for insert
with check (auth.uid() = id);

create policy "users_update_own"
on public.users for update
using (auth.uid() = id)
with check (auth.uid() = id);

create policy "user_settings_select_own"
on public.user_settings for select
using (auth.uid() = user_id);

create policy "user_settings_insert_own"
on public.user_settings for insert
with check (auth.uid() = user_id);

create policy "user_settings_update_own"
on public.user_settings for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "journal_entries_select_own"
on public.journal_entries for select
using (auth.uid() = user_id);

create policy "journal_entries_insert_own"
on public.journal_entries for insert
with check (auth.uid() = user_id);

create policy "journal_entries_update_own"
on public.journal_entries for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "journal_entries_delete_own"
on public.journal_entries for delete
using (auth.uid() = user_id);

create policy "user_vocabulary_select_own"
on public.user_vocabulary for select
using (auth.uid() = user_id);

create policy "user_vocabulary_insert_own"
on public.user_vocabulary for insert
with check (auth.uid() = user_id);

create policy "user_vocabulary_update_own"
on public.user_vocabulary for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "user_vocabulary_delete_own"
on public.user_vocabulary for delete
using (auth.uid() = user_id);

create policy "word_ai_cache_select_own"
on public.word_ai_cache for select
using (
  exists (
    select 1
    from public.user_vocabulary uv
    where uv.id = word_vocabulary_id
      and uv.user_id = auth.uid()
  )
);

create policy "word_ai_cache_insert_own"
on public.word_ai_cache for insert
with check (
  exists (
    select 1
    from public.user_vocabulary uv
    where uv.id = word_vocabulary_id
      and uv.user_id = auth.uid()
  )
);

create policy "word_ai_cache_update_own"
on public.word_ai_cache for update
using (
  exists (
    select 1
    from public.user_vocabulary uv
    where uv.id = word_vocabulary_id
      and uv.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1
    from public.user_vocabulary uv
    where uv.id = word_vocabulary_id
      and uv.user_id = auth.uid()
  )
);

create policy "word_ai_cache_delete_own"
on public.word_ai_cache for delete
using (
  exists (
    select 1
    from public.user_vocabulary uv
    where uv.id = word_vocabulary_id
      and uv.user_id = auth.uid()
  )
);

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.users (id, email, username)
  values (
    new.id,
    coalesce(new.email, ''),
    coalesce(new.raw_user_meta_data ->> 'username', new.raw_user_meta_data ->> 'full_name')
  )
  on conflict (id) do update
  set email = excluded.email;

  insert into public.user_settings (user_id, native_language, native_lang, default_target_lang, interface_lang, app_language)
  values (new.id, 'en', 'en', 'es', 'en', 'en')
  on conflict (user_id) do nothing;

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row
execute procedure public.handle_new_user();
