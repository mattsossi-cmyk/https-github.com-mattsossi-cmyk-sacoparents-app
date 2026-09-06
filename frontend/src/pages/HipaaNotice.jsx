/**
 * HIPAA Notice — public legal page.
 *
 * SA CoParents is not, on its own, a HIPAA Covered Entity. This page
 * explains what that means for parents, where PHI-like data actually
 * lives, and the safeguards the platform applies regardless. Language
 * is intentionally plain-English-first, lawyerly-second — matching the
 * existing Privacy Policy voice.
 */
import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

const LAST_UPDATED = "February 21, 2026";

export default function HipaaNotice() {
  return (
    <div className="min-h-screen gentle-bg" data-testid="hipaa-notice-page">
      <div className="max-w-3xl mx-auto px-5 sm:px-6 py-10 sm:py-14">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-sm text-[#2A0F5F] hover:text-[#3D1A78] mb-6"
          data-testid="hipaa-back-link"
        >
          <ArrowLeft size={14} /> Back to SA CoParents
        </Link>

        <div className="eyebrow mb-3">HIPAA Notice</div>
        <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] mb-2 leading-tight">
          Health-adjacent data, treated with clinical-grade care.
        </h1>
        <p className="text-sm text-[#857E9C] mb-8">Last updated: {LAST_UPDATED}</p>

        <Prose>
          <p>
            HIPAA (the Health Insurance Portability and Accountability
            Act) binds <em>healthcare providers, health plans, and
            healthcare clearinghouses</em> — collectively "Covered
            Entities" — and their contracted "Business Associates".
          </p>
          <p>
            <strong>SA CoParents is not a healthcare provider, and use of the platform does not, by itself, make information subject to HIPAA.</strong> We do not diagnose, treat, or bill for healthcare. When you fill in the Special Needs Co-Parenting Assessment or the Family Safety and Functioning Reflection, you are self-reporting information about your child to help you prepare for co-parenting conversations. That work is a preparation resource, not clinical care.
          </p>
          <p>
            <strong>We nevertheless treat health-related information as sensitive personal information</strong> and apply the privacy and security protections described in this notice and in our{" "}
            <Link to="/privacy" className="text-[#2A0F5F] underline">Privacy Policy</Link>. Some of what you tell us — your child's diagnoses, medication routines, therapy attendance, family-violence history — would be Protected Health Information (PHI) in a clinical context. The safeguards below apply to it regardless of whether HIPAA legally reaches it.
          </p>

          <H2>Where your health-adjacent data lives</H2>
          <ul>
            <li><strong>Your account</strong>: stored in our database, accessible only to you when signed in.</li>
            <li><strong>Special Needs Assessment answers, Safety-Lens findings, and any drafts</strong>: private to your account. The co-parent never sees them unless you both explicitly consent through the Compare flow.</li>
            <li><strong>Findings 1 (family-violence pattern) and 2 (trauma impact)</strong> of the Safety Lens: private to you even after a Compare consent. Only Finding 3 (parenting-plan implications) is ever included in any joint artefact.</li>
            <li><strong>Emails to professionals</strong> you send from the app: transmitted through Resend. The PDF attachment leaves our servers when you press "Send".</li>
            <li><strong>AI-generated summaries</strong>: your prep content is sent to Anthropic's Claude via the Emergent LLM proxy. Anthropic does not train on API traffic. See our <Link to="/privacy" className="text-[#2A0F5F] underline">Privacy Policy</Link> for the exact processing chain and retention limits, and please avoid pasting raw clinical records into free-text fields until the Emergent → Anthropic BAA chain is confirmed.</li>
          </ul>

          <H2>Safeguards we apply</H2>
          <ul>
            <li><strong>Transport encryption (TLS)</strong> on every request between your browser and our servers.</li>
            <li><strong>Consent-gated sharing</strong>: joint artefacts only exist when both parents have accepted a Compare share. Consent is revocable at any time.</li>
            <li><strong>Neutral-language guardrails</strong>: no artefact leaving the platform labels either parent as "correct", "at fault", or "should have custody". Enforced by automated tests.</li>
            <li><strong>PHI access audit log</strong>: every read of a Safety-Lens finding, Special Needs Assessment, or joint report is time-stamped and stored for six years — the HIPAA record-retention standard we adopt voluntarily.</li>
            <li><strong>Right to export</strong>: request a full copy of your data at any time (see the Data Retention page).</li>
            <li><strong>Right to deletion</strong>: request account and full-data deletion at any time. Backups purge on their normal 30-day cycle.</li>
            <li><strong>Never sold, never advertised against</strong>: we do not sell, license, or share your data with advertisers under any circumstance.</li>
          </ul>

          <H2>Business Associate Agreements (BAAs)</H2>
          <p>
            When required by our vendors and by your state law, we
            maintain BAAs with the third parties that handle
            health-adjacent data on our behalf. If you or your attorney
            need a copy of a specific BAA, email us at the address below
            and we'll respond within ten business days.
          </p>

          <H2>State law matters</H2>
          <p>
            Some states — notably Texas under HB 300 — apply
            HIPAA-style protections more broadly than federal HIPAA
            itself. If you reside in Texas, your data enjoys the more
            protective of the two standards. We do not weaken any
            protection based on where you live. See our full{" "}
            <Link to="/legal/hb300" className="text-[#2A0F5F] underline">
              Texas HB 300 Notice
            </Link>{" "}
            for the 15-business-day access SLA, the no-sale
            attestation, and the breach-notification timers.
          </p>

          <H2>What to do if something feels wrong</H2>
          <p>
            If you believe your data has been mishandled, contact us
            immediately. We will investigate and, where a breach is
            confirmed, notify you within 60 days as HIPAA requires of
            Covered Entities — again, a voluntary standard for us.
          </p>

          <H2>Not a substitute for professional advice</H2>
          <p>
            Nothing in SA CoParents is a clinical diagnosis, forensic
            assessment, custody evaluation, or legal opinion. Every
            artefact carries a universal disclaimer to that effect.
            Always work with your own licensed professionals for
            clinical or legal decisions.
          </p>

          <H2>Contact</H2>
          <p>Questions, complaints, BAA requests, or data-handling concerns:</p>
          <p>
            Email <a href="mailto:mattsossi@bsossi.com" className="text-[#2A0F5F] underline">mattsossi@bsossi.com</a>
            {" "}or call <a href="tel:2102241667" className="text-[#2A0F5F] underline">210-224-1667</a>.
          </p>

          <H2>See also</H2>
          <ul>
            <li><Link to="/legal/privacy-practices" className="text-[#2A0F5F] underline">Notice of Privacy Practices</Link> — the formal, HIPAA-styled notice.</li>
            <li><Link to="/legal/hb300" className="text-[#2A0F5F] underline">Texas HB 300 Notice</Link> — the Texas-specific addendum.</li>
            <li><Link to="/privacy" className="text-[#2A0F5F] underline">Privacy Policy</Link> — plain-English cover of everything we collect.</li>
            <li><Link to="/data-retention" className="text-[#2A0F5F] underline">Data retention policy</Link>.</li>
          </ul>
          <p className="text-xs text-[#857E9C] italic mt-8">
            SA CoParents · 16607 Blanco #703, San Antonio, Texas 78232
          </p>
        </Prose>
      </div>
    </div>
  );
}

function H2({ children }) {
  return (
    <h2 className="font-serif text-2xl text-[#1A1330] mt-10 mb-3">{children}</h2>
  );
}

function Prose({ children }) {
  return (
    <div className="prose-soft space-y-3 text-[#1A1330] leading-relaxed [&_p]:text-[#4B4567] [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:space-y-1.5 [&_li]:text-[#4B4567] [&_strong]:text-[#1A1330] text-[15px]">
      {children}
    </div>
  );
}
