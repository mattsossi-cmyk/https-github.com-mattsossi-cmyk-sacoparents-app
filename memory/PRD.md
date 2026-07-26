# SACOParents — Helping Families Communicate Better

<!-- Changelog latest entry -->
## 🆕 Landing Page + SEO Overhaul (Feb 2026)
Four workstreams shipped together, all frontend-visible on / :
1. **"Which assessment should I take?" guided selector** — 3-question inline quiz that maps answers to one of 4 result cards (Mediation / Safety / Special Needs / All-three). Live at #which-assessment. Full data-testid coverage for automation.
2. **Trust signals section** — 4 pillar cards (Created by Matt Sossi · Data protection · What it can/can't do · When to seek professional help) with deep links to /privacy, /data-retention, /methodology, /safety.
3. **Sample report previews** — tabbed mini-renders of Mediation Summary, Special Needs Care Plan, Safety Assessment, and Growth Snapshot so parents see the deliverable before investing time.
4. **SEO + brand rename**:
   - Canonical URL, JSON-LD schema (Organization + WebApplication + FAQPage), robots meta, keyword meta
   - Rich `<noscript>` block: h1 + subheading + assessments list + trust bullets + crisis lines (crawler-visible even before JS runs)
   - New `/robots.txt` and `/sitemap.xml` at `/public/`
   - **Brand rename** "SA Coparents" → "SA CoParents" (capital P) across 60+ files — including 7 JSX-split wordmark files caught during retest (AppShell, Login, Register, Orientation, CancelSubscription, MediatorBadge, Watch)

Testing: iteration_25 → iteration_26 fully green.

## 🆕 Phase 4 — Public Trust Pages (Feb 2026)
Published Privacy, Data-Retention, Accessibility, and Assessment-Validation info prominently across the app.
- **/accessibility** — WCAG 2.2 AA statement, keyboard shortcuts, screen-reader support, contrast policy, known gaps, contact
- **/methodology** — Full transparency about every score (Mediation Readiness, Family Violence, Special Needs 7-domain, AI Coach, Next-Three-Steps engine) including source instruments (Danger Assessment, HITS, WEB Scale, ODARA), rule locations, and honest disclosure of where we lack empirical validation
- **/data-retention** — Retention schedule table (10 data types), export & deletion workflows, GDPR/CCPA/POPIA rights, third-party processors
- **`AppFooter.jsx`** — persistent slim footer on every in-app page linking to Privacy · Terms · Data retention · Methodology · Accessibility · Crisis resources + educational-tool disclaimer
- Marketing footer on Landing page also updated with new links
- Cross-links added from Privacy → the 3 companion pages

## 🆕 Phase 2 — Selective Section Sharing (Feb 2026)
Parents can now hide any section of a report before downloading a PDF or copying a share link. Applied to all 4 report types:
- Mediation Summary (8 sections)
- Co-Parenting Agreement Draft (8 sections)
- Special Needs Care Plan (6 sections)
- Family Violence & Communication Safety Assessment (4 sections; `pathway` + `texas_resources` are locked-on for survivor safety)

Implementation:
- Shared catalog + filter helpers in `/app/backend/report_visibility.py`
- Reusable `<ReportShareControls />` React panel in `/app/frontend/src/components/`
- New endpoints per report:
  - `GET /api/mediation/reports/sections/{report_type}` — catalog
  - `PATCH /api/mediation/summary/{id}/visibility` (+ agreement/sn_report/safety variants)
  - Existing PDF endpoints extended with `?excluded=csv` query override
  - Existing `share-link` POST endpoints extended to accept `{"excluded":[...]}` body; the list is JWT-snapshotted as `ex` so recipients see the exact view chosen at share time
- 33 automated backend tests (9 unit + 24 HTTP) — all passing.



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

### Gmail Integration (Feb 2026 — this session)
- Google OAuth 2.0 connect flow at `/gmail` (frontend) with `Connect Gmail` card on `/my-plan`
- Backend routes: `GET /api/oauth/gmail/{login,callback}`, `GET /api/gmail/status`,
  `POST /api/gmail/disconnect`, `GET /api/gmail/messages` (with `?q=` search),
  `GET /api/gmail/messages/{id}`, `POST /api/gmail/send`
- Scopes: `gmail.readonly`, `gmail.send`, `openid`, `userinfo.email`
- Refresh tokens Fernet-encrypted in `gmail_tokens` collection (never returned to client)
- OAuth state persisted in `gmail_oauth_states` with 10-min TTL, cleared on callback
- Automatic token refresh + reconnect flow on expiry
- `PUBLIC_API_URL` env pins the redirect URI to the external URL (prevents
  cluster-internal hostname leaking into Google's OAuth request)

### Login Sign-in Options (Feb 2026 — this session)
- Demo mode ("Try the demo — no account needed") promoted to first-class
  alternative sign-in method, sitting directly beneath "Continue with Google"

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

### Feb 2026 — IPV Communication Safety Assessment + Problem-Solving Worksheet (P0 → SHIPPED)
- **New feature**: Confidential self-assessment that maps a parent's safety/control answers to one of 4 communication pathways (No Direct → Structured Written → Assisted → Cooperative). Texas DV resources baked into every result.
- **Discoverability**: Two large CTAs on `/safety` ("Take the assessment" + "Open the worksheet"), per user choice 1b. No surfacing on Dashboard.
- **Safety affordances**:
  - Full-screen `HighConcernOverlay` fires the instant a user toggles "Yes" on any of 5 high-concern questions (threats, strangulation/restraint, stalking, abduction threats, protective-order violations). Overlay includes tap-to-call 911 + 800-799-7233 + text START to 88788. ESC = Quick Exit (replaces page with google.com). "Change my answer" clears the Yes.
  - Sticky "Quick exit" button on every screen of the assessment + worksheet.
  - Server-side scoring (`score_assessment()`) so the pathway can never be tampered with via the wire.
- **Results delivery**: In-app card + Download PDF (`fpdf2`, branded) + Email-me-a-copy (Resend). Guests get a "Save my work" toast that routes to `/claim`.
- **Problem-Solving Worksheet**: Standalone route `/problem-solving` (9 prompts + 3 option fields) AND surfaced contextually from any assessment result. Saved worksheets list shows most recent 5.
- **Endpoints (mounted at `/api/safety-assessment`)**: `GET /questions`, `POST /`, `GET /me`, `GET /me/history`, `GET /{id}/pdf`, `POST /{id}/email`, `POST /problem-solving`, `GET /problem-solving/me`.
- **Tests**: 16/16 pytest at `/app/backend/tests/test_safety_assessment.py` (pure-function scoring across all 4 levels + every endpoint). Frontend Playwright covered intro → all 18 questions → high-concern overlay UX → L4 result → PDF/Email/Worksheet CTAs end-to-end. 100% pass.
- **Files added**: `/app/backend/safety_assessment_routes.py`, `/app/backend/safety_assessment_pdf.py`, `/app/frontend/src/pages/SafetyAssessment.jsx`, `/app/frontend/src/pages/ProblemSolvingWorksheet.jsx`, `/app/frontend/src/components/HighConcernOverlay.jsx`. `email_service.send_safety_assessment_report` appended.

### Feb 2026 — Admin analytics N+1 query fix (P2 → SHIPPED)
- **What**: `/api/analytics/admin/recent-users` used to issue 1 + 2N Mongo queries (one prep_data.find_one + one summaries.count_documents per user, up to 100 users → 201 queries). Now issues exactly 3 total: `users.find`, `prep_data.find({user_id: $in})`, and a `summaries.aggregate` `$group` by `user_id`.
- **Verified**: 25 users returned in ~105ms (previously grew linearly with limit). Response shape unchanged so admin dashboard consumers are untouched.
- **File**: `/app/backend/analytics_routes.py` (function `admin_recent_users`).

### Feb 2026 — Interactive AI Coach Chat (P1 → SHIPPED)
- **What**: A warm, BIFF-first, prep-aware chat surface for the heat-of-the-moment moments (right after a hard exchange, before a hard reply, when stuck). Multi-turn conversations persisted per user.
- **Backend** (`coach_routes.py` + append to `ai_service.py`):
  - Endpoints: `GET /api/coach/starters`, `POST /coach/sessions`, `GET /coach/sessions`, `GET /coach/sessions/{id}`, `DELETE /coach/sessions/{id}`, `POST /coach/sessions/{id}/message`.
  - Uses Claude Sonnet 4.5 via `emergentintegrations` `LlmChat` with `initial_messages` carrying full conversation history (capped at last 20 turns) so context is preserved.
  - System prompt enforces: validate feelings first, ground in child, teach BIFF, no character attacks, ≤200 words, offer-don't-direct, and a safety override that flips `safety_flag=true` and surfaces DV/988 hotlines.
  - Prep-aware: pulls child_goals, reflection, priority, and child_name from `prep_data` and folds them into the system prompt so the coach references the parent's actual goals.
  - First user message auto-derives a 60-char session title. Session `safety_flag` is promoted to true if any assistant reply carries one.
  - Collections: `coach_sessions`, `coach_messages`.
- **Frontend** (`pages/Coach.jsx` + routes in `App.js`):
  - `/coach` empty state renders 5 starter prompt cards + "Start blank" link.
  - `/coach/:sessionId` renders the thread with react-markdown assistant bubbles, safety-aware banner when the session has flagged content, and follow-up suggestion pills after each assistant turn.
  - Composer: Enter to send, Shift+Enter for newline, in-flight spinner, disclaimer under every state.
  - Past-conversations sidebar with title + delete (with confirm).
  - Discoverable from Pillar 4 of `FivePillarJourney` as "AI Coach Chat (in the moment)".
- **Tests**: 12/12 backend pytest + full frontend Playwright. All 100% pass.
- **Dependency added**: `react-markdown` (via yarn).

### Feb 2026 — Longitudinal Growth Tracking (P1 → SHIPPED)
- **What**: A timeline of readiness snapshots (from every generated Mediation Summary) with 30/60/90-day comparison windows and coach-authored insights. Parents can see growth — dimension by dimension — across weeks and months.
- **Backend** (`analytics_routes.py`):
  - `GET /api/analytics/growth` returns `{has_history, points, windows, insights, current, first_snapshot_at, days_tracked}`.
  - Points carry `{at, summary_id, overall, label, communication, trust, child_alignment, conflict}` in chronological order.
  - Windows pick baseline as the newest snapshot on-or-before `today - N days` (falls back to earliest when history is short). Overall + per-dimension deltas.
  - Insights engine: milestone crossings (55, 75), biggest gain (≥+5), biggest drop (≤-5). Max 3 insights.
  - Legacy summary handling: docs without a persisted `readiness.dimensions` block still emit valid points via `_readiness_score` fallback (dimensions become null).
- **Frontend** (`components/GrowthTracker.jsx`):
  - Recharts LineChart with dashed "Prepared" (y=75, green) and "Moderately ready" (y=55, tan) reference lines.
  - Current score panel (top-right) with `/100` and label.
  - InsightsPanel with lightbulb-icon coach narratives.
  - Three WindowCards (30/60/90d), each with an overall delta chip and per-dimension rows (from → to, delta).
  - Empty state, single-snapshot state, and full-history state all handled.
  - Mounted on `/my-plan` at anchor `id="growth"`, above the Certificate card.
- **Tests**: 7/7 backend pytest (auth, empty state, full-shape, delta math, days_tracked, repeated-call stability, legacy-summary handling) + full frontend Playwright (empty state, chart render, window cards, delta chip colouring). 100% pass.

### Feb 2026 — Dashboard Growth Widget (P1 enhancement → SHIPPED)
- **What**: Compact "Your growth" chip on the main Dashboard between the Progress Report teaser and the Achievement badges. Surfaces current readiness score, best-available window delta chip (30d → 60d → 90d fallback), and a one-liner narrative ("You're up 8 points this month — real, measurable movement." / "You've dipped 25 points this month — a good moment to sit with your coach.").
- **Reuses**: `GET /api/analytics/growth` — no new endpoints.
- **Behaviour**: Hides itself entirely when the parent has no snapshots yet (returns null), so first-time visitors don't see an empty box. Deep-links to `/my-plan#growth` for the full experience.
- **File**: `frontend/src/components/GrowthWidget.jsx` + Dashboard integration.
- **Verification**: Screenshot smoke test on parent1@test.com (4 summaries → shows widget with -25 delta and 66-day tracking) + curl-verified null-render for fresh guest.

### Jul 2026 — Watch-First image refresh · Badge share · Mediator email CTA · Coercive threshold (P0/P1/P2 → SHIPPED)
- **Watch-First image refresh (P0)**: Replaced user-supplied illustrations for the four hero modules and regenerated the corresponding TTS videos via `/app/memory/build_step_videos_from_images.py`:
  - `step-safety-assessment.png` (Assess Your Family Situation)
  - `step-comm-style.png` (Understand Your Co-Parenting Relationship)
  - `step-child-goals.png` (Identify Your Child's Goals & Needs)
  - `step-foundation.png` (Create Your Foundation Statement)
  Videos: `safety-assessment-reflection.mp4`, `comm-style-reflection.mp4`, `child-goals-reflection.mp4`, `reflection-foundation.mp4` all rebuilt from the same narration MP3s. Confirmed 200 responses with correct byte counts and `Content-Type: video/mp4`.
- **Badge share (P1)**: `BadgeShelf.jsx` now renders a Share pill (`data-testid=badge-share-<id>`) under every **earned** badge chip. Uses `navigator.share` when available (mobile), otherwise falls back to `navigator.clipboard.writeText`. Distinct toasts differentiate the two paths; a user-cancelled share (`AbortError`) is silently ignored. Locked badges stay minimal (no share affordance until earned).
- **Email my pathway to my mediator (P1)**: New CTA button `[data-testid=results-email-mediator-button]` on the IPV Safety Assessment results card opens `MediatorEmailDialog` capturing mediator email (required), mediator name (optional) and a short parent message (optional). POSTs to new backend endpoint `POST /api/safety-assessment/{assessment_id}/email-mediator`. Endpoint validates email format, rejects `@demo.local`, requires a non-guest user with a real email, and sends the full assessment PDF via Resend with the parent's email set as `Reply-To`. All send failures now surface as **503** (was 502) so Cloudflare doesn't rewrite the JSON body into raw HTML — the frontend shows friendly copy instead. `mediator_emails` array is pushed to the assessment doc on success.
- **Coercive-flag threshold change (P2 — user chose "Level 2")**: A **single** yes on any of the five coercive-control questions (`s1_q3, s1_q6, s1_q7, s1_q8, s1_q9`) now escalates the pathway to Level 2 — Structured Written Communication (previously required 2+). Level 3 gate simplified to `section_2_concerns >= 3` since coercive s1 hits now short-circuit to Level 2.
- **Backend files touched**: `safety_assessment_routes.py` (scoring + new `email_assessment_to_mediator` endpoint + `MediatorEmailBody` model), `email_service.py` (new `send_mediator_safety_assessment`).
- **Frontend files touched**: `pages/SafetyAssessment.jsx` (new dialog + wiring), `components/BadgeShelf.jsx` (share button + `shareBadge` helper).
- **Tests**: 28/28 backend pytest in `test_safety_assessment.py` + new `test_safety_assessment_mediator_email.py`. Coercive-yes → Level 2 verified for s1_q3, s1_q6, s1_q7, s1_q8, s1_q9. Level 1/3/4 regressions all pass. Frontend E2E: badge-share clipboard fallback toast, mediator dialog open/validate/close, all `data-testid` selectors match.

### 📋 Backlog (P2 remaining)
_All P2 items shipped — backlog empty. Next priorities will come from real user signals._

### Feb 2026 — Certificate of Completion (P1 → SHIPPED)
- **What**: Personalised Certificate of Completion. Overlays parent's name (Great Vibes cursive, auto-shrinks to fit) and today's date (Playfair Display bold) onto the branded template `certificate-template.png`. Returned as a downloadable PDF and previewed inline as PNG.
- **Backend** (`certificate_service.py` + 3 new routes in `mediation_routes.py`):
  - `GET /api/mediation/certificate/eligibility` — threshold is 5 of 6 core steps done (child_goals, issues, priority, comm_style, readiness, reflection). Guests are always eligible so they can preview.
  - `GET /api/mediation/certificate/preview` — returns image/png with optional `?name=` override.
  - `POST /api/mediation/certificate/download` — returns application/pdf with `Content-Disposition: attachment`. Optional `{name}` in body; falls back to account name, then to "Committed Co-Parent". Logs to `certificates_issued` best-effort.
  - Template has baked-in placeholder text ("Parent Name Here", "May 15, 2026") which the compositor masks with the cream paper colour before drawing real values.
  - Fonts bundled at `/app/backend/assets/fonts/` (GreatVibes-Regular.ttf, PlayfairDisplay-Bold.ttf).
- **Frontend** (`components/CertificateCard.jsx`):
  - Loading, locked, and earned states.
  - Live PNG preview refreshes as the user edits the name inline.
  - "Download certificate (PDF)" button with in-flight spinner and success toast.
  - Rendered under `Personalized Recommendations` on `/my-plan` (with `#certificate` anchor) and after the tab content on `/summary`.
  - Discoverable from Pillar 5 (Reports & Action Center) of `FivePillarJourney.jsx` — links to `/my-plan#certificate`. Dashboard populates a new `hasCertificate` pillar flag from the eligibility endpoint.
- **Tests**: 12/12 backend pytest at `/app/backend/tests/test_certificate.py` (eligibility guest+JWT, PNG preview magic bytes, name-override, blank-name fallback, PDF magic bytes, filename sanitisation, auth gating). Frontend Playwright covered eligibility → PNG preview → name edit → PDF download flow (with %PDF magic byte verification) on both /my-plan and /summary. All 100% pass.

### Feb 2026 — Product Maturation, Phase 1: "Do this next" Dashboard hero (SHIPPED)
- **Why**: The app had grown to hold assessments, videos, badges, reports, IPV tools, special-needs modules, Foundation Statements — all competing for attention on the home. Per user's product feedback: the home screen should answer one question immediately — **What should I do next?**
- **What**: New `NextStepJourney` component at the very top of the Dashboard, above every other section. Collapses the entire app into a single linear 6-stage journey and auto-detects where the parent actually is:
  1. **Assess** — Readiness Check + Communication Style (category: Assessment)
  2. **Understand Your Child** — Child-Centered Goals + Special Needs (category: Reflection & Wellness)
  3. **Set Priorities** — Priority & Agenda (category: Mediation Preparation)
  4. **Build Your Foundation** — Foundation Statement + Journal (category: Reflection & Wellness)
  5. **Prepare for Mediation** — Issues, Alignment Statement, Summary (category: Mediation Preparation)
  6. **Review Progress** — My Plan, Growth, Certificate (category: Review & Progress)
- **Hero card** (`data-testid="journey-stage-hero"`): purple gradient with step number of 6, category chip, "Start here" / "Do this next" / "You've completed the journey" eyebrow (context-aware), stage title, blurb, activity bullets, and a large white CTA linking to the appropriate start route.
- **Progress rail** (`data-testid="journey-progress-rail"`): compact horizontal 6-step indicator with completed stages showing a filled dark bar + CheckCircle2 icon; the current stage highlighted in `#3D1A78`.
- **Up-next teaser**: small "Up next: <category> · <next stage> →" line that hides itself when the parent is on stage 6.
- **Toolkit demotion**: The existing 5-pillar journey UI moved into a collapsible `<details data-testid="toolkit-collapsible">` labelled "Full toolkit — every module, assessment, and report", closed by default. Nothing was removed; progressive disclosure over overwhelming grids.
- **Pre-existing bug fixed on the way**: Dashboard was calling a non-existent `/api/analytics/personal` (returned 404) — swapped to `/api/analytics/me` reading `activity.summaries` so the summary count flag (used by Step 5 detection and the "Journey Complete" badge) actually populates.
- **File**: `frontend/src/components/NextStepJourney.jsx` + minor changes in `frontend/src/pages/Dashboard.jsx`.
- **Testing**: Full frontend Playwright — fresh guest lands on Step 1 with "Start here" eyebrow and CTA linking to `/prep/readiness`; parent1@test.com (4 summaries + all core steps + certificate-eligible) lands on Step 6 with "You've completed the journey" eyebrow. Progress rail + toolkit collapsible + all regression checks (BadgeShelf, GrowthWidget, trailers, classic module <details>) pass. Backend regression check on `/api/analytics/me`. 100% pass, zero issues.

### Feb 2026 — Product Maturation, Phase 2: Methodology cards on every assessment (SHIPPED)
- **Why**: Per user's product feedback: "Assessments need a visible methodology." The app must up-front declare what each assessment IS designed to determine, what it CANNOT determine, the source models behind it, how recommendations are actually built, when to seek professional help, and how frequently to retake.
- **What**: New shared `<MethodologyCard>` component + data-driven `methodology.js` catalogue. Rendered at the top of every assessment page. Six clearly-labelled sections. Purpose is always visible; the other five are collapsed by default behind a "Read the full methodology" toggle so the top of the page stays visually light.
- **Assessments covered**: Readiness Check (`/prep/readiness`), Communication Style (`/prep/communication`), Special Needs 6-Pillar (`/neurodivergent`), and IPV Safety Assessment (`/safety-assessment`).
- **Category theming**: Assessment-category cards use a soft blue palette (chip `#EEF3FE → #DDE7F9`, title `#2E4B8A`). The Safety card uses a warm rust palette (chip `#F5C9B4`, title `#8C3A1B`) so it visually distances itself from mediation prep — a small but important cue that safety screening is a different kind of question than "am I ready to negotiate?".
- **Standard disclaimer footer** on every card: *"This is a self-reflection tool for mediation preparation — not clinical advice, a legal determination, or a substitute for a licensed professional's judgement."*
- **Sources cited per assessment**: Readiness → BIFF (Eddy), Center for Understanding in Conflict, Fisher & Ury. Comm Style → NVC (Rosenberg), High Conflict Institute, Gottman. Special Needs → AAP Bright Futures, CDC Learn the Signs, IDEA framework (vocabulary only), SAMHSA trauma-informed care. Safety → Duluth Model, Johnson typologies, HITS screening (direction only), Eddy's Splitting.
- **Files**: `frontend/src/lib/methodology.js` (data), `frontend/src/components/MethodologyCard.jsx` (component), plus 4-line integrations in `ReadinessCheck.jsx`, `CommStyle.jsx`, `SafetyAssessment.jsx`, `Neurodivergent.jsx`.
- **Testing**: Full frontend Playwright — card visible on load across all 4 pages, correct chip/name/purpose/disclaimer, blue vs rust theming honoured, toggle expand/collapse works, 5 detail sections render in the specified order, sources render as bulleted lists, and no regression on the existing content below the card. 100% pass, zero issues.

### Feb 2026 — Special Needs Assessment Rebuild, Phase A: v2 questions + 7-score coordination model (SHIPPED)
- **Why**: Per user's product spec, the assessment must move from a single global "co-parent quality" number to a **practical, child-centered care plan**. The five reframing questions: What does the child need? Where do the parents agree? Where is coordination breaking down? What safeguards or structures would help? What should happen next?
- **What (Phase A — foundation)**:
  - New question catalogue (`backend/special_needs_questions.py`) — 31 items across 4 sections: (1) Begin with the child (strengths, what helps, communication, child's voice), (2) Concerns categorised as Documented / Under evaluation / Parent-observed, (3) 21 behaviour-based coordination items across 8 domains (Medical, Development, Education, Communication, Emotional regulation, Daily living, Social, Transitions), (4) Disagreement-response self-reflection.
  - New shared 7-value coordination scale — *Almost always · Usually · Sometimes · Rarely · Almost never · Not applicable · I do not know · Parents disagree* — with only the first five carrying numeric weight. "I do not know" and "Parents disagree" are surfaced as coach flags, never as bad-conduct penalties.
  - Deterministic scorer (`backend/special_needs_scoring.py`) emitting **7 coordination scores**: Understanding, Information sharing, Follow-through, Consistency, Professional collaboration, Decision-making, Transition stability — plus an 8-domain topical rollup. No single global "quality" number.
  - **Recommended structure** derived from the mean of scored dimensions: Cooperative Coordination (≥70) · Structured Coordination (45-69) · Parallel Coordination (<45), each with its own copy.
  - **New endpoints**: `GET /api/neurodivergent/schema` (returns the assessment structure), `POST /api/neurodivergent/answers/bulk`, `GET /api/neurodivergent/scores`. The existing `POST /answer` and `GET /prep` now write/read `answers_v2` on the same doc so v1 archival stays intact.
  - **Frontend wizard rewrite** (`Neurodivergent.jsx`) driven by the schema — one question per screen, section-title header, autosave, migration notice for parents with v1 answers on file.
  - **Score dashboard** (`components/SpecialNeedsScoreDashboard.jsx`) rendered above the AI narratives on `/neurodivergent/reports`: recommended structure card + 7 bars (green for strong/working, tan for inconsistent, red for breaking-down) + no-signal "not enough answers yet" states + flags line ("Items to bring to your coach or mediator: N where parents disagree · N 'I do not know' · N not answered yet").
  - Methodology card copy updated to reflect the new coordination framing and cited AAP Coordinating-Care-for-a-Child-with-Disabilities framework.
- **Files added**: `backend/special_needs_questions.py`, `backend/special_needs_scoring.py`, `frontend/src/components/SpecialNeedsScoreDashboard.jsx`. Files rewritten: `backend/neurodivergent_routes.py` (heavy), `frontend/src/pages/Neurodivergent.jsx` (full). Files touched: `frontend/src/pages/NeurodivergentReports.jsx`, `frontend/src/lib/methodology.js`.
- **Testing**: Backend curl loop verified — POST /answers/bulk → GET /scores returns dimensions, structure, overall_signal correctly (deterministic — same input → same output). Screenshot smoke on `/neurodivergent` shows Question 1/31 loading with new v2 catalogue and section header "Begin with the child"; Question 10/31 shows the coordination-scale item "During the past six months, how often did both parents receive important medical information…". Screenshot on `/neurodivergent/reports` shows the score dashboard with 7 dimension bars, "Structured Coordination" recommendation, no-signal state for Professional collaboration, and a flags line summarising disagree / dont_know / unanswered counts.
- **Phase B (Consistency Between Homes) · Phase C (6-part report + PDF + share link) · Phase D (safeguards & disagreement pathway) · Phase E (IEP/504 sub-module) remain queued.**

### Feb 2026 — Special Needs Rebuild, Phase C: 6-part report + HTML view + PDF + share link (SHIPPED)
- **What**: The new v2 Special Needs Coordination Report — six-part care plan generated from the parent's answers + the deterministic 7 coordination scores. Available as an HTML view, a downloadable PDF, and a signed share link for the pediatrician / therapist / school team / mediator / attorney.
- **Structure (per the product spec)**:
  1. Child Profile — summary + strengths & interests + what helps + support needs (documented / under-evaluation / parent-observed)
  2. Areas of Parent Agreement
  3. Coordination Gaps (with the coordination dimension tagged)
  4. Priority Levels — Immediate · Within 30 days · Longer-term
  5. Recommended Co-Parenting Structure — Cooperative / Structured / Parallel narrative (references the deterministic score-based recommendation)
  6. Special Needs Parenting Plan Worksheet — action table with columns: *Child's need · Agreed action · Responsible · Info shared by · Review date*
- **Backend**:
  - `ai_service.generate_special_needs_report_v2()` — Claude Sonnet 4.5 emits strict JSON in the 6-part shape; system prompt enforces child-first framing, diagnosis-neutrality, coordination-not-perfection, and never-legal-or-clinical-advice.
  - New `backend/sn_report_pdf.py` — FPDF renderer for the 6 sections including a paginated action-plan table with per-row height calculation, latin-1 character normalisation (em-dash / curly quotes / ellipsis → ASCII), full-page-width bullet rendering, and a footer disclaimer.
  - Endpoints on `neurodivergent_routes.py`: `POST /report/generate` (create/regenerate), `GET /report` (fetch current), `GET /report/pdf` (download PDF), `POST /report/{id}/share-link` (create signed token), `GET /report/shared/{token}` (public route with `?format=json` or default PDF).
  - Storage: one live report per user in `sn_v2_reports` — `replace_one` on insert so the latest generation is always what the parent sees.
- **Frontend**: Full rewrite of `NeurodivergentReports.jsx` — hero with Download PDF / Copy share link / Regenerate buttons, `SpecialNeedsScoreDashboard` above the report, six section cards (`nd-sec-profile`, `nd-sec-agreement`, `nd-sec-gaps`, `nd-sec-priorities`, `nd-sec-structure`, `nd-sec-action-plan`), priority tri-tone (rust immediate · purple 30-day · green longer-term), action table with 5 columns, disclaimer footer.
- **Testing**: Backend curl loop confirmed the full flow — bulk-save answers → generate report → 4 agreement areas + 3 gaps + 3/3/3 priorities + 7 action rows returned by Claude; `/report/pdf` returns `HTTP=200 SIZE=8828 %PDF-`; share-link endpoint returns a signed JWT with `/api/neurodivergent/report/shared/{token}` path. Frontend Playwright verified all 6 section data-testids visible and the "A care plan for Ada" title.
- **Files added**: `backend/sn_report_pdf.py`. Files rewritten: `frontend/src/pages/NeurodivergentReports.jsx`. Files touched: `backend/ai_service.py` (append), `backend/neurodivergent_routes.py` (v2 report endpoints appended).
- **Phase D (safeguards & disagreement pathway) · Phase E (IEP/504 sub-module) remain queued.**

### Feb 2026 — Special Needs Rebuild, Phase B: Consistency Between Homes module (SHIPPED)
- **Why**: Per the product spec, the assessment's signature feature. Identical homes should never be assumed. The parent should be able to name which routines the *child* actually needs consistent and which areas can hold flexibly between the two homes.
- **What**: New assessment section with 8 compound items — each rendered on a single wizard screen with two labelled selector groups:
  1. Medication timing & administration
  2. Sleep & eating routines
  3. Therapy exercises & behavioural strategies
  4. Screen use & sensory regulation
  5. Schoolwork & attendance
  6. Discipline & emotional dysregulation
  7. Transportation of medical / adaptive equipment
  8. Communicating changes in the child's functioning
- **Data model**: Each topic saves TWO answers on a flat dict — `<id>` (coordination scale) + `<id>__needs` (yes / can_flex / uncertain). The scorer only counts an item toward the **Consistency coordination score** when the parent flagged consistency as needed (or left it uncertain — treated as "needs" to be safe). `can_flex` items are surfaced elsewhere as informational, never dragging the score.
- **Backend**: `CONSISTENCY_ITEMS` + `NEEDS_CONSISTENCY_SCALE` added to `special_needs_questions.py`; schema returned by `/api/neurodivergent/schema` now has 5 sections (child_profile · concerns · coordination · **consistency** · disagreement). Scorer in `special_needs_scoring.py` reads `<id>__needs`, filters can_flex items, and adds a `consistency_can_flex` list to the response payload.
- **Frontend**: New `consistency_pair` item type in the wizard — `AnswerInput` renders two `ScaleChoices` groups labelled "Today — how consistent is this across your two homes?" + "Does your child actually need this to be consistent between homes?". `onChangeNeeds` prop threads the paired setter; `goNext`/`goPrev` persist both fields together. Score dashboard now surfaces a green "Areas your child can hold flexibly:" pill listing the `can_flex` items when present.
- **Testing**: Backend curl confirmed 5-section schema with 8 consistency items and 3-value needs scale. Bulk-save + `/scores` correctly excluded 2 `can_flex` items from the 10-item consistency dimension pool (6 scored) and surfaced them in `consistency_can_flex`. Frontend Playwright verified Question 31 of 39 renders the compound pair with both selector groups, correct eyebrows, and all option labels visible.
- **Phase D (safeguards & disagreement pathway) · Phase E (IEP/504 sub-module) remain queued.**

### Feb 2026 — "Your Next Three Steps" page after every assessment (SHIPPED)
- **Why**: Per user's product feedback, every assessment should end with a personalised routing surface — three specific, actionable next moves the parent can take right now. Removes the "I finished, what now?" moment across all four assessments.
- **What**: New `/next-steps/:assessment` page auto-loaded on completion of Readiness Check · Communication Style · Family Violence & Safety · Special Needs Coordination. Each step shows **What · Why it matters · How long · CTA to the next surface** with a category chip (reflection · preparation · safety · review). Parents can Mark done · Not right now · Bring it back — with visual state (strikethrough for done, muted for dismissed).
- **Backend** (`next_steps_routes.py` — rule-based, deterministic, no AI):
  - `GET /api/next-steps/{assessment}` — returns cached three steps (auto-generates on first call).
  - `POST /api/next-steps/{assessment}/generate` — force recompute from latest answers/scores.
  - `POST /api/next-steps/{assessment}/{step_id}/action` — done / dismiss / undo.
  - Per-assessment engines:
    - **readiness**: reads `prep_data` + `readiness_scoring.compute_readiness()`, routes by lowest dimension (communication → coach, trust → alignment, child_alignment → child goals, conflict → safety) + course by overall (≥75 → summary, ≥55 → growth, <55 → coach check-in).
    - **comm_style**: BIFF-practice → trigger reflection → Gmail AI draft.
    - **safety**: reads latest `safety_assessments` doc — L3/L4 routes to hotlines + parallel parenting + share-with-advocate; L1/L2 routes to BIFF + safety plan + retake reminder.
    - **special_needs**: reads `special_needs_scoring.compute_scores()`, always suggests generating the care plan + routes by weakest coordination dimension (info_sharing / consistency / follow_through / understanding / professional / decision_making / transitions) + structure-specific step (Cooperative/Structured/Parallel).
  - Storage: `next_steps` collection, one doc per (user_id, assessment) with `replace_one` on regeneration.
- **Frontend** (`pages/NextSteps.jsx`): route `/next-steps/:assessment`, protected. Category-chip tricolor, numbered step cards, done/dismiss/undo per step, "Regenerate" button, deep-link back to the source assessment.
- **Auto-navigation wired**: `ReadinessCheck.jsx` on submit → `/next-steps/readiness`, `CommStyle.jsx` on submit → `/next-steps/comm_style`, `Neurodivergent.jsx` on completion → `/next-steps/special_needs`, and a "See your Next Three Steps →" CTA on the Safety Assessment result screen → `/next-steps/safety`.
- **Testing**: Backend curl verified all 4 engines produce sensible steps for parent1@test.com (readiness → 3 steps, comm_style → 3 steps, safety → 3 steps, special_needs → 2 steps due to no v2 answers). Action endpoint correctly toggles done/dismissed state. Frontend screenshot verified all state variants (done strikethrough with Bring-it-back, active with primary CTA + Mark done / Not right now, category chips green/purple).
