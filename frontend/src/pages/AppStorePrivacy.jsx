/**
 * App Store Privacy Disclosure — reconciled Apple + Google format.
 *
 * A single, plain-language disclosure that maps 1:1 onto Apple's App
 * Privacy label taxonomy and Google Play's Data Safety form. Any answer
 * a store operator gives in either console MUST match what appears on
 * this page. The comprehensive legal policy lives at `/privacy`; this
 * page is the short-form reconciled statement referenced from both
 * store listings.
 *
 * When the underlying data practices change:
 *   1. Update this page first (source of truth for both stores).
 *   2. Update the App Store Connect App Privacy questionnaire.
 *   3. Update the Google Play Data Safety form.
 *   4. Bump LAST_UPDATED and add a row to the "Change log" section.
 */
import React from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  ShieldCheck,
  Database,
  Users,
  BellOff,
  KeyRound,
  Lock,
} from "lucide-react";

const EFFECTIVE_DATE = "February 21, 2026";
const LAST_UPDATED = "June 2026";
const DELETE_URL = `${process.env.REACT_APP_PARENT_URL}/delete-account`;

/* Data-type rows shared by Apple + Google. Every collected data type
   this app touches lives here; the columns tell the stores exactly
   what to disclose. `apple` / `google` are the canonical console
   category names so operators can copy them verbatim. */
const DATA_ROWS = [
  {
    key: "email",
    label: "Email address",
    purpose: "Sign-in, six-digit verification codes, password reset, reviewer share notifications.",
    apple: "Contact Info → Email Address",
    google: "Personal info → Email address",
    linkedToUser: true,
    usedForTracking: false,
    optional: false,
  },
  {
    key: "name",
    label: "Parent / co-parent display name",
    purpose: "Personalises reports and identifies which parent authored a shared artefact.",
    apple: "Contact Info → Name",
    google: "Personal info → Name",
    linkedToUser: true,
    usedForTracking: false,
    optional: true,
  },
  {
    key: "assessment_answers",
    label: "Assessment answers, reflections & journal entries",
    purpose: "Generate the parent's reports, coaching, and joint alignment artefacts.",
    apple: "User Content → Other User Content",
    google: "App activity → Other user-generated content",
    linkedToUser: true,
    usedForTracking: false,
    optional: false,
  },
  {
    key: "health",
    label: "Child health, education, and psychological context",
    purpose:
      "Special Needs, Medical Deep-Dive, Educational Deep-Dive, and Psychological Deep-Dive modules — used only to generate care-plan artefacts the parent chooses to view or share.",
    apple: "Health & Fitness → Health (self-reported, child-centered)",
    google: "Health and fitness → Health info",
    linkedToUser: true,
    usedForTracking: false,
    optional: true,
    note:
      "Treated as PHI (Texas HB 300 §181.006). Never used for advertising, analytics, or model training.",
  },
  {
    key: "safety",
    label: "Family-violence safety screen responses",
    purpose:
      "Route the parent to the appropriate communication pathway (co-parent, parallel, or safety-first) and to Texas crisis resources.",
    apple: "Sensitive Info → Other Sensitive Info",
    google: "Personal info → Other info",
    linkedToUser: true,
    usedForTracking: false,
    optional: true,
    note: "Safety data is never sent to third parties without a court order or the parent's explicit consent.",
  },
  {
    key: "device",
    label: "Account and session identifier",
    purpose:
      "Keep the parent signed in across the web app and PWA, and detect logged-out states.",
    apple: "Identifiers → User ID",
    google: "Personal info → User IDs",
    linkedToUser: true,
    usedForTracking: false,
    optional: false,
  },
  {
    key: "voice",
    label: "Voice notes",
    purpose: "Turned into text so the parent doesn't have to type. The audio is not stored.",
    apple: "User Content → Audio Data",
    google: "Audio files → Voice or sound recordings",
    linkedToUser: true,
    usedForTracking: false,
    optional: true,
    note: "Processed ephemerally: transcribed, then discarded.",
  },
  {
    key: "gmail",
    label: "Gmail messages (only if the parent connects Gmail)",
    purpose: "Shown in the app so the parent can draft a calmer reply. Messages are read live and not stored.",
    apple: "User Content → Emails or Text Messages",
    google: "Messages → Emails",
    linkedToUser: true,
    usedForTracking: false,
    optional: true,
    note: "Processed ephemerally. The parent can disconnect Gmail at any time.",
  },
];

