# ✅ TASK.md — Development Tasks

## 🧱 Core Setup
- [x] Set up Supabase auth and database schema
- [x] Scaffold frontend + backend directories
- [ ] Configure global rules
- [x] Create `.env` (manual)
- [x] Implement environment validation in config.py
- [x] Configure .env files
- [x] Add docker-compose dev stack

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

## 🧠 Backend (FastAPI)
- [x] `POST /log-entry` endpoint:
  - Input: journal text
  - Output: AI feedback (all dimensions)
- [x] `GET /entries` endpoint
- [x] `feedback_engine.py`: Logic for Claude/o3 calls
- [x] Implement Supabase persistence for entries
- [x] Enable CORS
- [x] Switch to real AI feedback
- [x] Integrate Mistral-7B-Instruct-v0.3 for text generation and translation
- [x] Configure Hugging Face token authentication for Mistral model access

## 🧪 Testing
- [x] Unit tests for `feedback_engine.py`
- [x] Integration tests for FastAPI routes
- [ ] React tests for JournalEditor
- [x] Add integration test for POST /log-entry
- [x] Add integration test for GET /entries
- [x] Add unit test for analyze_entry() output validity
- [x] Add integration tests once auth is implemented
- [x] Add unit tests for Mistral-7B-Instruct-v0.3 integration
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

## 🛠 Tech Debt
- [ ] Remove hardcoded localhost URL in frontend/v0_lingua-log/lib/api.ts
- [ ] Tighten RLS once auth is live
- [ ] Refactor sidebar.tsx (>500 lines) into smaller components