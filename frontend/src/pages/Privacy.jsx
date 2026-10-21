import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { BrandLogo } from "@/components/Brand";

const S = [
  {
    h: "Scope of this Policy",
    b: [
      { p: "This Privacy, Confidentiality & Data Protection Policy explains how SA CoParents Align collects, uses, stores, protects, processes, shares, retains, and deletes personal information. It applies to information collected through the SA CoParents Align website, application, private assessments, joint reports, co-parenting agreements, professional-facilitation requests, preparation tools, and related services. By using SA CoParents Align, you acknowledge the practices described in this Policy." },
    ],
  },
  {
    h: "SA CoParents Align is a parent preparation and educational platform",
    b: [
      { p: "SA CoParents Align provides parents with educational resources, structured assessments, communication tools, preparation materials, joint alignment reports, co-parenting agreement worksheets, and other resources intended to encourage child-focused decision-making." },
      { p: "SA CoParents Align is not a court, law firm, healthcare provider, mental-health provider, custody evaluator, forensic evaluator, or governmental agency. SA CoParents Align does not determine which parent is right or wrong, determine custody, diagnose a psychological or medical condition, determine whether family violence legally occurred, or replace advice from an attorney, physician, mental-health professional, mediator, or other qualified professional." },
      { p: "Assessments and reports generated through SA CoParents Align are intended to help parents identify issues, concerns, goals, possible areas of alignment, and topics that may require professional assistance." },
    ],
  },
  {
    h: "Information we may collect",
    b: [
      { p: "Depending upon the features you use, SA CoParents Align may collect information in the following categories." },
      { sub: "Account information", ul: ["Name", "Email address", "Account credentials", "Authentication information", "Account preferences", "Other information necessary to administer your account"] },
      { sub: "Co-parenting and family information", p2: "Parents may voluntarily provide information concerning:", ul: ["Co-parenting communication", "Parenting concerns", "Children's schedules", "Parenting goals", "Areas of agreement or disagreement", "Decision-making", "Parenting responsibilities", "Transitions between households", "Communication difficulties", "Conflict", "Family circumstances", "Other information relevant to co-parenting"] },
      { sub: "Information about children", p2: "Parents may provide information concerning their children, including:", ul: ["Age or developmental stage", "Educational needs", "School-related concerns", "Medical needs", "Psychological or emotional needs", "Special needs", "Extracurricular activities", "Parenting schedules", "Child-related goals", "Concerns regarding the child's well-being", "Other information a parent chooses to provide"] },
      { sub: "Sensitive family information", p2: "Certain SA CoParents Align tools may allow users to provide particularly sensitive information, including information concerning:", ul: ["Family violence", "Intimate partner violence", "Coercive or controlling behaviour", "Threats or intimidation", "Communication safety", "Mental or behavioural health", "Medical conditions", "Medication", "Disabilities or special needs", "Educational services", "Legal disputes", "Court proceedings", "Protective orders", "Substance-use concerns", "Other sensitive family circumstances"] },
      { p: "We encourage users to provide only information reasonably necessary to use the applicable SA CoParents Align feature." },
      { sub: "User-generated content", p2: "Depending upon the features available, this may include:", ul: ["Assessment responses", "Proposed co-parenting agreement terms", "Foundation Statements", "Child Needs Statements", "Mediation preparation", "Goals", "Concerns", "Proposed solutions", "Reports", "Other information voluntarily entered into the platform"] },
      { sub: "Technical information", p2: "We may automatically collect limited technical information necessary to operate and secure the service, such as:", ul: ["IP address", "Browser type", "Device information", "Login information", "Session information", "Security logs", "Error information", "Basic usage information"] },
      { p: "We do not use this information to create advertising profiles of parents or children." },
    ],
  },
  {
    h: "Information about children",
    b: [
      { p: "SA CoParents Align is intended for use by adults, parents, guardians, and professionals and is not intended to be used directly by children under 13. Parents may nevertheless provide information about their children when using co-parenting assessments and preparation tools. Information about children is treated as sensitive information." },
      { p: "SA CoParents Align does not knowingly solicit personal information directly from children under 13 through parent-facing services. If we learn that personal information has been collected directly from a child in circumstances requiring parental authorisation that was not obtained, we will take appropriate steps to address and, when required, delete that information." },
      { p: "Parents should not give children access to their SA CoParents Align account or ask children to complete adult assessments unless a particular feature expressly provides otherwise. We encourage parents to provide only the child information reasonably necessary for the purpose of the assessment or resource being used." },
    ],
  },
  {
    h: "Sensitive family information",
    b: [
      { p: "Because SA CoParents Align operates in the co-parenting and family-law environment, we recognise that some information deserves heightened protection. We consider information concerning the following matters particularly sensitive:" },
      { sub: "Family violence and safety", p2: "Information concerning alleged abuse, family violence, coercive control, stalking, intimidation, threats, safety concerns, protective orders, or fear." },
      { sub: "Medical information", p2: "Information concerning a child's or parent's medical needs, health conditions, treatment, medication, or healthcare professionals." },
      { sub: "Psychological information", p2: "Information concerning mental health, behavioural health, therapy, psychological concerns, diagnoses reported by a parent, or emotional well-being." },
      { sub: "Educational and special-needs information", p2: "Information concerning disabilities, special education, IEPs, accommodations, developmental needs, educational assessments, or other special-needs services." },
      { sub: "Family-law information", p2: "Information concerning custody, possession, access, parenting plans, mediation, litigation, court orders, allegations, or other family-law matters." },
      { p: "SA CoParents Align uses this information only for legitimate purposes associated with providing, securing, maintaining, and improving the services requested by the user, as otherwise described in this Policy, or as required by law." },
    ],
  },
  {
    h: "How we use information",
    b: [
      { p: "We may use personal information to:" },
      { ul: ["Provide SA CoParents Align assessments and resources", "Generate individualised reports", "Help parents identify needs, concerns, and goals", "Generate proposed co-parenting agreement terms", "Support mediation preparation", "Generate child-focused educational information", "Compare information when parents intentionally participate in a shared or joint process", "Provide communication and problem-solving resources", "Operate user accounts", "Authenticate users", "Protect platform security", "Prevent fraud or misuse", "Provide customer support", "Maintain and improve platform functionality", "Comply with applicable law", "Carry out other purposes disclosed to you when information is collected"] },
      { p: "We do not use sensitive family information to determine which parent should receive custody or possession of a child." },
    ],
  },
  {
    h: "Your individual assessment answers are private by default",
    b: [
      { p: "Your individual answers are private by default. Your co-parent never sees them. A professional sees them only when that professional is assigned to your case, or where disclosure is required by law. Sharing a report gives access to the report only." },
      { p: "Completing an SA CoParents Align assessment does not provide your individual answers to your co-parent. In a joint report, once both parents have submitted their answers, the generated comparison (areas of alignment and difference) is shown to both parents and to the professional on the case. No separate sharing step is needed for that comparison, and neither parent sees the other parent's raw answers." },
      { ul: ["Your individual responses remain associated with your account and are not disclosed to the other parent.", "Your Foundation Statement stays private unless you choose to share it; once shared, it appears in the joint report that both parents and the professional can read.", "When SA CoParents Align generates a report, Mediation Statement, co-parenting agreement, or similar output, the resulting document may contain selected information derived from your responses. You should review any report before sharing it."] },
    ],
  },
  {
    h: "Sharing is controlled by the user",
    b: [
      { p: "SA CoParents Align may provide tools allowing users to intentionally share selected reports or information with:" },
      { ul: ["A co-parent", "Attorney", "Mediator", "Therapist", "Parenting professional", "Collaborative-law professional", "Parenting coordinator or facilitator", "Other professional", "Another person selected by the user"] },
      { p: "In SA CoParents Align, you share a joint report with a professional by entering the email address of that professional's SA CoParents Align account. The professional signs in to read the report. There are no public sharing links. Shared access does not expire on its own; it ends when you stop sharing or delete your account." },
      { p: "Sharing one report does not, by itself, authorise access to your entire SA CoParents Align account. Sharing a report does not automatically provide access to unrelated assessments, private notes, raw responses, or other reports unless the sharing feature specifically states otherwise. Before sharing information, users should carefully review what the recipient will receive." },
    ],
  },
  {
    h: "Important limitation on shared information",
    b: [
      { p: "Once information leaves your private SA CoParents Align account, SA CoParents Align cannot completely control what happens to it. A recipient may potentially:" },
      { ul: ["Download a report", "Save it", "Print it", "Forward it", "Screenshot it", "Provide it to an attorney or professional", "Use it in a legal proceeding"] },
      { p: "You can stop sharing with a professional you added yourself from the report page; that professional can no longer open the report in SA CoParents Align. Professionals assigned to your case (for example by a court or as the professional running the case) cannot be removed by a parent. Stopping sharing cannot retrieve or delete copies that a recipient previously downloaded, printed, photographed, forwarded, or otherwise retained. Parents should therefore carefully consider what information they choose to share." },
    ],
  },
  {
    h: "Privacy does not automatically mean legal confidentiality or privilege",
    b: [
      { p: "Use of SA CoParents Align does not by itself create an attorney-client, therapist-patient, mediator-client, or other privileged relationship." },
      { p: "This distinction is particularly important in family-law matters. SA CoParents Align works to keep information private as described in this Policy. However, use of SA CoParents Align does not itself create a legally privileged relationship. Using SA CoParents Align does not automatically create:" },
      { ul: ["Attorney-client privilege", "Attorney work-product protection", "Therapist-patient privilege", "Physician-patient privilege", "Mediation confidentiality", "Mental-health professional privilege", "Any other evidentiary or legal privilege"] },
      { p: "Whether particular information is privileged, confidential, discoverable, admissible, or protected from disclosure depends upon applicable law and the circumstances in which the information was created or shared. If you are involved in litigation or anticipate litigation, you should consult your attorney before entering or sharing information when you are concerned about discovery, subpoenas, admissibility, privilege, confidentiality, or preservation obligations." },
    ],
  },
  {
    h: "Mediation and professional use",
    b: [
      { p: "SA CoParents Align may be used to help parents prepare for mediation or work with attorneys, therapists, mediators, parenting professionals, or other professionals. Using SA CoParents Align before or during mediation does not automatically make everything entered into the platform confidential under mediation law. Similarly, sharing information with an attorney, therapist, mediator, or other professional does not guarantee that the information will be privileged. The legal status of the information depends upon applicable law and the relationship between the user and the recipient." },
    ],
  },
  {
    h: "Court orders, subpoenas, and legal process",
    b: [
      { p: "SA CoParents Align does not voluntarily provide private user information to a court, opposing party, attorney, governmental agency, or law-enforcement agency merely because it is requested informally. We may disclose information when we reasonably believe disclosure is required by applicable law, valid legal process, court order, subpoena, warrant, or other legally enforceable requirement." },
      { p: "Where legally permitted and appropriate, SA CoParents Align may seek to notify the affected user before producing information so that the user may have an opportunity to seek legal advice or appropriate protection. Nothing in this Policy prevents SA CoParents Align from preserving or disclosing information when reasonably necessary to comply with law or respond to a valid emergency involving an imminent threat to safety." },
    ],
  },
  {
    h: "Family violence and communication safety",
    b: [
      { p: "SA CoParents Align recognises that information concerning family violence, intimate partner violence, coercive control, threats, stalking, intimidation, and communication safety may create unique risks." },
      { p: "Family Violence or Communication Safety assessments are educational and preparation tools. They are not professional risk assessments, forensic evaluations, diagnoses, or legal determinations that family violence has or has not occurred." },
      { p: "The Family check-in is completed by each parent individually. Your co-parent never sees your answers, which questions you skipped, or any concern level. Professionals assigned to your case can read your answers on a protected screen; every view is recorded and listed for you under \u201cWho can see my information\u201d. SA CoParents administrators can open the same screen when needed to support your case or keep someone safe; those views are recorded and shown to you as \u201cSA CoParents administrator\u201d. Court documents, shared reports, and emails show only whether the check-in was received, not started, or declined. Your answers, safe-contact details, and concern level are never sent to any AI service." },
      { p: "When a feature identifies possible safety concerns, the platform may provide information concerning possible safeguards, professional resources, communication structures, or dispute-resolution considerations. SA CoParents Align should not be used as an emergency service. A user experiencing an immediate emergency should contact appropriate emergency services (911), the National Domestic Violence Hotline (1-800-799-SAFE), or the Suicide & Crisis Lifeline (988)." },
    ],
  },
  {
    h: "Artificial intelligence",
    b: [
      { p: "Parent reports are generated from fixed, rule-based templates. SA CoParents Align also uses artificial-intelligence services, reached through Emergent's integration relay, in specific tools used by professionals. Family check-in answers, safe-contact details, and concern levels are never sent to any AI service." },
      { ul: [
        "Report drafting assistant (Claude Sonnet 5.5, Anthropic), used by professionals to draft report language. It receives the case code, the child's first initial, the professional's draft text, and the parents' assessment answers for that case.",
        "Align Assistant (GPT-5.5, OpenAI), a help assistant for professionals. It receives the professional's question and a neutral case summary (case code, child's first initial, step status, alignment counts). Never a parent's answers.",
        "Legal Lens research (Gemini 3.1 Pro, Google, or GPT-5.5, OpenAI). It receives the professional's research question only.",
        "Research summaries (Perplexity). They receive category labels, a joint rating, and the professional's ZIP code. Never names, case numbers, or answers.",
      ] },
      { p: "If we add or change an AI feature in a way that changes what parent information is sent, this Policy will be updated before launch and, where required by law, additional consent will be requested." },
    ],
  },
  {
    h: "We do not sell family information",
    b: [
      { p: "SA CoParents Align does not sell parents' or children's personal information. We do not sell:" },
      { ul: ["Assessment responses", "Reports", "Children's information", "Family-violence information", "Medical information", "Psychological information", "Educational information", "Proposed agreement terms", "Co-parenting information"] },
      { p: "We do not use sensitive family information for third-party targeted advertising." },
    ],
  },
  {
    h: "Service providers",
    b: [
      { p: "SA CoParents Align uses carefully selected service providers to operate the platform. Depending upon the services currently used, these providers may assist with cloud hosting, database storage, authentication, email delivery, security, error monitoring, and technical infrastructure. Service providers receive only the information reasonably necessary to perform their services and are expected to handle information consistently with their contractual obligations and applicable law." },
      { p: "Our current material service providers are:" },
      { ul: [
        "Emergent Labs — application hosting, platform infrastructure, the integration relay used for AI services, and fallback email delivery.",
        "MongoDB Atlas (provided through Emergent) — primary database, encryption at rest.",
        "Cloudflare — domain, DNS, and TLS for sacoparentsalign.com.",
        "Resend — transactional email delivery (invitations, verification codes, professional-request notifications). Never screening answers.",
        "Anthropic (Claude Sonnet 5.5), OpenAI (GPT-5.5), Google (Gemini 3.1 Pro), and Perplexity — AI services used in professional tools, limited to the information described in the Artificial intelligence section.",
        "Google — optional sign-in with an existing Google account for eligible professional, judge, and administrator accounts.",
      ] },
    ],
  },
  {
    h: "Data security",
    b: [
      { p: "SA CoParents Align uses reasonable administrative, technical, and organisational safeguards designed to protect personal information from unauthorised access, disclosure, alteration, destruction, or misuse. These include:" },
      { ul: ["Encryption of information in transit (HTTPS)", "Encryption of stored information on disk by our database provider", "Passwords stored as bcrypt hashes; never in plain text", "Access limited by role, with every view of a parent's safety or report information written to an access log", "Short-lived, HTTP-only, secure session cookies", "Sign-in lockout after repeated failed attempts", "Restricted administrative access", "Backup protections provided by our hosting provider"] },
      { p: "Access to stored information is limited to SA CoParents administrators and the operators of our hosting and database providers, who are bound by their service terms." },
      { p: "No website, application, database, or electronic communication system can guarantee absolute security. Users are responsible for protecting their passwords and devices and should not share account credentials with a co-parent or another person." },
    ],
  },
  {
    h: "Data minimisation",
    b: [
      { p: "SA CoParents Align seeks to collect and process information reasonably necessary to provide its services. Parents should avoid entering unnecessary information such as:" },
      { ul: ["Social Security numbers", "Full financial account numbers", "Passwords", "Unnecessary identifying information about third parties", "Information unrelated to the purpose of the assessment or tool"] },
      { p: "When discussing children, parents should provide only the information reasonably necessary to address the child's needs." },
    ],
  },
  {
    h: "Data retention",
    b: [
      { p: "SA CoParents Align keeps your information until you delete your account. We do not currently run automatic time-based deletion of case information." },
      { p: "Court submissions already sent to a court stay with the court. Security logs and access logs are kept to protect the service and to show you who has viewed your information." },
    ],
  },
  {
    h: "Account and data deletion",
    b: [
      { p: "Parents can delete their account at any time from the dashboard (Delete account, at the bottom of the page; your password is required). Deletion takes effect immediately: your assessment answers, Family check-in, safe-contact details, Foundation Statement, and communication readiness answers are removed from the case, and you appear to the other participants as \u201cFormer participant\u201d. Your co-parent's own information stays in the case." },
      { p: "Professionals and other users, or anyone who prefers not to use the dashboard, may request deletion by emailing the Privacy Officer from the address on the account. SA CoParents Align will delete or de-identify covered personal information from active systems within 30 days, except where retention is reasonably necessary or legally required." },
      { p: "Copies in system backups kept by our hosting provider remain for a limited backup-retention period before being automatically overwritten. Deleting information from SA CoParents Align cannot delete copies previously downloaded, printed, saved, or independently retained by another person, or records already submitted to a court." },
    ],
  },
  {
    h: "Your privacy rights",
    b: [
      { p: "Depending upon applicable law, users may have the right to:" },
      { ul: ["Confirm whether SA CoParents Align processes their personal information", "Access personal information", "Obtain a copy of certain personal information", "Correct inaccurate information", "Delete personal information", "Request information concerning certain disclosures", "Opt out of certain forms of processing where applicable", "Appeal certain decisions concerning a privacy request", "Exercise privacy rights without unlawful discrimination"] },
      { p: "SA CoParents Align will authenticate privacy requests as reasonably necessary to protect users from unauthorised access or deletion. To submit a request, email mattsossi@bsossi.com. If a request is denied, follow the appeal process described in our response." },
    ],
  },
  {
    h: "Texas privacy rights",
    b: [
      { p: "Texas residents may have rights under the Texas Data Privacy and Security Act and other applicable Texas law, including Texas HB 300 (Tex. Health & Safety Code Ch. 181). Where the law applies, SA CoParents Align will provide eligible Texas consumers with applicable rights regarding access, correction, deletion, portability, and certain processing activities. SA CoParents Align does not discriminate against users for exercising applicable privacy rights. A user whose privacy request is denied may use the appeal process described in our response to that request." },
    ],
  },
  {
    h: "Children's online privacy",
    b: [
      { p: "SA CoParents Align is designed for adults and is not directed to children under 13. Children under 13 should not create an SA CoParents Align account or independently submit personal information through adult-facing SA CoParents Align features." },
      { p: "The fact that a parent provides information about a child as part of a parent's co-parenting preparation is different from SA CoParents Align intentionally soliciting personal information directly from the child." },
      { p: "If SA CoParents Align develops features intended for direct use by children, those features will require separate privacy analysis and appropriate parental-consent procedures before implementation." },
    ],
  },
  {
    h: "Health information and HIPAA",
    b: [
      { p: "Parents may voluntarily enter information concerning medical, psychological, behavioural, developmental, or other health-related needs. SA CoParents Align treats such information as sensitive personal information." },
      { p: "However, providing health-related information to SA CoParents Align does not, by itself, mean that SA CoParents Align is a healthcare provider or that all information stored on the platform is Protected Health Information under HIPAA. HIPAA applies only when the applicable legal requirements are satisfied, including circumstances in which an organisation qualifies as a covered entity or business associate." },
      { p: "If SA CoParents Align enters into a relationship in which it acts as a HIPAA business associate, additional contractual and legal requirements may apply to information processed within that relationship. SA CoParents Align does not provide medical or psychological diagnoses or treatment." },
    ],
  },
  {
    h: "Cookies and tracking",
    b: [
      { p: "SA CoParents Align may use cookies or similar technologies necessary to authenticate users, maintain secure sessions, remember account preferences, prevent fraud, protect security, and maintain essential platform functionality." },
      { p: "SA CoParents Align does not use sensitive family information to create advertising profiles. If SA CoParents Align later introduces analytics, advertising, or other tracking technologies that materially change these practices, this Policy will be updated as required." },
    ],
  },
  {
    h: "Joint reports and shared assessments",
    b: [
      { p: "When two parents voluntarily participate in a joint or shared process, SA CoParents Align may generate a report comparing or organising information provided by both parents. The purpose of a Joint Report is not to declare a winner or determine which parent is correct." },
      { p: "A Joint Report may identify:" },
      { ul: ["Areas of alignment", "Areas of disagreement", "Shared concerns", "Different perceptions", "Child-related needs", "Possible communication issues", "Safety considerations", "Topics requiring professional assistance", "Options or resources for moving forward"] },
      { p: "Before participating in a joint process, users are told what information will be compared, what information will remain private, and what will appear in the resulting Joint Report. Once both parents have submitted their answers, the Joint Report is shown to both parents and to the professional on the case. Raw assessment answers are not disclosed; a parent only ever sees the generated comparison, never the other parent's raw answers." },
    ],
  },
  {
    h: "Professional reports",
    b: [
      { p: "SA CoParents Align may permit a parent to provide a report to an attorney, mediator, therapist, parenting professional, court-appointed professional, or other professional. A professional's receipt of an SA CoParents Align report does not make that professional an employee, agent, representative, or endorser of SA CoParents Align. Professionals remain responsible for exercising their own independent professional judgement." },
      { p: "SA CoParents Align reports should be considered alongside other relevant information and should not be treated as professional diagnoses, custody evaluations, forensic assessments, or independent verification of allegations unless an appropriately qualified professional separately conducts and adopts such an evaluation." },
    ],
  },
  {
    h: "No secret monitoring of the other parent",
    b: [
      { p: "SA CoParents Align is intended to support constructive, child-focused co-parenting. The platform should not be used to secretly access another parent's account, impersonate another person, obtain another person's password, circumvent security controls, or engage in unlawful surveillance. Each parent should maintain an independent account unless a specific shared feature expressly provides otherwise." },
    ],
  },
  {
    h: "Data breach and security incidents",
    b: [
      { p: "If SA CoParents Align discovers a security incident involving personal information, we will investigate and respond in accordance with applicable law. Where notification is legally required, affected users and appropriate authorities will be notified as required by applicable law. We may also take protective measures such as resetting credentials, disabling compromised access, ending shared access, or temporarily restricting affected functionality." },
    ],
  },
  {
    h: "Changes to this Policy",
    b: [
      { p: "SA CoParents Align may update this Policy as the platform, technology, service providers, or applicable laws change. The \u201cLast updated\u201d date at the top of this Policy identifies the most recent revision. If we make a material change affecting how sensitive personal information is collected, used, or shared, we will provide notice as described in the Notices section below and, where appropriate, request additional consent." },
    ],
  },
  {
    h: "Notices",
    notice: true,
    b: [
      { p: "Except as otherwise required by law, any legal notice, privacy notice, or other formal communication under this Policy must be in writing." },
      { sub: "Notices from SA CoParents Align to you", p2: "We may provide notices to you by any of the following means:" },
      { ul: ["Email to the address associated with your account (deemed given when sent);", "A prominent notice posted within the platform after you sign in (deemed given when posted); or", "For changes to this Policy, posting the revised Policy on this page with an updated \u201cLast updated\u201d date."] },
      { sub: "Notices from you to us", p2: "Notices concerning this Policy, privacy requests, deletion requests, or legal process must be delivered to the Privacy Officer:" },
      { ul: ["By email: mattsossi@bsossi.com (effective when actually received); or", "By mail: SA CoParents, Attn: Privacy Officer (Matt Sossi), 16607 Blanco #703, San Antonio, Texas 78232 (effective upon receipt)."] },
      { p: "You are responsible for keeping the email address associated with your account current. A notice sent to the email address on your account is effective even if you no longer monitor that address." },
    ],
  },
  {
    h: "Contact SA CoParents Align about privacy",
    b: [
      { p: "Questions, concerns, access requests, correction requests, deletion requests, or other privacy inquiries may be directed to:" },
      { ul: ["SA CoParents — Privacy Officer: Matt Sossi", "Email: mattsossi@bsossi.com", "Phone: 210-224-1667", "Mailing address: 16607 Blanco #703, San Antonio, Texas 78232", "Website: sacoparentsapp.online"] },
    ],
  },
];