/* Google Play Data Safety, one row per Google data type. Must match DATA_ROWS and the Apple answers below. */
const GOOGLE_ROWS = [
  { key: "name", type: "Personal info → Name", required: "Optional", ephemeral: "No", purposes: "App functionality, Account management" },
  { key: "email", type: "Personal info → Email address", required: "Required", ephemeral: "No", purposes: "App functionality, Account management" },
  { key: "user-ids", type: "Personal info → User IDs", required: "Required", ephemeral: "No", purposes: "App functionality, Account management, Fraud prevention, security, and compliance" },
  { key: "other-info", type: "Personal info → Other info (safety screen answers)", required: "Optional", ephemeral: "No", purposes: "App functionality" },
  { key: "health", type: "Health and fitness → Health info (child health, education and psychological context)", required: "Optional", ephemeral: "No", purposes: "App functionality" },
  { key: "emails", type: "Messages → Emails (Gmail, only if connected)", required: "Optional", ephemeral: "Yes", purposes: "App functionality" },
  { key: "voice", type: "Audio files → Voice or sound recordings", required: "Optional", ephemeral: "Yes", purposes: "App functionality" },
  { key: "ugc", type: "App activity → Other user-generated content", required: "Required", ephemeral: "No", purposes: "App functionality" },
];

const GOOGLE_NOT_COLLECTED = [
  "Location (approximate or precise)",
  "Financial info",
  "Photos and videos",
  "Files and docs",
  "Calendar",
  "Contacts",
  "App activity → App interactions, In-app search history, Installed apps, Other actions",
  "Web browsing",
  "App info and performance (crash logs, diagnostics, other performance data)",
  "Device or other IDs (including the advertising ID)",
];

const DATA_WE_DO_NOT_COLLECT = [
  "Precise or approximate location.",
  "Contacts, calendar, photos, or files from the parent's device.",
  "Uploaded child medical, educational, or psychological records or documents. There is no upload feature.",
  "Product analytics, session recordings, or crash-reporting SDKs.",
  "Advertising identifiers (IDFA / GAID).",
  "Financial information — the app is free; there is no payment collection.",
  "Purchase history from other apps.",
  "Browsing history outside SA CoParents.",
];

