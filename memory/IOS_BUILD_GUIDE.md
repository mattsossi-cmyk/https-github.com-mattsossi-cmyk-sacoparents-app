# iOS IPA Build & TestFlight Upload — Setup Guide

You're set up to build a signed iOS App (`.ipa`) entirely from GitHub Actions and auto-upload it to TestFlight / App Store Connect. **No Mac required**.

> ⚠️ **Honest cost warning**
> iOS builds use macOS runners which are **10× more expensive** than Linux runners on GitHub Actions free tier.
> - **Free tier (private repo):** ~200 macOS minutes/month → ~12 iOS builds/month
> - **If you exceed that:** $0.08/minute on the Pro plan
> - Each build takes ~20–25 min
>
> Plan accordingly. For development, build sparingly. Trigger releases on push to `main` only.

---

## ✅ What's already done

| File | Purpose |
|---|---|
| `.github/workflows/ios-build.yml` | The iOS build pipeline |
| `frontend/scripts/patch-ios-encryption-exemption.js` | Auto-answers Apple's encryption question + strips routing capability |
| `frontend/package.json` → `cap:ios:patch` script | Wired into the build |

## 🔑 What YOU need to set up (one-time, ~30–45 min)

### Step 1 — Apple Developer Program ($99/year)

If you don't have it:
1. Go to https://developer.apple.com/programs/enroll/
2. Sign in with your Apple ID (or create one)
3. Pay the $99 annual fee
4. **Wait 24–48 hours** for Apple's identity check
5. Once approved, you'll get a **Team ID** (a 10-character code like `ABCD123456`)

> ⚠️ Apple **rejects** prepaid cards, virtual cards, and non-personal cards. Use a real credit card in the name on your Apple ID.

### Step 2 — Generate Distribution Certificate + Provisioning Profile

This is the tedious part. Three sub-tasks: certificate, App ID, provisioning profile.

#### 2a — Create the App ID
1. https://developer.apple.com/account/resources/identifiers/list
2. Click **+** to register a new identifier
3. Choose **App IDs** → **App**
4. Description: `SA Coparents`
5. Bundle ID: **Explicit** → `com.bsossi.sacoparents`
6. Capabilities: leave defaults (you can add Push Notifications later if needed)
7. **Continue → Register**

#### 2b — Create the Distribution Certificate
1. https://developer.apple.com/account/resources/certificates/list
2. Click **+** → **Apple Distribution** → Continue
3. You need a **Certificate Signing Request (CSR)**. The easiest way without a Mac:
   - Go to https://certificatesigningrequest.com/
   - Fill in your email + common name (e.g., "SA Coparents Distribution")
   - Click **Generate** → downloads a `.csr` file + a `.key` file (KEEP THE .KEY FILE SAFE)
4. Back in Apple's portal, upload the `.csr` file
5. Apple gives you a `.cer` (certificate) file → download it
6. Convert to `.p12` (the signed format GitHub Actions needs):
   - Go to https://www.sslshopper.com/ssl-converter.html
   - Upload your `.cer` + your `.key` from step 3
   - Output type: **PFX/PKCS#12**
   - Set a strong password — **SAVE IT in your password manager**
   - Download the `.p12` file
7. **Save the `.p12` somewhere safe** (password manager attachment, encrypted drive)

#### 2c — Create the Provisioning Profile
1. https://developer.apple.com/account/resources/profiles/list
2. Click **+** → **App Store** → Continue
3. App ID: pick **com.bsossi.sacoparents** (the one you just created)
4. Certificate: pick the **Apple Distribution** certificate you just made
5. Profile name: `SA Coparents App Store`
6. **Generate → Download** the `.mobileprovision` file

### Step 3 — Get an App Store Connect API key (for auto-upload)

This lets the workflow push your `.ipa` to TestFlight without needing your Apple ID password.

1. https://appstoreconnect.apple.com/access/integrations/api
2. Click **+** to create a new key
3. Name: `SA Coparents CI`
4. Access: **App Manager**
5. **Generate** → Download the `.p8` file (ONLY downloadable ONCE — back it up immediately)
6. Note the **Key ID** (10-character code) and **Issuer ID** (UUID) shown at the top of the page

### Step 4 — Base64-encode the 3 binary files

GitHub Secrets can only hold text. Three files need encoding:

**Option A — online tool (no install):**
- Go to https://www.base64encode.org/
- For each of these files: upload, click Encode, copy the entire base64 output:
  - Your `.p12` distribution certificate → → `IOS_BUILD_CERTIFICATE_BASE64`
  - Your `.mobileprovision` file → `IOS_PROVISIONING_PROFILE_BASE64`
  - Your `.p8` App Store Connect key → `APP_STORE_CONNECT_API_KEY_BASE64`

