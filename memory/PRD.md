# SACOParents — Helping Families Communicate Better

## 🎯 Original Problem Statement

A modern co-parenting communication & support platform that helps separated and divorced parents create healthier communication patterns while keeping the emotional well-being of their children at the center. Moves parents from emotionally reactive to child-centered and prepared for relational mediation. Built for separating parents in South Africa and the US (San Antonio area).

> **Visual identity (Feb 2026 rebrand):** Deep royal purple → teal gradient. Brand mark: stylized heart-shaped family. Wordmark: `SACOParents` (single word, capital SACO, lowercase parents).

## 👥 Users / Personas

| Persona | Need |
|---|---|
| **Parent preparing for mediation** | Structured pre-work, AI-synthesized summary, safety tools |
| **Parent in high-conflict situation** | Quick Exit, hotlines, parallel-parenting alternative |
| **Mediator / family lawyer** | Clients arriving prepared with child-centered documents |
| **Survivor / at-risk user** | Inline crisis resources via keyword detection |

## 🧰 Tech Stack

- **Frontend:** React 19 + Craco + Tailwind + Shadcn UI
- **Backend:** FastAPI + Motor (async MongoDB)
- **Database:** MongoDB (preview: local; production: Atlas)
- **AI:** Claude Sonnet 4.5 via Emergent LLM key (no Anthropic SDK directly)
- **Auth:** JWT HttpOnly cookies + Emergent-managed Google OAuth
- **PDF:** FPDF2 (with embedded brand assets)
- **Mobile:** Capacitor 7 (iOS + Android wrappers), PWA, biometric login
- **CI/CD:** GitHub Actions (Android `.aab` + iOS `.ipa`)
- **Hosting:** Emergent native deployment at `https://sacoparentsapp.online`

## 🌐 URLs

| Purpose | URL |
|---|---|
| **Production** | https://sacoparentsapp.online |
| **Preview / dev** | https://prepared-parents.preview.emergentagent.com |
| **GitHub repo** | https://github.com/mattsossi-cmyk/sacoparents-app |
| **Privacy** | https://sacoparentsapp.online/privacy |
| **Terms** | https://sacoparentsapp.online/terms |
| **Account Deletion** | https://sacoparentsapp.online/delete-account |
| **Safety** | https://sacoparentsapp.online/safety |

## 🆔 Identifiers

- **Android package / Apple Bundle ID:** `com.bsossi.sacoparents`
- **App name:** `SA Coparents`
- **Display tagline:** "Relational Mediation Prep"

## ✅ Core Features Implemented (as of May 2026)

### Auth & Account
- JWT email/password auth (HttpOnly cookie + Bearer token)
- Emergent-managed Google OAuth
- Account Deletion page (Apple/Google compliant) — instant data wipe
- Biometric gate on mobile (Capacitor Biometric plugin)

### Mediation Prep Wizard (5 steps)
- Child-Centered Goals
- Issues & Concerns (with inline safety detection)
- Priority Ranking (11 legal custody categories, strict list)
- Communication Style (sample message reframing, safety detection)
- Readiness Check

### AI Synthesis (Claude Sonnet 4.5)
- Mediation Summary
- Co-Parenting Agreement Draft
- "Things I Can Improve On" growth plan
- Longitudinal "What's Changed Since Last Time" tracking
- **All prompts have safety/scope guardrails** (no legal advice, no abuse validation, no character attacks)

### Safety Guardrails
- Inline `SafetyAlert` component on free-text fields
- Keyword detection (12/12 tests pass) — `danger` vs `support` tiers
- Real hotlines surfaced: 988 (Suicide & Crisis), 1-800-799-7233 (National DV), 911
- Dedicated Safety page with Quick Exit + parallel-parenting guidance
- Backend AI prompts hardened with 6-rule safety prefix

### Personal Reflection (P1 — built May 2026)
- 4 journaling prompts
- 4-7-8 breathing exercise widget (animated breath circle)
- Auto-save, privacy notice, link to delete
- Safety detection on entries

