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

- Python 3.10+
- Node.js 18+
- Supabase account
- Minimum 16GB RAM (for Mistral model)
- GPU with 8GB+ VRAM recommended for faster model inference

### Environment Variables

Create a `.env` file in the root directory with:

```
SUPABASE_URL=your-supabase-url
SUPABASE_SERVICE_KEY=your-service-key

# AI Model configuration
USE_MISTRAL=true
MISTRAL_MODEL_PATH=/path/to/model/directory  # Optional, defaults to $HOME/mistral_models/7B-Instruct-v0.3
HUGGINGFACE_TOKEN=your-huggingface-token  # Required for accessing the Mistral model
OPENAI_API_KEY=your-openai-key  # Only needed if USE_MISTRAL=false or as fallback
```

### Backend Setup

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Run the FastAPI server
uvicorn backend.server:app --reload
```

### Frontend Setup

```bash
# Install dependencies
cd frontend
npm install

# Run the development server
npm run dev
```

### Docker Setup (Recommended)

```bash
# Start the complete environment (API + Frontend)
docker-compose up

# The services will be available at:
# - Frontend: http://localhost:5173
# - API: http://localhost:8000
```

## 🧪 Testing

```bash
# Run all tests
make test

# Run backend tests only
make test-backend

# Run frontend tests
cd frontend
npm test
```

## 📚 Documentation

- [Mistral-7B-Instruct-v0.3 Integration](backend/MISTRAL_INTEGRATION.md): Instructions for using the Mistral model in LinguaLog
- [Example Script](backend/example_mistral.py): Demonstrates Mistral model usage for text generation and translation

## 📈 Project Status

LinguaLog is currently in active development. MVP features are being implemented, with full launch planned soon.

## 🔜 Future Features

- Speech-to-text journaling
- Vocabulary tracking
- Conversation simulator
- Mobile app
- Streaks and gamification