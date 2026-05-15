# SA Coparents — App Store Submission Pack

Everything you need to submit to Apple App Store Connect and Google Play
Console. Copy-paste ready. Last updated: Feb 13, 2026.

---

## 1. App identity (must match exactly across Apple, Google, Capacitor)

| Field | Value |
|---|---|
| **App display name** | SA Coparents |
| **Bundle ID / App ID** | `com.bsossi.sacoparents` |
| **Primary language** | English (United States) |
| **SKU (Apple only)** | `sacoparents-v1` |
| **Version** | 1.0.0 |
| **Build number** | 1 |
| **Primary category** | Health & Fitness |
| **Secondary category** | Lifestyle |
| **Age rating** | 17+ (references to domestic violence, mental health crisis) |
| **Price** | Free |
| **Contains in-app purchases** | No |
| **Contains ads** | No |

## 2. Required URLs

| Where to paste | URL |
|---|---|
| **Privacy Policy URL** | https://sacoparentsapp.online/privacy |
| **Terms of Service URL** | https://sacoparentsapp.online/terms |
| **Support URL** | mailto:mattsossi@bsossi.com or https://sacoparentsapp.online |
| **Marketing URL** (optional) | https://sacoparentsapp.online |

## 3. App icon

File: `/app/memory/app_store_assets/icon-1024.png` (1024 × 1024 PNG, no transparency)

Also a 512 × 512 copy in the same folder for the Play Store feature graphic.

When you generate the iOS app via `npx cap add ios`, drop the 1024 icon
into Xcode → Assets.xcassets → AppIcon. Xcode will auto-generate every
smaller size from it.

For Android: drop the 512 into Android Studio → res/mipmap or use the
Image Asset wizard to produce all densities.

---

## 4. App Store description (4000 char limit)

**Short tagline / subtitle (30 char):**

> Prepared. Centered. Calm.

**Promotional text (170 char, can change anytime without re-review):**

> Walk into your next mediation session calm, child-centered, and clear on what matters most — without losing yourself in the process.

**Full description:**

> Walk into your mediation session calm, focused, and ready.
>
> SA Coparents is a private, child-centered preparation tool for parents heading into co-parenting mediation. Instead of arriving emotionally reactive, you arrive prepared — with a clear agenda, a written summary your mediator can read in two minutes, and a personal growth plan that meets you where you are.
>
> WHO THIS IS FOR
> • Parents preparing for a relational or court-ordered mediation session
> • Survivors of domestic violence considering parallel parenting — the safer framework when traditional co-parenting isn't viable
> • Anyone who wants to be more deliberate about their child's experience after separation
>
> WHAT YOU'LL DO (about 30 minutes total, your pace)
> 1. Choose your child-centered goals from a curated list — emotional safety, stability, school success, healthy relationships, reduced conflict exposure, and more.
> 2. Name what's actually happening — 10 specific concerns plus open space for your own.
> 3. Rank what matters — sort 11 key topics (custody, possession schedule, mental health, medication, geographic restriction, right of first refusal, and others) into "Most urgent," "Most emotionally difficult," "Easier agreements," and "Willing to compromise."
> 4. Self-assess your communication style and readiness — quick, judgment-free.
> 5. Generate three AI-synthesized documents:
>    • Mediation Summary — focused and ready for your mediator
>    • Co-Parenting Agreement Draft — neutral, starter language to build on together
>    • Things I Can Improve On — a warm, specific growth plan with concrete tips
>
> EVERY DOCUMENT
> • Downloads as a polished PDF
> • Can be emailed directly to your mediator with one tap
> • Can be shared via a private 7-day expiring link
> • Updates itself with "what's changed since last time" when you retake your assessments — so you can track your growth across multiple mediation sessions
>
> A SAFER FRAMEWORK FOR DOMESTIC VIOLENCE SURVIVORS
> When traditional co-parenting isn't safe, the app includes a complete Parallel Parenting framework — explaining why high-boundary structures protect children and survivors, what an effective parallel parenting plan includes, and where to find immediate help. A Quick Exit button (and ESC key shortcut) lets you switch away instantly. The 988 Suicide & Crisis Lifeline and National Domestic Violence Hotline are one tap away.
>
> PRIVACY IS THE WHOLE POINT
> Your prep is yours. We don't sell data, run ads, or use your content to train AI. Face ID / Touch ID locks the app every time you put it down. Anthropic's Claude AI processes your prep to generate your summaries — and per their commercial terms, your data is never used for model training.
>
> CALM BY DESIGN
> Muted, earthy palette. Warm typography. Non-judgmental tone. This is not a productivity tracker or a venting journal. It's a quiet ritual to help you arrive at the mediation table as the parent your child needs.
>
> SA Coparents was built in San Antonio. Local resources for Bexar County families sit alongside national 24/7 hotlines.

