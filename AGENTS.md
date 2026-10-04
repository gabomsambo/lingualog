# AGENTS.md

This project is an AI-powered language learning journal with comprehensive feedback, vocabulary enrichment, and multilingual support.

## Architecture Overview

Two main components:
- **backend**: FastAPI server with Gemini (journal feedback) and Lara Translate (upcoming)
- **frontend**: Next.js 15 App Router with React 18, TypeScript, and Supabase integration

## Development Environment

Setup, env templates, and the local Supabase workflow are owned by `README.md` (Setup & Installation).

```bash
# Full local stack: Supabase CLI + API + frontend (demo login seeded)
make dev        # App :3000, API :8000, Supabase Studio :54323
make reset-db   # Wipe local DB back to seed data
make stop

# Tests
make test-backend
cd frontend/v0_lingua-log && npm test
```

## Core Technologies

- **Agent Framework**: Direct `google-genai` SDK calls (stateless, one structured call per request)
- **API**: FastAPI 0.115.0+ with background tasks
- **Database**: Supabase (PostgreSQL) - no vector/RAG functionality
- **Frontend**: Next.js 15.2.4 + React 18.3.1 + TypeScript 5
- **UI Library**: shadcn/ui (Radix UI) + Tailwind CSS 3.4.17
- **i18n**: i18next + react-i18next (en, es, ar, he with RTL support)
- **AI Models**: Gemini 3.8 Flash (journal feedback), Gemini Flash-Lite (translation fallback), Lara Translate (meaning translations), optional Mistral-7B
- **Meaning translation**: Lara Translate (`backend/ai/lara.py`, always `no_trace` + `adapt_to=[]`),
  Gemini Flash-Lite fallback; never return untranslated text as a translation

## Code Style

- **Python**: PEP8, type hints required, Pydantic for validation
- **TypeScript**: Functional components, interfaces over types, strict mode
- **Line length**: 100-120 characters max
- **Comments**: Minimal - code should be self-documenting

## Environment Configuration

Templates: root `.env.example` (backend/compose) and `frontend/v0_lingua-log/.env.example` (copy to `.env.local`).
`make dev` fills in the local Supabase URL/keys. Optional Mistral deps: `backend/requirements-optional-mistral.txt`.

Gemini settings (`GEMINI_MODEL_FEEDBACK`, `GEMINI_THINKING_LEVEL`, `AI_PROVIDER=mock` for offline runs) are listed in `.env.example`.

## Key Integration Points

- **Frontend ↔ Backend**: REST API with auth via `X-User-ID` header
- **Backend ↔ Supabase**: Direct client for auth + CRUD operations
- **Backend ↔ Gemini**: Journal analysis (stateless structured output)
- **Backend ↔ Atomic Agents**: Vocabulary enrichment, quiz generation (to be migrated to Gemini in later PRs)
- **Frontend ↔ Supabase**: Direct client for auth state management
- **Database Tables**: `journal_entries`, `user_vocabulary`, `users`, `user_settings`, `word_ai_cache`, `support_events`

## Core Agent Workflows

### Journal Entry Flow
1. User submits text via `/log-entry` with language settings
2. `backend/ai/gemini.py` makes one stateless structured Gemini call (prompt built in `prompt_builder.py`)
3. Returns corrected text, rewrite, rubric, grammar notes, new words
4. Saves to `journal_entries` with flattened AI feedback and `analysis_status` (`ok`/`failed`/`mock`; pre-migration rows are `legacy`); returns the entry `id`
5. On Gemini failure, persists the entry as `failed` and returns 503 `{code, entry_id, message}`; retry via `/entries/{id}/analyze`
6. The result renders in `components/entry-side-by-side.tsx`, both after submit and on `/entries/[id]`. It reads the
   entry's `policy_snapshot` flags (`GET /user/policy` when an older entry has none), never the raw level number.
   Pure alignment/diff logic is in `lib/side-by-side.ts`.

Keep arrays the UI needs required in `ai/schemas.py`'s Gemini schema: live calls left optional arrays empty.

### Vocabulary Enrichment Flow
1. User adds word or system extracts from journal
2. `/ai/vocabulary/{id}/enrich` endpoint called
3. `VocabularyEnrichmentAgent` generates definitions, examples, synonyms, cultural notes
4. Results stored directly in `user_vocabulary` columns (no separate cache)
5. Frontend displays enriched data in LearnWordModal

