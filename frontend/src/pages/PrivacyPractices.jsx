/**
 * Notice of Privacy Practices — the more formal, HIPAA-styled notice.
 * Sits at /legal/privacy-practices so it's clearly separate from the
 * plain-English Privacy Policy at /privacy. Same voice conventions as
 * the other legal pages.
 */
import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

const EFFECTIVE_DATE = "February 17, 2026";

export default function PrivacyPractices() {
  return (
    <div className="min-h-screen gentle-bg" data-testid="privacy-practices-page">
      <div className="max-w-3xl mx-auto px-5 sm:px-6 py-10 sm:py-14">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-sm text-[#2A0F5F] hover:text-[#3D1A78] mb-6"
          data-testid="privacy-practices-back-link"
        >
          <ArrowLeft size={14} /> Back to SA CoParents
        </Link>

        <div className="eyebrow mb-3">Notice of Privacy Practices</div>
        <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] mb-2 leading-tight">
          How we protect, use, and disclose your information.
        </h1>
        <p className="text-sm text-[#857E9C] mb-8">Effective: {EFFECTIVE_DATE}</p>

        <Prose>
          <p>
            <strong>This Notice describes how information about you and
            your child may be used and disclosed and how you can get
            access to this information. Please review it carefully.</strong>
          </p>
          <p>
            SA CoParents is a preparation platform. We are not a
            HIPAA Covered Entity. We adopt this Notice of Privacy
            Practices voluntarily because much of the information you
            share with the platform would be considered Protected
            Health Information (PHI) in a clinical setting, and we
            want the same standard of care to apply here.
          </p>

          <H2>1. Our commitment</H2>
          <p>
            We are committed to protecting the privacy of the
            information you share with us. We follow the standards set
            by HIPAA's Privacy and Security Rules and Texas HB 300
            where they exceed HIPAA. We are required by law to:
          </p>
          <ul>
            <li>Maintain the privacy of your information.</li>
            <li>Give you this Notice explaining our practices.</li>
            <li>Follow the terms of this Notice as currently in effect.</li>
            <li>Notify you of any breach of unsecured PHI.</li>
          </ul>

          <H2>2. Information we collect</H2>
          <ul>
            <li><strong>Account information</strong>: name, email, hashed password.</li>
            <li><strong>Prep answers</strong>: your responses to the Mediation Prep, Special Needs Co-Parenting Assessment, Safety-Lens screen, and any agreement drafts you generate.</li>
            <li><strong>Comparison consents</strong>: the time-stamped record of any Compare share you accept or revoke.</li>
            <li><strong>Access log</strong>: an audit trail of every read of your health-adjacent data — retained for six years.</li>
          </ul>

          <H2>3. How we use and disclose your information</H2>
          <p>Only for the following purposes:</p>
          <ul>
            <li><strong>To operate the platform</strong>: generate your summaries, drafts, and reports.</li>
            <li><strong>To generate joint artefacts</strong>: only after both parents consent through the Compare flow, and only with the fields the artefact requires. Findings 1 and 2 of the Safety Lens are never disclosed to the co-parent under any circumstance.</li>
            <li><strong>To send information to a professional</strong> (mediator, attorney, therapist, court): only when you initiate that email through the app.</li>
            <li><strong>To comply with law</strong>: for example, in response to a valid subpoena. We will notify you unless legally prohibited.</li>
            <li><strong>To prevent imminent harm</strong>: consistent with the "serious threat" exception standards.</li>
          </ul>
          <p>
            We will never sell your information, share it with
            advertisers, or use it for marketing without your written
            authorisation.
          </p>

          <H2>4. Your rights</H2>
          <ul>
            <li><strong>Right of access</strong>: obtain a copy of your information in electronic form.</li>
            <li><strong>Right to amend</strong>: request correction of anything you believe is inaccurate.</li>
            <li><strong>Right to accounting of disclosures</strong>: request a list of any disclosures we've made to third parties in the past six years.</li>
            <li><strong>Right to restrict</strong>: ask us to restrict certain uses or disclosures.</li>
            <li><strong>Right to confidential communications</strong>: ask us to communicate with you at a specific email or phone.</li>
            <li><strong>Right to a paper copy</strong> of this Notice.</li>
            <li><strong>Right to complain</strong>: without retaliation, to us or to the U.S. Department of Health and Human Services, Office for Civil Rights.</li>
            <li><strong>Right to delete</strong>: request full deletion of your account and data at any time.</li>
          </ul>

          <H2>5. Safeguards</H2>
          <ul>
            <li>TLS on every request in transit.</li>
            <li>Consent-gated sharing on every joint artefact.</li>
            <li>Automated neutral-language guardrails on every artefact leaving the platform.</li>
            <li>PHI-access audit log retained for six years.</li>
            <li>Business Associate Agreements with third parties who handle health-adjacent data on our behalf.</li>
          </ul>

          <H2>6. Business Associate Agreements</H2>
          <p>
            We maintain BAAs with third parties that handle
            health-adjacent data on our behalf, where the vendor
            supports one and where our processing warrants it. If you
            or your attorney require a copy of a specific BAA, email us.
          </p>

          <H2>7. Data retention</H2>
          <p>
            We retain your account data until you delete your account.
            Audit logs of PHI access are retained for six years.
            Backups purge on their normal 30-day cycle.
          </p>

          <H2>8. Changes to this Notice</H2>
          <p>
            We may revise this Notice. Any revision becomes effective
            when posted on this page. If a change is material, we will
            email you before it takes effect.
          </p>

          <H2>9. Complaints and contact</H2>
          <p>
            If you believe your privacy rights have been violated, you
            may file a complaint with us — without fear of retaliation
            — at:
          </p>
          <p>
            <strong>Privacy Officer, SA CoParents</strong><br />
            16607 Blanco #703, San Antonio, Texas 78232<br />
            Email <a href="mailto:mattsossi@bsossi.com" className="text-[#2A0F5F] underline">mattsossi@bsossi.com</a>
            {" "}· Phone <a href="tel:2102241667" className="text-[#2A0F5F] underline">210-224-1667</a>
          </p>
          <p>
            You may also file a complaint with the U.S. Department of
            Health and Human Services, Office for Civil Rights, at{" "}
            <a
              href="https://www.hhs.gov/ocr/filing-with-ocr/index.html"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[#2A0F5F] underline"
            >
              hhs.gov/ocr/filing-with-ocr
            </a>.
          </p>

          <H2>Acknowledgement</H2>
          <p>
            By creating an account, you acknowledge that you have
            received a copy of this Notice of Privacy Practices.
          </p>

          <H2>See also</H2>
          <ul>
            <li><Link to="/legal/hipaa" className="text-[#2A0F5F] underline">HIPAA Notice</Link> — plain-English summary.</li>
            <li><Link to="/privacy" className="text-[#2A0F5F] underline">Privacy Policy</Link>.</li>
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
