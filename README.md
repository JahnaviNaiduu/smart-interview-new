# Smart Interview Scheduler

An AI-powered interview scheduling platform that automates coordination between candidates, recruiters, and panelists.

## AI Usage Transparency

This project uses AI tools in the following specific ways:

| Feature | Model | What was generated | What was hand-written |
|---------|-------|-------------------|----------------------|
| Slot ranking | Llama 3.1 8B via Groq | JSON-formatted slot scores and reasoning text | Prompt design, fallback logic, integration code |
| Email personalization | Llama 3.1 8B via Groq | Email body text per round type | Prompt engineering, HTML templates, send logic |
| Code scaffolding | Claude (Anthropic) | Project structure skeleton | All business logic, scheduling algorithm, security |

All AI-generated content passes through validation layers. Prompts are fixed system prompts — user data is passed as structured JSON to prevent prompt injection.

## Tech Stack

- **Frontend:** Next.js 14 (App Router) + Tailwind CSS
- **Backend:** Python FastAPI
- **Database:** PostgreSQL + SQLAlchemy ORM + Alembic
- **Calendar:** Google Calendar API (OAuth2)
- **Email:** Resend
- **AI:** Groq API → Llama 3.1 8B Instant (open source, free tier)
- **Meetings:** Google Meet (auto-created via Calendar API)

## Setup

### 1. Backend

```bash
cd backend
cp .env.example .env
# Fill in your API keys in .env
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

### 3. API Docs

Visit `http://localhost:8000/docs` for auto-generated Swagger documentation.

## Required Credentials

1. **PostgreSQL** — local or Supabase
2. **Google Cloud** — OAuth2 credentials with Calendar API enabled
3. **Groq** — free API key at console.groq.com
4. **Resend** — free API key at resend.com (3,000 emails/month free)

## Architecture Decision Record

**Why FastAPI over Django/Flask?** Auto-generated Swagger docs, async support, Pydantic validation built-in. At 100k users: add Redis + Celery for background jobs.

**Why PostgreSQL over SQLite?** Relational joins between candidates/panelists/bookings, ARRAY type for panelist_ids, production-grade ACID guarantees.

**Why Groq over OpenAI?** Free tier, open-source models (Llama 3.1), no credit card required for hackathon.

**What breaks at 100k users first?** The per-request Google Calendar API calls. Fix: background sync of panelist calendars into Redis cache, refreshed every 15 minutes.
"# smart-interview" 
