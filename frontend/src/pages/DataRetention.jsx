import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, HardDrive, Trash2, Download, Clock } from "lucide-react";
import MarketingConsentToggle from "../components/account/MarketingConsentToggle";

const LAST_UPDATED = "February 21, 2026";

/**
 * Data Retention Policy — companion to Privacy.
 * Focused on the specific question every parent asks: "how long do you
 * keep my stuff, and how do I get it out."
 */
export default function DataRetention() {
  return (
    <div className="min-h-screen gentle-bg" data-testid="data-retention-page">
      <div className="max-w-3xl mx-auto px-5 sm:px-6 py-10 sm:py-14">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-sm text-[#2A0F5F] hover:text-[#3D1A78] mb-6"
          data-testid="data-retention-back-link"
        >
          <ArrowLeft size={14} /> Back to SA CoParents
        </Link>

        <div className="eyebrow mb-3">Data Retention</div>
        <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] mb-2 leading-tight">
          Your data. Your timeline.
        </h1>
        <p className="text-sm text-[#6E6787] mb-8">Last updated: {LAST_UPDATED}</p>

        <Prose>
          <p>
            This page explains, in plain English, how long each type of data
            lives in SA CoParents — and how to get it out or delete it.
            For the full legal treatment, see our{" "}
            <Link to="/privacy" className="text-[#2A0F5F] underline">Privacy Policy</Link>.
          </p>

          <div className="grid sm:grid-cols-3 gap-3 not-prose my-6">
            <StatCard icon={<HardDrive size={16} />} label="Where it lives" value="MongoDB Atlas (US-East)" />
            <StatCard icon={<Clock size={16} />} label="Guest sandbox" value="1 year" />
            <StatCard icon={<Trash2 size={16} />} label="Deletion window" value="≤ 30 days" />
          </div>

          {/* Communication preferences — HB 300 marketing opt-in toggle.
              Lives on the Data & Retention page (parents' account hub)
              until a dedicated /account page ships. */}
          <div className="not-prose my-6">
            <MarketingConsentToggle />
          </div>

          <H2>Retention schedule</H2>
          <div tabIndex={0} role="region" aria-label="Scrollable table" className="overflow-x-auto not-prose my-4">
            <table className="w-full text-left text-sm border-collapse" data-testid="retention-table">
              <thead>
                <tr className="text-[0.6875rem] uppercase tracking-[0.12em] text-[#6E6787]">
                  <Th>Data type</Th>
                  <Th>How long we keep it</Th>
                  <Th>Why</Th>
                </tr>
              </thead>
              <tbody className="text-[#4B4567]">
                <Row
                  type="Account (name + email)"
                  duration="For as long as your account exists, or until you request deletion."
                  reason="Required to log you in and email your reports."
                />
                <Row
                  type="Prep answers & AI-generated summaries"
                  duration="For as long as your account exists. Historical snapshots retained so we can show 'what's changed since last time.'"
                  reason="Longitudinal growth tracking is a core feature."
                />
                <Row
                  type="Assessment scores (Readiness, Special Needs, Safety)"
                  duration="Retained per account. Never sold, never used for training."
                  reason="Needed to power your progress charts."
                />
                <Row
                  type="Guest sandbox data (no account)"
                  duration="1 year from first activity, then auto-purged."
                  reason="Lets you evaluate the product with zero commitment."
                />
                <Row
                  type="AI Coach chat transcripts"
                  duration="Stored in your account. Not sent to Anthropic for training."
                  reason="So you can revisit past coaching threads."
                />
                <Row
                  type="Shareable PDF links (signed tokens)"
                  duration="Default 7 days from creation. Parents can pick 1, 7, or 30 days at share time, or 'no expiry' for links they'll revoke manually. Every link is revocable from the dashboard at any moment."
                  reason="Time-boxed so a stale link cannot outlive its usefulness."
                />
                <Row
                  type="Journal entries"
                  duration="For as long as your account exists."
                  reason="Weekly recaps + longitudinal reflection."
                />
                <Row
                  type="Backups"
                  duration="Rolling 30-day encrypted backup. Purged after 30 days."
                  reason="Disaster recovery only."
                />
                <Row
                  type="Server access logs (IP + user-agent)"
                  duration="14 days."
                  reason="Security investigations only."
                />
                <Row
                  type="Anonymized usage metrics"
                  duration="Indefinitely, aggregated only (no individual can be re-identified)."
                  reason="Product analytics."
                />
              </tbody>
            </table>
          </div>

          <H2>Deleting your account</H2>
          <p>
            You can delete your account and all associated content at any time.
            <strong> Active-account data is purged from our primary database promptly</strong> — usually within seconds of tapping Delete. <strong>Encrypted rolling backups complete rotation within 30 days</strong>, at which point the deletion is total.
          </p>
          <div className="rounded-2xl border border-[#E5E0EE] bg-white p-4 not-prose flex gap-3 items-start my-4">
            <Trash2 size={18} className="text-[#3D1A78] mt-0.5 shrink-0" />
            <div className="text-sm text-[#4B4567] leading-relaxed">
              <div className="font-semibold text-[#1A1330] mb-1">Two ways to delete:</div>
              <ul className="list-disc pl-5 space-y-1">
                <li>Fill out the form at{" "}
                  <Link to="/delete-account" className="text-[#2A0F5F] underline">/delete-account</Link>.
                </li>
                <li>Email{" "}
                  <a href="mailto:mattsossi@bsossi.com" className="text-[#2A0F5F] underline">mattsossi@bsossi.com</a>{" "}
                  from the address on your account. We reply within 2 business days.
                </li>
              </ul>
            </div>
          </div>

          <H2>Exporting your data</H2>
          <p>
            Every generated report is already downloadable as PDF. If you'd
            like a machine-readable JSON export of your prep answers, journal
            entries, and assessment scores, email us and we'll deliver it
            within 7 business days.
          </p>
          <div className="rounded-2xl border border-[#E5E0EE] bg-white p-4 not-prose flex gap-3 items-start my-4">
            <Download size={18} className="text-[#3D1A78] mt-0.5 shrink-0" />
            <div className="text-sm text-[#4B4567] leading-relaxed">
              Portable formats we support: <strong>PDF</strong> (reports),{" "}
              <strong>JSON</strong> (raw data on request), <strong>HTML share links</strong> (reports).
            </div>
          </div>

          <H2>Your rights</H2>
          <p>
            Whether you fall under GDPR (EU), CCPA/CPRA (California), POPIA
            (South Africa), or another regime, you have the right to:
          </p>
          <ul>
            <li><strong>Access</strong> — request a copy of the data we hold about you.</li>
            <li><strong>Rectify</strong> — ask us to correct inaccurate data.</li>
            <li><strong>Delete</strong> — request full erasure (as described above).</li>
            <li><strong>Object</strong> — opt out of anonymized analytics processing.</li>
            <li><strong>Port</strong> — receive your data in a machine-readable format.</li>
          </ul>
          <p>
            To exercise any of these rights, contact us at the email below.
            We do not charge a fee for reasonable requests and respond within
            30 days.
          </p>

          <H2>Third-party processors</H2>
          <ul>
            <li><strong>Emergent Labs</strong> — application hosting <em>and</em> LLM proxy that fronts Anthropic Claude for report generation. The chain is <code>app → Emergent proxy → Anthropic</code>. Emergent's payload retention is not publicly stated; see <a href="https://app.emergent.sh/privacy-policy" target="_blank" rel="noopener noreferrer" className="text-[#2A0F5F] underline">Emergent's Privacy Policy</a>.</li>
            <li><strong>Anthropic (Claude Sonnet 4.5)</strong> — generates your report content. Anthropic's published commercial API policy is deletion of inputs and outputs within 30 days, subject to exceptions (legal holds, safety/Usage-Policy investigations, feature-specific retention). Anthropic states commercial API traffic is not used to train models unless the customer expressly permits it — we do not permit it.</li>
            <li><strong>MongoDB Atlas</strong> — primary database, US-East region, encryption at rest.</li>
            <li><strong>Resend</strong> — transactional email delivery (sign-in links and codes, and notices that a document is waiting). Emails never contain reports, health details or attachments; recipients open documents in SA CoParents with a one-time code.</li>
            <li><strong>Virtru Hosted Gateway</strong> — HIPAA-scoped joint report + agreement emails, enabled once our BAA and tenant provisioning complete. Currently OFF; standard emails route through Resend in the meantime.</li>
            <li><strong>Google (optional)</strong> — only if you sign in with Google. We receive your name + email, nothing more.</li>
          </ul>
          <p className="text-sm text-[#6E6787] italic">
            We have not represented Emergent's proxy as covered by a HIPAA Business Associate Agreement, because that chain is not yet contractually confirmed. Please avoid pasting raw clinical records into free-text fields until we publish BAA confirmation.
          </p>

          <H2>Contact</H2>
          <p>
            Email <a href="mailto:mattsossi@bsossi.com" className="text-[#2A0F5F] underline">mattsossi@bsossi.com</a>
            {" "}or call <a href="tel:2102241667" className="text-[#2A0F5F] underline">210-224-1667</a>.
          </p>
          <p className="text-xs text-[#6E6787] italic mt-8">
            SA CoParents · 16607 Blanco #703, San Antonio, Texas 78232
          </p>
        </Prose>
      </div>
    </div>
  );
}

