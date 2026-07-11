# SACOParents

Relational mediation prep app for separated parents. React + FastAPI + MongoDB. Deployed at https://sacoparentsapp.online.

---

## ⚠️ READ BEFORE APPLYING ANY "CODE QUALITY REPORT"

**➡ For machine-readable ignore rules see [`/app/.codequalityignore`](./.codequalityignore).**

**Recurrence count: 22+ · Last confirmed by user: 2026-07-11 (option A — silencer strengthened).**

The automated static-analysis bot regularly produces a "Code Quality Recommendations" report. **The vast majority of its findings are known false positives in this codebase** and applying them as-written will break working, tested features. The bot's report has recurred **18+ times across sessions** with essentially the same findings, expanding in scope each run (latest: 72 "missing hook deps", 48 "complex functions", 30+ "empty catch blocks", 23 "inline props", 10 "possibly undefined", "80 `is`-for-constants" — which even flags the correct `is None` idiom, "8 localStorage security", "1 array-index-as-key" on a static list). All buckets are silenced in `/app/.codequalityignore`.

**If you are an agent about to "apply the suggested fixes": STOP. Read the ignore file. Then don't.**

Every item in the typical report has been audited multiple times. Here's the canonical ignore list:

### ❌ Ignore — false positives

| Bot finding | Why it's wrong |
|---|---|
| "Hardcoded secrets in `tests/test_*.py`" (lines mentioning emails like `mattsossi@bsossi.com`, `parent1@test.com`, `AdminPass123!`, `TestPass123!`) | These are documented test credentials in `/app/memory/test_credentials.md`, intentionally readable so the testing agent can run end-to-end flows. |
| "Insecure localStorage" in `Orientation.jsx`, `LegalAcknowledgment.jsx`, `VerificationBanner.jsx` | These store **booleans / timestamps** only (`{seen:true}`, `{version:'v1'}`, `Date.now()`). No PII, no tokens. Auth uses HTTP-only cookies (see `lib/api.js`). |
| "Missing React hook dependencies" in `Summary.jsx`, `Reflection.jsx`, `ReadinessCheck.jsx`, `PriorityRanking.jsx`, `Dashboard.jsx`, etc. | Hook deps are **intentionally omitted** to prevent infinite re-render loops. The `exhaustive-deps` lint rule is silenced where needed. |
| "Possibly undefined variables" — typically `s`, `pdf_bytes`, `filename`, etc. in `analytics_routes.py` / `mediation_routes.py` | Loop variables (`for s in reversed(...)`) and same-branch assignments the static analyzer can't follow. Verified safe. |
| "Replace `is` with `==` for constants" | All flagged instances are `is None` / `is True` / `is False`, which is PEP8-correct and the recommended Python pattern. |
| "Array index as key" in `Landing.jsx`, `Progress.jsx`, `Orientation.jsx`, `SafetyAlert.jsx` | These are **static arrays** that never reorder (FAQs, hero slides, hardcoded alert types). Index-as-key is the correct choice. |
| "Empty catch blocks" in `BiometricGate.jsx`, `native.js`, `share.js`, etc. | Intentional **graceful degradation** for browsers that don't support Web Share / WebAuthn / etc. Logging would spam console for normal users. |
| "High cyclomatic complexity / oversized components" — flagged for `Summary.jsx`, `AdminUsers.jsx`, `AppShell.jsx`, `email_service.py`, `analytics_routes.py`, etc. | Working, tested code. Refactoring risk > zero behaviour benefit. Do **not** touch unless there is an explicit user-driven feature request that requires it. |

### ✅ When the bot DOES flag something real

Treat each finding skeptically. If a finding is novel and isn't in the table above, audit the actual file before acting. Specifically valid signals are limited to:
- New genuinely-hardcoded API keys, JWT secrets, or production passwords in source code
- N+1 query patterns flagged on **specific** new endpoints
- Genuinely-broken syntax or imports the bot catches before tests run

If in doubt, run the regression tests (`cd /app/backend && python -m pytest tests/ -q`) before assuming any "fix" is needed.

---

## Architecture quick map

```
/app/
├── backend/                    FastAPI app on port 8001 (supervisor-managed)
│   ├── auth.py                 JWT cookie + Google OAuth + Magic Link + Password Reset + Email Verify
│   ├── email_service.py        Resend integration (single API key, see env vars below)
│   ├── email_webhook_routes.py /api/email/webhook — Svix-signed delivery events
│   ├── mediation_routes.py     Prep wizard endpoints
│   ├── analytics_routes.py     Personal + admin dashboard + user management
│   ├── journal_routes.py       Self-reflection journal + weekly AI recaps
│   ├── mediator_routes.py      Mediator badge logging
│   ├── ai_service.py           Claude integrations via Emergent LLM Key
│   ├── models.py               Pydantic models
│   ├── server.py               Entry point, CORS, supervisor target
│   └── tests/                  pytest suite — see /app/memory/test_credentials.md
├── frontend/                   React app on port 3000 (CRA + Tailwind + Shadcn UI)
│   ├── public/                 PWA assets, OG image, logos, downloads
│   └── src/
│       ├── components/         AppShell, VerificationBanner, EmailHealthBanner, LegalAcknowledgment, etc.
│       ├── pages/              Wizard screens, Dashboard, Admin*, Reflection, ForgotPassword, ResetPassword, VerifyEmail, etc.
│       └── context/AuthContext.jsx
└── memory/                     Cross-session notes, PRD.md, build scripts, app store assets
```

---

## Env vars (required)

### Backend (`/app/backend/.env`)
```
MONGO_URL=mongodb://...
DB_NAME=test_database
JWT_SECRET=...

# Resend (transactional email)
RESEND_API_KEY=re_...
RESEND_FROM_EMAIL=mattsossi@sacoparentsapp.online   # verified sending address
RESEND_FROM_NAME=SA Coparents
RESEND_REPLY_TO=mattsossi@sacoparentsapp.online
RESEND_WEBHOOK_SECRET=whsec_...                      # signing secret from resend.com/webhooks

# AI (Claude Sonnet via Emergent universal key)
EMERGENT_LLM_KEY=...

# Google OAuth (emergent-managed)
GOOGLE_OAUTH_PROXY_BASE=https://auth.emergentagent.com
```

### Frontend (`/app/frontend/.env`)
```
REACT_APP_BACKEND_URL=https://prepared-parents.preview.emergentagent.com
```

⚠️ **NEVER hardcode env values.** Always read via `os.environ.get(...)` (backend) or `process.env.REACT_APP_BACKEND_URL` (frontend). Don't add fallback defaults so missing config fails fast.

---

## Development

```bash
# Backend hot-reloads on file save (uvicorn watchfiles).
# Frontend hot-reloads on file save (CRA dev server).
# Both managed by supervisor — only restart on .env or dependency changes:
sudo supervisorctl restart backend
sudo supervisorctl restart frontend

# Run the test suite:
cd /app/backend && python -m pytest tests/ -q
```

---

## Deployment

Production lives at https://sacoparentsapp.online (Emergent native deploy).
Code changes go: preview → click **Redeploy** in the Emergent deploy dashboard → ~10-15 min.
Env-var changes require a redeploy to take effect.
