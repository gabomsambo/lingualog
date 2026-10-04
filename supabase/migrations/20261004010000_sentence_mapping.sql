alter table public.journal_entries
  add column if not exists sentence_mapping jsonb,
  add column if not exists sentence_mapping_status text;

alter table public.journal_entries
  add constraint journal_entries_sentence_mapping_status_check
  check (sentence_mapping_status is null or sentence_mapping_status in ('valid', 'invalid'));
