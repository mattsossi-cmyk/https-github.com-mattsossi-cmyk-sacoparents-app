# SA Coparents — Relational Mediation Prep App (PRD)

## Original problem statement
A web app that guides separated/divorced parents from emotionally reactive →
child-centered → prepared for relational mediation. Calm, structured,
non-judgmental, supportive. Eleven screens spec'd: Welcome, Account,
Orientation, Child-Centered Goals, Personal Reflection, Issues & Concerns,
Priority Ranking, Communication Style, Readiness Check, Mediation Prep
Summary, Resource Center.

## User choices (Feb 12, 2026)
- Auth: **JWT email/password + Emergent-managed Google social login**
- AI: **Claude Sonnet 4.5** via `emergentintegrations` + `EMERGENT_LLM_KEY`
- PDF: **fpdf2** downloadable summary
- Design: Soft & calm earthy tones (sage/sand/cream) — Cormorant Garamond + Manrope
- Scope: Focused MVP (auth + core prep + summary)

## User personas
- **Primary**: A separated parent preparing for a mediation session, often
  emotionally activated; needs structure and dignity.
- **Secondary**: A mediator receiving the generated PDF summary.

## Architecture
- **Frontend**: React 19 + Tailwind + shadcn/ui + sonner + lucide-react
  - Routes: `/`, `/login`, `/register`, `/auth/callback`, `/dashboard`,
    `/prep/{child-goals|issues|priority|communication|readiness}`,
    `/summary`, `/resources`
- **Backend**: FastAPI on `:8001`, all routes prefixed `/api`
  - `auth.py` — JWT (`/auth/register|login|me|logout|profile`) +
    Emergent Google session exchange (`/auth/google/session`)
  - `mediation_routes.py` — prep CRUD, AI analyze & summary, PDF, resources
  - `ai_service.py` — Claude `claude-sonnet-4-5-20250929` via emergentintegrations
  - `pdf_service.py` — fpdf2 mediator-ready PDF
- **DB**: MongoDB collections: `users`, `user_sessions`, `prep_data`, `summaries`

## Implemented (Feb 12, 2026)
- Landing page with hero + philosophy strip + 5-step preview
- Auth: JWT register/login, Emergent Google OAuth flow + AuthCallback,
  protected routes
- Dashboard: progress bar, 5 module cards + Summary + Resources cards
- Child-Centered Goals wizard step (checkboxes + 3 free-text prompts)
- Issues & Concerns wizard step (5 categories + safety section)
- Priority Ranking with drag-and-drop into 4 buckets, seeded from issues
- Communication Style assessment quiz + AI Claude reflection card
- Readiness Check 1-5 Likert scale + dynamic Needs Support/Moderately
  Ready/Prepared label
- AI-generated Mediation Summary (Claude) with PDF download (fpdf2)
- Summary history persisted per user
- Resource Center with category filter and 6 seeded resources
- All flows verified by testing subagent — 15/15 backend tests pass

## P0 backlog (next iteration)
- App Orientation screen (philosophy explainer before first wizard step)
- Personal Reflection screen (private journal-style prompts, locked from share)
- "Invite co-parent" — shared/private toggle + share-with-mediator link
- Email PDF directly to mediator

## P1
- Animated wizard transitions (framer-motion)
- Breathing/grounding mini-exercises in Communication Style step
- Save draft summary edits before PDF export

## P2
- Mediator-facing read-only review page
- Multi-language (en/zh/es) support
- Calendar reminders for mediation date

## Test credentials
See `/app/memory/test_credentials.md`
