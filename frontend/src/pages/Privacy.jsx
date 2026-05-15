import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

const LAST_UPDATED = "February 13, 2026";

export default function Privacy() {
  return (
    <div className="min-h-screen gentle-bg">
      <div className="max-w-3xl mx-auto px-5 sm:px-6 py-10 sm:py-14">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-sm text-[#5C7A6A] hover:text-[#849D8E] mb-6"
          data-testid="privacy-back-link"
        >
          <ArrowLeft size={14} /> Back to SA Coparents
        </Link>

        <div className="eyebrow mb-3">Privacy Policy</div>
        <h1 className="font-serif text-3xl sm:text-4xl text-[#2A3631] mb-2 leading-tight">
          Your prep is private. Always.
        </h1>
        <p className="text-sm text-[#8A9A92] mb-8">Last updated: {LAST_UPDATED}</p>

        <Prose>
          <p>
            <strong>SA Coparents</strong> (the "app", "we", "us") is operated by
            Matt Sossi at 16607 Blanco #703, San Antonio, Texas 78232.
            This policy explains what we collect, why, and how we protect it.
            Plain English first. Lawyerly precision second.
          </p>

          <H2>The short version</H2>
          <ul>
            <li>We collect <strong>only what's needed</strong> for you to use the app: your account info and the prep answers you type.</li>
            <li>We <strong>never</strong> sell your data. We never share it with advertisers. Period.</li>
            <li>Your prep answers go through Anthropic's Claude AI to generate your summary, agreement, and growth plan — and Anthropic does not use your data to train models.</li>
            <li>You can delete your account and all your data at any time by emailing us.</li>
            <li>If you're a domestic violence survivor, the app has a Quick Exit button and links to confidential national hotlines. Use them whenever you need.</li>
          </ul>

          <H2>What we collect</H2>
          <p><strong>Account information</strong> — Your name and email when you sign up. If you sign in with Google, we receive your name and email from Google (nothing more).</p>
          <p><strong>Your preparation content</strong> — Everything you enter in the wizard: child-centered goals, issues and concerns, priority topics, communication self-assessment, readiness ratings, and any free-text notes. This is the heart of the product.</p>
          <p><strong>AI-generated outputs</strong> — Your Mediation Summary, Co-Parenting Agreement Draft, and Things I Can Improve On plan, plus the historical snapshots used to compare versions over time.</p>
          <p><strong>Technical signals</strong> — Browser type, device type, IP address (for security), and a session token cookie so you stay signed in. We do not use third-party advertising trackers.</p>
          <p><strong>What we do NOT collect</strong> — We do not access your location, contacts, photos, microphone, camera, or any other device data unless you grant a specific in-app permission (e.g., Face ID / Touch ID, which is processed entirely on-device).</p>

          <H2>How we use your information</H2>
          <ul>
            <li><strong>To run the app</strong> — sign you in, save your prep, generate your summaries, email PDFs to your mediator when you ask.</li>
            <li><strong>To improve your experience</strong> — comparing your current prep against past versions to show "what's changed since last time."</li>
            <li><strong>To keep the app secure</strong> — limited use of IP addresses to spot abuse or fraud.</li>
            <li><strong>To support you</strong> — replying when you email us.</li>
          </ul>
          <p>We do <strong>not</strong> use your prep content for advertising, profile-building, or any purpose other than serving you.</p>

          <H2>How AI fits in</H2>
          <p>
            We use <strong>Anthropic Claude</strong> (via the Emergent universal LLM key) to synthesize your prep into your summary documents and growth plan. When you tap "Generate", your prep data is sent to Claude with strict instructions to produce a child-centered, non-judgmental document.
          </p>
          <p>
            Per Anthropic's commercial terms, your data is <strong>not used to train their models</strong>. The data is processed transiently to generate your response and then discarded by Anthropic.
          </p>

          <H2>How we store your data</H2>
          <p>
            Your data is stored in MongoDB Atlas, encrypted at rest and in transit (TLS 1.2+). Passwords are hashed with bcrypt — even we can't read them. Sessions use httpOnly cookies, not browser localStorage, to reduce exposure to client-side attacks.
          </p>

          <H2>Who we share with</H2>
          <ul>
            <li><strong>Service providers</strong> we contract with to run the app (currently: Emergent Labs for hosting, MongoDB Atlas for database, Anthropic for AI, Google for optional sign-in, Gmail SMTP for the optional "Email to mediator" feature). Each is bound by their own privacy commitments.</li>
            <li><strong>Your mediator</strong> — but only when you explicitly tap "Email to mediator" and enter their email address. We do not share with mediators automatically.</li>
            <li><strong>People you choose</strong> — when you tap "Share via text", we generate a signed 7-day download link that anyone with the URL can use to view the PDF. The link expires automatically after 7 days.</li>
            <li><strong>Legal compliance</strong> — if compelled by a valid legal process. We will notify you unless legally prohibited.</li>
          </ul>
          <p>We do not sell your data to anyone, ever.</p>

          <H2>Your rights</H2>
          <ul>
            <li><strong>Access</strong> — email us and we'll send you a copy of everything we have about you.</li>
            <li><strong>Correction</strong> — most fields are editable directly in the app. For others, email us.</li>
            <li><strong>Deletion</strong> — email us and we'll delete your account and all associated data within 30 days. PDFs already shared via expired links can no longer be retrieved.</li>
            <li><strong>Portability</strong> — we can export your prep + generated documents as JSON on request.</li>
          </ul>

          <H2>Children</H2>
          <p>
            SA Coparents is intended for parents and is not directed at children under 13. We do not knowingly collect information from anyone under 13. If you believe we have done so inadvertently, email us and we will delete it.
          </p>

          <H2>Safety note for survivors of domestic violence</H2>
          <p>
            If you're using this app while still in an unsafe situation, please be aware that the app does keep records of what you enter. If your device may be monitored, consider using the <Link to="/safety" className="text-[#5C7A6A] underline">Safety page</Link>'s Quick Exit feature and accessing the app from a private device when possible. The Safety page provides 24/7 hotlines including the National Domestic Violence Hotline (1-800-799-7233) and 988 Suicide & Crisis Lifeline.
          </p>

          <H2>Changes to this policy</H2>
          <p>
            We'll update this date and post the new policy here if we make material changes. If the changes are significant (e.g., new categories of data shared), we'll email you before they take effect.
          </p>

          <H2>Contact</H2>
          <p>Questions? Concerns? Want your data deleted?</p>
          <p>
            Email <a href="mailto:mattsossi@bsossi.com" className="text-[#5C7A6A] underline">mattsossi@bsossi.com</a>
            {" "}or call <a href="tel:2102241667" className="text-[#5C7A6A] underline">210-224-1667</a>.
          </p>
          <p className="text-xs text-[#8A9A92] italic mt-8">
            SA Coparents · 16607 Blanco #703, San Antonio, Texas 78232
          </p>
        </Prose>
      </div>
    </div>
  );
}

function H2({ children }) {
  return (
    <h2 className="font-serif text-2xl text-[#2A3631] mt-10 mb-3">{children}</h2>
  );
}

function Prose({ children }) {
  return (
    <div className="prose-soft space-y-3 text-[#2A3631] leading-relaxed [&_p]:text-[#5C6B64] [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:space-y-1.5 [&_li]:text-[#5C6B64] [&_strong]:text-[#2A3631] text-[15px]">
      {children}
    </div>
  );
}
