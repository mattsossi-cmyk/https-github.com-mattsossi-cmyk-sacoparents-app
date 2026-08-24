import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

const LAST_UPDATED = "February 21, 2026";

export default function Privacy() {
  return (
    <div className="min-h-screen gentle-bg">
      <div className="max-w-3xl mx-auto px-5 sm:px-6 py-10 sm:py-14">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-sm text-[#2A0F5F] hover:text-[#3D1A78] mb-6"
          data-testid="privacy-back-link"
        >
          <ArrowLeft size={14} /> Back to SA CoParents
        </Link>

        <div className="eyebrow mb-3">Privacy Policy</div>
        <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] mb-2 leading-tight">
          Your prep is private. Always.
        </h1>
        <p className="text-sm text-[#857E9C] mb-8">Last updated: {LAST_UPDATED}</p>

        <Prose>
          <p>
            <strong>SA CoParents</strong> (the "app", "we", "us") is operated by
            Matt Sossi at 16607 Blanco #703, San Antonio, Texas 78232.
            This policy explains what we collect, why, and how we protect it.
            Plain English first. Lawyerly precision second.
          </p>

          <H2>The short version</H2>
          <ul>
            <li>We collect <strong>only what's needed</strong> for you to use the app: your account info and the prep answers you type.</li>
            <li>We <strong>never</strong> sell your data. We never share it with advertisers. Period.</li>
            <li>Your prep content is sent through Emergent Labs' LLM proxy to Anthropic's Claude API to generate your summaries, drafts, and growth plans. <strong>Anthropic does not train on API traffic.</strong> Retention along that chain is described in "How AI fits in" below.</li>
            <li>You can delete your account and all your active-account data at any time — instantly from inside the app. Encrypted rolling backups complete rotation within 30 days.</li>
            <li>If you're a domestic violence survivor, the app has a Quick Exit button and links to confidential national hotlines. Use them whenever you need.</li>
          </ul>

          <H2>What we collect</H2>
          <p><strong>Account information</strong> — Your name and email when you sign up. If you sign in with Google, we receive your name and email from Google (nothing more).</p>
          <p><strong>Your preparation content</strong> — Everything you enter in the wizard: child-focused goals, issues and concerns, priority topics, communication self-assessment, readiness ratings, and any free-text notes. This is the heart of the product.</p>
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
            When you tap "Generate", your prep content is transmitted from our backend to <strong>Emergent Labs' LLM proxy</strong> using our Universal LLM Key, and Emergent routes the request to <strong>Anthropic's Claude API</strong> for processing. Emergent and Anthropic may process associated technical, security, billing, and abuse-prevention information.
          </p>
          <p>
            <strong>Retention</strong> — Anthropic's published commercial API policy states that inputs and outputs are deleted from Anthropic's backend within 30 days, subject to exceptions including legal holds and safety/Usage-Policy investigations. Anthropic states that commercial API inputs and outputs are <strong>not used to train generative models</strong> unless the customer expressly permits it (we do not permit it). Emergent's proxy payload retention is not publicly stated — see{" "}
            <a href="https://app.emergent.sh/privacy-policy" target="_blank" rel="noopener noreferrer" className="text-[#2A0F5F] underline">Emergent's Privacy Policy</a>{" "}
            for their commitments.
          </p>
          <p className="text-sm text-[#857E9C] italic">
            We have not represented Emergent's proxy as zero-retention or as covered by a HIPAA Business Associate Agreement, because that chain is not yet contractually confirmed. See the <strong>AI + sensitive information</strong> notice below before pasting clinical records into free-text fields.
          </p>

          <H2>AI + sensitive information — what to avoid</H2>
          <p>
            Because the Emergent → Anthropic BAA chain is <strong>not yet confirmed</strong> for SA CoParents, do <strong>not</strong> paste the following into free-text fields that feed the AI coach until we publish BAA confirmation on this page:
          </p>
          <ul>
            <li>Raw medical records, lab results, or full clinical notes.</li>
            <li>Explicit diagnostic codes or medication dosages tied to identifiers.</li>
            <li>Court exhibits containing verbatim safety/violence allegations.</li>
          </ul>
          <p>
            The structured fields in the Special Needs and Safety-Lens assessments are designed to minimise this exposure — they collect the categories and scores we need, not verbatim clinical detail. Keep free-text notes at that same level.
          </p>

          <H2>Information about children</H2>
          <p>
            SA CoParents is designed for parents. We do not knowingly collect information directly from anyone under 13. But parents <strong>do</strong> enter information <em>about</em> their children — that's the point of a co-parenting prep tool — and we treat that information with the same standard as any other sensitive personal information.
          </p>
          <p><strong>Categories a parent may enter about a child</strong>:</p>
          <ul>
            <li>First name, age, and education setting (school, grade).</li>
            <li>Special-needs categories: neurodevelopmental (ADHD, autism spectrum), medical (chronic conditions, allergies), psychological (anxiety, depression), sensory, communication, and learning differences — plus severity ratings and any therapies/medications the parent wants included in the co-parenting plan.</li>
            <li>Safety and family-violence observations relevant to the parenting arrangement — captured through the Safety-Lens instrument, never as free-text court exhibits.</li>
            <li>Free-text notes the parent chooses to include in a Journal entry or an agreement clause.</li>
          </ul>
          <p>
            <strong>Please only enter what's reasonably necessary</strong> for the assessment or agreement you're preparing. Skip fields you don't need.
          </p>
          <p><strong>Our commitments regarding children's information</strong>:</p>
          <ul>
            <li>Never sold, licensed, or shared with advertisers.</li>
            <li>Never used to train AI models (Anthropic API traffic is contractually excluded from training).</li>
            <li>Only ever shared with your co-parent through an explicit, revocable Compare consent — and even then only the fields the artefact requires.</li>
            <li>Deletion of the child's data follows the account-deletion path — instantly on the primary database, backups rotate out within 30 days. You may also email us to remove a specific child's record without deleting the whole account; we honour that request within 15 business days per Texas HB 300.</li>
          </ul>

          <H2>Sensitive information — enhanced protection</H2>
          <p>
            Some of what parents enter is <strong>more sensitive</strong> than the rest. We apply extra safeguards to this category. It includes:
          </p>
          <ul>
            <li>Family-violence and coercive-control observations captured through the Safety-Lens instrument.</li>
            <li>Children's medical, psychological, and neurodevelopmental information.</li>
            <li>Allegations involving either parent.</li>
            <li>Journal entries.</li>
            <li>Safety assessments and their findings.</li>
            <li>Free-text narratives you type anywhere in the app.</li>
          </ul>
          <p><strong>The extra safeguards</strong>:</p>
          <ul>
            <li><strong>Consent-gated Compare share</strong> — the co-parent never sees any of this without your explicit acceptance of a Compare share, and only the fields the shared artefact requires.</li>
            <li><strong>Finding-3-only guardrail</strong> — Findings 1 (family-violence pattern) and 2 (trauma impact) of the Safety Lens are <strong>never</strong> included in any joint artefact under any circumstance. Only Finding 3 (parenting-plan implications) is shareable.</li>
            <li><strong>PHI access audit log</strong> — every read of a Safety-Lens finding, Special Needs assessment, or joint report is timestamped and retained for six years. You can pull your own copy from your account.</li>
            <li><strong>Neutral-language guardrails</strong> — every joint artefact leaving the platform passes automated tests that block "correct/at-fault/should have custody" language.</li>
            <li><strong>Encryption at rest and in transit</strong> — TLS on every request; MongoDB Atlas encryption at rest.</li>
          </ul>
          <p>
            <strong>An important limit on sharing that you should understand:</strong> revoking a share link prevents future access <em>through that link</em>, but it cannot retrieve a PDF that another person has already downloaded, printed, forwarded, or saved. Once you tap "Send", assume that copy exists outside our systems.
          </p>

          <H2>How we store your data</H2>
          <p>
            Your data is stored in MongoDB Atlas, encrypted at rest and in transit (TLS 1.2+). Passwords are hashed with bcrypt — even we can't read them. Sessions use httpOnly cookies, not browser localStorage, to reduce exposure to client-side attacks.
          </p>

          <H2>Who we share with</H2>
          <ul>
            <li><strong>Service providers</strong> we contract with to run the app (currently: Emergent Labs for hosting <em>and</em> for the LLM proxy that fronts Anthropic Claude, MongoDB Atlas for the database, Google for optional sign-in, <strong>Resend</strong> for standard transactional email, and <strong>Virtru Hosted Gateway</strong> which will be enabled for HIPAA-scoped emails once our BAA and tenant provisioning complete). Each is bound by their own privacy commitments.</li>
            <li><strong>Your mediator, attorney, therapist, or court</strong> — but only when you explicitly initiate the send from inside the app and confirm the recipient email. We do not share with professionals automatically.</li>
            <li><strong>People you choose</strong> — when you tap "Share via link", we generate a signed download link. The default lifetime is <strong>7 days</strong>; you can choose 1, 7, or 30 days at share time, or "no expiry" for links you'll revoke manually. Every link is revocable from your dashboard at any moment.</li>
            <li><strong>Legal compliance</strong> — if compelled by a valid legal process. We will notify you unless legally prohibited.</li>
          </ul>
          <p>We do not sell your data to anyone, ever.</p>

          <H2>Your rights</H2>
          <ul>
            <li><strong>Access</strong> — email us and we'll send you a copy of everything we have about you.</li>
            <li><strong>Correction</strong> — most fields are editable directly in the app. For others, email us.</li>
            <li><strong>Deletion</strong> &mdash; you can <Link to="/delete-account" className="text-[#2A0F5F] underline">delete your account and all associated data</Link> from inside the app or from that public page. <strong>Active-account data is purged from our primary database promptly</strong> — usually within seconds. <strong>Encrypted rolling backups complete rotation within 30 days</strong>, at which point the deletion is total. PDFs already shared via links can no longer be retrieved by us, but a person who downloaded one before revocation may still have their copy.</li>
            <li><strong>Portability</strong> — we can export your prep + generated documents as JSON on request.</li>
          </ul>

          <H2>Children (direct collection)</H2>
          <p>
            SA CoParents is intended for parents and is not directed at children under 13. We do not knowingly collect information <em>directly</em> from anyone under 13. (For information a parent may enter <em>about</em> their children, see the "Information about children" section above.) If you believe we have inadvertently collected information directly from a child, email us and we will delete it.
          </p>

          <H2>Safety note for survivors of domestic violence</H2>
          <p>
            If you're using this app while still in an unsafe situation, please be aware that the app does keep records of what you enter. If your device may be monitored, consider using the <Link to="/safety" className="text-[#2A0F5F] underline">Safety page</Link>'s Quick Exit feature and accessing the app from a private device when possible. The Safety page provides 24/7 hotlines including the National Domestic Violence Hotline (1-800-799-7233) and 988 Suicide & Crisis Lifeline.
          </p>

          <H2>Changes to this policy</H2>
          <p>
            We'll update this date and post the new policy here if we make material changes. If the changes are significant (e.g., new categories of data shared), we'll email you before they take effect.
          </p>

          <H2>Contact</H2>
          <p>Questions? Concerns? Want your data deleted?</p>
          <p>
            Email <a href="mailto:mattsossi@bsossi.com" className="text-[#2A0F5F] underline">mattsossi@bsossi.com</a>
            {" "}or call <a href="tel:2102241667" className="text-[#2A0F5F] underline">210-224-1667</a>.
          </p>

          <H2>See also</H2>
          <ul>
            <li><Link to="/legal/hipaa" className="text-[#2A0F5F] underline">HIPAA Notice</Link> — how we treat health-adjacent data (and why HIPAA does not automatically apply to us).</li>
            <li><Link to="/legal/privacy-practices" className="text-[#2A0F5F] underline">Notice of Privacy Practices</Link> — the formal HIPAA-styled notice.</li>
            <li><Link to="/legal/hb300" className="text-[#2A0F5F] underline">Texas HB 300 Notice</Link> — Texas-specific medical-records privacy addendum.</li>
            <li><Link to="/data-retention" className="text-[#2A0F5F] underline">Data retention policy</Link> — how long we keep each data type, and how to delete or export.</li>
            <li><Link to="/methodology" className="text-[#2A0F5F] underline">Methodology &amp; assessment validation</Link> — how our scoring works and its limits.</li>
            <li><Link to="/accessibility" className="text-[#2A0F5F] underline">Accessibility statement</Link> — WCAG 2.2 AA commitments.</li>
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
