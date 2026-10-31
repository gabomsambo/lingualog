# 🌐 LinguaLog

![CI](https://github.com/gabrielsambo/Lingualog/actions/workflows/ci.yml/badge.svg)

AI-Powered Language Learning Journal for improving your fluency through daily writing.

## 🎯 Purpose

LinguaLog helps language learners improve their fluency by writing journal entries in their target language and receiving immediate AI feedback. The feedback system analyzes grammar, fluency, emotion/tone, and provides native-like rewriting suggestions.

## 🧩 Core Features

- **Journal Entry System**: Write text entries in your target language
- **Comprehensive AI Feedback**:
  - Grammar correction
  - Fluency score (0-100)
  - Native-like rewrite suggestions
  - Emotional tone detection
  - Meaning translation into your native language (Lara Translate, Gemini fallback)
  - Explanation of mistakes
- **Word notebook and review**: look up any word, keep it with the sentence you met it in, and review it with FSRS: two buttons, your own sentences, 10 new words a day per language (see Vocabulary review below)
- **Book mode**: a reading companion for the paper or e-book you already read: mark words without stopping, photograph a page, build the cards when you stop, keep a printable glossary, and watch the words per page fall (see Book mode below)
- **Side-by-side result**: after submit and on each entry page, every sentence shows what you wrote, what it means, and how to write it (corrected or native rewrite), with help shown per your immersion level
- **Progress Tracking**: View your improvement over time
- **Secure User Authentication**: Via Supabase

## 💻 Tech Stack

| Layer        | Technology          |
|--------------|---------------------|
| Frontend     | React + Tailwind CSS |
| Backend      | FastAPI (Python)    |
| AI Feedback  | Gemini 3.8 Flash (journal feedback) |
| Translation  | Lara Translate (Gemini Flash-Lite fallback) |
| Database     | Supabase (Postgres) |
| Auth         | Supabase            |
| Deployment   | Docker → Railway    |

## 🔌 API Overview

### Endpoints

- **POST /log-entry**
  - Submit a journal entry text
  - Returns comprehensive AI feedback, including the saved entry `id`
  - If AI feedback fails, the entry is still saved and the API returns 503 with `{code, entry_id, message}`

- **POST /entries/{id}/analyze**
  - Retry AI feedback for a saved entry

- **GET /entries**
  - Retrieve past journal entries with feedback

- **GET /entries/{id}**
  - One entry, including `policy_snapshot`, `corrected`, `rewrite` (also `rewritten`), and `analysis_status`

- **GET /user/policy?l2=**
  - The current learning policy for one language; entries stored without `policy_snapshot` render with it

- **GET /review/session?language=&mode=normal|catchup**
  - The next cards to review (20 by default) with the learner's own sentences, plus the counts the page needs

- **GET /review/summary**
  - Reviews waiting per studied language, for the dashboard's "N due"

- **POST /review/{card_id}**
  - Answer `{"rating": "again" | "got_it", "reps"?, "duration_ms"?}`; schedules the card and keeps the word's state in step. A repeated answer for the same serving returns 409

## Learning policy

### Languages

Settings holds the whole language model; the rest of the app follows it.

- **Explain things to me in** (`user_settings.native_lang`) is the learner's own language. Notes, meaning translations and rescues are written in it.
- **Languages I'm learning** are the active rows of `user_language_profiles`, each with its own immersion level and proficiency. `user_settings.default_target_lang` marks one as the default. Any language can be studied, including English and the learner's own language.
- **Removing** a language sets `active = false`. Its entries and its row stay; adding it again restores its level and proficiency. The default cannot be removed.
- **Studying your own language** (`native_lang` equals the target) is full immersion: `resolve_policy` always returns level 3 with `same_language` sources, and nothing is translated.
- The **new-entry picker** offers only the studied languages, default first, plus a link to Settings.
- **Did you mean…?** Gemini reports the language it read (`detected_language`, stored on the entry) in the same call. When it differs from the chosen language, the result asks the learner to switch or keep. Switch (`POST /entries/{id}/analyze` with `target_language`) is offered only for a studied language; otherwise the learner is sent to Settings. Keep is stored as `detected_language_kept`. The app never switches on its own.
- Legacy `user_settings.native_language` and `target_languages` are no longer read or written.

### Immersion

Immersion is how much of your own language you want while practising a target language. Proficiency (A1–C2) is separate, and both are stored per target language in `user_language_profiles`. `resolve_policy()` in `backend/learning_policy.py` is the only place a level becomes behaviour. The resolved object (`v: 1`) is stored on the entry as `policy_snapshot`.

Precedence, highest first:

- **Immersion level** (and meaning, rewrite gloss, vocabulary, quiz): per-entry slider, then the language profile, then the account-wide `user_settings.immersion_level`, then 1.
- **Note language**: per-entry explanation mode, then a per-entry immersion override (the slider means "use this level", including its notes), then a saved explanation mode the learner picked in Settings (`explanation_mode_explicit`), then the immersion level. The `bilingual` column default is not a choice.

The settings "Explanation mode" control and the new-entry immersion slider stay. Choose "Follow my immersion level" (`level`) to clear a saved choice and let the level decide notes. Settings sends the mode only when you change it. The new-entry slider shows the saved level for the selected language and is sent only after you move it.

The app may suggest a different immersion level for one language. It never changes the level on its own. `GET /user/level-suggestions` reads `support_events` and scores from recent entries written at the current level, since it last changed (`user_language_profiles.level_changed_at`), with a real (`ok`) analysis. It does this only for the languages Settings lists under "Languages I'm learning" (active `user_language_profiles` rows and `default_target_lang`), never a removed language or one that only appears on an entry. A studied language that is also the native language stays at level 3. A default language with no profile row uses the level `resolve_policy` gives it today and counts only entries newer than its newest entry written at another level. An accept never cascades into a second suggestion, and returning to a level does not reuse its old history; the thresholds and windows are named constants in `backend/level_suggestion.py`. Accept (`POST /user/level-suggestions/{l2}/accept`) writes that language's profile through `save_user_settings`. Dismiss snoozes the suggestion for 7 days.

- **POST /books**, **GET /books**, **GET|PATCH|DELETE /books/{id}**
  - The books a learner is reading (title, author, language); `GET /books/{id}` also returns the open reading session with its marks

- **POST /books/{id}/sessions**, **POST /books/{id}/sessions/{session_id}/marks**, **POST /books/{id}/sessions/{session_id}/end**
  - Start (or resume) a reading session, mark a word with an optional sentence and page, and end the session

- **POST /books/{id}/page-photo**
  - The raw JPEG, PNG or WebP bytes of a book page; returns its text and pre-highlighted words. The image is never stored

- **POST /books/{id}/sessions/{session_id}/cards**, **POST /books/{id}/marks/skip**, **GET /books/{id}/glossary|progress|writing-words**
  - End-of-session cards and choices, the book glossary, the words-per-page progress, and this week's words for "write about what you read"

Gemini infers what you meant. A translation is not fed into the correction.

### Vocabulary review

Review costs no model calls. `backend/review_scheduler.py` runs FSRS-6 (`py-fsrs` 6.3.2) and `backend/review_cards.py` builds each card from the learner's own sentences; `backend/app/services/review_service.py` loads and stores them.

- **Cards.** Choosing Study on a word gives it a recognition card (`vocab_cards`). Once that card has held for about a week (stability of 7 days), a production card joins it. Every answer appends a row to `vocab_review_logs`; the review and its log row are written together by the `apply_card_review` function.
- **Two buttons.** "Again" and "Got it" map to FSRS Again and Good. A word is never retired after one correct answer.
- **The front is your sentence.** Recognition highlights the word in a sentence you met it in (the sentence rotates with each review). Production blanks the word in the *corrected* version of that sentence, found from the entry's sentence mapping, never in your mistaken original. If no sentence qualifies it falls back to the card's example, then to meaning-to-word.
- **Format follows the policy `quiz` flag.** Level 0 recognition and meaning-to-word; level 1 adds typed recall; level 2 a cloze with the native gloss behind a tap; level 3 a target-language-only cloze with the definition.
- **States.** Learning until the recognition card's stability reaches 21 days, then Known; a lapse can move it back. At risk is a flag, not a state: due and below 80% recall probability. Mastered needs writing evidence as well (see Word bank).
- **Per-language settings** on `user_language_profiles`: `daily_new_words` (default 10; how many never-reviewed words a session may introduce a day, on top of the Study cap) and `desired_retention` (default 0.90, adjustable 0.80-0.95). Days are UTC days.
- **Sessions** are 20 cards: due reviews first, the most likely forgotten first, then new words up to the daily limit. When 40 or more reviews are waiting the app offers **catch-up**: reviews only, 30 a day, most at risk first, no new words, so a backlog drains over days instead of arriving at once.
- `user_fsrs_params` holds per-learner parameters for a later optimisation; with no row the library defaults apply.

### Word bank and "used it" mastery

The word bank is a panel beside the editor with 5-6 of the learner's own words to write the entry with. Offering it makes no model calls; checking the uses adds one field to the existing feedback call.

- **Which words** (`backend/word_bank.py`, `GET /word-bank?language=`): Learning words that are due or at risk come first, then recently saved words never used in writing, then Known words that still need a second day of use. Ignored and Mastered words are never offered. Shuffle asks again with `exclude`; pinned words stay on screen. Each chip's meaning follows the policy `quiz` flag: open for levels 0-1, behind a tap for levels 2-3 (the tap is logged as a `reveal_gloss` support event).
- **Ticks** are client-side: the draft is matched against the lemma and the forms the learner has met or written. They are a hint; the tutor decides.
- **Checking.** `POST /log-entry` takes `target_word_ids` (and `challenge_word_ids`); the server loads those words for the caller (another learner's, another language's and ignored words are dropped) and sends only their lemmas to the tutor. `GeminiJournalFeedback.target_word_uses` is a required array of `{term, status, form_in_text, fix, note}` with status `used_correctly`, `used_with_error`, `not_used` or `unclear`. Only claims the entry text can back up are kept: a use whose `form_in_text` is not in the entry, a word that was not requested and a second claim about one word are dropped, never stored. **`unclear` is a question to the learner** (a defensible use whose meaning the tutor cannot tell); it is neither credited nor counted as an error.
- **What a use does** (`word_bank_service.record_uses`): a correct use is a `used_ok` encounter and a use with an error a `used_error` encounter, both in the learner's own entry with the sentence they wrote. `used_ok` sentences become review fronts; `used_error` ones never do. Re-analysing an entry replaces what it recorded, and deleting the entry removes it.
- **Mastered** = Known (recognition card stability of 21 days or more) **and** used correctly in the learner's own entries on two different UTC days (uses from deleted entries do not count). It is checked when a use is recorded and when a review makes a word Known, and it only ever promotes. A word that is "known" only because the learner tapped *I know it* has no stability and is not promoted by writing.
- **FSRS credit.** Writing a word the bank displayed is copying, so it is not a review. In challenge mode the bank hides the words and shows only meanings; a correct use of a word the learner never peeked at is a real recall and becomes a "Got it" on that word's production card (`vocab_review_logs.source = 'challenge_use'`). A word with no production card yet earns no credit, and an entry credits a word once.
- **The result** shows a "Your words today" row (`3 used well · 1 to fix · 1 not used`) with the fix for each error, the question for each unclear use and a note when a word has just become Mastered. Sample feedback from the offline provider (`AI_PROVIDER=mock`) shows the row but is never recorded.
- Entries remember their chosen words and verdicts in `journal_entries.target_words` / `target_word_uses`, so a retried analysis checks the same words. Migration: `supabase/migrations/20261007000000_word_bank.sql`.
### Book mode

Book mode is a companion, not a reader: LinguaLog never stores book text beyond the sentence of a word you marked.

- **Marks are encounters.** A mark is a `word_encounters` row (`kind` `read`, `source_type` `book_session`) with the sentence, page and `book_id`, so reading shares the "seen N times" count and the notebook with lookups. Marking makes no model call. The same word on the same page is not marked twice; on a later page it counts again.
- **"I need this now"** is `POST /lookup` with `source: "book_session"`, the session id and the page: it shows the card at once and completes the mark already made of that word.
- **Page photos.** `backend/ai/page_photo.py` makes one Flash-Lite vision call at medium resolution and returns the text plus words a learner at the language profile's proficiency probably does not know. The photo and its text are held in memory for the call and returned to the browser, never stored; only a `page_photo_events` row (no image) is kept. Limits live in `book_service.py`: 4 MB, 6 a minute, 40 a day per learner. A photo the model cannot read or fails on is not counted. `page_photo_quota_allows` is the one place a future Plus quota plugs in; today it allows everyone.
- **End of session.** The session's page range widens to cover every marked page, and `words_marked` and `pages_read` are fixed. `POST .../cards` builds the cards for the marks that have none, a few at a time (reusing a lookup of the same sentence when there is one), then returns the choices: words marked more than once first, one-offs after with "Skip all for now". Study and "I know it" use the normal save (`POST /vocabulary`, then the daily new-word cap applies); Skip only hides the mark from the choices. A failed card stores nothing and can be retried.
- **Glossary and quiz.** `GET /books/{id}/glossary` lists every marked word with its sentences, pages and the card's meaning (already in the policy's language). The page prints as a bookmark, and "Quiz myself" hides each meaning until the learner reveals it.
- **Words per page and coverage.** `backend/book_coverage.py` holds the soft bands: up to 6 unknown words a page is comfortable, 7-15 study reading, 16-24 demanding, 25 or more hard. They are always shown as estimates; a book that stays hard for three finished sessions suggests an easier one.
- **Write about what you read.** `/entries/new?book=<id>` shows this week's words from that book above the editor.

