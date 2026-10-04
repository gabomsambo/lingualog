alter table public.journal_entries
  add column if not exists sentence_mapping jsonb,
  add column if not exists sentence_mapping_status text,
  add column if not exists sentence_actions jsonb;

-- Drop the old constraint that only allowed 'valid' or 'invalid'; the new
-- contract adds 'invalid_no_explanation' so a missing or empty action reason
-- can be surfaced to the UI distinctly from a structurally broken mapping.
alter table public.journal_entries
  drop constraint if exists journal_entries_sentence_mapping_status_check;

alter table public.journal_entries
  add constraint journal_entries_sentence_mapping_status_check
  check (
    sentence_mapping_status is null
    or sentence_mapping_status in ('valid', 'invalid', 'invalid_no_explanation')
  );