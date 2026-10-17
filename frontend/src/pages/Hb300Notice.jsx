/**
 * Texas HB 300 Notice — Medical Records Privacy Act addendum.
 *
 * HB 300 (Tex. Health & Safety Code Ch. 181) extends HIPAA for Texas
 * residents. SA CoParents adopts HB 300 standards voluntarily because
 * (a) our users are predominantly Texas parents, and (b) the safety-
 * lens and co-parenting data we hold would be "Protected Health
 * Information" in a clinical setting. This page is written for
 * parents first, attorneys second, and matches the voice of the
 * existing HIPAA Notice and Privacy Practices.
 */
import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

const EFFECTIVE_DATE = "February 21, 2026";

export default function Hb300Notice() {
  return (
    <div className="min-h-screen gentle-bg" data-testid="hb300-notice-page">
      <div className="max-w-3xl mx-auto px-5 sm:px-6 py-10 sm:py-14">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-sm text-[#2A0F5F] hover:text-[#3D1A78] mb-6"
          data-testid="hb300-back-link"
        >
          <ArrowLeft size={14} /> Back to SA CoParents
        </Link>

        <div className="eyebrow mb-3">Texas HB 300 Notice</div>
        <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] mb-2 leading-tight">
          The Texas standard, applied to every parent's data.
        </h1>
        <p className="text-sm text-[#6E6787] mb-8">Effective: {EFFECTIVE_DATE}</p>

        <Prose>
          <p>
            Texas House Bill 300 — codified as the Texas Medical
            Records Privacy Act at{" "}
            <em>Tex. Health &amp; Safety Code Ch. 181</em> — extends
            HIPAA for anyone who assembles, collects, analyses, uses,
            evaluates, stores, or transmits Protected Health
            Information ("PHI") on a Texas resident. Its definition
            of "covered entity" is much broader than HIPAA's.
          </p>
          <p>
            SA CoParents operates from San Antonio, Texas, and stores
            safety, trauma, and co-parenting data that would be PHI in
            a clinical setting. We therefore treat ourselves as a
            Texas covered entity and adopt HB 300 in full, even where
            HIPAA alone would not require it.
          </p>

          <H2>1. Notice of Electronic Disclosure</H2>
          <p>
            HB 300 §181.154 requires clear notice before your PHI is
            electronically disclosed to a third party — unless the
            disclosure is one HIPAA already permits (treatment,
            payment, healthcare operations, court order, etc.).
          </p>
          <p>Inside SA CoParents, an electronic disclosure only happens when:</p>
          <ul>
            <li>You accept a <strong>Compare share</strong> with your co-parent — and even then, only the fields the artefact requires are shared. Findings 1 and 2 of the Safety Lens are never disclosed.</li>
            <li>You explicitly <strong>email a Joint Report, Joint Agreement, or Professional Introduction</strong> to a mediator, attorney, therapist, or court from within the app.</li>
            <li>You use the <strong>Co-Sign Portal</strong> to route a report to a reviewing professional.</li>
          </ul>
          <p>
            Each of those actions requires an on-screen consent step
            that names the recipient. No electronic disclosure happens
            in the background.
          </p>

          <H2>2. Sale of PHI — prohibited</H2>
          <p>
            HB 300 §181.153 bans the sale of PHI without written
            authorisation. SA CoParents does not sell, rent, or barter
            PHI under any circumstance. We do not accept marketing
            money in exchange for access to your data, and we will
            never do so.
          </p>

          <H2>3. Marketing communications — opt-in only</H2>
          <p>
            HB 300 requires affirmative opt-in for marketing
            communications that use PHI. Every account starts with
            marketing communications turned <strong>off</strong>. You
            can turn them on (and off again) from your account
            settings, and we will never send you marketing based on
            the content of your safety, trauma, or agreement data.
          </p>

          <H2>4. Right of access — 15 business days</H2>
          <p>
            HB 300 §181.102 shortens HIPAA's 30-day access window to{" "}
            <strong>15 business days</strong> for electronic health
            records. Your data is available instantly via the{" "}
            <Link to="/data-retention" className="text-[#2A0F5F] underline">
              Data & Retention
            </Link>{" "}
            page (right-of-export button). If you ever prefer a
            formal written request, we honour it inside 15 business
            days.
          </p>

          <H2>5. Breach notification</H2>
          <ul>
            <li><strong>You</strong>: notified within 60 days of discovery of any breach involving your PHI.</li>
            <li><strong>Texas Attorney General</strong>: notified without unreasonable delay, and no later than 60 days after discovery, for any breach affecting 250 or more Texas residents (per Tex. Bus. &amp; Com. Code §521.053, as amended).</li>
            <li><strong>US Department of Health &amp; Human Services (OCR)</strong>: notified for HIPAA-scoped breaches per §164.408.</li>
          </ul>
          <p>
            Our internal breach runbook (60-day clock, AG notice,
            OCR notice, user notice, credit-monitoring evaluation) is
            reviewed annually.
          </p>

          <H2>6. Workforce training</H2>
          <p>
            HB 300 §181.101 requires every workforce member to receive
            training on state and federal PHI laws within 90 days of
            joining, and again whenever their duties materially
            change. Attestations are retained for six years. Because
            SA CoParents is currently operated by a single owner, the
            attestation on file covers the owner and any future
            employees, contractors, or interns.
          </p>

          <H2>7. Reasonable safeguards</H2>
          <ul>
            <li>TLS on every request in transit; strict CORS allow-list on every API.</li>
            <li>Bcrypt password hashing; short-lived reset tokens that are never written to application logs.</li>
            <li>PHI-access audit log retained for six years — you can pull your own log from your account.</li>
            <li>Consent-gated Compare share; automated neutral-language guardrails on every artefact.</li>
            <li>Business Associate Agreements with vendors that touch health-adjacent data.</li>
          </ul>

          <H2>8. Your Texas-specific rights</H2>
          <ul>
            <li><strong>Access</strong>: an electronic copy of your data within 15 business days.</li>
            <li><strong>Correction</strong>: request amendment of anything inaccurate.</li>
            <li><strong>Restriction</strong>: ask us to restrict certain uses or disclosures.</li>
            <li><strong>Accounting of disclosures</strong>: your PHI-access log covers this — self-serve.</li>
            <li><strong>Deletion</strong>: full account deletion at any time, subject only to the de-identified audit log we must retain by law.</li>
            <li><strong>Complaint without retaliation</strong>: to us, to the US Department of Health &amp; Human Services (OCR), or to the Texas Attorney General's Consumer Protection Division.</li>
          </ul>

          <H2>9. Complaints and contact</H2>
          <p>
            <strong>Privacy Officer, SA CoParents</strong><br />
            16607 Blanco #703, San Antonio, Texas 78232<br />
            Email <a href="mailto:mattsossi@bsossi.com" className="text-[#2A0F5F] underline">mattsossi@bsossi.com</a>
            {" "}· Phone <a href="tel:2102241667" className="text-[#2A0F5F] underline">210-224-1667</a>
          </p>
          <p>
            You may also file a complaint with the{" "}
            <a
              href="https://www.texasattorneygeneral.gov/consumer-protection"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[#2A0F5F] underline"
            >
              Texas Attorney General's Consumer Protection Division
            </a>{" "}
            or the{" "}
            <a
              href="https://www.hhs.gov/ocr/filing-with-ocr/index.html"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[#2A0F5F] underline"
            >
              US Department of Health &amp; Human Services (OCR)
            </a>.
          </p>

          <H2>Acknowledgement</H2>
          <p>
            By creating an account, you acknowledge that you have
            received this HB 300 Notice alongside our Notice of
            Privacy Practices. A time-stamped record of your
            acknowledgement is stored in your account audit log.
          </p>

          <H2>See also</H2>
          <ul>
            <li><Link to="/legal/hipaa" className="text-[#2A0F5F] underline">HIPAA Notice</Link> — plain-English summary.</li>
            <li><Link to="/legal/privacy-practices" className="text-[#2A0F5F] underline">Notice of Privacy Practices</Link>.</li>
            <li><Link to="/privacy" className="text-[#2A0F5F] underline">Privacy Policy</Link>.</li>
            <li><Link to="/data-retention" className="text-[#2A0F5F] underline">Data retention policy</Link>.</li>
          </ul>
          <p className="text-xs text-[#6E6787] italic mt-8">
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
