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
        <div className="mt-6 space-y-4">
          {content.body.map((p, i) => (
            <p key={i} className="text-muted-foreground leading-relaxed" data-testid={`legal-${page}-p-${i}`}>{p}</p>
          ))}
        </div>
      </main>
    </div>
  );
}
