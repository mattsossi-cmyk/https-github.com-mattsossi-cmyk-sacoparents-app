# SA Coparents — App Store Deployment Guide

This guide walks you through publishing **SA Coparents** to the Apple App Store
and Google Play Store. The Capacitor scaffolding is already in place — what's
left is the platform-specific work that requires accounts and a Mac.

## What's already done (in code)
- ✅ Capacitor 7 installed and configured (`capacitor.config.ts`)
- ✅ App ID: `com.bsossi.sacoparents`
- ✅ App display name: `SA Coparents`
- ✅ PWA manifest + service worker (works on web today)
- ✅ Icon set generated (192/256/384/512 + iOS 180×180 + maskable)
- ✅ Splash screen (2048×2732)
- ✅ Biometric login wrapper (`BiometricGate` — gates the app behind Face ID / Touch ID on native)
- ✅ Push notification registration hook (calls `/api/mediation/devices/register`)
- ✅ Offline caching (service worker)

## Phase 0 — Test the PWA right now (zero cost, zero wait)

You can install SA Coparents on your phone today without any of the work below:

1. **iPhone (Safari):** Open https://sacoparentsapp.online → tap the **Share** button → scroll down → **Add to Home Screen**. The icon appears on your home screen; tapping it opens full-screen, no browser bar.
2. **Android (Chrome):** Open https://sacoparentsapp.online → tap the **⋮** menu → **Install app**.

Share this with a few real users to gather feedback while you set up the app store submissions.

---

## Phase 1 — Create developer accounts

### Apple Developer ($99/yr)
1. Go to https://developer.apple.com/programs/enroll/
2. Sign in with the Apple ID you want to own the app (use the business email, not personal)
3. Enroll as an **Individual** or **Organization**:
   - Individual = faster (~24-48 hrs approval), shows your personal name in the App Store
   - Organization = shows "SA Coparents" in the App Store, requires a D-U-N-S number (free, ~1-3 days to get)
4. Pay the $99 annual fee
5. While waiting: collect a high-resolution app screenshot, privacy policy URL, and 1024×1024 app icon

### Google Play Console ($25 one-time)
1. Go to https://play.google.com/console
2. Sign in, accept the developer agreement, pay $25
3. Choose **Personal** or **Organization** account type
4. Optionally enable Google's identity verification (recommended for trust)

---

## Phase 2 — Build the native apps

You need a **Mac with Xcode** for iOS. Android can be built on any OS but Mac is easiest if you're already there.

