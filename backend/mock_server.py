"""
Simple mock server for LinguaLog to test the frontend.
"""
import datetime
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="LinguaLog Mock API",
    description="Mock API for testing frontend",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock entries data
MOCK_ENTRIES = [
    {
        "id": str(uuid.uuid4()),
        "original_text": "Hoy he aprendido mucho sobre programación y me siento feliz.",
        "corrected": "Hoy he aprendido mucho sobre programación y me siento feliz.",
        "rewrite": "Hoy ha sido un día productivo, he aprendido bastante sobre programación y estoy muy contento con mi progreso.",
        "score": 85,
        "tone": "Reflective",
        "translation": "Today I learned a lot about programming and I feel happy.",
        "created_at": (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "original_text": "Je pense que j'ai fait beaucoup de progrès dans mon apprentissage du français.",
        "corrected": "Je pense que j'ai fait beaucoup de progrès dans mon apprentissage du français.",
        "rewrite": "Je constate que j'ai vraiment progressé dans mon apprentissage de la langue française.",
        "score": 78,
        "tone": "Confident",
        "translation": "I think I have made a lot of progress in my French learning.",
        "created_at": (datetime.datetime.now() - datetime.timedelta(days=3)).isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "original_text": "Ich möchte heute über meine Reisepläne schreiben.",
        "corrected": "Ich möchte heute über meine Reisepläne schreiben.",
        "rewrite": "Heute würde ich gerne meine Reisepläne für die kommenden Wochen beschreiben.",
        "score": 90,
        "tone": "Neutral",
        "translation": "I would like to write about my travel plans today.",
        "created_at": (datetime.datetime.now() - datetime.timedelta(days=5)).isoformat()
    }
]

@app.get("/")
async def root():
    return {"message": "Welcome to LinguaLog Mock API"}

@app.get("/entries")
async def get_entries():
    """
    Return mock journal entries.
    """
    return MOCK_ENTRIES

@app.post("/log-entry")
async def create_log_entry(entry: dict):
    """
    Process a mock journal entry.
    """
    # Create mock feedback
    feedback = {
        "corrected": entry.get("text", ""),
        "rewritten": "Improved version of your text would go here.",
        "score": 85,
        "tone": "Neutral",
        "translation": "Translation of your text would go here.",
        "explanation": "This is a mock explanation of your text."
    }
    return feedback

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001) 