### Data Models

```python
# Journal Entry Request
{
  "text": "string"  # The journal entry text in target language
}

# Feedback Response
{
  "id": "string",            # Saved journal entry ID
  "corrected": "string",     # Grammar-corrected version
  "rewritten": "string",     # Native-like rewrite
  "score": 0-100,            # Fluency score
  "tone": "string",          # Detected emotional tone
  "translation": "string",   # Empty until Lara translation ships
  "explanation": "string",   # Optional explanation
  "is_mock": false           # True when generated by AI_PROVIDER=mock
}
```

## 🚀 Setup & Installation

### Prerequisites

- Docker
- Python 3.12+
- Node.js 22 (for `npx supabase`)

### Environment Variables

Copy these templates:

```bash
cp .env.example .env
cp frontend/v0_lingua-log/.env.example frontend/v0_lingua-log/.env.local
```

`make dev` creates those files from the templates if missing and only updates the Supabase URL/key entries,
so any other values you set (AI keys, ports, CORS origins) are preserved. Override the Supabase CLI command with
`make dev SUPABASE_NPX="supabase"` if you have it installed globally.

Root `.env`:

```
SUPABASE_URL=http://host.docker.internal:54321
SUPABASE_SERVICE_KEY=<local-service-role-key>
OPENAI_API_KEY=
OPEN_AI_API_KEY=
GEMINI_API_KEY=
GEMINI_MODEL_FEEDBACK=gemini-3.8-flash
GEMINI_MODEL_WORD_CARD=gemini-3.5-flash-lite
GEMINI_THINKING_LEVEL=low
AI_PROVIDER=gemini
LARA_TRANSLATE_ID=
LARA_TRANSLATE_SECRET=
USE_MISTRAL=false
API_PORT=3011
WEB_PORT=3010
NEXT_PUBLIC_API_URL=http://localhost:3011
CORS_ALLOW_ORIGINS=http://localhost:3010
```

