# Karma - AI-Powered Task Suggestions

## Overview
Karma is a multi-agent AI-powered web application that helps users make productive use of small time blocks by suggesting tasks from their todo lists based on available time, energy level, and emotional state.

## Current Branch
**ss/front-end-backend** - React frontend + FastAPI backend split architecture (synced with remote)

## Project Architecture
- **Backend**: FastAPI (Python 3.11) with SQLite database
- **Frontend**: React 18 + TypeScript + Vite + TailwindCSS
- **AI**: OpenAI GPT-4o-mini integration
- **Auth**: Clerk authentication (optional)

## Project Structure
```
karma/
├── backend/                 # FastAPI Python backend
│   ├── app/
│   │   ├── agents/          # AI agents (orchestrator, analyzer, suggester, etc.)
│   │   ├── config/          # External config files
│   │   │   └── starter_tasks.json  # 6 categories × 4 tasks each
│   │   ├── database/        # SQLite + SQLAlchemy
│   │   ├── routes/          # API endpoints (incl. onboarding.py)
│   │   ├── auth.py          # Clerk authentication (CLERK_ENABLED flag)
│   │   ├── config.py        # Configuration
│   │   └── main.py          # FastAPI app
│   └── requirements.txt
│
├── frontend/                # React + TypeScript frontend
│   ├── src/
│   │   ├── api/             # API client
│   │   ├── components/      # React components
│   │   └── pages/           # Page components (incl. EmptyStatePage.tsx)
│   ├── package.json
│   └── vite.config.ts
│
└── docker-compose.yml
```

## Configuration
Environment variables:
- `OPENAI_API_KEY`: OpenAI API key (optional - dummy mode works without)
- `OPENAI_KARMA`: Set to "true" to enable AI
- `OPENAI_MODEL`: OpenAI model (default: gpt-4o-mini)
- `CLERK_SECRET_KEY`: Clerk secret key (optional)
- `VITE_CLERK_PUBLISHABLE_KEY`: Clerk publishable key for frontend (optional)

## Running the App
Two workflows are configured:
- **Backend API**: Runs on port 8000 (`cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`)
- **Frontend**: Runs on port 5000 (`cd frontend && npm run dev`)

## Deployment
Configured for autoscale deployment:
- Build: `cd frontend && npm install && npm run build`
- Run: `cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 5000`

## Dev-Only Preview Hooks
- `?emptyState=1` on the home page renders the Empty State / Intro screen (gated by `!import.meta.env.PROD`)

## Key Patterns
- **Cache invalidation**: After any mutation that changes task count (add, delete, complete, archive, onboarding), both `['tasks']` and `['stats']` TanStack Query caches must be invalidated.
- **Auth bypass for testing**: Setting `CLERK_SECRET_KEY=""` in `backend/.env` and commenting out `VITE_CLERK_PUBLISHABLE_KEY` in `frontend/.env` disables Clerk auth; backend returns `legacy-user`.

## Recent Changes
- 2026-03-07: Added onboarding persistence — `POST /api/onboarding/complete` endpoint (body: `{task_text, categories}`) persists user-entered tasks and starter-category tasks via AI analysis. Starter task catalog externalized to `backend/app/config/starter_tasks.json` (6 categories × 4 tasks). Frontend `EmptyStatePage` wired to call the API on "Save & Continue". Fixed stale cache bugs in BrowsePage (delete/archive now also invalidate `['stats']`).
- 2026-02-28: Added EmptyStatePage component + dev-only preview hook (?emptyState=1) in HomePage
- 2026-02-15: Deterministic task selection: TaskSuggester temp=0.0, exact energy match, time-tightness gap<=2, code-level pre-filtering
- 2026-02-15: QuickWin time-tightness: estimated_minutes clamped to [available-2, available], temp=0.7
- 2026-02-15: Post-LLM validation: selected task_id checked against eligible list, subtask estimates validated
- 2026-02-15: Debug logging in BaseAgent for all agent LLM interactions (system prompt, user prompt, raw response, tokens)
- 2026-01-15: Synced with remote ss/front-end-backend branch (latest: "subtasks slider")
- 2026-01-15: Fixed unused import in Layout.tsx, updated fastapi-clerk-auth version
- 2026-01-15: Configured Vite for port 5000 with allowedHosts