### App Orientation (P1 — built May 2026)
- 6-slide onboarding walkthrough
- Auto-redirects first-time users from Dashboard
- localStorage persistence, revisit link in Dashboard

### Marketing Landing Page
- Full conversion-focused site at `/` (root)
- 11 sections: Hero, Philosophy, How it works, Screenshot showcase, Features, For Mediators, Testimonials, FAQ, Final CTA, Footer
- "Coming soon" App Store + Google Play badges

### Mediator Channels
- "Email to mediator" feature (SMTP via Gmail App Password)
- Email mediator button on Summary page
- All AI documents exportable as branded PDF

### Resource Center
- Curated articles & videos (YouTube + Amazon links)
- 6 category filters (Communication / Parallel Parenting / High Conflict / Healing / Legal / Recommended Reading)

### PWA / Mobile
- `manifest.json`, `service-worker.js` for offline caching
- Capacitor scaffolding for native iOS + Android builds
- Biometric login via `@capacitor-community/biometric-auth`

### Production Infrastructure
- Mongo connection pool capped (20 max, 5s timeout) — fixes restart loop
- `/api/health` DB-free for K8s liveness probe
- CORS configured with credentials
- All env vars from `os.environ` only

### App Store Assets Generated
- iPhone screenshots (1242×2688 portrait, 1284×2778 portrait, 2688×1242 landscape)
- Marketing portrait compositions with branded captions (1242×2688)
- Tablet screenshots (10-inch)
- Chromebook screenshots (1920×1080)
- App icon (1024×1024)
- Google Play Feature Graphic (1024×500) — branded
- Routing App Coverage placeholder GeoJSON
- iOS encryption-exemption Info.plist patch script (`patch-ios-encryption-exemption.js`)

### CI/CD Pipelines
- `.github/workflows/android-aab.yml` — produces signed Android App Bundle, prints SHA-1 + SHA-256 fingerprints
- `.github/workflows/ios-build.yml` — produces signed iOS `.ipa`, auto-uploads to TestFlight
- `codemagic.yaml` — backup Codemagic config for iOS

## 🛑 Currently Blocked

### iOS — "You must choose a build" in App Store Connect
**Status:** Workflow exists; user needs to complete one-time signing setup
**Blockers:**
- User has Apple Developer account ✅
- Needs to: generate CSR + private key (in progress — Stage 2a), submit to Apple, convert to `.p12`, generate provisioning profile, add 8 GitHub Secrets
- Full guide at `/memory/IOS_BUILD_GUIDE.md`

### Android — `.aab` not yet built
**Status:** Workflow exists; user needs to add 4 GitHub Secrets (keystore + passwords)
**Blockers:**
- User needs to: generate keystore at androidkeystoregenerator.com → base64-encode → add to GitHub Secrets → run workflow
- Full guide at `/memory/GITHUB_ACTIONS_GUIDE.md`

### Production AI Summary failing (from original handoff)
**Status:** Possibly resolved by latest deployment fixes (Mongo connection pool cap, DB-free health endpoint) — needs user verification
**Blocker:** User must verify `EMERGENT_LLM_KEY` is set in Emergent deploy env vars and redeploy

### Google OAuth on custom domain
**Status:** Awaiting Emergent support whitelist
**Blocker:** User must email support@emergent.sh with `sacoparentsapp.online`

## 📋 Backlog (P2)

- Invite Co-parent flow (magic link sharing)
- Demo sandbox / "try without signing up" (24-hour guest session)
- Mediator dashboard / partner portal
- Push notifications (currently stub MOCKED at `/api/mediation/devices/register`)
- App Clip / instant access (iOS-only, requires Mac for build)
- Promotional graphics for Instagram / Facebook / LinkedIn

## 🧪 Test Credentials

See `/app/memory/test_credentials.md`

## 📁 Project Structure