(~3,150 characters — well under Apple's 4,000 limit, room to add testimonials later)

---

## 5. App Store keywords (100 char limit, comma-separated, no spaces after commas)

> mediation,coparenting,co-parenting,divorce,custody,family,parenting,reflection,prep,san antonio,calm

(98 chars)

**Why these keywords:**
- `mediation` + `coparenting` are the high-intent searches — our exact audience
- `custody` + `divorce` + `family` widen the funnel without pulling in the wrong audience
- `prep` + `reflection` + `calm` differentiate from venting / journaling apps
- `san antonio` captures the local SEO advantage (Bexar County resources baked in)
- Apple ignores stopwords like `the`, `for`, `app` — don't waste characters on those

---

## 6. Screenshots — what to capture and in what order

Apple requires at least 3, allows up to 10. Order matters — first 3 are what people see in the preview row. Take all on a 6.7" iPhone simulator (1290 × 2796) or use the Xcode → Window → Devices menu to capture from a real phone.

Order the screenshots like a story:

1. **Landing / Hero** — Showcases the calm, warm tone. Caption: *"Prepared. Centered. Calm."*
2. **Dashboard with progress bar** — Tells the story of the 5-step prep. Caption: *"A 30-minute ritual at your pace."*
3. **Priority Ranking with drag-and-drop** — Shows the unique interaction. Caption: *"Rank what really matters."*
4. **Mediation Summary tab** — The payoff. Caption: *"Your prep — ready for the mediator."*
5. **Things I Can Improve On** — The growth feature. Caption: *"Compiled tips for the real you."*
6. **Safety page with hotlines** — The trust-building moment. Caption: *"24/7 support, always one tap away."*
7. **(Optional) Email-to-mediator dialog** — Shows the share/email features. Caption: *"Email your mediator in one tap."*

**Caption tone:** Warm, specific, never breathless. Match the app's voice. No exclamation points.

**Easiest capture method:** open the app on a real iPhone (or iPhone 15 Pro Max simulator at 1290×2796 in Xcode), navigate to each screen, take a screenshot (volume up + side button). Drag into App Store Connect.

---

## 7. App Privacy "Data Types Collected" answers

When Apple asks about data collection during submission, here's what to select. Each item must include the *purpose*.

| Data | Linked to user? | Used for tracking? | Purpose |
|---|---|---|---|
| **Name** | Yes | No | App Functionality |
| **Email** | Yes | No | App Functionality, Customer Support |
| **User Content** (your prep answers) | Yes | No | App Functionality |
| **Other User Content** (AI-generated summaries, agreement drafts) | Yes | No | App Functionality |
| **Device ID** (push notification token, optional) | Yes | No | App Functionality |
| **Crash Data** | No | No | Analytics |
| **Performance Data** | No | No | Analytics |

**Important:** Select "No" for "Used for tracking" on every single item. We don't track users across other apps or websites. Make sure to also disable any cross-app tracking in code (we have none, this is just to be explicit).

---

## 8. Demo account for Apple/Google review

Apple and Google reviewers need a working account to test the app. **Do not** give them your real admin account.

Already provisioned (also lives in `/app/memory/test_credentials.md`):

```
Email:    parent1@test.com
Password: TestPass123!
```

This account has:
- Completed wizard answers
- One previously-generated summary (so the "Changes since last time" feature is visible on the second generation)
- Test priority items already sorted

If the reviewer wants to test the biometric login, instruct them to:
> "After signing in with the email above, close the app and reopen it. The biometric prompt will appear. On a simulator, use Face ID → Matching Face from the Features menu."

---

## 9. App Review Information — Notes to Reviewer

Paste this EXACTLY in the "Notes" field when submitting (Apple is very strict about wrapped websites; this note pre-empts that rejection):

> Hello,
>
> SA Coparents is a private preparation tool for parents heading into co-parenting mediation. Below is context the reviewer may find helpful.
>
> 1) UNIQUE NATIVE FEATURES (NOT JUST A WEB WRAPPER)
> • Biometric authentication: After signing in, the app locks every time it returns to the foreground. The user must use Face ID or Touch ID to re-enter. This is implemented via the native LocalAuthentication framework and is genuinely useful for a privacy-sensitive use case — survivors of domestic violence may share a device.
> • Offline access: The Safety page (with crisis hotlines including 988 and the National DV Hotline) is cached via a service worker so users can reach it without an internet connection.
> • Push notifications: Users receive reminders when their mediation date approaches and when their prep is more than 7 days old (re-engagement).
> • Native PDF generation, sharing, and email-to-mediator features.
>
> 2) DEMO ACCOUNT
> Email: parent1@test.com
> Password: TestPass123!
> This account has pre-filled prep data so the reviewer can immediately tap "Generate" on the Summary page and see the full feature set, including the "Changes since last time" comparison feature.
>
> 3) AGE RATING — 17+
> We selected 17+ because the app references domestic violence dynamics, mental health crisis (988 Suicide & Crisis Lifeline), and provides resources specifically for survivors of coercive controlling violence. The content is educational and supportive, never graphic, but the topic area warrants the higher rating.
>
> 4) CONTENT IS USER-GENERATED, REVIEWED INTERNALLY
> All content shown publicly inside the app is curated by us. There is no user-to-user content sharing, no comments, no chat — eliminating the typical UGC moderation concerns.
>
> 5) AI USAGE
> The app uses Anthropic Claude (via API) to synthesize the user's own preparation into structured summary documents. We do not generate images, audio, or persona-based responses. Outputs are explicitly framed as "starter documents" — not legal advice, not medical advice. We have clear disclaimers in the app and Terms of Service.
>
> 6) PRIVACY POLICY & TERMS
> Both are linked from the app footer and hosted at https://sacoparentsapp.online/privacy and /terms. Both explicitly state we do not sell, share, or use user data for advertising or AI training.
>
> Thank you for reviewing SA Coparents. If anything needs clarification, please reach me at mattsossi@bsossi.com or 210-224-1667.

