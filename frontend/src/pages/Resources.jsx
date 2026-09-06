import { Link } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Lock, ShieldAlert, FileText } from "lucide-react";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";

const GETTING_STARTED = [
  "Create your free professional account.",
  "Create a Joint Alignment Case: select the report subject and enter each parent's email. Align generates the Alignment Code (e.g. SA-EDU-482731) automatically.",
  "Each parent receives a separate, secure invitation — the email's button links them directly to their private assessment; the case code is only a backup.",
  "Track progress from your dashboard: invited, in progress, or complete for each parent, with a Send Reminder option for anyone outstanding.",
  "When both parents are complete, select Generate Report to view and download the Joint Alignment Report PDF.",
];

const SHARING_GUIDANCE = [
  "Parents provide their perspectives independently; one parent's responses are never shown to the other.",
  "The joint report contains only the generated comparison — alignment, differences in perspective, the child's identified needs, and options.",
  "The report is not a custody evaluation, a determination of truth, or a clinical or legal opinion.",
  "Obtain appropriate authorization before sharing a report outside the identified professional process.",
  "Add an optional private case reference to any case — it is visible only to you.",
];

const FAQ = [
  {
    q: "Do parents need their own accounts before I invite them?",
    a: "No. Parents create their free parent account while accepting your secure invitation — they simply use the email address the invitation was sent to.",
  },
  {
    q: "Can a parent start a joint report themselves?",
    a: "No. The professional initiates every case. Parents participate only through a secure invitation link or case code.",
  },
  {
    q: "What do parents see?",
    a: "Only their own private assessment, the status of the case, and the final joint report when the professional's process makes it available. They never see the other parent's answers.",
  },
  {
    q: "How does this relate to the SA CoParents App?",
    a: "The App (sacoparentsapp.online) is the parent reflection platform where individual assessments begin. Align is the professional platform that brings those perspectives together into a joint report.",
  },
];

export default function Resources() {
  return (
    <div className="min-h-screen bg-background" data-testid="resources-page">
      <header className="bg-white border-b border-border">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground" data-testid="resources-back-link">
            <ArrowLeft className="h-4 w-4" /> Home
          </Link>
          <BrandLogo size="text-xl" />
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-12 space-y-14">
        <div>
          <p className="text-sm uppercase tracking-widest text-primary font-bold mb-2">Professional Resources</p>
          <h1 className="text-4xl sm:text-5xl font-semibold" data-testid="resources-heading">Using SA CoParents Align in Your Practice</h1>
          <p className="mt-4 text-muted-foreground max-w-2xl" data-testid="resources-intro">
            Align converts independently provided parent perspectives into structured, child-focused joint
            reports — a clearer starting point for mediation, counseling, parenting coordination, and other
            family-law processes.
          </p>
        </div>

        <section data-testid="resources-getting-started">
          <div className="flex items-center gap-3 mb-4">
            <FileText className="h-6 w-6 text-brand-purple" />
            <h2 className="text-2xl font-semibold">Getting started</h2>
          </div>
          <ol className="space-y-3">
            {GETTING_STARTED.map((s, i) => (
              <li key={i} className="flex items-start gap-3 text-sm bg-white border border-border rounded-md px-4 py-3" data-testid={`resources-step-${i}`}>
                <span className="h-6 w-6 rounded-full bg-brand-purple text-white text-xs font-bold flex items-center justify-center shrink-0">{i + 1}</span>
                {s}
              </li>
            ))}
          </ol>
        </section>

        <section data-testid="resources-confidentiality">
          <div className="flex items-center gap-3 mb-4">
            <Lock className="h-6 w-6 text-brand-purple" />
            <h2 className="text-2xl font-semibold">Confidentiality and report sharing</h2>
          </div>
          <ul className="space-y-2">
            {SHARING_GUIDANCE.map((g) => (
              <li key={g} className="flex items-start gap-2.5 text-sm">
                <CheckCircle2 className="h-4 w-4 text-align-green shrink-0 mt-0.5" /> {g}
              </li>
            ))}
          </ul>
          <p className="mt-4 text-sm text-muted-foreground">
            Full terms: <Link to="/privacy" className="text-primary font-medium hover:underline" data-testid="resources-privacy-link">Confidentiality &amp; Privacy Notice</Link>.
          </p>
        </section>

        <section className="bg-red-50 border border-red-200 rounded-xl p-6" data-testid="resources-safety">
          <div className="flex items-center gap-3 mb-3">
            <ShieldAlert className="h-6 w-6 text-red-700" />
            <h2 className="text-2xl font-semibold text-red-900">Safety-sensitive reports</h2>
          </div>
          <p className="text-sm text-red-900/90 leading-relaxed">
            The IPV / Family-Violence Safety report requires a separate, safety-sensitive process and is not
            automatically appropriate for joint discussion. Individual responses are provided to the designated
            professional and are never exchanged between the parties. Always complete your own safety screening
            before introducing any joint process.
          </p>
        </section>

        <section data-testid="resources-faq">
          <h2 className="text-2xl font-semibold mb-4">Common questions</h2>
          <div className="space-y-4">
            {FAQ.map((f, i) => (
              <div key={i} className="bg-white border border-border rounded-lg p-5" data-testid={`resources-faq-${i}`}>
                <p className="font-semibold text-sm">{f.q}</p>
                <p className="text-sm text-muted-foreground mt-2 leading-relaxed">{f.a}</p>
              </div>
            ))}
          </div>
        </section>

        <div className="text-center border-t border-border pt-10" data-testid="resources-cta">
          <p className="font-script text-2xl text-brand-purple">Reflect Individually. Understand Together. Align Around the Child. Build Agreement.</p>
          <Link to="/auth?mode=register" className="inline-block mt-6" data-testid="resources-register-link">
            <Button size="lg" data-testid="resources-register-btn">Create a Free Professional Account</Button>
          </Link>
        </div>
      </main>
    </div>
  );
}
