

# 📝 LinguaLog — AI-Powered Language Learning Journal

LinguaLog helps users improve fluency in their target language by writing daily journal entries and receiving intelligent feedback powered by AI.

Users receive grammar corrections, fluent rewrites, fluency scores, tone/emotion analysis, and side-by-side translations — all stored and tracked for visible progress over time.

---

## 🚀 Features

- ✍️ Journal entry interface with instant feedback
- ✅ AI-powered analysis:
  - Grammar correction
  - Native-style rewrite
  - Fluency score (0–100)
  - Tone & emotion detection
  - Side-by-side translation
- 📚 View past entries + progress over time
- 🔐 Supabase Auth & Postgres storage
- 📊 Future: visual dashboard, voice journaling, gamification

---

## 🧠 Tech Stack

| Layer        | Tech                         |
|--------------|------------------------------|
| Frontend     | React, Tailwind CSS          |
| Backend      | FastAPI (Python)             |
| AI Feedback  | Claude or o3 via API         |
| Database     | Supabase (PostgreSQL)        |
| Auth         | Supabase Auth                |
| Deployment   | Docker → Railway or Vercel   |

---

## 📂 Project Structure

lingualog/
├── backend/
│   ├── server.py                # FastAPI server
│   ├── feedback_engine.py       # LLM integration + feedback logic
│   └── tests/                   # Pytest unit/integration tests
│
├── frontend/
│   ├── components/
│   │   └── JournalEditor.tsx    # Main journal UI
│   └── pages/                   # Routing and views
│
├── PLANNING.md                  # High-level vision and goals
├── TASK.md                      # Project task tracking
├── README.md                    # You’re here.
├── .env.example                 # Environment variable template
└── dockerfile                   # Containerization setup

---

## 🛠️ Setup & Development

### 1. Clone the repo
```bash
git clone https://github.com/gabriel.m.sambo/lingualog.git
cd lingualog

2. Backend Setup

cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Copy .env.example → .env and add Supabase keys

3. Frontend Setup

cd frontend
npm install
npm run dev


⸻

🔐 Environment Variables

Add the following in your .env file:

SUPABASE_URL=your-project-url
SUPABASE_SERVICE_KEY=your-service-key
SUPABASE_ANON_KEY=your-anon-key
OPENAI_API_KEY=your-openai-or-claude-key


⸻

✅ Running Tests

# From backend/
pytest tests/


⸻

🐳 Docker

To build and run the project as a container:

docker build -t lingualog .
docker run -p 8000:8000 lingualog


⸻

🧭 Roadmap
	•	Supabase Auth
	•	MVP API endpoints
	•	AI feedback with Claude/o3
	•	Frontend journaling UI
	•	Fluency trend dashboard
	•	Speech-to-text journaling
	•	Mobile app

⸻

📄 License

MIT License. See LICENSE for more.

⸻

🤝 Contributing

Pull requests and ideas welcome!
Contact: gabrielsambo [at] gmail.com