Set `AI_PROVIDER=mock` for offline development/tests; mock feedback is flagged with `is_mock=true` and saved with `analysis_status='mock'`, never as real AI output.

Frontend `frontend/v0_lingua-log/.env.local`:

```
NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=<local-anon-key>
NEXT_PUBLIC_API_URL=http://localhost:3011
```

### One-command local start (recommended)

```bash
make dev
```

This command will:
- start local Supabase with the CLI
- write local env values
- on first run, `supabase db reset --local` (migrations + seed); afterwards only pending migrations
  are applied, so your data is kept
- build/start backend + frontend containers

Endpoints after startup:
- App: `http://localhost:3010`
- API docs: `http://localhost:3011/docs`
- Supabase Studio (table browser): `http://127.0.0.1:54323`

To wipe the local database back to the seed data, run `make reset-db`.

Demo login for local Supabase seed data:
- Email: `demo@lingualog.dev`
- Password: `DemoPass123!`

### Manual backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --reload --port 3011
```

### Manual frontend setup

```bash
cd frontend/v0_lingua-log
npm install --legacy-peer-deps
npm run dev
```

### Stop local stack

```bash
make stop
```

## 🧪 Testing

```bash
# Run all tests
make test

# Run backend tests only
make test-backend

# Manual Gemini corpus (not CI): cd backend && python -m evals.score_ref

# Run frontend tests (Vitest)
make test-frontend
```

## 📚 Documentation

- Optional Mistral dependencies: `backend/requirements-optional-mistral.txt`

## 📈 Project Status

LinguaLog is currently in active development. MVP features are being implemented, with full launch planned soon.

## 🔜 Future Features

- Speech-to-text journaling
- Vocabulary tracking
- Conversation simulator
- Mobile app
- Streaks and gamification
