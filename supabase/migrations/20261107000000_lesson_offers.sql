BEGIN;

CREATE TABLE IF NOT EXISTS public.lesson_offers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  l2 text NOT NULL,
  tag text NOT NULL,
  offered_at timestamptz NOT NULL DEFAULT now(),
  offered_entry_id uuid,
  seen_at timestamptz,
  snoozed_until timestamptz,
  CONSTRAINT lesson_offers_user_l2_tag_key UNIQUE (user_id, l2, tag)
);

CREATE INDEX IF NOT EXISTS idx_lesson_offers_user_l2
  ON public.lesson_offers (user_id, l2);

ALTER TABLE public.lesson_offers ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS lesson_offers_select_own ON public.lesson_offers;
CREATE POLICY lesson_offers_select_own ON public.lesson_offers
  FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS lesson_offers_insert_own ON public.lesson_offers;
CREATE POLICY lesson_offers_insert_own ON public.lesson_offers
  FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS lesson_offers_update_own ON public.lesson_offers;
CREATE POLICY lesson_offers_update_own ON public.lesson_offers
  FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS lesson_offers_delete_own ON public.lesson_offers;
CREATE POLICY lesson_offers_delete_own ON public.lesson_offers
  FOR DELETE USING (auth.uid() = user_id);

COMMENT ON TABLE public.lesson_offers IS
  'Per-learner lesson offer state, including the last offer, view and snooze times.';

COMMIT;
