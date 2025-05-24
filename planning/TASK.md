# ✅ TASK.md — Development Tasks

## 🧱 Core Setup
- [x] Set up Supabase auth and database schema
- [x] Scaffold frontend + backend directories
- [x] Configure global rules
- [x] Create `.env` (manual)
- [x] Implement environment validation in config.py
- [x] Configure .env files
- [x] Add docker-compose dev stack
- [x] Fix Python package initialization

## 🧑‍💻 Frontend (React + Tailwind)
- [x] Unify Entry type & build API helper
- [x] Create `JournalEditor.tsx` with:
  - Textarea
  - Submit button
  - Feedback panel
- [x] Refactor new entry page to use JournalEditor
- [x] Connect PastEntries view to GET /entries
- [x] Add auth flow to supply user_id
- [x] Add Past Entries view (calendar/timeline)
- [x] Create individual entry insight page `app/(app)/entries/[id]/page.tsx`
- [ ] Add prompt selector component (for guided writing)
- [x] Create `vocabulary` page under `(app)` for shared layout
- [x] Enhance `vocabulary` page design and functionality
- [x] Create `stats` page under `(app)` for shared layout
- [x] Fix Next.js build error due to duplicate page definitions
- [x] Integrate v0 code for `stats` page into `(app)/stats/page.tsx`
- [ ] **Feature: Vocabulary Learning Modal (`LearnWordModal.tsx`)**
  - [x] Create `LearnWordModal.tsx` component structure with Tailwind CSS.
  - [x] Define `VocabWordData` interface for modal props.
  - [x] Implement display for all 11 requested sections using placeholder/passed data:
    - Word Header (script, romaji, audio, frequency, POS)
    - Definitions (primary, secondary)
    - Example Sentences (journal, AI placeholder)
    - Synonyms & Antonyms (lists, basic styling)
    - Related Phrases (list)
    - Conjugation Chart
    - Cultural Note / AI Usage Insight (placeholders)
    - Emotion/Tone (text, emoji placeholder)
    - Mnemonic/Metaphor (text)
    - User Note & Tagging (inputs, display)
  - [x] Include placeholders for Optional Enhancements (ELI5, more examples, quiz preview).
  - [x] Integrate `LearnWordModal` into `vocabulary/page.tsx`.
  - [x] Add "Learn It" button to vocabulary cards to trigger the modal.
  - [x] Implement modal open/close state management.
  - [x] Map `UserVocabularyItemResponse` to `VocabWordData` (using available fields).
  - [x] Implement actual data fetching/AI enrichment for dynamic fields (audio, AI explanations, synonyms, etc.).
  - [x] Frontend: Call enrichment endpoint when modal opens for a new/stale word.
    - [x] Add state for enriched data, loading, and errors in `LearnWordModal.tsx`.
    - [x] Implement `useEffect` to call `getEnrichedVocabularyDetails`.
    - [x] Update UI to use enriched data, prioritizing it over initial `vocabEntry`.
    - [x] Define `EnrichedVocabDetails` type in `api.ts` for the enrichment endpoint response.
  - [x] Frontend: Implement interactive functionalities (ELI5, generate examples, generate quiz) for on-demand AI in LearnWordModal.
    - [x] Add UI elements (buttons, display areas) to LearnWordModal.tsx.
    - [x] Add state management (data, loading, error) for on-demand features.
    - [x] Create API call functions in frontend/v0_lingua-log/lib/api.ts for on-demand endpoints.
    - [x] Integrate API calls into LearnWordModal.tsx event handlers.
  - [ ] Implement modal open/close state management.
  - [ ] Map `UserVocabularyItemResponse` to `VocabWordData` (using available fields).
  - [ ] Implement actual data fetching/AI enrichment for dynamic fields (audio, AI explanations, synonyms, etc.).
  - [ ] Implement interactive functionalities (save note/tags, ELI5, generate examples).
  - [ ] Implement highlighting word in example sentences.
  - [ ] Implement "View usage" for synonyms/antonyms.

## 🧠 Backend (FastAPI)
- [x] `POST /log-entry` endpoint:
  - Input: journal text
  - Output: AI feedback (all dimensions)
- [x] `GET /entries` endpoint
- [x] `feedback_engine.py`: Logic for Claude/o3 calls
- [x] Implement Supabase persistence for entries
- [x] Enable CORS
- [x] Switch to real AI feedback (Mistral/Gemini path)
- [x] Integrate Mistral-7B-Instruct-v0.3 for text generation and translation (parameter passing fixed)
- [x] Configure Hugging Face token authentication for Mistral model access (assuming this was already in place for download)
- [x] Implement detailed AI feedback fields (rubric, grammar_suggestions, new_words) in Gemini engine and backend models/routes
- [x] Add `DELETE /entries/{entry_id}` endpoint
- [x] `POST /vocabulary` - Add vocabulary item
- [x] `GET /vocabulary` - Get user vocabulary items
- [x] `DELETE /vocabulary/{item_id}` - Delete vocabulary item

## 🧪 Testing
- [x] Unit tests for `feedback_engine.py` (updated for language parameter)
- [x] Integration tests for FastAPI routes
- [ ] React tests for JournalEditor
- [x] Add integration test for POST /log-entry
- [x] Add integration test for GET /entries
- [x] Add unit test for analyze_entry() output validity
- [x] Add integration tests once auth is implemented
- [x] Add unit tests for Mistral-7B-Instruct-v0.3 integration (updated for language parameter)
- [x] Add tests for entry deletion
- [x] Add tests for Vocabulary AI Enrichment (service and router)
- [x] Add tests for On-Demand Vocabulary AI (service and router)
- [ ] Add Supabase service to CI for integration tests
- [ ] Run e2e in CI once backend containerised

## 📄 Documentation
- [x] Write `README.md`
- [x] Write dev setup + Docker instructions
- [x] Update this file on every completed task

## ✍️ Discovered During Work
- [x] Add Python dependencies management (requirements.txt or pyproject.toml)
- [x] Add pytest configuration for backend tests
- [ ] Replace remaining mock translation modal API
- [x] Fix `ModuleNotFoundError: No module named 'jose'` by adding `python-jose[cryptography]` to `api/requirements.txt`
- [ ] Consolidate duplicate Python files between `backend/` and `backend/app/`

## 🛠 Tech Debt
- [ ] Remove hardcoded localhost URL in frontend/v0_lingua-log/lib/api.ts
- [ ] Tighten RLS once auth is live
- [ ] Refactor sidebar.tsx (>500 lines) into smaller components