function H2({ children }) {
  return <h2 className="font-serif text-2xl text-[#1A1330] mt-10 mb-3">{children}</h2>;
}

function Prose({ children }) {
  return (
    <div className="prose-soft space-y-3 text-[#1A1330] leading-relaxed [&_p]:text-[#4B4567] [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:space-y-1.5 [&_li]:text-[#4B4567] [&_strong]:text-[#1A1330] text-[15px]">
      {children}
    </div>
  );
}

function StatCard({ icon, label, value }) {
  return (
    <div className="rounded-2xl border border-[#E5E0EE] bg-white p-4">
      <div className="flex items-center gap-2 text-[#3D1A78]">
        {icon}
        <div className="text-[0.6875rem] uppercase tracking-[0.12em] text-[#6E6787]">{label}</div>
      </div>
      <div className="text-lg font-serif text-[#1A1330] mt-2">{value}</div>
    </div>
  );
}

function Th({ children }) {
  return (
    <th className="pb-2 px-3 border-b border-[#E5E0EE] font-semibold whitespace-nowrap">
      {children}
    </th>
  );
}

function Row({ type, duration, reason }) {
  return (
    <tr className="border-b border-[#F1EDF6]">
      <td className="py-3 px-3 align-top font-semibold text-[#1A1330]">{type}</td>
      <td className="py-3 px-3 align-top">{duration}</td>
      <td className="py-3 px-3 align-top text-[#6E6787]">{reason}</td>
    </tr>
  );
}
