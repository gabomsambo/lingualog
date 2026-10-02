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
  - Side-by-side translation
  - Explanation of mistakes
- **Progress Tracking**: View your improvement over time
- **Secure User Authentication**: Via Supabase

## 💻 Tech Stack

| Layer        | Technology          |
|--------------|---------------------|
| Frontend     | React + Tailwind CSS |
| Backend      | FastAPI (Python)    |
| AI Feedback  | Mistral-7B-Instruct-v0.3 / OpenAI (fallback) |
| Database     | Supabase (Postgres) |
| Auth         | Supabase            |
| Deployment   | Docker → Railway    |

## 🔌 API Overview

### Endpoints

- **POST /log-entry**
  - Submit a journal entry text
  - Returns comprehensive AI feedback
  
- **GET /entries**
  - Retrieve past journal entries with feedback

### Data Models

```python
# Journal Entry Request
{
  "text": "string"  # The journal entry text in target language
}

# Feedback Response
{
  "corrected": "string",     # Grammar-corrected version
  "rewritten": "string",     # Native-like rewrite
  "score": 0-100,            # Fluency score
  "tone": "string",          # Detected emotional tone
  "translation": "string",   # Direct translation
  "explanation": "string"    # Optional explanation
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

`make dev` will auto-populate local Supabase keys into those files.

Root `.env`:

```
SUPABASE_URL=http://host.docker.internal:54321
SUPABASE_SERVICE_KEY=<local-service-role-key>
OPENAI_API_KEY=
OPEN_AI_API_KEY=
GEMINI_API_KEY=
USE_MISTRAL=false
API_PORT=8000
WEB_PORT=3000
NEXT_PUBLIC_API_URL=http://localhost:8000
CORS_ALLOW_ORIGINS=http://localhost:3000
```

Frontend `frontend/v0_lingua-log/.env.local`:

```
NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=<local-anon-key>
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### One-command local start (recommended)

```bash
make dev
```

This command will:
- start local Supabase with the CLI
- run `supabase db reset --local` (migrations + seed)
- write local env values
- build/start backend + frontend containers

Endpoints after startup:
- App: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`
- Supabase Studio (table browser): `http://127.0.0.1:54323`

Demo login for local Supabase seed data:
- Email: `demo@lingualog.dev`
- Password: `DemoPass123!`

### Manual backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --reload --port 8000
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

# Run frontend tests
cd frontend/v0_lingua-log
npm test
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