BEGIN;

CREATE TABLE IF NOT EXISTS public.class_notes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  l2 text NOT NULL,
  raw_text text NOT NULL,
  source text NOT NULL DEFAULT 'paste',
  extracted jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT class_notes_source_check CHECK (source IN ('paste', 'photo'))
);

CREATE INDEX IF NOT EXISTS idx_class_notes_user_l2_created
  ON public.class_notes (user_id, l2, created_at DESC);

ALTER TABLE public.class_notes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "class_notes_select_own" ON public.class_notes;
CREATE POLICY "class_notes_select_own"
ON public.class_notes FOR SELECT
USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "class_notes_insert_own" ON public.class_notes;
CREATE POLICY "class_notes_insert_own"
ON public.class_notes FOR INSERT
WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "class_notes_update_own" ON public.class_notes;
CREATE POLICY "class_notes_update_own"
ON public.class_notes FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "class_notes_delete_own" ON public.class_notes;
CREATE POLICY "class_notes_delete_own"
ON public.class_notes FOR DELETE
USING (auth.uid() = user_id);

ALTER TABLE public.journal_entries
  ADD COLUMN IF NOT EXISTS class_note_id uuid
    REFERENCES public.class_notes(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS focus_uses jsonb;

ALTER TABLE public.word_encounters
  DROP CONSTRAINT IF EXISTS word_encounters_source_type_check,
  ADD CONSTRAINT word_encounters_source_type_check
    CHECK (source_type IN ('entry', 'book_session', 'manual', 'class_note'));

COMMENT ON TABLE public.class_notes IS
  'Learner-pasted class material and its confirmed practice extraction. Images are never stored.';
COMMENT ON COLUMN public.class_notes.raw_text IS
  'Only the text the learner pasted; no surrounding worksheet or image is stored.';
COMMENT ON COLUMN public.journal_entries.class_note_id IS
  'Class note that prompted this entry, when it was written from a class task.';
COMMENT ON COLUMN public.journal_entries.focus_uses IS
  'The same feedback call’s optional check of the class note grammar focus.';

COMMIT;
