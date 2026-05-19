# GitHub Actions — Android AAB Build Guide

You're now set up to build a signed Android App Bundle (`.aab`) entirely from inside GitHub. No tools needed on your computer.

## ✅ What was added to your repo

| File | Purpose |
|---|---|
| `.github/workflows/android-aab.yml` | The GitHub Actions workflow |
| `/codemagic.yaml` | (Existing — ignore for now) |
| `/package.json` | (Existing — monorepo marker) |

## 🚀 One-time setup (~15 min)

### Step 1 — Push everything to GitHub

In your Emergent chat input, click **"Save to GitHub"** → save to existing `sacoparents-app` repo. This pushes the new workflow file along with the recent fixes.

### Step 2 — Generate an Android signing keystore (3 min)

> ⚠️ **Critical:** This keystore signs your app forever. If you lose it, you can never update the app on Google Play. Store it in a password manager AND save the file somewhere safe.

Easiest way without installing tools: **online keystore generator**.

Recommended: https://www.androidkeystoregenerator.com/ (open-source, runs in your browser, no data uploaded to server — all generation is client-side).

Fill in:

| Field | Value |
|---|---|
| **Keystore password** | Generate a strong password → **save in password manager** |
| **Key alias** | `sacoparents` |
| **Key password** | Same as keystore password (simpler) |
| **First and last name** | Matt Sossi |
| **Organisation unit** | App |
| **Organisation** | SA Coparents |
| **City** | San Antonio |
| **State** | Texas |
| **Country code** | US |
| **Validity (years)** | 25 |

Click **"Generate"** → download the `.keystore` file (probably named `keystore.jks` or `release.keystore`).

> 🛡️ **Backup this keystore file in 2 places right now** (e.g., password manager attachment + encrypted USB drive). If both copies are lost, your Google Play app is permanently locked.

### Step 3 — Convert the keystore to base64 (1 min)

GitHub Secrets can only hold text, so you encode the binary keystore as base64.

**Option A — use a free online converter:**
- Go to https://www.base64encode.org/
- Click the **"Choose file"** button and select your `.keystore` file
- Click **"Encode"**
- Copy the entire base64 text output (it'll be a long string of letters/numbers)

**Option B — if you have Mac/Linux terminal access:**
```bash
base64 -w 0 release.keystore > keystore.base64.txt
# Then copy the contents of keystore.base64.txt
```

### Step 4 — Add 4 GitHub Secrets (3 min)

1. Open https://github.com/mattsossi-cmyk/sacoparents-app
2. Click **Settings** (tab at the top right of the repo)
3. Left sidebar → **Secrets and variables** → **Actions**
4. Click **"New repository secret"** and add these 4 secrets one by one:

| Secret name | Value |
|---|---|
| `ANDROID_KEYSTORE_BASE64` | Paste the long base64 text from Step 3 |
| `ANDROID_KEYSTORE_PASSWORD` | The keystore password from Step 2 |
| `ANDROID_KEY_ALIAS` | `sacoparents` |
| `ANDROID_KEY_PASSWORD` | Same as `ANDROID_KEYSTORE_PASSWORD` |

(Optional — only if your production backend is on a domain other than `sacoparentsapp.online`):

| Secret name | Value |
|---|---|
| `REACT_APP_BACKEND_URL` | `https://your-production-backend.com` |

### Step 5 — Trigger the build (1 min)

1. Open https://github.com/mattsossi-cmyk/sacoparents-app/actions
2. Click **"Android AAB"** on the left
3. Click **"Run workflow"** button (top right) → branch: `main` → **"Run workflow"**
4. ☕ Wait ~10 minutes — the first build takes the longest (downloads Android SDK, Gradle, dependencies)

### Step 6 — Download your AAB

1. When the build shows a green ✅, click into the workflow run
2. Scroll to the bottom — you'll see an **Artifacts** section
3. Click **"sa-coparents-android-aab"** → downloads a `.zip` containing `app-release.aab`
4. Unzip → you have your **signed Android App Bundle** ready for Google Play

---

## 🎯 Upload to Google Play

1. Go to https://play.google.com/console
2. *First time only:* pay the **$25 USD** one-time developer fee
3. **Create app** → fill in name "SA Coparents" → Create
4. Left sidebar: **Testing → Internal testing → Create new release**
5. Drag `app-release.aab` into the upload area
6. Release notes: *"Initial internal build — SA Coparents 1.0.0"*
7. **Save → Review release → Start rollout to Internal testing**
8. On the **Testers** tab → "Create email list" → upload `/memory/app_store_assets/internal-testers-emails.csv`
9. Copy the **opt-in URL** that Google generates → send it to your testers
10. Complete remaining Play Console tasks (Privacy URL, Account Deletion URL, Data Safety form, Content Rating — see [APP_STORE_SUBMISSION_PACK.md](./APP_STORE_SUBMISSION_PACK.md))

### Required URLs for Google Play Console

| Field | URL |
|---|---|
| **Privacy Policy** | `https://sacoparentsapp.online/privacy` |
| **Account Deletion URL** | `https://sacoparentsapp.online/delete-account` |

### Data Safety form — quick answers

| Data type | Collected? | Shared? | Purpose | Required? |
|---|---|---|---|---|
| Email address | Yes | No | Account management | Required |
| Name | Yes | No | Account management | Required |
| App activity (mediation answers) | Yes | No | App functionality (private to user) | Required |
| Crash logs / diagnostics | Yes | No | Analytics | Optional |
| Device IDs (push token) | Yes | No | App functionality | Optional |

Mark:
- **Data encrypted in transit:** Yes (HTTPS)
- **Users can request data deletion:** Yes (via /delete-account)

---

## 🔄 Future builds (after this one-time setup)

Every time you push to `main` (via Emergent's "Save to GitHub"), GitHub automatically rebuilds the AAB. You can also trigger it manually any time:

1. Repo → **Actions** tab → **"Android AAB"** → **"Run workflow"**

To upload to Google Play:
1. Download the new AAB from Artifacts
2. Google Play Console → Testing → Internal testing → **Create new release** → upload

> ⚠️ Each release needs a **higher versionCode** than the previous one. The workflow auto-increments versionCode based on the GitHub Actions run number, so you don't need to bump anything manually.

---

## 🆘 Common failures & fixes

| Error in build log | Fix |
|---|---|
| `signingConfig "release" is missing` | One of the 4 GitHub Secrets isn't set or has wrong name. Re-check Step 4. |
| `Keystore was tampered with, or password was incorrect` | Wrong password in `ANDROID_KEYSTORE_PASSWORD`. |
| `Failed to find target with hash string 'android-34'` | Transient SDK download issue — re-run the workflow. |
| `npm ERR! ERESOLVE` | Yarn lock conflict — usually re-running fixes it. |
| `Unsigned bundle` warning in the run summary | You haven't added `ANDROID_KEYSTORE_BASE64` secret yet. The workflow produces an unsigned `.aab` so you can verify the build pipeline works, but Google Play will reject it. Add the secret and re-run. |

---

## 💰 Cost

- **GitHub Actions (private repo):** 2,000 minutes/month free. Each Android build takes ~10 min, so you can run ~200 builds/month free.
- **Google Play Developer:** $25 USD one-time registration.
- **No other costs.**

---

## 🔐 Security notes

- The keystore is stored as a GitHub Secret — encrypted at rest, never logged
- The keystore file itself never appears in logs or artifacts (only the AAB it produced)
- Anyone with admin access to your GitHub repo can view/edit secrets — keep the repo private
- **The local `.keystore` file you downloaded is your insurance copy** — protect it like a Bitcoin wallet
