# Smart Interview Scheduler — GitHub Push Guide

## IMPORTANT: Before Anything Else

The `backend/.env` file contains real API keys. **NEVER push this to GitHub.**
The `.gitignore` in this project already excludes it, but double-check before pushing.

---

## Step 1: Check the .gitignore

Make sure these are in the root `.gitignore` (they should already be there):

```
backend/.env
backend/interview_scheduler.db
backend/__pycache__/
backend/**/__pycache__/
frontend/node_modules/
frontend/.next/
*.pyc
*.db
.DS_Store
```

---

## Step 2: Initialize Git (if not already done)

```bash
cd smart-interview-scheduler

git init
git add .
git status
```

**Before committing** — scan the `git status` output and make sure you do NOT see:
- `backend/.env`
- `backend/interview_scheduler.db`
- Any file with "secret", "key", or "token" in the name

---

## Step 3: First Commit

```bash
git add .
git commit -m "Initial commit: Smart Interview Scheduler

- FastAPI backend with SQLite
- Next.js 14 frontend (glassmorphic UI)
- Google Calendar OAuth + Meet link generation
- Groq AI slot ranking
- Resend email notifications
- Token-based candidate scheduling links"
```

---

## Step 4: Create a Repository on GitHub

1. Go to https://github.com → click **New** (green button)
2. Repository name: `smart-interview-scheduler`
3. Set to **Private** (recommended — project has API key setup instructions)
4. Do NOT initialize with README (you already have one)
5. Click **Create repository**

---

## Step 5: Push to GitHub

GitHub will show you these commands after creating the repo — copy them exactly:

```bash
git remote add origin https://github.com/YOUR_USERNAME/smart-interview-scheduler.git
git branch -M main
git push -u origin main
```

---

## Step 6: Verify on GitHub

1. Open the repository on GitHub
2. Confirm you can see `backend/`, `frontend/`, `LOCAL_SETUP.md`, etc.
3. Confirm you **cannot** see `backend/.env` — if you can, stop immediately and run:

```bash
git rm --cached backend/.env
git commit -m "Remove .env from tracking"
git push
```

Then add `backend/.env` to `.gitignore` and never add it again.

---

## Sharing with a Friend / Collaborator

### Option A: Add them as a collaborator (they clone your private repo)
1. GitHub repo → **Settings → Collaborators → Add people**
2. They run: `git clone https://github.com/YOUR_USERNAME/smart-interview-scheduler.git`
3. They create their own `backend/.env` with their own API keys (see LOCAL_SETUP.md)

### Option B: Share as a ZIP
```bash
# From the project root
zip -r smart-interview-scheduler.zip . \
  --exclude "*/node_modules/*" \
  --exclude "*/.next/*" \
  --exclude "*/__pycache__/*" \
  --exclude "*.pyc" \
  --exclude "*/.env" \
  --exclude "*.db" \
  --exclude "*/.DS_Store"
```
Share the ZIP — they unzip and follow `LOCAL_SETUP.md` to set up their own API keys.

---

## For Future Updates

```bash
# Make changes, then:
git add .
git commit -m "Your commit message"
git push
```

If collaborating:
```bash
git pull origin main   # get latest changes first
# make your changes
git add .
git commit -m "Your changes"
git push
```
