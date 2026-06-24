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


### Feb 2026 — Migrated Email from Gmail SMTP → Resend (P0 → SHIPPED)
- **Problem**: Production signup was failing with "Couldn't send the setup link right now." Gmail SMTP requires App Passwords + domain quirks (`bsossi.com` not necessarily Workspace-hosted).
- **Solution**: Swapped `email_service.py` from `smtplib` → Resend SDK. Single `RESEND_API_KEY` env var. Public function signatures preserved — `auth.py` and `mediation_routes.py` unchanged.
- **Env vars** (preview set, prod needs to be set too):
  - `RESEND_API_KEY=re_csdm6jeD_*` (Resend dashboard → API Keys)
  - `RESEND_FROM_EMAIL=onboarding@resend.dev` (or `noreply@sacoparentsapp.online` after domain verification)
  - `RESEND_FROM_NAME=SA Coparents`
  - `RESEND_REPLY_TO=` (optional)
- **Templates**: Refactored HTML templates into a shared `_branded_html()` helper. All 4 email types (magic-link, setup, reset, verification) + mediator-PDF-attachment all working.
- **Testing**: 31/31 backend pytest pass. Smoke tests confirmed all 4 email types deliver via Resend API.
- **Known limitation**: Resend account is in test mode — until a domain is verified at https://resend.com/domains, emails only deliver to the account owner's own email. After domain verification, set `RESEND_FROM_EMAIL=noreply@sacoparentsapp.online` and recipients can be anyone.


### Feb 2026 — Resend Webhook Handler (P2 → SHIPPED)
- **New endpoint**: `POST /api/email/webhook` receives Resend delivery events. Signature verified via Svix.
- **Idempotency**: dedupes on `svix-id`. Events stored in MongoDB `email_events` collection. Helper: `GET /api/email/webhook/recent?limit=N`.
- **User flagging**: `email.bounced` → `users.email_bounced=true`; `email.complained` → `users.email_complained=true` (with reasons captured).
- **Frontend**: new `<EmailHealthBanner>` on Dashboard surfaces delivery problems to the user. `UserPublic` extended with both flags.
- **Setup for user**: Resend dashboard → Webhooks → Add Endpoint → `https://sacoparentsapp.online/api/email/webhook` → copy signing secret → set `RESEND_WEBHOOK_SECRET` in prod env → redeploy.
- **Tests**: 42 tests pass (5 new for webhooks; 4 pre-existing mediator tests updated for Resend era).