---

## 10. Google Play Store specifics (where it differs from Apple)

- **Short description** (80 char): *"Calm, child-centered preparation for co-parenting mediation."*
- **Long description**: same as Apple (above)
- **Feature graphic** (1024 × 500 banner) — needed for Play Store. Easiest: open Photoshop / Canva, place the SA Coparents logo on the cream `#FDFAF3` background with the tagline "Prepared. Centered. Calm." in Cormorant Garamond. Save 1024×500.
- **Target audience and content rating**: 18+. When the rating questionnaire asks about violence, alcohol, or drugs, answer NO — the references to domestic violence are educational resources, not depictions.
- **Data Safety section**: same answers as Apple's privacy questionnaire above. Google's form is more granular but the same truth applies — nothing is tracked, nothing is sold.

---

## 11. Submission checklist

Before tapping "Submit for Review":

- [ ] App icon dropped in (1024 for iOS, 512 for Android)
- [ ] All screenshots uploaded (at least 3, ideally 5–7)
- [ ] Description, subtitle, keywords pasted
- [ ] Privacy Policy URL: https://sacoparentsapp.online/privacy
- [ ] Demo account credentials in the App Review Information section
- [ ] Reviewer notes pasted
- [ ] Age rating: 17+ (iOS) / 18+ (Android)
- [ ] Pricing: Free
- [ ] Available in: All countries (or limit to US if you prefer initially)
- [ ] Build uploaded from Xcode → Archive → Distribute → App Store Connect
- [ ] App version number matches between Capacitor config, Xcode, and App Store Connect

Then tap **Submit for Review**.

Expected review times:
- **Apple**: 24-48 hours typically, occasionally up to 7 days
- **Google**: 1-3 hours for updates, up to 7 days for first submission

---

## 12. After approval

- **Don't forget** to update SMTP_PASSWORD in production env vars so the "Email to mediator" feature actually sends mail.
- **Set up a deep-link domain association file** at https://sacoparentsapp.online/.well-known/apple-app-site-association so tapping a link to sacoparentsapp.online from another app opens directly in the SA Coparents native app.
- **Add screenshots of real, anonymized testimonials** after a month of feedback — boosts conversion rate dramatically.

That's it. Everything else is captured in `APP_STORE_GUIDE.md`.
