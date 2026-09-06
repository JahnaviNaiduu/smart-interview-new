# Smart Interview Scheduler — Project Explanation

## What This Project Does

An end-to-end automated interview scheduling platform that:
1. Recruiter creates an interview request (job title, round type, candidate info, panelists)
2. System checks panelists' Google Calendars for availability
3. AI ranks the best time slots (timezone fit, morning preference, load balancing)
4. Candidate receives an email with a unique link to pick their preferred slot
5. On booking — Google Calendar event is created, Google Meet link is generated, confirmation emails go to all 3 parties (candidate, panelist, recruiter)

---

## Tech Stack & Why We Chose Each

### Backend: Python FastAPI
**Why FastAPI over Django/Flask?**
- Automatic API documentation at `/docs` — great for demos
- Built-in async support for background tasks (email sending, calendar events)
- Pydantic for data validation — catches bad input at the boundary
- Much faster to build APIs vs Django's ceremony

### Database: SQLite
**Why SQLite over PostgreSQL/MySQL?**
- Zero setup — no database server to install or configure
- File-based — the entire database is one `.db` file
- Perfect for hackathons and local development
- For production, swap `DATABASE_URL` to a PostgreSQL URL — SQLAlchemy handles the rest

### Frontend: Next.js 14 (App Router)
**Why Next.js over React/Vue?**
- Server components render pages faster (no blank loading flash)
- File-based routing — `/availability/[token]/page.tsx` just works
- Built-in API proxying via `NEXT_PUBLIC_API_URL`
- Deployment on Vercel is one command if needed later

### AI: Groq + compound-mini model
**Why Groq over OpenAI/Claude?**
- **Completely free** — no credit card needed for Groq's free tier
- Extremely fast inference (milliseconds per request)
- Open-source model ecosystem — not locked into one provider
- Falls back gracefully to chronological ordering if the AI call fails

**What the AI does:**
- Ranks time slots by: candidate's timezone fit, morning preference (9AM-12PM ranked higher), mid-week preference (Tue/Wed/Thu), panelist interview load
- Generates personalized email invite body (instead of a generic template)

### Email: Resend
**Why Resend over SendGrid/Mailgun?**
- The most developer-friendly API — one `resend.Emails.send()` call
- Free tier is generous (3,000 emails/month)
- Beautiful API design, great error messages
- `onboarding@resend.dev` works as a from-address with no domain setup

### Calendar + Meet Links: Google Calendar API
**Why Google Calendar?**
- Google Meet links are auto-created when you add a `conferenceData` request to a calendar event — no separate Meet API needed
- OAuth2 refresh tokens mean panelists only authorize once
- Free busy API tells us exactly when panelists are unavailable
- The most common calendar used in professional settings

---

## Architecture

```
Browser (Next.js :3000)
    │
    ├── GET /panelists         → FastAPI (:8000)
    ├── POST /interviews        →    │
    ├── GET /availability/token →    │
    └── POST /bookings          →    │
                                     │
                          ┌──────────▼──────────┐
                          │   FastAPI Backend    │
                          │                      │
                          │  ┌────────────────┐  │
                          │  │  SQLite DB     │  │
                          │  │  (file-based)  │  │
                          │  └────────────────┘  │
                          │                      │
                          │  ┌────────────────┐  │
                          │  │  Groq AI       │  │ → Slot ranking
                          │  └────────────────┘  │ → Email generation
                          │                      │
                          │  ┌────────────────┐  │
                          │  │  Google Cal    │  │ → Check busy times
                          │  │  API           │  │ → Create events
                          │  └────────────────┘  │ → Meet links
                          │                      │
                          │  ┌────────────────┐  │
                          │  │  Resend        │  │ → Invite emails
                          │  └────────────────┘  │ → Confirmations
                          └──────────────────────┘
```

---

## Key Design Decisions

### Token-based Candidate Links
Each interview request gets a UUID token (72-hour expiry, single-use). The candidate never needs an account — they just open their email link. This is the same pattern used by Calendly and scheduling tools.

### Soft-delete for Panelists
When a panelist is "removed", they're marked `is_active=False` not deleted. This preserves historical booking data. The UI only shows active panelists.

### Background Tasks for Email + Calendar
Email sending and calendar event creation happen in FastAPI `BackgroundTasks` — the API responds immediately (fast UX) while these run asynchronously.

### Glassmorphic Black & White UI
The frontend uses a single-color design system (black, white, translucent glass effects with `backdrop-filter: blur`). No accent colors — this makes it look premium and avoids needing a brand.

---

## Complete User Flow

```
Recruiter → Creates Interview Request
              ↓
         System finds slots (intersects panelist calendars)
              ↓
         AI ranks top 10 slots
              ↓
         Candidate receives email with selection link
              ↓
         Candidate picks slot (UI at /availability/[token])
              ↓
         System creates booking
              ↓
         Google Calendar event created + Meet link generated
              ↓
         3 confirmation emails sent (candidate + panelist + recruiter)
              ↓
         Interview status → "booked"
```