### Language Policy Resolution
1. `backend/learning_policy.py` `resolve_policy()` is the only level-to-behaviour map. Precedence is documented there and in `README.md` (Learning policy).
2. Immersion and proficiency (A1–C2) are per target language in `user_language_profiles`. Proficiency is not derived from immersion.
3. Each entry stores the resolved object on `journal_entries.policy_snapshot` (`v: 1`). The older `*_snapshot` columns stay.
4. Suggested level changes are computed in `backend/level_suggestion.py` (named thresholds). Accept goes through `save_user_settings`. Dismiss snoozes in `level_suggestion_snoozes` for 7 days. The level never changes on its own.
5. A per-entry override, or a saved explanation mode the learner picked (`user_settings.explanation_mode_explicit`), is honoured.
   Otherwise the immersion level decides note language; the `bilingual` column default is not a choice.

## Security

- Never commit secrets or `.env` files
- Use environment variables for all credentials
- Validate inputs with Pydantic models
- User ownership verified in all database queries
- Auth tokens managed by Supabase

## Documentation

Key reference files:
- `backend/MISTRAL_INTEGRATION.md` - Optional Mistral model setup
- `backend/example_mistral.py` - Mistral usage examples
- `supabase/MIGRATION_README.md` - Local Supabase migrations and seed
- `PRPs/` - Product requirement plans (if using Archon workflow)

## Common Issues

- **CORS errors**: Check `NEXT_PUBLIC_API_URL` matches backend URL and `CORS_ALLOW_ORIGINS` includes the frontend origin
- **Auth failures**: Verify Supabase keys and `X-User-ID` header
- **AI enrichment slow**: First-time vocabulary enrichment takes 3-5 seconds
- **Port conflicts**: 8000 (backend), 3000 (frontend), 54321-54323 (local Supabase); override with `API_PORT`/`WEB_PORT`
- **Mistral out of memory**: Requires 16GB RAM + 8GB VRAM (use OpenAI instead)
- **i18n missing keys**: Strings live in two places: inline resources in `frontend/v0_lingua-log/i18n/i18n.ts`
  and `frontend/v0_lingua-log/locales/{lang}/{namespace}.json`, lazy-loaded by `i18n/LocaleProvider.tsx`.
  The side-by-side result's keys (`feedback` and `journal` namespaces) are in the inline `i18n.ts` resources.
- **Database migrations**: See `supabase/MIGRATION_README.md`

## Database Schema Quick Reference

### `journal_entries`
- Stores journal text + flattened AI feedback (corrected, rewritten, score, tone, etc.) + `analysis_status`, `analysis_model`, `analysis_error_code` + `policy_snapshot`
- `meaning_translations_cache` (jsonb): per-part translations, merged via `merge_meaning_translation` RPC
- Foreign key: `user_id`

### `user_language_profiles`
- One row per `(user_id, l2)`: `immersion_level` and `proficiency` (A1–C2)
- Schema: `supabase/migrations/20261003030000_learning_policy.sql`

### `user_vocabulary`
- Stores user's vocabulary items with AI enrichment columns
- Unique constraint: `(user_id, term, language)`
- AI fields: `ai_definitions`, `ai_example_sentences`, `ai_synonyms`, `ai_antonyms`, `ai_cultural_note`, `ai_pronunciation_guide`, `emotion_tone`, `mnemonic`, `emoji`

### `user_settings`
- Stores multilingual preferences: `target_language`, `ui_language`, `explanation_mode` (+ `explanation_mode_explicit`), `strictness`, `formality`, `immersion_level`

## API Endpoint Reference

- `POST /login` - Magic link authentication
- `POST /log-entry` - Submit journal entry with AI feedback
- `POST /entries/{id}/analyze` - Retry AI analysis for an entry
- `GET /entries` - Fetch user journal entries
- `GET /entries/{id}` - Get single entry, including `policy_snapshot`, `corrected`, `rewrite`, and `analysis_status`
- `DELETE /entries/{id}` - Delete entry
- `POST /entries/{id}/translate` - Meaning translation of an entry part into L1 (cached per entry)
- `POST /vocabulary` - Add vocabulary item
- `GET /vocabulary` - Fetch user vocabulary
- `DELETE /vocabulary/{id}` - Delete vocabulary item
- `POST /ai/vocabulary/{id}/enrich` - AI enrich vocabulary item
- `GET /user/profile` - Get user profile
- `PUT /user/settings` - Update user settings and per-language profiles (one `save_user_settings` RPC)
- `GET /user/policy?l2=` - The learner's current LearningPolicy for one language
- `GET /user/level-suggestions` - Current step-up/step-down suggestion per language, or none
- `POST /user/level-suggestions/{l2}/accept` - Apply that suggestion via `save_user_settings`
- `POST /user/level-suggestions/{l2}/dismiss` - Snooze that language's suggestion for 7 days
- `GET /user/stats` - Get user statistics
- `POST /events` - Log a support event (reveal/rescue taps)

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