export default function Privacy() {
  return (
    <div className="min-h-screen bg-background" data-testid="privacy-page">
      <header className="bg-white border-b border-border">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground" data-testid="privacy-back-link">
            <ArrowLeft className="h-4 w-4" /> Back to SA CoParents
          </Link>
          <BrandLogo size="text-xl" />
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-12">
        <p className="text-xs uppercase tracking-widest text-brand-teal font-bold mb-2">Privacy, Confidentiality &amp; Data Protection Policy</p>
        <h1 className="text-4xl sm:text-5xl font-semibold mb-3" data-testid="privacy-heading">Private by Default. Shared by Choice.</h1>
        <p className="text-sm text-muted-foreground mb-8" data-testid="privacy-effective">Effective: September 2, 2026 · Last updated: October 20, 2026</p>

        <div className="space-y-4 text-muted-foreground leading-relaxed mb-12">
          <p>
            SA CoParents Align is designed to help parents better understand their co-parenting relationship, identify the needs of their
            children, prepare for productive conversations, consider options and resources, and prepare for mediation or other family-law processes.
          </p>
          <p>
            We recognise that parents may provide deeply personal information concerning themselves, their children, their co-parenting
            relationship, family conflict, family violence, medical needs, educational needs, psychological needs, and legal circumstances.
            Protecting that information is a fundamental part of the SA CoParents Align platform.
          </p>
          <p className="text-foreground font-medium">
            Our guiding privacy principle is: <em>Private by Default. Shared by Choice.</em>
          </p>
          <p>
            Your information is private by default. SA CoParents Align does not share your individual assessment answers, proposed
            agreement terms, or other private preparation materials with your co-parent, attorney, mediator, therapist, court, or other
            professional. In a joint case, the generated comparison is shown to both parents and the professional on the case once both parents
            have submitted; everything else is shared only when you choose, subject to the limited circumstances described in this Policy,
            including service providers necessary to operate the platform and disclosures required by law.
          </p>
        </div>

        <div className="space-y-10">
          {S.map((sec, i) => (
            <section key={sec.h} data-testid={sec.notice ? "notice-provision" : `privacy-section-${i + 1}`}>
              <h2 className="text-lg font-semibold mb-3">
                {i + 1}. {sec.h}
              </h2>
              <div className="space-y-3 text-muted-foreground leading-relaxed text-base">
                {sec.b.map((blk, j) => (
                  <div key={j}>
                    {blk.sub && <h3 className="text-base font-semibold text-foreground mt-4 mb-1">{blk.sub}</h3>}
                    {blk.p && <p>{blk.p}</p>}
                    {blk.p2 && <p>{blk.p2}</p>}
                    {blk.ul && (
                      <ul className="list-disc pl-6 space-y-1">
                        {blk.ul.map((li) => (
                          <li key={li}>{li}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>

        <div className="mt-16 bg-secondary/50 border border-border rounded-lg p-6" data-testid="privacy-commitment">
          <h2 className="text-lg font-semibold mb-3">Our privacy commitment</h2>
          <div className="space-y-3 text-muted-foreground leading-relaxed text-base">
            <p>
              SA CoParents Align was created to help parents move from conflict toward greater understanding, alignment, and child-focused
              decision-making. Parents should be able to explore difficult issues without assuming that every thought, concern, or assessment
              response will automatically be transmitted to the other parent.
            </p>
            <p>That is why our approach is: <strong className="text-foreground">Private by Default. Shared by Choice.</strong></p>
            <p>
              We seek to collect only what is reasonably necessary, protect sensitive family information, give parents meaningful control over
              sharing, clearly explain the limits of confidentiality, and keep the needs and safety of children at the centre of the platform.
            </p>
            <p className="text-foreground font-medium">SA CoParents — Starting With Alignment, Ending With Agreement.</p>
          </div>
        </div>
      </main>
    </div>
  );
}
