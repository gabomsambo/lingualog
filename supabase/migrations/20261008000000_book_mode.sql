-- =============================================
-- Migration: Vocabulary V5 - book mode (the reading companion)
-- Created: 2026-10-31
-- Description:
--   books and reading_sessions hold what the learner is reading and when. Marks are
--   word_encounters (kind 'read', source_type 'book_session'), so reading feeds the same
--   "seen N times" and notebook as lookups; no book text is stored beyond the sentence
--   of a marked word.
--   word_encounters gains book_id (which book the mark belongs to), resolution (the
--   end-of-session choice "skipped"; Study and "I know it" are the saved word itself) and
--   a 'pending' card_status for marks whose card has not been built yet.
--   page_photo_events logs each page photo (never the image) for the per-learner rate limit
--   and the future Plus quota.
-- =============================================

BEGIN;

CREATE TABLE IF NOT EXISTS public.books (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  title text NOT NULL,
  author text,
  language text NOT NULL,
  status text NOT NULL DEFAULT 'reading',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT books_title_check CHECK (char_length(btrim(title)) BETWEEN 1 AND 200),
  CONSTRAINT books_author_check CHECK (author IS NULL OR char_length(author) <= 200),
  CONSTRAINT books_status_check CHECK (status IN ('reading', 'finished', 'paused'))
);

COMMENT ON TABLE public.books IS
  'A book the learner is reading beside the app. Only its title, author and language are kept.';

CREATE INDEX IF NOT EXISTS idx_books_user_language
  ON public.books (user_id, language, updated_at DESC);

CREATE TABLE IF NOT EXISTS public.reading_sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  book_id uuid NOT NULL REFERENCES public.books(id) ON DELETE CASCADE,
  started_at timestamptz NOT NULL DEFAULT now(),
  ended_at timestamptz,
  page_from integer,
  page_to integer,
  words_marked integer NOT NULL DEFAULT 0,
  pages_read integer,
  CONSTRAINT reading_sessions_pages_check
    CHECK (page_from IS NULL OR page_to IS NULL OR page_to >= page_from),
  CONSTRAINT reading_sessions_page_from_check CHECK (page_from IS NULL OR page_from > 0)
);

COMMENT ON TABLE public.reading_sessions IS
  'One sitting with a book. words_marked and pages_read are fixed when the session ends; the words-per-page chart reads them.';
COMMENT ON COLUMN public.reading_sessions.pages_read IS
  'page_to - page_from + 1 when both ends are known, otherwise NULL (no words-per-page for that session).';

CREATE INDEX IF NOT EXISTS idx_reading_sessions_book
  ON public.reading_sessions (book_id, started_at);

-- At most one open session per book, so a second tab resumes instead of forking.
CREATE UNIQUE INDEX IF NOT EXISTS idx_reading_sessions_one_open
  ON public.reading_sessions (book_id)
  WHERE ended_at IS NULL;

CREATE TABLE IF NOT EXISTS public.page_photo_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  book_id uuid REFERENCES public.books(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.page_photo_events IS
  'One row per page photo sent for transcription. The image is never stored; this only counts usage.';

CREATE INDEX IF NOT EXISTS idx_page_photo_events_user_time
  ON public.page_photo_events (user_id, created_at DESC);

DO $$
DECLARE
  table_name text;
BEGIN
  FOREACH table_name IN ARRAY ARRAY['books', 'reading_sessions', 'page_photo_events'] LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', table_name || '_select_own', table_name);
    EXECUTE format(
      'CREATE POLICY %I ON public.%I FOR SELECT USING (auth.uid() = user_id)',
      table_name || '_select_own', table_name
    );
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', table_name || '_insert_own', table_name);
    EXECUTE format(
      'CREATE POLICY %I ON public.%I FOR INSERT WITH CHECK (auth.uid() = user_id)',
      table_name || '_insert_own', table_name
    );
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', table_name || '_update_own', table_name);
    EXECUTE format(
      'CREATE POLICY %I ON public.%I FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id)',
      table_name || '_update_own', table_name
    );
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', table_name || '_delete_own', table_name);
    EXECUTE format(
      'CREATE POLICY %I ON public.%I FOR DELETE USING (auth.uid() = user_id)',
      table_name || '_delete_own', table_name
    );
  END LOOP;
END $$;

ALTER TABLE public.word_encounters
  ADD COLUMN IF NOT EXISTS book_id uuid REFERENCES public.books(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS resolution text;

ALTER TABLE public.word_encounters
  DROP CONSTRAINT IF EXISTS word_encounters_resolution_check,
  ADD CONSTRAINT word_encounters_resolution_check CHECK (resolution IS NULL OR resolution = 'skipped');

ALTER TABLE public.word_encounters
  DROP CONSTRAINT IF EXISTS word_encounters_card_status_check,
  ADD CONSTRAINT word_encounters_card_status_check CHECK (card_status IN ('ok', 'failed', 'pending'));

COMMENT ON COLUMN public.word_encounters.book_id IS
  'The book a reading mark belongs to. Deleting the book clears it; unsaved marks are removed with the book.';
COMMENT ON COLUMN public.word_encounters.resolution IS
  'skipped when the learner chose "skip for now" at the end of a reading session. Saved words need no value: word_id is set.';

CREATE INDEX IF NOT EXISTS idx_word_encounters_book
  ON public.word_encounters (book_id, created_at)
  WHERE book_id IS NOT NULL;

COMMIT;