```
/app/
├── backend/
│   ├── server.py             # FastAPI entry, Mongo pool config, /api/health
│   ├── auth.py               # JWT + Google OAuth + DELETE /account
│   ├── models.py             # Pydantic + MongoDB models
│   ├── mediation_routes.py   # All /api/mediation/* endpoints
│   ├── ai_service.py         # Claude AI with safety guardrails
│   ├── pdf_service.py        # FPDF2 PDF generation
│   ├── email_service.py      # SMTP mediator emails
│   └── .env                  # All secrets (gitignored)
├── frontend/
│   ├── src/
│   │   ├── pages/            # Landing, Dashboard, all 5 prep steps, Summary, Reflection, Orientation, Safety, Privacy, Terms, DeleteAccount, Login, Register, Resources
│   │   ├── components/       # AppShell, BiometricGate, BreathingExercise, SafetyAlert, WizardLayout, ui/*
│   │   ├── lib/              # api, logger, native, safety
│   │   ├── context/          # AuthContext
│   │   └── App.js            # Routes
│   ├── public/               # PWA manifest, service worker, branded assets, marketing/
│   ├── capacitor.config.ts
│   ├── scripts/patch-ios-encryption-exemption.js
│   └── package.json
├── .github/
│   ├── workflows/
│   │   ├── android-aab.yml
│   │   └── ios-build.yml
│   └── scripts/inject-signing.py
├── memory/
│   ├── PRD.md                # This file
│   ├── ANDROID_BUILD_GUIDE.md
│   ├── GITHUB_ACTIONS_GUIDE.md
│   ├── IOS_BUILD_GUIDE.md
│   ├── APP_STORE_SUBMISSION_PACK.md
│   ├── APP_SUMMARY.md
│   └── app_store_assets/     # All screenshots, icons, feature graphic, CSVs, GeoJSON
├── codemagic.yaml
└── package.json              # Monorepo manifest (for CI detection)
```

## 🚀 Deployment Notes

- **Hot reload** for frontend + backend in preview
- Supervisor manages services (`sudo supervisorctl restart {frontend|backend}`)
- Production env vars must include: `MONGO_URL`, `DB_NAME`, `JWT_SECRET`, `CORS_ORIGINS`, `EMERGENT_LLM_KEY`, `SMTP_PASSWORD`
- After every redeploy: verify `EMERGENT_LLM_KEY` is still set (the most common cause of AI failures in prod)

---

## 📜 Changelog

### Feb 2026 — SACOParents Visual Rebrand (entire app)
- New palette: deep royal purple `#3D1A78` → teal `#2DB5B5` gradient, with magenta/blue/green/purple accent circles
- New typography: Plus Jakarta Sans (bold display + body) + Caveat (script accents)
- New SVG brand mark: gradient heart-shaped family face — replaces legacy `sa-coparents-mark.png` across AppShell, Login, Register, Orientation
- Brand wordmark renamed from "SA Coparents" → "SACOParents" (55 references swapped)
- New utility classes: `bg-brand-gradient`, `btn-gradient`, `card-bold`, `text-brand-gradient`, `font-script`, `icon-circle-{purple,teal,magenta,blue,green}`
- Tailwind extended with `brand` palette and `brand-gradient` background image
- 600+ hex literals bulk-replaced via sed so existing wizard screens inherit the new look automatically
- Two-mode design: **Confident** (Landing/Auth/Dashboard — gradients) and **Grounded** (Wizard/Reflection/Safety — calm purple-light wash). Safety alerts stay terra/red.
- Landing page fully rewritten in brochure style: gradient hero with inline `PhoneMockup` (no static screenshots — all CSS), brochure "struggles list" with script accent, 5-feature icon-circle grid, curved wave dividers, gradient mediator panel, dark footer
- Service worker version bumped to `sac-v2` to force PWA cache eviction
- HTML metadata: title, theme-color, manifest, OG tags all renamed
- AuthCallback now shows actionable error UI with diagnostic code (e.g. `missing_session_id`, `http_401`) instead of silent redirect

