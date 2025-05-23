# 📘 PLANNING.md — Project Overview

## 🧠 Project Name
**LinguaLog** – AI-Powered Language Learning Journal

## 🎯 Purpose
LinguaLog helps users improve language fluency by writing daily journal entries in their target language and receiving immediate AI feedback.

## 🧩 Core Features
- Journal entries in text (and eventually audio)
- Grammar & fluency correction
- Native-like rewrite suggestions
- Direct translation side-by-side
- Fluency scoring system (0–100)
- Emotional tone and style detection
- Visual progress tracking over time
- Supabase-based user authentication and data storage

## 🔐 Target Users
- Language learners (A2–C2 level)
- Study abroad students
- Immigrants learning English
- Self-taught polyglots

## 💻 Technology Stack
| Layer        | Stack               |
|--------------|---------------------|
| Frontend     | React + Tailwind CSS |
| Backend      | FastAPI (Python)     |
| AI Feedback  | Claude or o3 via API |
| Database     | Supabase (Postgres)  |
| Auth         | Supabase             |
| Deployment   | Docker → Railway     |

## 🧠 AI Feedback Components
1. **Grammar Correction**
2. **Fluent Rewrite**
3. **Fluency Score** (0–100 based on length, cohesion, vocabulary, syntax)
4. **Tone & Emotion Analysis**
5. **Direct Translation**
6. **Explanation of Mistakes** (optional toggle)
7. **Feedback History** for all entries

## 📊 Progress Dashboard (Planned for v2)
- Daily streaks
- Tone trends
- Vocab diversity
- Fluency growth line graph

## 📈 MVP Goals
- User can create an account
- Write a journal entry
- Receive AI feedback (corrections, rewrite, score, tone)
- View past entries + feedback

## 🔜 Future Features (v2+)
- Speech-to-text journaling
- Vocabulary tracking
- Conversation simulator
- Mobile app
- Streaks and gamification 