**Option B — terminal (Mac/Linux):**
```bash
base64 -w 0 SA_Coparents_Distribution.p12 > p12.base64.txt
base64 -w 0 SA_Coparents_AppStore.mobileprovision > profile.base64.txt
base64 -w 0 AuthKey_XXXXXX.p8 > p8.base64.txt
```

### Step 5 — Add 8 GitHub Secrets

1. Open https://github.com/mattsossi-cmyk/sacoparents-app/settings/secrets/actions
2. Click **"New repository secret"** and add each of these:

| Secret name | Value |
|---|---|
| `IOS_BUILD_CERTIFICATE_BASE64` | base64 of your `.p12` from step 2 |
| `IOS_P12_PASSWORD` | the password you set when creating the `.p12` |
| `IOS_PROVISIONING_PROFILE_BASE64` | base64 of your `.mobileprovision` from step 2c |
| `IOS_KEYCHAIN_PASSWORD` | any strong password (used to lock the temp keychain on the runner) |
| `IOS_TEAM_ID` | your Apple Team ID (10-char code from step 1) |
| `APP_STORE_CONNECT_API_KEY_ID` | Key ID from step 3 |
| `APP_STORE_CONNECT_API_ISSUER_ID` | Issuer ID from step 3 |
| `APP_STORE_CONNECT_API_KEY_BASE64` | base64 of the `.p8` file from step 3 |

(Optional, if your production backend isn't `https://sacoparentsapp.online`):

| Secret name | Value |
|---|---|
| `REACT_APP_BACKEND_URL` | e.g., `https://your-backend.com` |

### Step 6 — Trigger the build

1. https://github.com/mattsossi-cmyk/sacoparents-app/actions
2. Click **"iOS IPA"** in the left sidebar
3. Click **"Run workflow"** → branch: `main` → **"Run workflow"**
4. ☕ Wait ~25 minutes (first build is slow — Xcode caching kicks in for subsequent builds)
5. When green ✅, the workflow will have already **uploaded the IPA to App Store Connect**

### Step 7 — Find the build in App Store Connect

1. https://appstoreconnect.apple.com → My Apps → SA Coparents
2. **TestFlight tab** → wait ~10–15 minutes for Apple to process the build
3. The build appears under **"iOS Builds"** with a yellow ⏳ "Processing" badge
4. When processing finishes, the badge turns green ✅
5. **Now you can choose this build** on the App Store submission page

---

## 🆘 Common build failures & fixes

| Error | Fix |
|---|---|
| `error: No profiles for 'com.bsossi.sacoparents' were found` | The `IOS_PROVISIONING_PROFILE_BASE64` secret isn't matching the App ID. Re-generate the profile in Apple's portal making sure it points to `com.bsossi.sacoparents`. |
| `error: No signing certificate "Apple Distribution" found` | The `.p12` cert didn't import properly. Most common cause: wrong `IOS_P12_PASSWORD`. |
| `Authentication failed... Could not authenticate. Either Apple ID or password is incorrect.` | Your App Store Connect API key was revoked or `APP_STORE_CONNECT_API_KEY_ID` doesn't match the `.p8`. Re-check. |
| `ITMS-90189: Redundant Binary Upload` | You tried uploading the same build number twice. The workflow auto-bumps build number from `github.run_number`, so just re-run. |
| `Invalid Provisioning Profile. Your distribution provisioning profile must be regenerated` | Apple revoked or expired your profile. Re-generate it in the portal, re-base64, replace the secret. |
| Build hangs at "Preparing Workspace" for 10+ min | `pod install` is slow on first run — wait it out. |

---

## ⚖️ Alternative: skip auto-upload, just download the IPA

If you don't want to set up the App Store Connect API key, you can skip Step 3 and only set the 5 signing secrets (steps 5 rows 1–5). The workflow will:
- Build the signed IPA ✅
- Upload it as a GitHub Actions Artifact ✅
- Skip the auto-upload to TestFlight (no error) ✅

You'd then manually upload to TestFlight using:
- **Mac:** Drag-drop into Apple Configurator 2 or Transporter app
- **No Mac:** Use https://transporter.itunes.apple.com (web upload — slower but works)

---

## 🔄 Future builds

After this one-time setup, every push to `main` (via Emergent's "Save to GitHub") triggers a new iOS build automatically. Or trigger manually any time via Actions → "iOS IPA" → Run workflow.

Each release auto-increments the build number, so you'll never hit Apple's "duplicate build number" error.

---

## 💸 Final cost reality check

| Item | One-time | Recurring |
|---|---|---|
| Apple Developer Program | — | **$99/year** |
| Google Play Developer | $25 | — |
| GitHub Actions macOS (private) | — | ~200 min/month free (~12 iOS builds) |
| GitHub Actions Linux (private) | — | ~2000 min/month free (~150 Android builds) |
| Codemagic (alternative) | — | 500 min/month free (mixed iOS+Android) |

**Total to ship to BOTH stores:** ~$124 one-time + ~$99/year + your GitHub Actions usage.