### Status
- ✅ Visual rebrand verified by frontend testing agent — all 10 tested screens render cleanly, no JS errors, no legacy "SA Coparents" text in DOM
- ⏳ Google OAuth on production `sacoparentsapp.online` — diagnostic UI deployed; awaiting user redeploy + retest to capture failure code
- ⏳ Marketing assets (`/marketing/raw-*.png`) still show old branding but are no longer referenced from Landing (replaced by inline CSS `PhoneMockup`). App Store screenshot suite in `/app/memory/app_store_assets/` will need refresh before publishing.


### Feb 2026 — 24-Hour Demo Sandbox (P2 → SHIPPED)
- **New backend endpoints**: `POST /api/auth/guest` (creates a 24h guest user, IP rate-limited 3/hr) and `POST /api/auth/claim` (upgrades guest → permanent account, preserves all wizard data)
- **User model extended** with `is_guest`, `guest_expires_at`, `guest_ip` fields; `_user_by_id` now rejects expired guests at the auth layer
- **`require_active_user` dependency** added — gates premium endpoints behind sign-up. Returns HTTP 402 with the message "Save your work to unlock this feature."
- **Gated endpoints**: `POST /mediation/summary`, `POST /mediation/agreement`, `POST /mediation/improvement-plan`, `GET /summary/:id/pdf`, `GET /agreement/:id/pdf`, `POST /summary/:id/share-link`, `POST /agreement/:id/share-link`, `POST /email-mediator`
- **Frontend additions**:
  - `useAuth().startGuest()` and `useAuth().claimGuest()` actions
  - `<GuestBanner/>` — sticky top banner with live countdown + "Save my work" link, shown only when `user.is_guest`
  - `/claim` route + page — guest-only signup form that upgrades the existing user record
  - Global axios 402 interceptor → toast with "Save my work" action
  - Landing hero: new "Try it free — no signup" button next to "Start your prep — free"
- **Cost protection**: AI generation, PDF download, email send, share link — all guest-gated, so an anonymous demo session can't burn `EMERGENT_LLM_KEY` budget or generate downloadable artifacts
- **Verified end-to-end** in preview: guest creation → wizard → 402 on premium endpoint → /claim → permanent account.



### May 2026 — Personal + Admin Analytics Dashboards (P2 → SHIPPED)
- **New backend file** `/app/backend/analytics_routes.py` mounted at `/api/analytics`
- **New personal endpoint** `GET /api/analytics/me` — returns the signed-in user's progress (sections completed / total), readiness trend across past summaries, activity counts (summaries, agreements, improvement plans, mediator emails) and the 10 most recent summaries
- **New admin endpoints** gated to `ADMIN_EMAILS` (defaults to `mattsossi@bsossi.com`, override via env):
  - `GET /api/analytics/admin/overview` — users (total / new 7d / 30d / guests / claimed-from-guest / auth breakdown), engagement (summaries / agreements / improvement plans / mediator emails — totals + 7d deltas), magic-link conversion %, full prep funnel
  - `GET /api/analytics/admin/recent-users?limit=N` — recent signups enriched with per-user progress + AI counts (N capped at 100)
  - `GET /api/analytics/admin/daily-signups?days=N` — N-day signup time series (N capped at 90)
- **Frontend additions**:
  - `/progress` route (`pages/Progress.jsx`) — personal dashboard with hero progress bar, 4 stat cards, readiness sparkline, module checklist, recent summaries list
  - `/admin` route (`pages/AdminDashboard.jsx`) — owner ops dashboard with 4 top stats, daily signup chart, magic-link conversion gauge, prep funnel, auth method breakdown, recent users table; renders friendly "Admin only" message for non-owners
  - `AppShell.jsx` nav: "Progress" link for all users + conditional "Admin" link for `mattsossi@bsossi.com`
  - Dashboard hero: "View my progress →" link
- **Backend tests**: 11 pytest cases at `/app/backend/tests/test_analytics.py` covering auth gating (401 unauth, 403 non-admin, 403 guest), shape validation, day clamping, no-`_id` leak. 100% pass.


