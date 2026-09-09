import { Link } from "react-router-dom";
import { ArrowLeft, Link2, Printer, ArrowRight, CheckCircle2, Download } from "lucide-react";
import { toast } from "sonner";
import { BrandLogo } from "@/components/Brand";
import { AlignModel } from "@/components/AlignModel";
import { Button } from "@/components/ui/button";

const STEPS = [
  ["Create a Case", "The professional chooses the family and the issue to address."],
  ["Invite Each Parent", "Each parent receives a private invitation and completes their reflection independently. Responses are never exchanged between parents."],
  ["Generate Joint Alignment Report", "Align identifies shared understanding, differences in perspective, child needs, and subjects requiring discussion."],
  ["Guide the Conversation", "The professional uses the report to move the parents from alignment toward agreement."],
];

const PAGES = [
  "Joint Alignment Overview", "Your Child at the Center", "Where You Align", "Where Your Perspectives Differ",
  "What Might Your Child Need?", "Options & Resources", "Questions for Parent Conversation",
  "Professional Conversation Guide", "Parent Action Plan", "Joint Alignment Summary",
];

const PRINCIPLES = [
  "Neutral language only — \"Both parents identified…\", \"The parents expressed different perspectives regarding…\"",
  "No custody recommendation, diagnosis, finding of fact, or ranking of parents.",
  "One parent's raw responses are never shown to the other parent.",
  "Safety concerns are routed to the professional through a separate, safety-sensitive process.",
  "If only one parent participates, the result is an individual reflection — never called a joint report.",
];

export default function Methodology() {
  const share = async () => {
    try { await navigator.clipboard.writeText(window.location.href); toast.success("Link copied"); }
    catch { toast.error("Copy failed — use your browser's share menu"); }
  };
  return (
    <div className="min-h-screen bg-background" data-testid="methodology-page">
      <header className="no-print bg-white border-b border-border">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between gap-2 sm:gap-4">
          <Link to="/" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground shrink-0" data-testid="methodology-back-link"><ArrowLeft className="h-4 w-4" /> <span className="hidden sm:inline">Home</span></Link>
          <BrandLogo size="text-xl" />
          <div className="flex gap-1.5 sm:gap-2 shrink-0">
            <a href={`${process.env.REACT_APP_BACKEND_URL}/api/methodology/pdf`} data-testid="methodology-pdf-link">
              <Button size="sm" className="gap-1.5" data-testid="methodology-pdf-btn"><Download className="h-4 w-4" /> <span className="hidden sm:inline">Download PDF</span></Button>
            </a>
            <Button variant="outline" size="sm" onClick={share} className="gap-1.5" data-testid="methodology-share-btn"><Link2 className="h-4 w-4" /> <span className="hidden sm:inline">Copy link</span></Button>
            <Button variant="outline" size="sm" onClick={() => window.print()} className="gap-1.5 hidden sm:inline-flex" data-testid="methodology-print-btn"><Printer className="h-4 w-4" /> Print</Button>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-12 space-y-16">
        <section>
          <p className="text-xs uppercase tracking-widest text-primary font-bold">The SA CoParents Align model</p>
          <h1 className="mt-2 text-4xl sm:text-5xl lg:text-6xl font-extrabold text-brand-purple leading-tight" data-testid="methodology-heading">
            Reflection → Comparison → Alignment → Options → Agreement
          </h1>
          <p className="mt-4 text-base md:text-lg text-muted-foreground max-w-3xl" data-testid="methodology-intro">
            SA CoParents Align is a structured, child-centered methodology for organizing two parents' independent
            perspectives before a mediation, counseling session, parenting-coordination meeting, or court-connected
            conference. It is designed to be shared with colleagues, courts, and referring professionals.
          </p>
        </section>

        <section data-testid="methodology-model"><AlignModel /></section>

        <section data-testid="methodology-steps">
          <h2 className="text-base md:text-lg font-bold uppercase tracking-widest text-brand-purple">How a case moves through the model</h2>
          <ol className="mt-6 grid md:grid-cols-2 gap-4">
            {STEPS.map(([t, b], i) => (
              <li key={t} className="bg-white border border-border rounded-xl p-5 flex gap-4" data-testid={`methodology-step-${i + 1}`}>
                <span className="h-9 w-9 shrink-0 rounded-full bg-brand-purple text-white font-extrabold flex items-center justify-center">{i + 1}</span>
                <div><p className="font-bold">{t}</p><p className="text-sm text-muted-foreground mt-1">{b}</p></div>
              </li>
            ))}
          </ol>
        </section>

        <section className="grid md:grid-cols-2 gap-10" data-testid="methodology-report">
          <div>
            <h2 className="text-base md:text-lg font-bold uppercase tracking-widest text-brand-purple">The universal 10-page report</h2>
            <p className="mt-3 text-sm text-muted-foreground">Every Joint Alignment Report follows the same neutral structure, so parents, professionals, and courts always know where to look.</p>
            <Link to="/samples/mediation" className="inline-block mt-4 mr-2" data-testid="methodology-sample-link"><Button className="gap-2">View a Sample Report <ArrowRight className="h-4 w-4" /></Button></Link>
            <a href={`${process.env.REACT_APP_BACKEND_URL}/api/methodology/pdf`} className="inline-block mt-4" data-testid="methodology-handout-link"><Button variant="outline" className="gap-2"><Download className="h-4 w-4" /> One-page handout (PDF)</Button></a>
          </div>
          <ol className="space-y-2">
            {PAGES.map((p, i) => (
              <li key={p} className="flex items-center gap-3 text-sm bg-white border border-border rounded-lg px-4 py-2.5">
                <span className="h-6 w-6 shrink-0 rounded-full bg-brand-purple/10 text-brand-purple text-xs font-bold flex items-center justify-center">{i + 1}</span>{p}
              </li>
            ))}
          </ol>
        </section>

        <section data-testid="methodology-principles">
          <h2 className="text-base md:text-lg font-bold uppercase tracking-widest text-brand-purple">What the model will not do</h2>
          <ul className="mt-5 space-y-3">
            {PRINCIPLES.map((p) => (
              <li key={p} className="flex items-start gap-2.5 text-sm"><CheckCircle2 className="h-4 w-4 text-brand-teal shrink-0 mt-0.5" /> {p}</li>
            ))}
          </ul>
          <p className="mt-6 text-sm text-muted-foreground italic" data-testid="methodology-disclaimer">
            SA CoParents Align is an educational, organizational, and mediation-preparation platform. It does not replace
            professional judgment, legal advice, psychological evaluation, safety assessment, or individualized case management.
          </p>
        </section>

        <p className="text-center font-script text-2xl text-brand-purple" data-testid="methodology-mantra">
          Reflect Individually. Understand Together. Align Around the Child. Build Agreement.
        </p>
      </main>
    </div>
  );
}
