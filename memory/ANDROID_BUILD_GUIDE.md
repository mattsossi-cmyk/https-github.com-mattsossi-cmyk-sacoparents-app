# Android App Bundle (.aab) — Build & Upload Guide

You don't have any dev tools locally and that's fine. We'll build your Android App Bundle 100% in the cloud using **Codemagic**, then upload it to Google Play.

> Total time: ~30–45 min (one-time). Subsequent builds = one click.

---

## ✅ What's already prepared in this repo

| File | Purpose |
|---|---|
| `/app/frontend/capacitor.config.ts` | Capacitor config — appId `com.bsossi.sacoparents`, app name "SA Coparents" |
| `/app/codemagic.yaml` | Pre-configured Codemagic workflow that installs deps, builds React, generates Android platform, signs the AAB, and emails it to you |
| `/app/frontend/package.json` | Includes `@capacitor/android@^7` |

You do **not** need Android Studio, Java, or a Mac. Codemagic runs the whole thing on a Mac in the cloud.

---

## 🧭 Step-by-step

### Step 1 — Push the code to GitHub

1. In the Emergent chat input box, click the **"Save to GitHub"** button
2. Pick a repo name (e.g., `sacoparents-app`) and make it **Private**
3. Wait for the push to complete — you'll see a confirmation with the repo URL

If you don't have a GitHub account: create one free at https://github.com/signup

### Step 2 — Sign up for Codemagic

1. Go to https://codemagic.io/signup
2. Click **"Sign up with GitHub"**
3. Authorize Codemagic to read your repos

### Step 3 — Connect your repo to Codemagic

1. On the Codemagic dashboard, click **"Add application"**
2. Pick **GitHub** → select your `sacoparents-app` repo
3. Choose project type: **"Other"** (because we already have a `codemagic.yaml`)
4. Codemagic auto-detects `codemagic.yaml` at the repo root — confirm

### Step 4 — Create the signing keystore (CRITICAL — one-time)

> ⚠️ **The keystore is the cryptographic identity of your app on Google Play. You MUST use the same keystore for every update forever. Losing it means you can never update the app.** Codemagic stores it for you securely — this is the safest option.

1. In Codemagic, go to **Teams → Personal Account → Code signing identities → Android keystores**
2. Click **"Generate new keystore"**
3. Reference name: **`sacoparents_keystore`** ← must match the value in `codemagic.yaml`
4. Alias: `sacoparents`
5. Set a strong password for both the keystore and the alias (save them in a password manager — you'll need them if you ever migrate)
6. Click **Save**

### Step 5 — Add the production backend URL

1. In Codemagic, go to **Teams → Personal Account → Environment variables**
2. Create a group called **`production_env`** (must match `codemagic.yaml`)
3. Add a variable:
   - Name: `REACT_APP_BACKEND_URL`
   - Value: `https://sacoparentsapp.online` *(or whatever your production backend is)*
   - Mark as **Secure**

### Step 6 — Run your first build

1. Open the workflow **"SA Coparents — Android App Bundle (AAB)"**
2. Click **"Start new build"** → branch: `main` → workflow: `android-aab`
3. Wait ~10–15 minutes
4. When the green check appears, scroll to the **Artifacts** section
5. Download the file ending in **`.aab`** (e.g., `app-release.aab`)
6. You'll also get the build email with the AAB attached

### Step 7 — Upload to Google Play Console

1. Go to https://play.google.com/console
2. **Create app** → fill in name "SA Coparents", default language, app/game = App, free/paid
3. Complete the required Play Console "Dashboard" tasks:
   - App access (login required: parent1@test.com / TestPass123! for reviewer)
   - Ads (No)
   - Content rating questionnaire
   - Target audience (adults 18+)
   - News app (No)
   - Data safety form (declare what you collect — see below)
   - **Privacy Policy URL:** `https://sacoparentsapp.online/privacy`
   - **Account Deletion URL:** *(not built yet — let me know if you want this)*
4. **Testing → Internal testing → Create new release**
5. Drag the `.aab` into the upload area
6. Add a release name (e.g., "1.0.0 — First internal build") and release notes
7. **Save → Review release → Start rollout to Internal testing**
8. On the **Testers** tab, upload `/app/memory/app_store_assets/internal-testers-emails.csv`
9. Copy the **opt-in URL** Google generates and send it to your testers

---

## 🔐 Data Safety form quick answers

When filling Google Play's **Data Safety** section, declare:

| Data type | Collected? | Shared? | Purpose | Required? |
|---|---|---|---|---|
| Email address | Yes | No | Account management | Required |
| Name | Yes | No | Account management | Required |
| App activity (mediation answers) | Yes | No | App functionality (private to user) | Required |
| Crash logs / diagnostics | Yes | No | Analytics | Optional |
| Device or other IDs (push token) | Yes | No | App functionality | Optional |

Mark:
- **Data encrypted in transit:** Yes (HTTPS)
- **Users can request data deletion:** Yes (point them to the account deletion URL when it's built)

---

## 🆘 Common build failures & fixes

| Error | Fix |
|---|---|
| `npm ERR! could not resolve` | Codemagic ran `npm` instead of `yarn` — check `yarn.lock` exists in `/frontend` |
| `Capacitor command not found` | `@capacitor/cli` missing — already in `package.json`, no action needed |
| `Keystore not found` | The keystore reference name in `codemagic.yaml` doesn't match the one you created in Step 4 |
| `versionCode already exists` | Each upload to Play needs a higher versionCode — the YAML auto-increments via `$PROJECT_BUILD_NUMBER`, so just rebuild |

---

## 💸 Cost

- **Codemagic free tier:** 500 build minutes/month — about 30 builds/month at ~15 min each. You're well within free tier.
- **Google Play Developer:** $25 USD one-time registration fee.
- **No other costs** for internal testing.

---

## 📦 What goes inside the .aab

The Android App Bundle contains:
- Your compiled React web app (the `build/` folder)
- A Capacitor WebView wrapper that renders your React app natively
- Native plugins: SplashScreen, StatusBar, PushNotifications, Biometric
- Signed manifest with appId `com.bsossi.sacoparents`

Google Play later generates optimised `.apk` files from the `.aab` for each device.
