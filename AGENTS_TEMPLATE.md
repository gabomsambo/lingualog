# AGENTS.md

This project is a modular AI agent deployment system with RAG capabilities, real-time streaming chat, and document processing pipelines.

## Architecture Overview

Three independently deployable components:
- **backend_agent_api**: Pydantic AI agent with tools (RAG, web search, image analysis, code execution)
- **backend_rag_pipeline**: Document processor for local files and Google Drive
- **frontend**: React/TypeScript with SSE streaming and Supabase integration

## Development Environment

### Quick Start Commands

```bash
# Backend Agent API
cd backend_agent_api && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn agent_api:app --reload --port 8001

# RAG Pipeline (Local Files)
cd backend_rag_pipeline && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python Local_Files/main.py --directory "./data"

# Frontend
cd frontend && npm install && npm run dev
```

### Testing

```bash
# Backend: pytest
# Frontend: npm test (Playwright)
```

## Core Technologies

- **Agent Framework**: Pydantic AI with MCP support
- **API**: FastAPI with SSE streaming
- **Database**: Supabase (PostgreSQL + pgvector)
- **Frontend**: Vite + React 18 + TypeScript + Shadcn UI
- **Testing**: pytest + Playwright

## Code Style

- **Python**: PEP8, type hints required, async-first
- **TypeScript**: Functional components, interfaces over types
- **Line length**: 100 characters max
- **No comments** unless absolutely necessary

## Environment Configuration

Each component needs `.env` file (copy from `.env.example`):
- LLM providers (OpenAI/Ollama)
- Supabase credentials
- Embedding configuration

## Key Integration Points

- Agent ↔ Database: Vector search via `retrieve_relevant_documents_tool`
- RAG Pipeline → Database: Stores chunks in `documents` table
- Frontend ↔ Agent: SSE streaming via `/api/pydantic-agent`
- Frontend ↔ Database: Direct Supabase client

## Security

- Never commit secrets
- Use environment variables
- Validate inputs with Pydantic
- RestrictedPython for code execution

## Documentation

Detailed patterns (don't write to this folder, this is just for your reference): PRPs/ai_docs/
- Backend patterns: PRPs/ai_docs/backend_patterns.md
- RAG pipeline: PRPs/ai_docs/rag_patterns.md
- Frontend patterns: PRPs/ai_docs/frontend_patterns.md
- Testing patterns: PRPs/ai_docs/testing_patterns.md

## Common Issues

- Vector dimension mismatches: Check embedding model (1536 for OpenAI, 768 for Ollama)
- CORS errors: Verify VITE_AGENT_ENDPOINT
- Port conflicts: 8001 (agent), 8081 (frontend dev)