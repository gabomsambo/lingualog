-- Prompt Bank v1: curated prompts are static content, while entry attribution and usage are nullable.

BEGIN;

ALTER TABLE public.journal_entries
  ADD COLUMN IF NOT EXISTS prompt_id text,
  ADD COLUMN IF NOT EXISTS entry_mode text;

ALTER TABLE public.journal_entries
  DROP CONSTRAINT IF EXISTS journal_entries_entry_mode_check,
  ADD CONSTRAINT journal_entries_entry_mode_check CHECK (
    entry_mode IS NULL OR entry_mode IN ('idea', 'frame', 'one_sentence')
  );

COMMENT ON COLUMN public.journal_entries.prompt_id IS
  'Optional id of the curated writing prompt used for this entry.';
COMMENT ON COLUMN public.journal_entries.entry_mode IS
  'Optional prompt entry path: idea, frame, or one_sentence.';

ALTER TABLE public.support_events
  ADD COLUMN IF NOT EXISTS prompt_id text,
  DROP CONSTRAINT IF EXISTS support_events_kind_check,
  ADD CONSTRAINT support_events_kind_check CHECK (
    kind IN (
      'reveal_meaning', 'rescue_note', 'reveal_rewrite_gloss', 'reveal_example',
      'reveal_gloss', 'prompt_selected'
    )
  );

COMMENT ON COLUMN public.support_events.prompt_id IS
  'Optional curated prompt id for a prompt_selected usage event.';

COMMIT;