### Feb 2026 — Admin User Management Page (P0 → SHIPPED)
- **New page** `/admin/users` (`AdminUsers.jsx`) — searchable, filterable user table for the app owner:
  - Search by name/email (case-insensitive substring)
  - Filter chips: Active / Suspended / All
  - "Include guests" checkbox toggle
  - Paginated 25 rows per page with Previous / Next controls
  - Per-row actions: **Suspend** (with reason modal), **Restore**, **Reset link** (emails the user a magic-link to sign in / reset password; falls back to clipboard copy when SMTP isn't configured in preview)
  - Hard block: admin can't suspend their own account
- **AdminDashboard** now exposes a "Manage all users →" link to the new page
- **Backend fix**: `admin_send_reset_link` had a kwarg-mismatch bug (called `send_magic_link` with `link=`/`name=`/`mode=` and `await` on a sync fn) — corrected to use `link_url=`/`user_name=` and a sync call. SMTP-not-configured path now correctly returns the fallback link for clipboard copy.
- **Tests**: 11/11 pytest cases pass at `/app/backend/tests/test_admin_users.py` (auth gating, listing shape, search, suspended filter, include_guests, pagination clamp, self-suspend block, full suspend→login-403→unsuspend→login-200 cycle, reset-link). Frontend verified end-to-end by testing agent.


### Feb 2026 — Forgot Password / Reset Password Flow (P0 → SHIPPED)
- **New backend endpoints**:
  - `POST /api/auth/password-reset/request` — generates a 15-min reset token; SMTP-not-configured path logs the link instead of leaking 5xx
  - `GET /api/auth/password-reset/preview?token=…` — validates a token and returns the email (no consumption)
  - `POST /api/auth/password-reset/confirm` — updates `hashed_password`, burns the token + any siblings, sets the auth cookie (auto-signs-in)
- **New email**: `send_password_reset_link()` in `email_service.py` (matches the existing magic-link / setup-link template)
- **New frontend pages**:
  - `/forgot-password` (`ForgotPassword.jsx`) — email input → success state with "Check your inbox"
  - `/reset-password?token=…` (`ResetPassword.jsx`) — token preview → new+confirm password → auto-signin → `/dashboard`
- **Login.jsx** now has a "Forgot password?" link under the password field
- **Privacy**: unknown / suspended emails return the same human-readable message as real emails to prevent account enumeration
- **Tests**: 7/7 pytest pass at `/app/backend/tests/test_password_reset.py`; 4/4 frontend flows verified end-to-end. parent1@test.com password restored to `TestPass123!` after the test run.


### Feb 2026 — Email Verification (soft-nudge) (P1 → SHIPPED)
- **New `email_verified` field** on `UserPublic` + `users` collection (default `false`)
- **Auto-verify paths** (the user proved email ownership): Google login, magic-link sign-in (`/auth/magic-link/consume`), magic-link sign-up (`/auth/signup-from-token`), and password-reset confirm
- **New backend endpoints**:
  - `POST /api/auth/verify-email/send` (auth-required) — issues a 24h verification token + emails it; 3/hour rate-limit per user; refuses guests; returns `already_verified:true` if applicable
  - `POST /api/auth/verify-email/confirm` — consumes the token, flips `email_verified:true`; idempotent on already-used tokens
- **New email**: `send_verification_link()` in `email_service.py`
- **Register flow** best-effort issues a verification email on signup (failure does NOT block account creation)
- **Frontend**:
  - `<VerificationBanner>` on Dashboard — shown only for unverified non-guest users; "Resend email" + 24h-dismiss localStorage
  - `/verify-email?token=…` (`VerifyEmail.jsx`) — confirms token → refreshes auth → "Email confirmed" success or graceful error
- **Tests**: 13/13 backend pytest + 8/8 frontend flows pass (iteration_7.json). New test file `/app/backend/tests/test_email_verification.py`.