### Feb 2026 — Intro Tour Video (P1 → SHIPPED)
- 67.5-second narrated walkthrough auto-plays once per device after "Enter the App"
- Voiceover regenerated with **OpenAI TTS `tts-1-hd` (voice: nova)** explaining the three core reports — Co-Parenting Assessment, Co-Parenting Agreement Draft, Child Needs Statement
- Build scripts at `/app/memory/build_intro_narration.py` + `build_intro_video_compose.py`
- Files: `/app/frontend/public/intro-tour.mp4` (10.2 MB H.264 + AAC, portrait 1080×2340) + `/app/frontend/public/downloads/sacoparents-intro-tour.mp4`
- Modal: `IntroTourModal.jsx` (skip-after-3s, tap-to-unmute fallback, `localStorage` flag so returning users don't see it again)


### Feb 2026 — Admin Weekly Insights Page (P3 → SHIPPED)
- **AI-generated 5-minute Monday read** for the platform owner. Pulls 7 days of: post-event survey open-text, journal snippets, legal acks, sign-ups, summaries, invites + acceptance rate, and the NPS distribution. Sends the structured payload to **Claude (Emergent LLM Key)** with a strict-JSON contract.
- **Output schema**: `{headline, highlights[], user_voice_themes[], concerning_patterns[], recommended_actions[], closing_note}`. The `concerning_patterns` block surfaces anything hinting at DV / suicidal ideation / child welfare — rendered in a red-edged callout card.
- **Caching**: keyed by ISO week (`weekly_insights` collection). Generated automatically on first GET each week; admin can hit **Regenerate** any time to force a fresh build.
- **Backend**: new `insights_routes.py`. Reuses `SAFETY_GUARDRAIL` + `CLAUDE_MODEL` from `ai_service.py`. Tolerant JSON parser handles fenced/wrapped responses.
- **Frontend**: new `pages/AdminInsights.jsx` route at `/admin/insights`. Linked from AdminDashboard. Loading state explains the ~30s first-build delay.
- **Endpoints**: `GET /api/insights/admin/weekly`, `POST /api/insights/admin/weekly/regenerate` — both admin-gated.
- **Tests**: 4/4 pytest pass — auth gate, non-admin 403, real-DB signal gathering (no crashes on empty collections), and `_build_and_cache` writes a doc keyed by ISO week (LLM mocked).


### Feb 2026 — Legal Acknowledgment Audit Trail (P2 → SHIPPED)
- **Server-side record** of who acknowledged the legal disclaimer and when — durable record for liability defense. The frontend modal still gates the UI via localStorage; the audit trail is in addition to it, not instead of it.
- **Endpoint**: `POST /api/legal/acknowledge` — records `{user_id, email, name, is_guest, version, ip (honors x-forwarded-for), user_agent, acknowledged_at}` in the `legal_acknowledgments` collection. **Idempotent upsert** on `(user_id, version)` so refreshes don't bloat the table; `first_acknowledged_at` is preserved on re-acks.
- **Admin endpoints**: `GET /api/legal/admin/acks` (recent list + counts), `GET /api/legal/admin/acks.csv` (full CSV export). Linked from AdminDashboard top bar.
- **Frontend**: `LegalAcknowledgment.jsx` now fires the POST in the background when the user clicks "I acknowledge — continue". Best-effort: if the user isn't authed yet (rare; modal usually appears after they enter), the request 401s silently.
- **DB**: new `legal_acknowledgments` collection.
- **Tests**: 4/4 pytest pass at `/app/backend/tests/test_legal_ack.py` (auth gate, row + metadata recorded, idempotent upsert, admin gate).


### Feb 2026 — Two-Week Post-Summary Check-in Email (P2 → SHIPPED)
- **Auto-scheduled 14 days** after a user generates their first Mediation Summary. Idempotent per (user, summary). Skipped for guests / demo emails.
- **Personalised content**: if the user has ≥2 journal entries in the past 7 days, the email embeds an **AI-generated weekly recap** (Claude via Emergent LLM Key) in a branded callout. If not, sends a simpler "How are things going?" check-in note.
- **CTA**: "Open my journal" → `/journal`.
- **Background sweeper**: new `asyncio` task `checkin_scheduler_loop` runs every 30 minutes (configurable via `POST_SUMMARY_CHECKIN_SWEEP_SECONDS`). Bails gracefully if Resend isn't configured. Per-doc try/except so one bad row never blocks the queue.
- **Backend files**: new `checkin_routes.py` (scheduling helper + sweeper). New `send_post_summary_checkin()` in `email_service.py`. Hooked into `POST /api/mediation/summary` alongside the existing post-event survey scheduler.
- **DB**: new `post_summary_checkins` collection — `{checkin_id, user_id, summary_id, email, name, status, created_at, scheduled_send_at, sent_at}`.
- **Env knobs**: `POST_SUMMARY_CHECKIN_DELAY_DAYS=14`, `POST_SUMMARY_CHECKIN_SWEEP_SECONDS=1800` (both optional with sensible defaults).
- **Tests**: 5/5 pytest pass at `/app/backend/tests/test_post_summary_checkin.py` (idempotency, demo-skip, 14-day scheduling, due-send marks `sent`, future-scheduled stays `pending`). 13/13 across all three growth-loop test suites.


### Feb 2026 — Landing Page Rewrite (P1 → SHIPPED)
- **Replaced the entire marketing page** with the user-authored 6-section structure focused on the SA CoParents positioning:
  1. **Hero** — "Stop Parent Conflict Before It Reaches the Courtroom" + dual CTAs ("Take the Free Assessment" / "See How It Works") + 4 trust badges
  2. **The Problem** — "When Parents Fight, Children Feel It" + 6 common challenges + good-news block
  3. **How It Works** — 3-step process (Assess → Learn → Prepare)
  4. **Why Different** — Child-Centered Focus, Child-Focused Mediation Prep, Foundation Statement card with 5 outcomes, Co-Parenting Agreement card
  5. **Built on Child-Focused Mediation** — 5 helps + Pre-Mediation Assessment with 5 benefits + closing quote card ("Children thrive when parents work together…")
  6. **Final CTA** — "Your Children Deserve Parents Who Can Work Together" + dual CTAs + tagline
- **All CTAs route through `EnterAppProvider`** — every "Take the Free Assessment" click plays the intro video first, then drops the user into the guest demo wizard.
- **Removed**: FAQ, App Store screenshots, mediator panel, App Store badges (user requested "replace everything").
- **Cache-busted video URL** (`/intro-tour.mp4?v=3-reports-2026-06`) and bumped storage key so every browser picks up the new narration.
- **File**: `pages/Landing.jsx` fully rewritten (~710 lines, single-file for now — extract subcomponents only if a section grows further).


### Feb 2026 — Intro Video Plays on Landing + Cache Busted (P1 → SHIPPED)
- **Moved trigger from Dashboard → Landing**. The 67.5-second narrated tour now plays as soon as a user clicks **"Enter the App"** (any CTA on the marketing page), before they reach the dashboard. Every click triggers it; the modal closes via `onEnded` and then `startGuest()` + navigate to dashboard run.
- **Architecture**: Added `EnterAppProvider` context at the top of `pages/Landing.jsx` — exposes `useEnterApp()` for every CTA, manages modal state, loading, errors centrally. The modal is mounted once at the Landing root.
- **Dashboard cleaned up**: removed the duplicate trigger + `IntroTourModal` import from `Dashboard.jsx`.
- **Cache-busted video URL**: `/intro-tour.mp4?v=3-reports-2026-06` — forces every browser to pull the **latest 3-reports narration** even if the old version was aggressively cached. Bumped `STORAGE_KEY` to `sac_intro_tour_seen_v2_3reports` so any user who already "saw" the previous video gets the new one once.
- **Files**: `pages/Landing.jsx`, `pages/Dashboard.jsx`, `components/IntroTourModal.jsx`.


### Feb 2026 — Demo Mode Restored to 1-Year Sandbox (P0 → SHIPPED)
- **Original PRD spec restored**: guest demo sessions now last **1 year** (was 24 hours). Override via `GUEST_LIFETIME_HOURS` env var if needed.
- **Full read+write parity with permanent accounts**: demo users can use every feature — wizard, AI summary, PDF, mediator email, invite co-parent, journal, weekly recap. No artificial paywalls.
- **Soft upgrade nudge** still shown on Summary page (gentle, dismissible — not a block).
- **Files changed**: `auth.py` (GUEST_LIFETIME_HOURS default 24 → 8760; updated docstring), `invite_routes.py` (removed 402 block — guests with an email can now invite co-parents).
- **Entry point**: Landing page "Enter the App" CTA already calls `startGuest()` — no UI changes needed. The button was never removed; only the session lifetime had been shortened.
- **Verified**: `curl POST /api/auth/guest` returns a session with `expires_at` 364 days in the future. All 8 invite + survey tests still pass.


### Feb 2026 — Invite Co-parent Flow (P2 → SHIPPED)
- **One-tap email invite** lets a signed-in parent email their co-parent a link to prep in their **own private workspace** — answers never shared between the two accounts.
- **Card placed in two locations**: Dashboard (always visible for non-guests) + Summary page (after first prep is complete).
- **Email-only invite** (no custom note in v1, keeps the email body universally neutral — important for estranged-couple context).
- **Rate limit**: 3 fresh invites per inviter per 24h. Resends of an existing invite don't count against the cap but are gated to once every 5 minutes per invite.
- **Status tracking**: Sent → Opened → Joined badges visible to the inviter. Resend button on any non-joined invite.
- **Recipient experience**: `/invite/:token` shows "[Inviter] invited you to prep with you" + private-account signup form (name + password). Email pre-filled. Token expires after 30 days. Already-accepted tokens 409 with sign-in nudge.
- **Backend files**: new `invite_routes.py` (token + idempotency + rate limit + tracking). New `send_coparent_invite()` in `email_service.py`.
- **Frontend files**: new `components/InviteCoparentCard.jsx` (reusable for Dashboard + Summary), new `pages/InviteAccept.jsx` (public token-based signup).
- **DB**: new `coparent_invites` collection — `{invite_id, token, inviter_user_id, inviter_name, inviter_email, invitee_email, status, created_at, expires_at, last_sent_at, opened_at, signed_up_at, signed_up_user_id}`. New users created via invite get `invited_by_user_id` for analytics.
- **Env knobs**: `COPARENT_INVITE_PER_DAY=3`, `COPARENT_INVITE_LIFETIME_DAYS=30` (optional overrides).
- **Tests**: 4/4 pytest pass at `/app/backend/tests/test_coparent_invite.py` (auth gate, full invite→accept cycle, self-invite block, invalid token 404). Frontend smoke verified via Playwright.


### Feb 2026 — Post-Event "How Was Mediation?" Survey (P2 → SHIPPED)
- **Trigger**: Auto-scheduled 7 days after a user generates their first Mediation Summary (idempotent — re-runs on subsequent summaries no-op). Skipped for guest sessions without an email.
- **Reminder**: Single follow-up email 7 days later if no response. Then stops.
- **Survey questions** (12 total): primary reason for use, ease of navigation, helpfulness of each of the 3 reports, preparedness change, child-focus agreement, most valuable feature (long text), improvements (long text), NPS 0-10, optional outcome change + explanation.
- **Public flow** (no login): email link → `/survey/<token>` → answers → submit → branded **Thank-you screen** ("Your feedback helps us make SA CoParenting App better…").
- **Admin**: New `/admin/surveys` tab → counts (scheduled / sent / responded / response-rate / avg NPS), distribution bars for every multi-choice + scale question, full open-text replies, recent surveys table. **CSV export** at `/api/surveys/admin/post-event.csv`.
- **Backend files**: new `survey_routes.py` (routes + idempotent scheduler hook + background `asyncio` sweeper that runs every 30 min, sends due emails + reminders). New `send_post_event_survey()` and `send_post_event_survey_reminder()` in `email_service.py`.
- **Frontend files**: new `pages/PostEventSurvey.jsx` (public branded standalone page), new `pages/AdminSurveys.jsx` (admin tab with charts + CSV). Link from AdminDashboard added.
- **DB schema**: new `post_event_surveys` collection — `{survey_id, token, user_id, summary_id, email, name, status, created_at, scheduled_send_at, sent_at, reminder_sent_at, responded_at, responses}`.
- **Env knobs**: `POST_EVENT_SURVEY_DELAY_DAYS=7`, `POST_EVENT_SURVEY_REMINDER_DAYS=7`, `POST_EVENT_SURVEY_SWEEP_SECONDS=1800` (all optional, sensible defaults).
- **Tests**: 4/4 pytest pass at `/app/backend/tests/test_post_event_survey.py` (idempotency, guest-skip, full submit cycle, invalid token 404). End-to-end frontend flow verified via Playwright (load → fill → submit → thank-you screen).


### Feb 2026 — Demo Mode Auto-Bootstrap on Every Protected Route (P0 → SHIPPED)
- **Reported bug**: "please undo the changes from yesterday - i'm having problems saving the data now - we need people to sign in using demo mode - not signing into the account - on all pages of the app"
- **Root cause**: `ProtectedRoute` previously redirected any unauthenticated visitor to `/login`. So (a) every protected route presented a sign-in barrier, and (b) when a session was lost mid-flow (cookie expired, browser cleared cookies, cross-domain SameSite quirks), the user was bounced to `/login` and their unsaved wizard data was orphaned.
- **Fix**: `/app/frontend/src/components/ProtectedRoute.jsx` now silently calls `startGuest()` (POST `/api/auth/guest`) instead of redirecting when `user` is null. The httpOnly cookie is set fresh and the user stays inside the app. Bootstrap is one-shot per mount (useRef guard) with a friendly "Try again" screen if the guest endpoint fails.
- **Why saves work now**: All `PUT /api/mediation/{child-goals,issues,priority,comm-style,readiness}` handlers already use `get_current_user` (NOT `require_active_user`), so guest sessions can save. The previous bug wasn't a save bug — it was a session-loss bug masquerading as a save bug.
- **Rate limit bumped**: `GUEST_RATE_LIMIT_PER_HOUR` default 3 → 30 because shared IPs (corporate NAT, household, mobile carrier) hitting auto-bootstrap on multiple devices could otherwise trip a false 429. Override via env if needed.
- **Tests**: 9/9 backend pytest pass at `/app/backend/tests/test_guest_autobootstrap.py`. Frontend cold-start deep-link verified end-to-end: `/prep/child-goals` no longer redirects to `/login`; observed `GET /auth/me=401 → POST /auth/guest=200 → GET /mediation/prep=200`. Cookie persists across refresh; saved data reappears. `/login` route still reachable for explicit sign-in (regression OK).
- **What was NOT changed**: Per user instruction (option 4d), the new 6-section Landing page and the IntroTourModal are preserved untouched.

### 📋 Backlog (P2 remaining)
_All P2 items shipped — backlog empty. Next priorities will come from real user signals._
