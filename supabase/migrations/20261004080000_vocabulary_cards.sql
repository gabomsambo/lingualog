BEGIN;

ALTER TABLE public.user_vocabulary
  ADD COLUMN IF NOT EXISTS lemma text,
  ADD COLUMN IF NOT EXISTS sense text,
  ADD COLUMN IF NOT EXISTS card jsonb,
  ADD COLUMN IF NOT EXISTS card_status text NOT NULL DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS card_policy jsonb,
  ADD COLUMN IF NOT EXISTS note text,
  ADD COLUMN IF NOT EXISTS tags text[] NOT NULL DEFAULT '{}';

ALTER TABLE public.user_vocabulary
  DROP CONSTRAINT IF EXISTS user_vocabulary_status_check,
  DROP CONSTRAINT IF EXISTS user_vocabulary_card_status_check,
  DROP CONSTRAINT IF EXISTS unique_user_term_language,
  DROP CONSTRAINT IF EXISTS unique_user_lemma_language;

UPDATE public.user_vocabulary
SET status = 'new'
WHERE status = 'saved';

ALTER TABLE public.user_vocabulary
  ALTER COLUMN status SET DEFAULT 'new',
  ADD CONSTRAINT user_vocabulary_status_check
    CHECK (status IN ('new', 'learning', 'known', 'mastered', 'ignored')),
  ADD CONSTRAINT user_vocabulary_card_status_check
    CHECK (card_status IN ('pending', 'ok', 'failed'));

ALTER TABLE public.support_events
  DROP CONSTRAINT IF EXISTS support_events_kind_check,
  ADD CONSTRAINT support_events_kind_check CHECK (
    kind IN ('reveal_meaning', 'rescue_note', 'reveal_rewrite_gloss', 'reveal_example', 'reveal_gloss')
  );

-- The retired provider sometimes serialized its exception text into otherwise valid AI fields.
UPDATE public.user_vocabulary
SET
  ai_example_sentences = CASE WHEN ai_example_sentences::text ILIKE '%error generating%'
    THEN NULL ELSE ai_example_sentences END,
  ai_definitions = CASE WHEN ai_definitions::text ILIKE '%error generating%'
    THEN NULL ELSE ai_definitions END,
  ai_synonyms = CASE WHEN ai_synonyms::text ILIKE '%error generating%'
    THEN NULL ELSE ai_synonyms END,
  ai_antonyms = CASE WHEN ai_antonyms::text ILIKE '%error generating%'
    THEN NULL ELSE ai_antonyms END,
  ai_related_phrases = CASE WHEN ai_related_phrases::text ILIKE '%error generating%'
    THEN NULL ELSE ai_related_phrases END,
  ai_conjugation_info = CASE WHEN ai_conjugation_info::text ILIKE '%error generating%'
    THEN NULL ELSE ai_conjugation_info END,
  ai_cultural_note = CASE WHEN ai_cultural_note ILIKE '%error generating%'
    THEN NULL ELSE ai_cultural_note END,
  ai_pronunciation_guide = CASE WHEN ai_pronunciation_guide ILIKE '%error generating%'
    THEN NULL ELSE ai_pronunciation_guide END,
  ai_alternative_forms = CASE WHEN ai_alternative_forms::text ILIKE '%error generating%'
    THEN NULL ELSE ai_alternative_forms END,
  ai_common_mistakes = CASE WHEN ai_common_mistakes::text ILIKE '%error generating%'
    THEN NULL ELSE ai_common_mistakes END,
  emotion_tone = CASE WHEN emotion_tone ILIKE '%error generating%'
    THEN NULL ELSE emotion_tone END,
  mnemonic = CASE WHEN mnemonic ILIKE '%error generating%'
    THEN NULL ELSE mnemonic END,
  emoji = CASE WHEN emoji ILIKE '%error generating%'
    THEN NULL ELSE emoji END;

UPDATE public.user_vocabulary
SET lemma = term
WHERE lemma IS NULL OR btrim(lemma) = '';

UPDATE public.user_vocabulary
SET
  sense = COALESCE(
    NULLIF(definition, ''),
    CASE
      WHEN jsonb_typeof(ai_definitions) = 'array' AND jsonb_array_length(ai_definitions) > 0
      THEN COALESCE(ai_definitions -> 0 ->> 'definition', ai_definitions ->> 0)
    END,
    term
  ),
  card = jsonb_build_object(
    'lemma', lemma,
    'surface', term,
    'is_phrase', position(' ' IN btrim(term)) > 0,
    'part_of_speech', COALESCE(part_of_speech, ''),
    'gender', '',
    'sense_in_context', COALESCE(
      NULLIF(definition, ''),
      CASE
        WHEN jsonb_typeof(ai_definitions) = 'array' AND jsonb_array_length(ai_definitions) > 0
        THEN COALESCE(ai_definitions -> 0 ->> 'definition', ai_definitions ->> 0)
      END,
      term
    ),
    'gloss_l1', COALESCE(NULLIF(definition, ''), ''),
    'other_senses', '[]'::jsonb,
    'register', 'neutral',
    'cefr', '',
    'frequency_band', '',
    'examples', CASE
      WHEN jsonb_typeof(ai_example_sentences) = 'array' THEN ai_example_sentences
      WHEN NULLIF(example_sentence, '') IS NOT NULL THEN jsonb_build_array(example_sentence)
      ELSE '[]'::jsonb
    END,
    'collocations', CASE
      WHEN jsonb_typeof(ai_related_phrases) = 'array' THEN ai_related_phrases
      ELSE '[]'::jsonb
    END,
    'word_family', CASE
      WHEN jsonb_typeof(ai_alternative_forms) = 'array' THEN ai_alternative_forms
      ELSE '[]'::jsonb
    END,
    'common_mistake', CASE
      WHEN jsonb_typeof(ai_common_mistakes) = 'array' AND jsonb_array_length(ai_common_mistakes) > 0
      THEN COALESCE(
        ai_common_mistakes -> 0 ->> 'explanation',
        ai_common_mistakes -> 0 ->> 'correction',
        ai_common_mistakes ->> 0
      )
      ELSE ''
    END,
    'memory_hook', COALESCE(mnemonic, '')
  ),
  card_status = 'ok',
  card_policy = jsonb_build_object(
    'v', 1,
    'level', 0,
    'l1', 'en',
    'vocab_def', 'l1',
    'model', 'legacy'
  )
WHERE card IS NULL
  AND (
    NULLIF(definition, '') IS NOT NULL
    OR ai_definitions IS NOT NULL
    OR ai_example_sentences IS NOT NULL
    OR ai_related_phrases IS NOT NULL
    OR ai_common_mistakes IS NOT NULL
    OR NULLIF(mnemonic, '') IS NOT NULL
  );

ALTER TABLE public.user_vocabulary
  ALTER COLUMN lemma SET NOT NULL,
  ADD CONSTRAINT unique_user_lemma_language UNIQUE (user_id, lemma, language);

DROP TABLE IF EXISTS public.word_ai_cache;

COMMIT;
