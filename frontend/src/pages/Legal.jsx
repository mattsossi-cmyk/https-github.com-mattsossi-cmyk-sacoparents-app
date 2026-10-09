import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { BrandLogo } from "@/components/Brand";

const PAGES = {
  terms: {
    title: "Terms of Use",
    body: [
      "SA CoParents Align is a professional platform for organizing parent-authorized information into neutral, child-focused reports. By using the portal you agree to use it only for lawful, professional purposes connected to family matters you are authorized to work on.",
      "Reports are conversation starters intended to support child-focused professional work. They are not determinations of fact, parental fitness, or the best interests of a child.",
      "You are responsible for maintaining the confidentiality of your account credentials and for all activity under your account.",
    ],
  },
  "professional-use": {
    title: "Professional-Use Agreement",
    body: [
      "Creating or using an SA CoParents Align account does not establish an attorney-client, therapist-client, physician-patient, mediator, evaluator, or other professional relationship with a parent or family.",
      "Professionals receive access only to the reports specifically authorized by each parent. Authorization for one report does not authorize all reports, and authorization from one parent never authorizes access to the other parent's information.",
      "Professionals may not forward access invitations, share login credentials, or reproduce report content outside the authorized professional process without appropriate consent.",
    ],
  },
  methodology: {
    title: "Methodology",
    body: [
      "Parents complete individual assessments privately in the SA CoParents App (sacoparentsapp.online). Responses are never exchanged between parents.",
      "SA CoParents Align compares the two independent perspectives using neutral, structured analysis: areas of alignment, differences in perspective, the child's identified needs, options and resources, and possible next steps.",
      "The platform does not decide who is telling the truth, rank parents, recommend custody, diagnose anyone, treat assessment scores as clinical findings, or present allegations as verified facts.",
      "Safety-related information requires careful professional review. SA CoParents Align does not independently verify allegations, conduct risk assessments, or replace legal, clinical, or emergency safety planning.",
    ],
  },
  "data-retention": {
    title: "Data Retention",
    body: [
      "Account and case data is retained while your account is active. You may request deletion of your account and associated data at any time.",
      "Previously downloaded reports cannot be remotely recalled — parents are informed of this before granting consent.",
      "Audit records of access events are retained to support security review and consent tracking.",
    ],
  },
  accessibility: {
    title: "Accessibility",
    body: [
      "SA CoParents Align is designed for accessible color contrast, clear typography, keyboard-usable controls, and mobile-responsive layouts.",
      "If you encounter an accessibility barrier, contact us and we will work to provide the content in an accessible format.",
    ],
  },
  "safety-resources": {
    title: "Safety Resources",
    body: [
      "If anyone is in immediate danger, call emergency services (911 in the US) before using any online tool.",
      "National Domestic Violence Hotline: 1-800-799-7233 (US), available 24/7.",
      "Family-violence assessments on this platform are professional-mediated: individual safety responses are never converted into a joint comparison or shared with the other parent.",
    ],
  },
  confidentiality: {
    title: "Confidentiality",
    draft: true,
    body: [
      "SA CoParents Align keeps your individual assessment answers, safety screening responses, personal reflections, and drafts private by default. Your co-parent does not automatically see any of this material.",
      "Only professionals assigned to your matter may view individual screening answers. Every time a professional opens item-level screening responses, the access is recorded in an access log that includes who viewed the material and when.",
      "Reports, court packets, and anything your co-parent may see contain only neutral, selected information — such as whether a screening was received and the professional-confirmed communication pathway — never raw answers, computed flags, locations, or narratives.",
      "Privacy within the platform is not the same as legal privilege. Using SA CoParents Align does not by itself create an attorney-client, therapist-patient, mediator-client, or other legally privileged relationship. Information may be subject to lawful disclosure requirements such as a subpoena or court order. If you are involved in or anticipate litigation, consult your attorney before entering information you are concerned about.",
      "An assessment is not a finding. A difference in perspective is not a determination of fact. An AI-assisted draft is not a professional opinion, and a professional report is not a court determination. Professionals — not software — review, decide, and certify what is shared.",
      "Questions about confidentiality may be sent to the Privacy Officer at mattsossi@bsossi.com.",
    ],
  },
  "sharing-consent": {
    title: "Sharing & Consent",
    draft: true,
    body: [
      "You control what you share. In the Self Journey you choose which completed reports to share and with whom. Sharing one report does not grant access to your whole account, your private journal, your raw answers, or any other report.",
      "Joint participation is different. When you accept an invitation to a joint alignment report or co-parenting agreement, you are consenting to have your responses compared with your co-parent's responses in a neutral, structured report. You see only the generated comparison — never the other parent's raw answers — and the other parent sees only the comparison as well. Please review the subject list on the invitation before you begin.",
      "Court-ordered or professionally facilitated participation follows separate rules. A professional you or a court have assigned may invite both parents, view individual screening answers (access-logged), and select which neutral material appears in a report or court packet. The professional's report is not a court determination.",
      "Family-violence and communication-safety screenings are never turned into a joint comparison and are never shared with the other parent. Only the assigned professional may see them.",
      "Consent is revocable going forward, but not backward. You may stop sharing a report or withdraw from a joint process at any time; however, copies that a recipient has already downloaded, printed, or forwarded cannot be recalled by SA CoParents Align.",
      "Each time a sharing or consent choice is presented, you will be told what the recipient will receive before you confirm. If anything is unclear, pause and ask the assigned professional or contact mattsossi@bsossi.com before continuing.",
    ],
  },
  contact: {
    title: "Contact SA CoParents",
    body: [
      "For professional account questions, privacy requests, or platform support, email the SA CoParents team via your registered professional contact channel.",
      "For data-access or deletion requests, include your registered email and the family reference number of any relevant matter.",
    ],
  },
};

export default function Legal() {
  const { page } = useParams();
  const content = PAGES[page] || PAGES.terms;
  return (
    <div className="min-h-screen bg-background" data-testid={`legal-${page}-page`}>
      <header className="bg-white border-b border-border">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground" data-testid="legal-back-link">
            <ArrowLeft className="h-4 w-4" /> Home
          </Link>
          <BrandLogo size="text-xl" />
        </div>
      </header>
      <main className="max-w-3xl mx-auto px-6 py-12">
        <h1 className="text-4xl font-extrabold text-brand-purple" data-testid={`legal-${page}-title`}>{content.title}</h1>
        {content.draft && <p className="mt-3 inline-block rounded-md border border-amber-300 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-900" data-testid={`legal-${page}-draft`}>Draft — pending owner review</p>}
        <div className="mt-6 space-y-4">
          {content.body.map((p, i) => (
            <p key={i} className="text-muted-foreground leading-relaxed" data-testid={`legal-${page}-p-${i}`}>{p}</p>
          ))}
        </div>
      </main>
    </div>
  );
}