### Option A — You buy/borrow a Mac
- macOS 14+ with Xcode 16+ installed (free from Mac App Store)
- Android Studio (free, https://developer.android.com/studio)

### Option B — Cloud Mac service
- **MacInCloud** (~$25-50/mo) — easiest, browser-based VNC
- **MacStadium** (~$80/mo) — bare metal, faster builds
- **Codemagic** (~free tier then ~$30/mo) — CI/CD, builds in the cloud and can submit directly

### Option C — Hire someone
- **Fiverr / Upwork** — search "ionic capacitor app store submission". Expect $200-500 for a full first-time submission.

### Once you have a Mac with Xcode + Android Studio:
```bash
cd /app/frontend
yarn install           # if not done already
yarn build             # produces /app/frontend/build
npx cap add ios        # creates /app/frontend/ios/
npx cap add android    # creates /app/frontend/android/
npx cap sync           # copies the web build into the native projects
```

To open the projects:
```bash
npx cap open ios       # opens Xcode
npx cap open android   # opens Android Studio
```

---

## Phase 3 — iOS-specific setup

In **Xcode** (after `npx cap open ios`):
1. Select the **App** project in the left sidebar
2. Under **Signing & Capabilities**:
   - Team: select your Apple Developer team
   - Bundle Identifier: `com.bsossi.sacoparents` (confirm this matches)
3. Add capabilities:
   - **Push Notifications** (for the PushNotifications plugin)
   - **Sign in with Apple** (Apple often requires this if you offer any third-party login)
4. Edit **Info.plist**:
   - `NSFaceIDUsageDescription`: *"SA Coparents uses Face ID to keep your private mediation prep secure."*
5. Replace icons: Xcode → App → Assets.xcassets → AppIcon → drag in `/app/frontend/public/icon-1024.png` (you'll need to generate a 1024×1024 — easy: `convert sa-coparents-mark.png -resize 1024x1024 icon-1024.png`)
6. Build & run on a real iPhone (Product → Run with a device connected). Test:
   - Sign up / log in
   - Face ID unlock on app foreground
   - Allow push notifications prompt

**APNs cert for push:** developer.apple.com → Certificates → New → Apple Push Notification service SSL → upload to your backend's push provider (e.g., Firebase Cloud Messaging for iOS, OneSignal, or directly send via APNs).

---

## Phase 4 — Android-specific setup

In **Android Studio** (after `npx cap open android`):
1. Wait for Gradle sync to finish (first time: ~5 min)
2. **Build → Generate Signed Bundle / APK → Android App Bundle**
3. Create a new keystore (save the .jks file + passwords in 1Password — losing this means you can never update the app)
4. Build → produces `app-release.aab` for Play Store upload

**FCM project (push notifications):**
1. console.firebase.google.com → Add project → "SA Coparents"
2. Add Android app with package name `com.bsossi.sacoparents`
3. Download `google-services.json` → place in `/app/frontend/android/app/`
4. Build & test on a real Android phone

---

## Phase 5 — App Store submission

### App Store Connect (Apple)
1. https://appstoreconnect.apple.com → My Apps → New App
2. Fill in:
   - **Name:** SA Coparents
   - **Primary language:** English (US)
   - **Bundle ID:** com.bsossi.sacoparents
   - **SKU:** sacoparents-v1
3. Pricing: Free
4. App Information:
   - **Category:** Health & Fitness (Primary), Lifestyle (Secondary)
   - **Content rights:** Confirm you have rights to all content
   - **Age rating:** 17+ (because of references to domestic violence / mental health crisis)
5. Screenshots (required):
   - 6.7" iPhone (1290×2796) — at least 3, recommended 5-8
   - 5.5" iPhone (1242×2208) — fallback
   - Easiest: run the app in a phone-sized window, take screenshots, or use Xcode's simulator
6. Privacy:
   - Privacy policy URL (host one on sacoparentsapp.online/privacy — I can draft this)
   - Data collected: Name, Email, Contact info, User content (mediation prep), Usage data
7. App Review Information:
   - Demo account: parent1@test.com / TestPass123!  (or create a fresh review-only account)
   - **Critical note to reviewer:** *"This app helps parents prepare for co-parenting mediation. The biometric login keeps sensitive personal reflections private. The Safety page provides offline-accessible domestic violence resources, including the 988 Suicide & Crisis Lifeline."*
8. Submit for Review → wait 1-7 days

### Google Play Console
1. Create app → SA Coparents → English (US) → Free
2. Upload the .aab from Android Studio
3. Fill out:
   - **Privacy policy URL**
   - **Category:** Health & Fitness
   - **Content rating questionnaire**
   - **Target audience:** 18+
   - **News app declaration:** No
   - **COVID-19 contact tracing:** No
4. Screenshots: phone + 7-inch tablet + 10-inch tablet (Play Store is stricter)
5. Submit → review usually 1-3 days for first submission

---

## Phase 6 — Common gotchas

| Problem | Cause | Fix |
|---|---|---|
| Apple rejects "duplicate of website" | App is too thin a wrapper | Make sure biometric login is working & demoable. Add unique copy in App Store description: *"Biometric-locked mediation prep with offline-accessible safety resources."* |
| Google sign-in fails inside app | WebView cookies don't carry Emergent OAuth session | Switch to `@codetrix-studio/capacitor-google-auth` plugin and use the native flow on mobile |
| Push notifications silently fail on iOS | APNs cert not uploaded or expired | Re-issue APNs cert in developer.apple.com → re-upload to your push provider |
| App crashes on launch on iOS | Bundle ID mismatch | Make sure `capacitor.config.ts`, Xcode `Bundle Identifier`, and App Store Connect all match `com.bsossi.sacoparents` |

---

## Phase 7 — Going forward (each new release)

1. Build the web app: `yarn build`
2. Sync to native: `npx cap sync`
3. Bump version in `capacitor.config.ts`, `package.json`, AND in Xcode (`Marketing Version` + `Build`) AND in `android/app/build.gradle` (`versionCode` + `versionName`)
4. Open Xcode → Product → Archive → upload to App Store Connect → submit
5. Open Android Studio → Generate Signed Bundle → upload to Play Console → submit
6. Apple review: ~24 hrs for updates (much faster than first submission)
7. Google review: ~1-2 hrs for updates

---

## Cost summary
| Item | One-time | Annual |
|---|---|---|
| Apple Developer | — | $99 |
| Google Play | $25 | — |
| Cloud Mac (if needed) | — | $300-600 |
| Firebase Cloud Messaging | Free (within limits) | Free |
| **Total minimum to ship** | **$25** | **$99** |
| **Realistic if no Mac** | **$25** | **$400-700** |

---

## Open questions for the team
- [ ] Who owns the Apple Developer account credentials? (recommend: 1Password vault shared with 2 people)
- [ ] Privacy policy URL? (I can draft a template)
- [ ] App Store description text (4000 char limit)? (I can draft based on the existing app summary)
- [ ] Marketing screenshots — design them or take live ones?
- [ ] How will push notifications be sent — Firebase Cloud Messaging from the backend, or a managed service like OneSignal?
