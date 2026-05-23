# SA Coparents — Relational Mediation Prep App

## 🎯 Original Problem Statement

A calm, structured, non-judgmental, supportive web/mobile app that moves co-parents from emotionally reactive to child-centered and prepared for relational mediation. Built for separating parents in South Africa and the US (San Antonio area).

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