export default function AppStorePrivacy() {
  return (
    <div className="min-h-screen gentle-bg" data-testid="app-store-privacy-page">
      <div className="max-w-3xl mx-auto px-5 sm:px-6 py-10 sm:py-14">
        <Link
          to="/privacy"
          className="inline-flex items-center gap-2 text-sm text-[#2A0F5F] hover:text-[#3D1A78] mb-6"
          data-testid="app-store-privacy-back-link"
        >
          <ArrowLeft size={14} /> Back to the full Privacy Policy
        </Link>

        <div className="eyebrow mb-3">App Store Privacy Disclosure</div>
        <h1
          className="font-serif text-3xl sm:text-4xl text-[#1A1330] mb-2 leading-tight"
          data-testid="app-store-privacy-title"
        >
          Apple App Privacy &amp; Google Play Data Safety — Reconciled Disclosure
        </h1>
        <p className="text-sm text-[#6E6787] mb-8">
          Effective: {EFFECTIVE_DATE} · Last updated: {LAST_UPDATED}
        </p>

        <div className="rounded-2xl border border-[#E5E0EE] bg-white p-5 mb-8 flex items-start gap-3">
          <ShieldCheck size={20} className="text-[#3D1A78] flex-shrink-0 mt-0.5" />
          <p className="text-sm text-[#4B4567] leading-relaxed !m-0">
            This page is the single reconciled short-form statement referenced
            from both the App Store and Google Play listings. Every answer
            given in App Store Connect (App Privacy) and Google Play Console
            (Data Safety) matches the categories, purposes, and linkage flags
            on this page. The full 32-section policy lives at{" "}
            <Link
              to="/privacy"
              className="text-[#2A0F5F] underline"
              data-testid="app-store-privacy-policy-link"
            >
              /privacy
            </Link>
            .
          </p>
        </div>

        {/* Section 1 — The five headline commitments both stores render */}
        <H2 icon={<Lock size={16} />}>1. Headline commitments</H2>
        <ul className="space-y-2 text-[15px] text-[#4B4567] leading-relaxed list-disc pl-5">
          <li>
            <strong className="text-[#1A1330]">No tracking across other apps or websites.</strong>{" "}
            SA CoParents does not use IDFA, GAID, cross-app cookies, or
            third-party advertising SDKs. Both the Apple &ldquo;Tracking&rdquo;
            and Google &ldquo;Data shared with third parties for
            advertising&rdquo; answers are <em>No</em>.
          </li>
          <li>
            <strong className="text-[#1A1330]">No AI model training on user data.</strong>{" "}
            Reflections, assessment answers, and family-violence screens are
            never used to train the AI models that generate summaries. LLM
            calls are transient and no user content is retained by the
            provider beyond the request.
          </li>
          <li>
            <strong className="text-[#1A1330]">Encrypted in transit and at rest.</strong>{" "}
            TLS 1.2+ in transit; database encrypted at rest by the managed
            provider. Emails to reviewers can additionally be routed through
            the Virtru Hosted Gateway when the flag is enabled and a BAA is
            in place with the receiving practice.
          </li>
          <li>
            <strong className="text-[#1A1330]">Delete anytime.</strong> Parents
            can delete their account and every artefact from{" "}
            <Link to="/account" className="text-[#2A0F5F] underline">
              /account
            </Link>{" "}
            → Delete my account. Full deletion completes within 30 days.
          </li>
          <li>
            <strong className="text-[#1A1330]">Children under 13 are not the primary users.</strong>{" "}
            SA CoParents is for the adult parent. Information <em>about</em>{" "}
            a child (name, needs, medical/educational context) is entered by
            the parent and treated as their content, not directly collected
            from the child.
          </li>
        </ul>

        {/* Section 2 — The full reconciled data table */}
        <H2 icon={<Database size={16} />}>2. Data we collect (both stores)</H2>
        <p className="text-[15px] text-[#4B4567] leading-relaxed">
          Every row below lists a single data type, why we collect it, and the
          exact category to select in both App Store Connect and Google Play
          Console. If a data type does not appear on this list, we do not
          collect it.
        </p>

        <div tabIndex={0} role="region" aria-label="Scrollable table" className="mt-4 overflow-x-auto rounded-2xl border border-[#E5E0EE] bg-white">
          <table
            className="w-full text-[13px] text-left"
            data-testid="app-store-privacy-data-table"
          >
            <thead className="bg-[#F8F7FC] text-[#1A1330]">
              <tr>
                <th className="px-3 py-2 font-medium">Data type</th>
                <th className="px-3 py-2 font-medium">Purpose</th>
                <th className="px-3 py-2 font-medium">Apple category</th>
                <th className="px-3 py-2 font-medium">Google category</th>
                <th className="px-3 py-2 font-medium text-center">Linked?</th>
                <th className="px-3 py-2 font-medium text-center">Tracking?</th>
                <th className="px-3 py-2 font-medium text-center">Optional?</th>
              </tr>
            </thead>
            <tbody>
              {DATA_ROWS.map((row) => (
                <tr
                  key={row.key}
                  className="border-t border-[#EFE9F9] align-top"
                  data-testid={`app-store-privacy-row-${row.key}`}
                >
                  <td className="px-3 py-3 text-[#1A1330] font-medium">
                    {row.label}
                    {row.note && (
                      <div className="text-[11px] text-[#6E6787] italic mt-1 leading-snug font-normal">
                        {row.note}
                      </div>
                    )}
                  </td>
                  <td className="px-3 py-3 text-[#4B4567] leading-snug">
                    {row.purpose}
                  </td>
                  <td className="px-3 py-3 text-[#4B4567] leading-snug">
                    {row.apple}
                  </td>
                  <td className="px-3 py-3 text-[#4B4567] leading-snug">
                    {row.google}
                  </td>
                  <td className="px-3 py-3 text-center text-[#4B4567]">
                    {row.linkedToUser ? "Yes" : "No"}
                  </td>
                  <td className="px-3 py-3 text-center text-[#4B4567]">
                    {row.usedForTracking ? "Yes" : "No"}
                  </td>
                  <td className="px-3 py-3 text-center text-[#4B4567]">
                    {row.optional ? "Yes" : "No"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="text-[12px] text-[#6E6787] italic mt-3 leading-relaxed">
          &ldquo;Linked?&rdquo; matches Apple&rsquo;s &ldquo;Data Linked to
          You&rdquo; and Google&rsquo;s &ldquo;Personal info collected&rdquo;
          flag. &ldquo;Tracking?&rdquo; is <em>No</em> for every row — SA
          CoParents does not track parents across apps or websites owned by
          other companies.
        </p>

        {/* Section 3 — What we deliberately do not collect */}
        <H2 icon={<BellOff size={16} />}>3. Data we do NOT collect</H2>
        <ul className="space-y-1.5 text-[15px] text-[#4B4567] leading-relaxed list-disc pl-5">
          {DATA_WE_DO_NOT_COLLECT.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>

        {/* Section 4 — Data sharing */}
        <H2 icon={<Users size={16} />}>4. Data sharing</H2>
        <p className="text-[15px] text-[#4B4567] leading-relaxed">
          Data is shared only when the parent explicitly initiates the share
          from within the app, or when required by law:
        </p>
        <ul className="space-y-1.5 text-[15px] text-[#4B4567] leading-relaxed list-disc pl-5">
          <li>
            <strong className="text-[#1A1330]">With a co-parent</strong> —
            only after the parent creates a compare share and their co-parent
            accepts. Parents never share passwords; each parent signs in with
            their own credentials.
          </li>
          <li>
            <strong className="text-[#1A1330]">With a mediator, attorney, therapist, or pediatrician</strong>{" "}
            — only via a time-limited share token or PDF the parent
            personally mints. Revocable at any time from{" "}
            <Link to="/account" className="text-[#2A0F5F] underline">
              /account
            </Link>
            .
          </li>
          <li>
            <strong className="text-[#1A1330]">With service providers</strong>{" "}
            necessary to run the app (MongoDB hosting, Resend transactional
            email, LLM providers). Contracts
            forbid secondary use of user content.
          </li>
          <li>
            <strong className="text-[#1A1330]">When required by law</strong>{" "}
            — a valid subpoena or court order for a specific user record.
          </li>
        </ul>

        {/* Section 5 — Parent controls */}
        <H2 icon={<KeyRound size={16} />}>5. Parent controls</H2>
        <ul className="space-y-1.5 text-[15px] text-[#4B4567] leading-relaxed list-disc pl-5">
          <li>
            View, revoke, or re-send active share links from{" "}
            <Link to="/dashboard" className="text-[#2A0F5F] underline">
              /dashboard
            </Link>{" "}
            → Share management.
          </li>
          <li>
            Export the accounting-of-disclosures log (every access to the
            parent&rsquo;s PHI) from{" "}
            <Link to="/data-retention" className="text-[#2A0F5F] underline">
              /data-retention
            </Link>
            .
          </li>
          <li>
            Delete the account and every artefact from{" "}
            <Link to="/account" className="text-[#2A0F5F] underline">
              /account
            </Link>
            .
          </li>
          <li>
            Contact the Privacy Officer at{" "}
            <a
              href="mailto:mattsossi@bsossi.com"
              className="text-[#2A0F5F] underline"
            >
              mattsossi@bsossi.com
            </a>{" "}
            or 210-224-1667.
          </li>
        </ul>

        {/* Section 6 — Google Play Data Safety */}
        <H2>6. Google Play Data Safety answers</H2>
        <GoogleDataSafety />

        {/* Section 7 — Store-console answer sheet */}
        <H2>7. Store-console quick answers</H2>
        <p className="text-[15px] text-[#4B4567] leading-relaxed">
          Copy these answers verbatim into each console when re-submitting
          the app. Apple and Google answers describe the same data:
        </p>
        <div className="rounded-2xl border border-[#E5E0EE] bg-[#F8F7FC] p-5 mt-3 text-[14px] text-[#1A1330] leading-relaxed space-y-2" data-testid="app-store-privacy-quick-answers">
          <p className="!m-0">
            <strong>Apple App Privacy → Do you or your third-party partners use data for tracking?</strong>{" "}
            No.
          </p>
          <p className="!m-0">
            <strong>Apple App Privacy → Data used to track you:</strong> None.
          </p>
          <p className="!m-0" data-testid="app-store-privacy-apple-linked">
            <strong>Apple App Privacy → Data linked to you:</strong> Contact
            Info (Email Address, Name), User Content (Emails or Text Messages,
            only if Gmail is connected; Audio Data, voice notes; Other User
            Content), Health &amp; Fitness (Health, self-reported,
            child-centered), Sensitive Info (safety screen), Identifiers
            (User ID).
          </p>
          <p className="!m-0" data-testid="app-store-privacy-apple-not-linked">
            <strong>Apple App Privacy → Data not linked to you:</strong>{" "}
            None.
          </p>
          <p className="!m-0">
            <strong>Apple App Privacy → Purpose for every data type:</strong>{" "}
            App Functionality.
          </p>
          <p className="!m-0">
            <strong>Google Play Data Safety → Does your app collect or share any of the required user data types?</strong>{" "}
            Yes. It collects the types in section 6. It shares none.
          </p>
          <p className="!m-0">
            <strong>Google Play Data Safety → Is all of the user data collected by your app encrypted in transit?</strong>{" "}
            Yes (TLS 1.2+).
          </p>
          <p className="!m-0">
            <strong>Google Play Data Safety → Do you provide a way for users to request that their data be deleted?</strong>{" "}
            Yes. In the app at{" "}
            <Link to="/account" className="text-[#2A0F5F] underline">
              /account
            </Link>
            , and on the web at{" "}
            <a href={DELETE_URL} className="text-[#2A0F5F] underline break-all" data-testid="app-store-privacy-delete-url">
              {DELETE_URL}
            </a>
            .
          </p>
        </div>

        {/* Section 8 — Change log */}
        <H2>Change log</H2>
        <ul className="space-y-1 text-[13px] text-[#4B4567] leading-relaxed list-disc pl-5">
          <li>
            <strong className="text-[#1A1330]">June 2026</strong> — Added the
            Google Play Data Safety answers (section 6). Removed product
            analytics and crash diagnostics, which are no longer collected,
            and the matching Apple answers. Added voice notes and optional
            Gmail messages,
            both processed ephemerally. Child record folders were removed, so
            no child records or documents are stored. Account and session
            identifiers now map to Google &ldquo;User IDs&rdquo;.
          </li>
          <li>
            <strong className="text-[#1A1330]">March 4, 2026</strong> —
            Initial reconciled Apple + Google disclosure created; matches
            the full policy at /privacy (dated Feb 21, 2026).
          </li>
        </ul>

        <p className="text-xs text-[#6E6787] italic mt-10">
          SA CoParents · 16607 Blanco #703, San Antonio, Texas 78232 ·{" "}
          <a
            href="mailto:mattsossi@bsossi.com"
            className="text-[#2A0F5F] underline"
          >
            mattsossi@bsossi.com
          </a>
        </p>
      </div>
    </div>
  );
}

function YesNo({ v }) {
  return <span className={v === "Yes" ? "font-semibold text-[#1A1330]" : "text-[#4B4567]"}>{v}</span>;
}

function GoogleDataSafety() {
  return (
    <div data-testid="app-store-privacy-google">
      <p className="text-[15px] text-[#4B4567] leading-relaxed">
        In Google Play Console → App content → Data safety, mark each type below
        as <strong className="text-[#1A1330]">collected</strong> and{" "}
        <strong className="text-[#1A1330]">not shared</strong>. Leave every
        other type unselected.
      </p>
      <div tabIndex={0} role="region" aria-label="Scrollable table" className="mt-4 overflow-x-auto rounded-2xl border border-[#E5E0EE] bg-white">
        <table className="w-full text-[13px] text-left" data-testid="app-store-privacy-google-table">
          <thead className="bg-[#F8F7FC] text-[#1A1330]">
            <tr>
              <th className="px-3 py-2 font-medium">Google data type</th>
              <th className="px-3 py-2 font-medium text-center">Collected</th>
              <th className="px-3 py-2 font-medium text-center">Shared</th>
              <th className="px-3 py-2 font-medium text-center">Processed ephemerally</th>
              <th className="px-3 py-2 font-medium text-center">Required or optional</th>
              <th className="px-3 py-2 font-medium">Purposes</th>
            </tr>
          </thead>
          <tbody>
            {GOOGLE_ROWS.map((r) => (
              <tr key={r.key} className="border-t border-[#EFE9F9] align-top" data-testid={`app-store-privacy-google-row-${r.key}`}>
                <td className="px-3 py-3 text-[#1A1330] font-medium">{r.type}</td>
                <td className="px-3 py-3 text-center"><YesNo v="Yes" /></td>
                <td className="px-3 py-3 text-center"><YesNo v="No" /></td>
                <td className="px-3 py-3 text-center"><YesNo v={r.ephemeral} /></td>
                <td className="px-3 py-3 text-center text-[#4B4567]">{r.required}</td>
                <td className="px-3 py-3 text-[#4B4567] leading-snug">{r.purposes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h3 className="font-serif text-lg text-[#1A1330] mt-6 mb-2">Not collected (leave unselected)</h3>
      <ul className="space-y-1 text-[14px] text-[#4B4567] leading-relaxed list-disc pl-5" data-testid="app-store-privacy-google-not-collected">
        {GOOGLE_NOT_COLLECTED.map((t) => (
          <li key={t}>{t}</li>
        ))}
      </ul>
      <h3 className="font-serif text-lg text-[#1A1330] mt-6 mb-2">Why &ldquo;Shared&rdquo; is No</h3>
      <p className="text-[14px] text-[#4B4567] leading-relaxed">
        Google doesn&rsquo;t count two kinds of transfer as sharing: data sent to
        service providers that process it for us (hosting, email delivery, AI
        processing), and data a parent sends on purpose after an in-app
        disclosure (for example, sending a document to a professional, see{" "}
        <Link to="/what-professionals-see" className="text-[#2A0F5F] underline">What professionals can see</Link>
        ). Both are explained in the{" "}
        <Link to="/privacy" className="text-[#2A0F5F] underline">Privacy Policy</Link>.
      </p>
      <p className="text-[13px] text-amber-900 bg-amber-50 border border-amber-200 rounded-xl px-3 py-2 mt-3 leading-relaxed" data-testid="app-store-privacy-google-review">
        <strong>Attorney review:</strong> confirm whether data SA CoParents Align
        reads after a parent links their account counts as &ldquo;sharing&rdquo;
        for Google and Apple.
      </p>
    </div>
  );
}

function H2({ children, icon }) {
  return (
    <h2 className="font-serif text-2xl text-[#1A1330] mt-10 mb-3 flex items-center gap-2">
      {icon && <span className="text-[#3D1A78]">{icon}</span>}
      {children}
    </h2>
  );
}
