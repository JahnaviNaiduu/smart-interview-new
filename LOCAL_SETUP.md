# Smart Interview Scheduler — Local Setup Guide

## Prerequisites

- Python 3.9 or higher
- Node.js 18 or higher
- Git

---

## Step 1: Get Your API Keys (All Free)

### 1A. Groq API Key (Free — AI Slot Ranking)

1. Go to https://console.groq.com
2. Sign up for a free account
3. Go to **API Keys** in the left sidebar
4. Click **Create API Key**
5. Copy the key — looks like: `gsk_xxxxxxxxxxxxxxxxxxxx`

### 1B. Resend API Key (Free — Email Notifications)

1. Go to https://resend.com
2. Sign up for a free account (use the email you want to test with)
3. Go to **API Keys** in the left sidebar
4. Click **Create API Key** → name it anything → **Full Access**
5. Copy the key — looks like: `re_xxxxxxxxxxxxxxxxxxxx`

> **IMPORTANT — Resend Test Mode Restriction:**
> In free mode, Resend can only send emails to the email address you used to sign up.
> Set `RESEND_TEST_TO_EMAIL` in your .env to that email — all emails will be redirected there.

### 1C. Google OAuth Credentials (Free — Calendar + Meet Links)

1. Go to https://console.cloud.google.com
2. Create a new project (top left dropdown → New Project)
3. Search for **"Google Calendar API"** → Enable it
4. Go to **APIs & Services → OAuth consent screen**
   - Choose **External**
   - App name: anything (e.g. "Interview Scheduler")
   - Support email: your email
   - Save
   - Under **Test users** → Add Users → add your Gmail address
5. Go to **APIs & Services → Credentials**
   - Click **Create Credentials → OAuth 2.0 Client IDs**
   - Application type: **Web application**
   - Authorized redirect URIs: `http://localhost:8000/api/v1/panelists/calendar-callback`
   - Click Create
   - Copy the **Client ID** and **Client Secret**

---

## Step 2: Clone / Unzip the Project

```bash
cd ~/Documents
# If you have the zip:
unzip smart-interview-scheduler.zip
cd smart-interview-scheduler

# If cloning from GitHub:
git clone <your-repo-url>
cd smart-interview-scheduler
```

---

## Step 3: Backend Setup

```bash
cd backend
pip3 install -r requirements.txt
```

Create the `.env` file inside `backend/`:

```
DATABASE_URL=sqlite:///./interview_scheduler.db

GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/panelists/calendar-callback

GROQ_API_KEY=your_groq_key_here

RESEND_API_KEY=your_resend_key_here
RESEND_FROM_EMAIL=onboarding@resend.dev
RESEND_TEST_TO_EMAIL=your_resend_signup_email@gmail.com

SECRET_KEY=any-random-string-here-change-this
ENCRYPTION_KEY=

FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
TOKEN_EXPIRY_HOURS=72
```

Start the backend:

```bash
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Verify it works: http://localhost:8000/api/v1/health → should return `{"status":"ok"}`

---

## Step 4: Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

---

## Step 5: Connect Google Calendar (to get Meet links)

1. Go to http://localhost:3000/panelists
2. Create a panelist using the Gmail address you added as a test user in Google Cloud Console
3. Click **Connect →** next to that panelist
4. Sign in with that Google account
5. You'll be redirected back to the panelists page — calendar is now connected
6. New bookings for this panelist will auto-generate Google Meet links

---

## Known Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| "A panelist with this email already exists" when email was deleted | Soft-delete keeps the email in DB | Already fixed in the code — it auto-reactivates |
| Google OAuth "access_denied" | Email not added as test user | Add your email in Google Cloud Console → OAuth consent screen → Test users |
| "Panelist not found" after OAuth | Route ordering bug | Already fixed in the code |
| Emails not received | Resend test mode restriction | Set RESEND_TEST_TO_EMAIL to your Resend signup email |
| AI ranking fails | Groq model name changed | Already fixed — using `groq/compound-mini` |

---

## Running Both Servers (Quick Reference)

Terminal 1 — Backend:
```bash
cd backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Terminal 2 — Frontend:
```bash
cd frontend
npm run dev
```

Then open: http://localhost:3000
