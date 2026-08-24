/**
 * Privacy, Confidentiality & Data Protection Policy.
 *
 * This is the canonical, comprehensive 32-section privacy notice. Other
 * pages (HIPAA Notice, HB 300 Notice, Notice of Privacy Practices, Data
 * Retention) are focused excerpts that link back here. The wording was
 * counsel-reviewed on 2026-02-21; keep the section numbering intact so
 * downstream contracts and email templates can reference specific
 * paragraphs by number.
 *
 * Placeholder policy (deliberately no `[Insert …]` strings left in
 * production): every blank in the source draft was filled with the
 * canonical value already used elsewhere in the codebase (address,
 * Privacy Officer, providers, retention schedule at /data-retention).
 */
import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

const EFFECTIVE_DATE = "February 21, 2026";
const LAST_UPDATED = "February 21, 2026";

export default function Privacy() {
  return (
    <div className="min-h-screen gentle-bg" data-testid="privacy-page">
      <div className="max-w-3xl mx-auto px-5 sm:px-6 py-10 sm:py-14">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-sm text-[#2A0F5F] hover:text-[#3D1A78] mb-6"
          data-testid="privacy-back-link"
        >
          <ArrowLeft size={14} /> Back to SA CoParents
        </Link>

        <div className="eyebrow mb-3">Privacy, Confidentiality &amp; Data Protection Policy</div>
        <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] mb-2 leading-tight">
          Private by Default. Shared by Choice.
        </h1>
        <p className="text-sm text-[#857E9C] mb-8">
          Effective: {EFFECTIVE_DATE} · Last updated: {LAST_UPDATED}
        </p>

        <Prose>
          <p>
            SA CoParents is designed to help parents better understand
            their co-parenting relationship, identify the needs of their
            children, prepare for productive conversations, consider
            options and resources, and prepare for mediation or other
            family-law processes.
          </p>
          <p>
            We recognise that parents may provide deeply personal
            information concerning themselves, their children, their
            co-parenting relationship, family conflict, family violence,
            medical needs, educational needs, psychological needs, and
            legal circumstances. Protecting that information is a
            fundamental part of the SA CoParents platform.
          </p>

          <Callout>
            <p className="!m-0">
              <strong>Our guiding privacy principle is:</strong>{" "}
              <em>Private by Default. Shared by Choice.</em>
            </p>
            <p className="!mb-0 mt-2">
              Your information is private by default. SA CoParents does
              not automatically share your individual assessment
              answers, journal entries, Foundation Statements, reports,
              or other private preparation materials with your
              co-parent, attorney, mediator, therapist, court, or other
              professional. You decide when available sharing features
              are used, subject to the limited circumstances described
              in this Policy, including service providers necessary to
              operate the platform and disclosures required by law.
            </p>
          </Callout>

          <H2>1. Scope of this Policy</H2>
          <p>
            This Privacy, Confidentiality &amp; Data Protection Policy
            explains how SA CoParents collects, uses, stores, protects,
            processes, shares, retains, and deletes personal
            information. It applies to information collected through
            the SA CoParents website, application, assessments, reports,
            journals, preparation tools, AI-assisted features, and
            related services. By using SA CoParents, you acknowledge
            the practices described in this Policy.
          </p>

          <H2>2. SA CoParents is a parent preparation and educational platform</H2>
          <p>
            SA CoParents provides parents with educational resources,
            structured assessments, communication tools, preparation
            materials, reports, and other resources intended to
            encourage child-focused decision-making.
          </p>
          <p>
            SA CoParents is not a court, law firm, healthcare provider,
            mental-health provider, custody evaluator, forensic
            evaluator, or governmental agency. SA CoParents does not
            determine which parent is right or wrong, determine
            custody, diagnose a psychological or medical condition,
            determine whether family violence legally occurred, or
            replace advice from an attorney, physician, mental-health
            professional, mediator, or other qualified professional.
          </p>
          <p>
            Assessments and reports generated through SA CoParents are
            intended to help parents identify issues, concerns, goals,
            possible areas of alignment, and topics that may require
            professional assistance.
          </p>

          <H2>3. Information we may collect</H2>
          <p>Depending upon the features you use, SA CoParents may collect information in the following categories.</p>
          <H3>Account information</H3>
          <ul>
            <li>Name;</li>
            <li>Email address;</li>
            <li>Account credentials;</li>
            <li>Authentication information;</li>
            <li>Account preferences; and</li>
            <li>Other information necessary to administer your account.</li>
          </ul>
          <H3>Co-parenting and family information</H3>
          <p>Parents may voluntarily provide information concerning:</p>
          <ul>
            <li>Co-parenting communication;</li>
            <li>Parenting concerns;</li>
            <li>Children&apos;s schedules;</li>
            <li>Parenting goals;</li>
            <li>Areas of agreement or disagreement;</li>
            <li>Decision-making;</li>
            <li>Parenting responsibilities;</li>
            <li>Transitions between households;</li>
            <li>Communication difficulties;</li>
            <li>Conflict;</li>
            <li>Family circumstances; and</li>
            <li>Other information relevant to co-parenting.</li>
          </ul>
          <H3>Information about children</H3>
          <p>Parents may provide information concerning their children, including:</p>
          <ul>
            <li>Age or developmental stage;</li>
            <li>Educational needs;</li>
            <li>School-related concerns;</li>
            <li>Medical needs;</li>
            <li>Psychological or emotional needs;</li>
            <li>Special needs;</li>
            <li>Extracurricular activities;</li>
            <li>Parenting schedules;</li>
            <li>Child-related goals;</li>
            <li>Concerns regarding the child&apos;s well-being; and</li>
            <li>Other information a parent chooses to provide.</li>
          </ul>
          <H3>Sensitive family information</H3>
          <p>Certain SA CoParents tools may allow users to provide particularly sensitive information, including information concerning:</p>
          <ul>
            <li>Family violence;</li>
            <li>Intimate partner violence;</li>
            <li>Coercive or controlling behaviour;</li>
            <li>Threats or intimidation;</li>
            <li>Communication safety;</li>
            <li>Mental or behavioural health;</li>
            <li>Medical conditions;</li>
            <li>Medication;</li>
            <li>Disabilities or special needs;</li>
            <li>Educational services;</li>
            <li>Legal disputes;</li>
            <li>Court proceedings;</li>
            <li>Protective orders;</li>
            <li>Substance-use concerns; and</li>
            <li>Other sensitive family circumstances.</li>
          </ul>
          <p>We encourage users to provide only information reasonably necessary to use the applicable SA CoParents feature.</p>
          <H3>User-generated content</H3>
          <p>Depending upon the features available, this may include:</p>
          <ul>
            <li>Assessment responses;</li>
            <li>Foundation Statements;</li>
            <li>Child Needs Statements;</li>
            <li>Mediation preparation;</li>
            <li>Journal entries;</li>
            <li>Notes;</li>
            <li>Goals;</li>
            <li>Concerns;</li>
            <li>Proposed solutions;</li>
            <li>Reports; and</li>
            <li>Other information voluntarily entered into the platform.</li>
          </ul>
          <H3>Technical information</H3>
          <p>We may automatically collect limited technical information necessary to operate and secure the service, such as:</p>
          <ul>
            <li>IP address;</li>
            <li>Browser type;</li>
            <li>Device information;</li>
            <li>Login information;</li>
            <li>Session information;</li>
            <li>Security logs;</li>
            <li>Error information; and</li>
            <li>Basic usage information.</li>
          </ul>
          <p>We do not use this information to create advertising profiles of parents or children.</p>

          <H2>4. Information about children</H2>
          <p>
            SA CoParents is intended for use by adults, parents,
            guardians, and professionals and is not intended to be used
            directly by children under 13. Parents may nevertheless
            provide information about their children when using
            co-parenting assessments and preparation tools. Information
            about children is treated as sensitive information.
          </p>
          <p>
            SA CoParents does not knowingly solicit personal information
            directly from children under 13 through parent-facing
            services. If we learn that personal information has been
            collected directly from a child in circumstances requiring
            parental authorisation that was not obtained, we will take
            appropriate steps to address and, when required, delete
            that information.
          </p>
          <p>
            Parents should not give children access to their SA
            CoParents account or ask children to complete adult
            assessments unless a particular feature expressly provides
            otherwise. We encourage parents to provide only the child
            information reasonably necessary for the purpose of the
            assessment or resource being used.
          </p>

          <H2>5. Sensitive family information</H2>
          <p>Because SA CoParents operates in the co-parenting and family-law environment, we recognise that some information deserves heightened protection. We consider information concerning the following matters particularly sensitive:</p>
          <H3>Family violence and safety</H3>
          <p>Information concerning alleged abuse, family violence, coercive control, stalking, intimidation, threats, safety concerns, protective orders, or fear.</p>
          <H3>Medical information</H3>
          <p>Information concerning a child&apos;s or parent&apos;s medical needs, health conditions, treatment, medication, or healthcare professionals.</p>
          <H3>Psychological information</H3>
          <p>Information concerning mental health, behavioural health, therapy, psychological concerns, diagnoses reported by a parent, or emotional well-being.</p>
          <H3>Educational and special-needs information</H3>
          <p>Information concerning disabilities, special education, IEPs, accommodations, developmental needs, educational assessments, or other special-needs services.</p>
          <H3>Family-law information</H3>
          <p>Information concerning custody, possession, access, parenting plans, mediation, litigation, court orders, allegations, or other family-law matters.</p>
          <p>
            SA CoParents uses this information only for legitimate
            purposes associated with providing, securing, maintaining,
            and improving the services requested by the user, as
            otherwise described in this Policy, or as required by law.
          </p>

          <H2>6. How we use information</H2>
          <p>We may use personal information to:</p>
          <ul>
            <li>Provide SA CoParents assessments and resources;</li>
            <li>Generate individualised reports;</li>
            <li>Help parents identify needs, concerns, and goals;</li>
            <li>Generate Foundation Statements;</li>
            <li>Support mediation preparation;</li>
            <li>Generate child-focused educational information;</li>
            <li>Compare information when parents intentionally participate in a shared or joint process;</li>
            <li>Provide communication and problem-solving resources;</li>
            <li>Operate user accounts;</li>
            <li>Authenticate users;</li>
            <li>Protect platform security;</li>
            <li>Prevent fraud or misuse;</li>
            <li>Provide customer support;</li>
            <li>Maintain and improve platform functionality;</li>
            <li>Comply with applicable law; and</li>
            <li>Carry out other purposes disclosed to you when information is collected.</li>
          </ul>
          <p>We do not use sensitive family information to determine which parent should receive custody or possession of a child.</p>

          <H2>7. Your individual assessment answers are private by default</H2>
          <Callout>
            <p className="!m-0">
              <strong>Your information is private by default.</strong>{" "}
              SA CoParents does not share your assessment or reports with your co-parent or a professional unless you choose to share them, except where disclosure is required by law.
            </p>
          </Callout>
          <p>Completing an SA CoParents assessment does not automatically provide your answers to your co-parent. Unless a particular feature clearly tells you otherwise before you submit information:</p>
          <ul>
            <li>Your individual responses remain associated with your account and are not automatically disclosed to the other parent.</li>
            <li>When SA CoParents generates a report, Foundation Statement, Mediation Statement, or similar output, the resulting document may contain selected information derived from your responses.</li>
            <li>You should review any report before sharing it.</li>
          </ul>

          <H2>8. Sharing is controlled by the user</H2>
          <p>SA CoParents may provide tools allowing users to intentionally share selected reports or information with:</p>
          <ul>
            <li>A co-parent;</li>
            <li>Attorney;</li>
            <li>Mediator;</li>
            <li>Therapist;</li>
            <li>Parenting professional;</li>
            <li>Collaborative-law professional;</li>
            <li>Parenting coordinator or facilitator;</li>
            <li>Other professional; or</li>
            <li>Another person selected by the user.</li>
          </ul>
          <p>Sharing one report does not, by itself, authorise access to your entire SA CoParents account. Sharing a report does not automatically provide access to unrelated assessments, journal entries, private notes, raw responses, or other reports unless the sharing feature specifically states otherwise. Before sharing information, users should carefully review what the recipient will receive.</p>

          <H2>9. Important limitation on shared information</H2>
          <p>Once information leaves your private SA CoParents account, SA CoParents cannot completely control what happens to it. A recipient may potentially:</p>
          <ul>
            <li>Download a report;</li>
            <li>Save it;</li>
            <li>Print it;</li>
            <li>Forward it;</li>
            <li>Screenshot it;</li>
            <li>Provide it to an attorney or professional; or</li>
            <li>Use it in a legal proceeding.</li>
          </ul>
          <p>Revoking an SA CoParents sharing link may prevent future access through that link, but cannot retrieve or delete copies that a recipient previously downloaded, printed, photographed, forwarded, or otherwise retained. Parents should therefore carefully consider what information they choose to share.</p>

          <H2>10. Privacy does not automatically mean legal confidentiality or privilege</H2>
          <Callout>
            <p className="!m-0">
              <strong>Use of SA CoParents does not by itself create an attorney-client, therapist-patient, mediator-client, or other privileged relationship.</strong>
            </p>
          </Callout>
          <p>This distinction is particularly important in family-law matters. SA CoParents works to keep information private as described in this Policy. However, use of SA CoParents does not itself create a legally privileged relationship. Using SA CoParents does not automatically create:</p>
          <ul>
            <li>Attorney-client privilege;</li>
            <li>Attorney work-product protection;</li>
            <li>Therapist-patient privilege;</li>
            <li>Physician-patient privilege;</li>
            <li>Mediation confidentiality;</li>
            <li>Mental-health professional privilege; or</li>
            <li>Any other evidentiary or legal privilege.</li>
          </ul>
          <p>Whether particular information is privileged, confidential, discoverable, admissible, or protected from disclosure depends upon applicable law and the circumstances in which the information was created or shared. If you are involved in litigation or anticipate litigation, you should consult your attorney before entering or sharing information when you are concerned about discovery, subpoenas, admissibility, privilege, confidentiality, or preservation obligations.</p>

          <H2>11. Mediation and professional use</H2>
          <p>SA CoParents may be used to help parents prepare for mediation or work with attorneys, therapists, mediators, parenting professionals, or other professionals. Using SA CoParents before or during mediation does not automatically make everything entered into the platform confidential under mediation law. Similarly, sharing information with an attorney, therapist, mediator, or other professional does not guarantee that the information will be privileged. The legal status of the information depends upon applicable law and the relationship between the user and the recipient.</p>

          <H2>12. Court orders, subpoenas, and legal process</H2>
          <p>SA CoParents does not voluntarily provide private user information to a court, opposing party, attorney, governmental agency, or law-enforcement agency merely because it is requested informally. We may disclose information when we reasonably believe disclosure is required by applicable law, valid legal process, court order, subpoena, warrant, or other legally enforceable requirement.</p>
          <p>Where legally permitted and appropriate, SA CoParents may seek to notify the affected user before producing information so that the user may have an opportunity to seek legal advice or appropriate protection. Nothing in this Policy prevents SA CoParents from preserving or disclosing information when reasonably necessary to comply with law or respond to a valid emergency involving an imminent threat to safety.</p>

          <H2>13. Family violence and communication safety</H2>
          <p>SA CoParents recognises that information concerning family violence, intimate partner violence, coercive control, threats, stalking, intimidation, and communication safety may create unique risks.</p>
          <p>Family Violence or Communication Safety assessments are educational and preparation tools. They are not professional risk assessments, forensic evaluations, diagnoses, or legal determinations that family violence has or has not occurred.</p>
          <p>When a feature identifies possible safety concerns, the platform may provide information concerning possible safeguards, professional resources, communication structures, or dispute-resolution considerations. SA CoParents should not be used as an emergency service. A user experiencing an immediate emergency should contact appropriate emergency services or a qualified local professional.</p>

          <H2>14. Artificial intelligence</H2>
          <p>Certain SA CoParents features may use artificial intelligence (&quot;AI&quot;) to organise user-provided information, identify themes, generate educational explanations, create summaries, suggest questions or options, and assist in generating reports.</p>
          <p>AI-generated information is intended to support reflection and preparation. AI does not make legal decisions for SA CoParents users. AI output does not constitute:</p>
          <ul>
            <li>Legal advice;</li>
            <li>Medical advice;</li>
            <li>Mental-health advice;</li>
            <li>A custody recommendation;</li>
            <li>A diagnosis;</li>
            <li>A forensic opinion;</li>
            <li>A determination that abuse occurred;</li>
            <li>A professional risk assessment; or</li>
            <li>A court recommendation unless expressly reviewed and adopted by an appropriately qualified professional.</li>
          </ul>
          <p>AI systems may occasionally generate incomplete or inaccurate information. Users should review AI-generated material before relying upon or sharing it.</p>

          <H2>15. AI and your personal information</H2>
          <p>When information must be processed by an AI provider to provide a feature requested by the user, SA CoParents seeks to transmit only information reasonably necessary to perform that function.</p>
          <p>SA CoParents does not authorise AI providers to use parents&apos; assessment responses, children&apos;s information, family-violence information, reports, or other private SA CoParents content to train general-purpose AI models except where clearly disclosed to and authorised by the user.</p>
          <H3>Our current AI processing chain</H3>
          <p>
            When you use a feature that calls the AI coach, summariser,
            or joint-artefact generator, your prep content is
            transmitted from our backend to <strong>Emergent Labs&apos;
            LLM proxy</strong> using our Universal LLM Key, and Emergent
            routes the request to{" "}
            <strong>Anthropic Claude Sonnet 4.5</strong> for processing.
            Emergent and Anthropic may process associated technical,
            security, billing, and abuse-prevention information.
          </p>
          <ul>
            <li><strong>Anthropic retention</strong>: Anthropic&apos;s published commercial API policy states that inputs and outputs are deleted from Anthropic&apos;s backend within 30 days, subject to exceptions including legal holds and safety/Usage-Policy investigations.</li>
            <li><strong>Training</strong>: Anthropic states that commercial API inputs and outputs are not used to train generative models unless the customer expressly permits it. We do not permit it.</li>
            <li><strong>Emergent retention</strong>: Emergent&apos;s proxy payload retention is not publicly stated — see{" "}
              <a href="https://app.emergent.sh/privacy-policy" target="_blank" rel="noopener noreferrer" className="text-[#2A0F5F] underline">
                Emergent&apos;s Privacy Policy
              </a>{" "}
              for their commitments.
            </li>
            <li><strong>HIPAA / BAA chain</strong>: We have not represented Emergent&apos;s proxy as covered by a HIPAA Business Associate Agreement, because that chain is not yet contractually confirmed. Until we publish BAA confirmation on this page, please do not paste raw medical records, diagnostic codes tied to identifiers, or verbatim court exhibits into free-text fields that feed the AI coach.</li>
          </ul>

          <H2>16. We do not sell family information</H2>
          <p>SA CoParents does not sell parents&apos; or children&apos;s personal information. We do not sell:</p>
          <ul>
            <li>Assessment responses;</li>
            <li>Reports;</li>
            <li>Children&apos;s information;</li>
            <li>Family-violence information;</li>
            <li>Medical information;</li>
            <li>Psychological information;</li>
            <li>Educational information;</li>
            <li>Journal entries; or</li>
            <li>Co-parenting information.</li>
          </ul>
          <p>We do not use sensitive family information for third-party targeted advertising.</p>

          <H2>17. Service providers</H2>
          <p>SA CoParents uses carefully selected service providers to operate the platform. Depending upon the services currently used, these providers may assist with:</p>
          <ul>
            <li>Cloud hosting;</li>
            <li>Database storage;</li>
            <li>Authentication;</li>
            <li>Email delivery;</li>
            <li>Security;</li>
            <li>AI processing;</li>
            <li>Error monitoring;</li>
            <li>Payment processing; and</li>
            <li>Technical infrastructure.</li>
          </ul>
          <p>Service providers receive only the information reasonably necessary to perform their services and are expected to handle information consistently with their contractual obligations and applicable law.</p>
          <p>Our current material service providers are:</p>
          <ul>
            <li><strong>Emergent Labs</strong> — application hosting and the LLM proxy that fronts Anthropic Claude for report generation.</li>
            <li><strong>Anthropic (Claude Sonnet 4.5)</strong> — generates AI-assisted report content, called only through the Emergent proxy.</li>
            <li><strong>MongoDB Atlas</strong> — primary database, US-East region, encryption at rest.</li>
            <li><strong>Resend</strong> — transactional email delivery (magic links, standard PDF-to-professional sends).</li>
            <li><strong>Virtru Hosted Gateway</strong> — HIPAA-scoped joint-artefact email, enabled once our BAA and tenant provisioning complete. Currently OFF; standard emails route through Resend in the meantime.</li>
            <li><strong>Google (optional)</strong> — only if you sign in with Google. We receive your name and email, nothing more.</li>
          </ul>
          <p>
            See our{" "}
            <Link to="/data-retention" className="text-[#2A0F5F] underline">
              Data Retention Policy
            </Link>{" "}
            for the canonical processor list and applicable retention periods.
          </p>

          <H2>18. Data security</H2>
          <p>SA CoParents uses reasonable administrative, technical, and organisational safeguards designed to protect personal information from unauthorised access, disclosure, alteration, destruction, or misuse. Depending upon the production environment, these safeguards may include:</p>
          <ul>
            <li>Encryption of information in transit;</li>
            <li>Encryption of stored information;</li>
            <li>Secure password hashing;</li>
            <li>Access controls;</li>
            <li>Authentication controls;</li>
            <li>Secure session management;</li>
            <li>Restricted administrative access;</li>
            <li>Security logging;</li>
            <li>Vendor access controls;</li>
            <li>Backup protections; and</li>
            <li>Security monitoring.</li>
          </ul>
          <p>No website, application, database, or electronic communication system can guarantee absolute security. Users are responsible for protecting their passwords and devices and should not share account credentials with a co-parent or another person.</p>

          <H2>19. Data minimisation</H2>
          <p>SA CoParents seeks to collect and process information reasonably necessary to provide its services. Parents should avoid entering unnecessary information such as:</p>
          <ul>
            <li>Social Security numbers;</li>
            <li>Full financial account numbers;</li>
            <li>Passwords;</li>
            <li>Unnecessary identifying information about third parties; or</li>
            <li>Information unrelated to the purpose of the assessment or tool.</li>
          </ul>
          <p>When discussing children, parents should provide only the information reasonably necessary to address the child&apos;s needs.</p>

          <H2>20. Data retention</H2>
          <p>SA CoParents retains personal information only for as long as reasonably necessary to:</p>
          <ul>
            <li>Provide the service;</li>
            <li>Maintain the user&apos;s account;</li>
            <li>Fulfill the purpose for which information was collected;</li>
            <li>Maintain platform security;</li>
            <li>Meet legitimate operational requirements; and</li>
            <li>Comply with applicable legal obligations.</li>
          </ul>
          <p>
            Users may request deletion of their account and personal
            information subject to applicable legal, security, backup,
            fraud-prevention, and record-retention requirements.
          </p>
          <p>
            The canonical, versioned retention schedule — including
            active-account data, deleted-account data, backups, system
            logs, AI-provider data, email-provider data, and sharing
            links — is published on the{" "}
            <Link to="/data-retention" className="text-[#2A0F5F] underline">
              Data Retention page
            </Link>. That page is the single source of truth; this
            Policy, the Terms of Use, and in-app disclosures all defer
            to it.
          </p>

          <H2>21. Account and data deletion</H2>
          <p>Users may request deletion of their account and associated personal information. Upon a valid deletion request, SA CoParents will delete or de-identify covered personal information from active systems within the period described in our Data Retention Policy, except where retention is reasonably necessary or legally required.</p>
          <p>Information contained in system backups may remain for a limited backup-retention period before being automatically overwritten or deleted. Deleting information from SA CoParents cannot delete copies previously downloaded, printed, saved, or independently retained by another person.</p>

          <H2>22. Your privacy rights</H2>
          <p>Depending upon applicable law, users may have the right to:</p>
          <ul>
            <li>Confirm whether SA CoParents processes their personal information;</li>
            <li>Access personal information;</li>
            <li>Obtain a copy of certain personal information;</li>
            <li>Correct inaccurate information;</li>
            <li>Delete personal information;</li>
            <li>Request information concerning certain disclosures;</li>
            <li>Opt out of certain forms of processing where applicable;</li>
            <li>Appeal certain decisions concerning a privacy request; and</li>
            <li>Exercise privacy rights without unlawful discrimination.</li>
          </ul>
          <p>
            SA CoParents will authenticate privacy requests as
            reasonably necessary to protect users from unauthorised
            access or deletion. To submit a request, use the in-app{" "}
            <Link to="/delete-account" className="text-[#2A0F5F] underline">
              Delete Account
            </Link>{" "}
            page or email{" "}
            <a href="mailto:mattsossi@bsossi.com" className="text-[#2A0F5F] underline">
              mattsossi@bsossi.com
            </a>. If a request is denied, follow the appeal process described in our response.
          </p>

          <H2>23. Texas privacy rights</H2>
          <p>Texas residents may have rights under the Texas Data Privacy and Security Act and other applicable Texas law, including Texas HB 300 (Tex. Health &amp; Safety Code Ch. 181). Where the law applies, SA CoParents will provide eligible Texas consumers with applicable rights regarding access, correction, deletion, portability, and certain processing activities. SA CoParents does not discriminate against users for exercising applicable privacy rights. A user whose privacy request is denied may use the appeal process described in our response to that request. See the{" "}
            <Link to="/legal/hb300" className="text-[#2A0F5F] underline">
              Texas HB 300 Notice
            </Link>{" "}
            for the 15-business-day access SLA, no-sale attestation, and breach-notification timers.
          </p>

          <H2>24. Children&apos;s online privacy</H2>
          <p>SA CoParents is designed for adults and is not directed to children under 13. Children under 13 should not create an SA CoParents account or independently submit personal information through adult-facing SA CoParents features.</p>
          <p>The fact that a parent provides information about a child as part of a parent&apos;s co-parenting preparation is different from SA CoParents intentionally soliciting personal information directly from the child.</p>
          <p>If SA CoParents develops features intended for direct use by children, those features will require separate privacy analysis and appropriate parental-consent procedures before implementation.</p>

          <H2>25. Health information and HIPAA</H2>
          <p>Parents may voluntarily enter information concerning medical, psychological, behavioural, developmental, or other health-related needs. SA CoParents treats such information as sensitive personal information.</p>
          <p><strong>However, providing health-related information to SA CoParents does not, by itself, mean that SA CoParents is a healthcare provider or that all information stored on the platform is Protected Health Information under HIPAA.</strong> HIPAA applies only when the applicable legal requirements are satisfied, including circumstances in which an organisation qualifies as a covered entity or business associate.</p>
          <p>If SA CoParents enters into a relationship in which it acts as a HIPAA business associate, additional contractual and legal requirements may apply to information processed within that relationship. SA CoParents does not provide medical or psychological diagnoses or treatment. See the{" "}
            <Link to="/legal/hipaa" className="text-[#2A0F5F] underline">HIPAA Notice</Link>{" "}
            and{" "}
            <Link to="/legal/privacy-practices" className="text-[#2A0F5F] underline">
              Notice of Privacy Practices
            </Link>{" "}
            for the details.
          </p>

          <H2>26. Cookies and tracking</H2>
          <p>SA CoParents may use cookies or similar technologies necessary to:</p>
          <ul>
            <li>Authenticate users;</li>
            <li>Maintain secure sessions;</li>
            <li>Remember account preferences;</li>
            <li>Prevent fraud;</li>
            <li>Protect security; and</li>
            <li>Maintain essential platform functionality.</li>
          </ul>
          <p>SA CoParents does not use sensitive family information to create advertising profiles. If SA CoParents later introduces analytics, advertising, or other tracking technologies that materially change these practices, this Policy will be updated as required.</p>

          <H2>27. Joint reports and shared assessments</H2>
          <p>When two parents voluntarily participate in a joint or shared process, SA CoParents may generate a report comparing or organising information provided by both parents. The purpose of a Joint Report is not to declare a winner or determine which parent is correct.</p>
          <p>A Joint Report may identify:</p>
          <ul>
            <li>Areas of alignment;</li>
            <li>Areas of disagreement;</li>
            <li>Shared concerns;</li>
            <li>Different perceptions;</li>
            <li>Child-related needs;</li>
            <li>Possible communication issues;</li>
            <li>Safety considerations;</li>
            <li>Topics requiring professional assistance; and</li>
            <li>Options or resources for moving forward.</li>
          </ul>
          <p>Before participating in a joint process, users should be clearly informed about what information will be compared, what information will remain private, and what information may appear in the resulting Joint Report. Raw assessment answers should not automatically be disclosed merely because a Joint Report is generated unless that disclosure is clearly explained and authorised.</p>

          <H2>28. Professional reports</H2>
          <p>SA CoParents may permit a parent to provide a report to an attorney, mediator, therapist, parenting professional, court-appointed professional, or other professional. A professional&apos;s receipt of an SA CoParents report does not make that professional an employee, agent, representative, or endorser of SA CoParents. Professionals remain responsible for exercising their own independent professional judgement.</p>
          <p>SA CoParents reports should be considered alongside other relevant information and should not be treated as professional diagnoses, custody evaluations, forensic assessments, or independent verification of allegations unless an appropriately qualified professional separately conducts and adopts such an evaluation.</p>

          <H2>29. No secret monitoring of the other parent</H2>
          <p>SA CoParents is intended to support constructive, child-focused co-parenting. The platform should not be used to secretly access another parent&apos;s account, impersonate another person, obtain another person&apos;s password, circumvent security controls, or engage in unlawful surveillance. Each parent should maintain an independent account unless a specific shared feature expressly provides otherwise.</p>

          <H2>30. Data breach and security incidents</H2>
          <p>If SA CoParents discovers a security incident involving personal information, we will investigate and respond in accordance with applicable law. Where notification is legally required, affected users and appropriate authorities will be notified as required by applicable law. We may also take protective measures such as resetting credentials, disabling compromised access, revoking sharing links, or temporarily restricting affected functionality. Our internal HB 300 breach response runbook governs the notification timers — see the{" "}
            <Link to="/legal/hb300" className="text-[#2A0F5F] underline">Texas HB 300 Notice</Link> for the applicable deadlines.
          </p>

          <H2>31. Changes to this Policy</H2>
          <p>SA CoParents may update this Policy as the platform, technology, service providers, or applicable laws change. The &quot;Last updated&quot; date at the top of this Policy identifies the most recent revision. If we make a material change affecting how sensitive personal information is collected, used, or shared, we will provide notice as required by applicable law and, where appropriate, request additional consent.</p>

          <H2>32. Contact SA CoParents about privacy</H2>
          <p>Questions, concerns, access requests, correction requests, deletion requests, or other privacy inquiries may be directed to:</p>
          <p>
            <strong>SA CoParents</strong><br />
            Privacy Officer: Matt Sossi<br />
            Email: <a href="mailto:mattsossi@bsossi.com" className="text-[#2A0F5F] underline">mattsossi@bsossi.com</a><br />
            Phone: <a href="tel:2102241667" className="text-[#2A0F5F] underline">210-224-1667</a><br />
            Mailing address: 16607 Blanco #703, San Antonio, Texas 78232<br />
            Website: <a href="https://sacoparentsapp.online" target="_blank" rel="noopener noreferrer" className="text-[#2A0F5F] underline">sacoparentsapp.online</a>
          </p>

          <Callout>
            <div className="eyebrow mb-2 !text-[#3D1A78]">Our privacy commitment</div>
            <p className="!mb-2">
              SA CoParents was created to help parents move from
              conflict toward greater understanding, alignment, and
              child-focused decision-making. Parents should be able to
              explore difficult issues without assuming that every
              thought, concern, or assessment response will
              automatically be transmitted to the other parent.
            </p>
            <p className="!mb-2">
              That is why our approach is:{" "}
              <strong>Private by Default. Shared by Choice.</strong>
            </p>
            <p className="!mb-0">
              We seek to collect only what is reasonably necessary,
              protect sensitive family information, give parents
              meaningful control over sharing, clearly explain the
              limits of confidentiality, and keep the needs and safety
              of children at the centre of the platform.
            </p>
            <p className="!mb-0 mt-3 text-sm italic text-[#4B4567]">
              SA CoParents — Starting With Alignment, Ending With Agreement.
            </p>
          </Callout>

          <H2>See also</H2>
          <ul>
            <li><Link to="/legal/hipaa" className="text-[#2A0F5F] underline">HIPAA Notice</Link> — health-adjacent data framing.</li>
            <li><Link to="/legal/privacy-practices" className="text-[#2A0F5F] underline">Notice of Privacy Practices</Link> — formal HIPAA-styled notice.</li>
            <li><Link to="/legal/hb300" className="text-[#2A0F5F] underline">Texas HB 300 Notice</Link> — Texas Medical Records Privacy Act addendum.</li>
            <li><Link to="/data-retention" className="text-[#2A0F5F] underline">Data Retention Policy</Link> — canonical retention schedule.</li>
            <li><Link to="/methodology" className="text-[#2A0F5F] underline">Methodology &amp; assessment validation</Link>.</li>
            <li><Link to="/accessibility" className="text-[#2A0F5F] underline">Accessibility statement</Link>.</li>
            <li><Link to="/terms" className="text-[#2A0F5F] underline">Terms of Use</Link>.</li>
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

function H3({ children }) {
  return (
    <h3 className="font-serif text-lg text-[#1A1330] mt-5 mb-2">{children}</h3>
  );
}

function Callout({ children }) {
  return (
    <div className="rounded-2xl border border-[#E5E0EE] bg-[#F8F7FC] p-5 my-6 space-y-2 text-[#1A1330] leading-relaxed [&_p]:text-[#4B4567] [&_strong]:text-[#1A1330]">
      {children}
    </div>
  );
}

function Prose({ children }) {
  return (
    <div className="prose-soft space-y-3 text-[#1A1330] leading-relaxed [&_p]:text-[#4B4567] [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:space-y-1.5 [&_li]:text-[#4B4567] [&_strong]:text-[#1A1330] text-[15px]">
      {children}
    </div>
  );
}
