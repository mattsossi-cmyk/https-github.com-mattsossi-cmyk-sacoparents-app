import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Users, ShieldAlert, HeartPulse, GraduationCap, Brain, Scale, MessagesSquare,
  ArrowRight, FolderPlus, Mail, FileText, Lock, CheckCircle2, Eye, ClipboardCheck, Send, Gavel,
} from "lucide-react";
import { BrandLogo } from "@/components/Brand";
import { SampleCard } from "@/components/SampleCard";
import { AlignModel } from "@/components/AlignModel";
import { MomentsStrip } from "@/components/MomentsStrip";
import { ListedProsTeaser } from "@/components/ListedProsTeaser";
import { SAMPLE_REPORTS } from "@/lib/samples";

const POSTER_IMG = "/align-hero-simple.jpg";

const STEPS = [
  { n: 1, key: "create", icon: FolderPlus, title: "Create or Receive a Case", body: "Open a case yourself, or accept a matter referred to you by a court." },
  { n: 2, key: "invite", icon: Mail, title: "Invite Parents", body: "Each parent receives a private invitation and completes their assessment independently." },
  { n: 3, key: "monitor", icon: Eye, title: "Monitor Assessments", body: "Track each parent's progress without seeing the other parent's answers." },
  { n: 4, key: "report", icon: FileText, title: "Review Joint Reports", body: "Align organizes shared ground, differences, child needs, and subjects for discussion." },
  { n: 5, key: "statement", icon: ClipboardCheck, title: "Prepare Professional Statement", body: "Record your neutral professional assessment alongside the Joint Report." },
  { n: 6, key: "submit", icon: Send, title: "Share / Submit Authorized Reports", body: "Release authorized reports to parents, counsel, or the court — frozen, timestamped, and logged." },
];

const COURT_STEPS = [
  "Court Refers Case", "Professional Accepts", "Professional Invites Parents", "Parents Complete Assessments",
  "Joint Report Created", "Professional Reviews", "Professional Statement Created", "Professional Sends Reports to Court",
];

const SUBJECTS = [
  { slug: "general", icon: Users, title: "General Co-Parenting", key: "co_parenting" },
  { slug: "communication", icon: MessagesSquare, title: "Communication", key: "communication" },
  { slug: "high-conflict", icon: ShieldAlert, title: "High-Conflict Parenting", key: null },
  { slug: "safety", icon: ShieldAlert, title: "IPV and Family-Violence Safety", key: "safety", danger: true },
  { slug: "medical", icon: HeartPulse, title: "Medical Needs", key: "medical" },
  { slug: "educational", icon: GraduationCap, title: "Educational Needs", key: "education" },
  { slug: "psychological", icon: Brain, title: "Psychological and Behavioral Needs", key: "psychological" },
  { slug: "mediation-court", icon: Scale, title: "Preparation for Mediation or Court", key: "mediation" },
];

const CONTROL_POINTS = [
  "The professional creates the case and sends every invitation — parents never exchange codes.",
  "Each parent reflects privately; one parent's answers are never shown to the other.",
  "Safety concerns are routed only to the professional, never into an ordinary joint report.",
  "The report does not decide who is right. It organizes perspectives for professional guidance.",
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-background" data-testid="landing-page">
      <header className="no-print max-w-6xl mx-auto px-4 sm:px-6 py-6 flex items-center justify-between gap-3">
        <div data-testid="brand" className="shrink-0">
          <BrandLogo sub="For Professionals" />
        </div>
        <nav className="hidden lg:flex items-center gap-6 text-sm font-medium whitespace-nowrap ml-8" data-testid="main-nav">
          <a href="#how-it-works" className="text-muted-foreground hover:text-foreground" data-testid="nav-how-it-works">How It Works</a>
          <a href="#for-courts" className="text-muted-foreground hover:text-foreground" data-testid="nav-for-courts">For Courts</a>
          <Link to="/samples" className="text-muted-foreground hover:text-foreground" data-testid="nav-sample-report">Sample Reports</Link>
          <Link to="/resources" className="text-muted-foreground hover:text-foreground" data-testid="nav-resources">Resources</Link>
          <Link to="/find-a-professional" className="text-muted-foreground hover:text-foreground" data-testid="nav-find-professional">Find a Professional</Link>
          <Link to="/verify" className="text-muted-foreground hover:text-foreground" data-testid="nav-verify">Verify a Professional</Link>
        </nav>
        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          <Link to="/auth" data-testid="nav-login-link" className="hidden sm:block">
            <Button variant="ghost" data-testid="nav-login-btn">Professional Sign In</Button>
          </Link>
          <Link to="/auth?court=1" data-testid="nav-judicial-link">
            <Button size="sm" variant="outline" className="sm:h-9 sm:px-4 border-brand-purple/40 text-brand-purple" data-testid="nav-judicial-btn"><Gavel className="h-4 w-4 mr-1.5" /> Judicial Portal</Button>
          </Link>
        </div>
      </header>

      <section className="max-w-6xl mx-auto px-6 pt-10 pb-16 grid md:grid-cols-2 gap-12 items-center overflow-hidden" data-testid="hero-section">
        <div className="relative md:order-first min-w-0">
          <div className="absolute -top-4 -right-4 w-full h-full bg-secondary rounded-xl -z-10" />
          <img
            src={POSTER_IMG}
            alt="SA CoParents Align — For Professionals. Two parent perspectives. One child-focused report."
            className="rounded-xl shadow-xl w-full"
            data-testid="hero-image"
          />
        </div>
        <div className="md:order-last min-w-0">
          <p className="text-sm uppercase tracking-widest text-primary font-bold mb-4" data-testid="hero-eyebrow">SA CoParents Align · Professional &amp; Court Tools for Child-Focused Family Resolution</p>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-brand-purple leading-tight" data-testid="hero-heading">
            Turning Individual Perspectives Into Child-Focused Alignment
          </h1>
          <p className="mt-4 text-base md:text-lg text-muted-foreground max-w-xl" data-testid="hero-subtext">
            For professionals and courts working with parents experiencing separation, divorce, and co-parenting conflict.
            Better Information. Stronger Decisions. Brighter Futures.
          </p>
          <div className="mt-8 grid gap-4 sm:grid-cols-2" data-testid="portal-doors">
            <div className="rounded-xl border-2 border-brand-purple/30 bg-white p-5" data-testid="portal-professionals">
              <p className="text-xs font-bold uppercase tracking-widest text-brand-purple">Professionals</p>
              <p className="mt-1 text-lg font-semibold">Manage Cases</p>
              <ul className="mt-2 space-y-0.5 text-sm text-muted-foreground">{["Invite parents.", "Assign assessments.", "Generate Joint Reports.", "Identify alignment and differences.", "Prepare Professional Statements."].map((t) => <li key={t}>{t}</li>)}</ul>
              <div className="mt-4 flex flex-wrap gap-2">
                <Link to="/auth" data-testid="hero-signin-link"><Button size="sm" data-testid="hero-signin-btn">Professional Portal <ArrowRight className="h-4 w-4 ml-1" /></Button></Link>
                <Link to="/auth?mode=register" data-testid="hero-create-account-link"><Button size="sm" variant="ghost" data-testid="hero-create-account-btn">Create a free account</Button></Link>
              </div>
            </div>
            <div className="rounded-xl border-2 border-border bg-secondary/40 p-5" data-testid="portal-courts">
              <p className="text-xs font-bold uppercase tracking-widest text-brand-purple flex items-center gap-1.5"><Gavel className="h-3.5 w-3.5" /> Courts</p>
              <p className="mt-1 text-lg font-semibold">Review Referred Cases</p>
              <ul className="mt-2 space-y-0.5 text-sm text-muted-foreground">{["Track assessment completion.", "Review Joint Reports.", "Read Professional Statements.", "View case-status summaries.", "Communicate with assigned professionals."].map((t) => <li key={t}>{t}</li>)}</ul>
              <div className="mt-4"><Link to="/auth?court=1" data-testid="hero-judicial-link"><Button size="sm" variant="outline" className="border-brand-purple/40 text-brand-purple" data-testid="hero-judicial-btn">Judicial Portal <ArrowRight className="h-4 w-4 ml-1" /></Button></Link></div>
            </div>
          </div>
          <p className="mt-5 text-sm text-muted-foreground" data-testid="hero-accept-line">
            Have an invitation? <Link to="/auth" className="text-primary font-medium hover:underline" data-testid="hero-accept-link">Accept Invitation</Link>
          </p>
          <p className="mt-6 text-sm font-semibold tracking-wide text-brand-purple" data-testid="hero-journey">
            Parent Reflection → Shared Understanding → Professional Alignment → Options &amp; Resources → Agreement → Court Review (when needed)
          </p>
        </div>
      </section>

      <MomentsStrip />
      <section id="how-it-works" className="bg-brand-purple text-white py-16" data-testid="four-steps">
        <div className="max-w-6xl mx-auto px-6">
          <p className="text-xs uppercase tracking-widest font-bold text-white/70">How it works · Two ways a case begins</p>
          <h2 className="mt-2 text-base md:text-lg text-white/90 max-w-3xl" data-testid="four-steps-heading">
            <span className="font-semibold">Option 1 — Not court-ordered:</span> the professional opens the case and invites both parents.{" "}
            <span className="font-semibold">Option 2 — Court-ordered:</span> the court sends the professional an invitation to create the reports. Either way, the same six steps follow.
          </h2>
          <ol className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4" data-testid="four-steps-list">
            {STEPS.map((s, i) => (
              <li key={s.key} className="relative bg-white/10 rounded-xl p-5 border border-white/15 hover:bg-white/15 transition-colors duration-200" data-testid={`step-${s.key}`}>
                <div className="flex items-center justify-between">
                  <span className="h-9 w-9 rounded-full bg-white text-brand-purple font-extrabold flex items-center justify-center">{s.n}</span>
                  <s.icon className="h-6 w-6 text-white/80" />
                </div>
                <p className="mt-4 text-sm font-extrabold uppercase tracking-wide">{s.title}</p>
                <p className="mt-2 text-sm text-white/85 leading-relaxed">{s.body}</p>
                {i < STEPS.length - 1 && i % 3 !== 2 && (
                  <ArrowRight className="hidden md:block absolute -right-4 top-1/2 -translate-y-1/2 h-5 w-5 text-white/60 z-10" />
                )}
              </li>
            ))}
          </ol>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/auth?mode=register" data-testid="steps-create-account-link">
              <Button size="lg" variant="secondary" className="gap-2" data-testid="steps-create-account-btn">Create a Case <ArrowRight className="h-4 w-4" /></Button>
            </Link>
            <Link to="/samples" data-testid="steps-samples-link">
              <Button size="lg" variant="outline" className="bg-transparent text-white border-white/50 hover:bg-white/10 hover:text-white" data-testid="steps-samples-btn">See a Sample Report</Button>
            </Link>
          </div>
        </div>
      </section>

      <section id="for-courts" className="border-b border-border bg-white py-16" data-testid="court-pathway-section">
        <div className="max-w-6xl mx-auto px-6">
          <p className="text-xs uppercase tracking-widest font-bold text-brand-purple flex items-center gap-2"><Gavel className="h-4 w-4" /> For court-referred cases</p>
          <h2 className="mt-2 text-base md:text-lg text-muted-foreground max-w-2xl" data-testid="court-pathway-heading">
            A separate, procedural pathway. The professional is the bridge between the court and the parents; judges receive only authorized, frozen submissions.
          </h2>
          <ol className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="court-pathway-list">
            {COURT_STEPS.map((t, i) => (
              <li key={t} className="relative rounded-lg border border-brand-purple/25 bg-secondary/40 px-4 py-3 text-sm font-semibold text-brand-purple" data-testid={`court-step-${i + 1}`}>
                <span className="mr-2 inline-flex h-6 w-6 items-center justify-center rounded-full bg-brand-purple text-xs text-white">{i + 1}</span>{t}
              </li>
            ))}
          </ol>
          <p className="mt-6 text-sm text-muted-foreground" data-testid="court-pathway-note">
            Court accounts are invitation-only. <Link to="/auth?mode=register&court=1" className="text-primary font-medium hover:underline" data-testid="court-register-link">Register a court account</Link> · <Link to="/verify" className="text-primary font-medium hover:underline">Verify a professional</Link>
          </p>
        </div>
      </section>

      <section id="model" className="max-w-6xl mx-auto px-6 py-20" data-testid="model-section">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <p className="text-xs uppercase tracking-widest text-primary font-bold">The SA CoParents Align model</p>
          <h2 className="mt-2 text-3xl md:text-4xl font-semibold text-brand-purple" data-testid="model-heading">
            Reflection → Comparison → Alignment → Options → Agreement
          </h2>
          <p className="mt-3 text-base md:text-lg text-muted-foreground">
            Every case follows the same child-centered methodology. The parents' individual reflections become
            a shared map, and the professional turns that alignment into workable agreement.
          </p>
        </div>
        <AlignModel />
        <p className="mt-8 text-center font-script text-2xl text-brand-purple" data-testid="model-mantra">
          Reflect Individually. Understand Together. Align Around the Child. Build Agreement.
        </p>
        <div className="mt-6 text-center">
          <Link to="/methodology" data-testid="model-methodology-link">
            <Button variant="outline" className="gap-2" data-testid="model-methodology-btn">Explore the Methodology <ArrowRight className="h-4 w-4" /></Button>
          </Link>
        </div>
      </section>

      <section id="samples" className="max-w-6xl mx-auto px-6 py-20" data-testid="samples-section">
        <h2 className="text-3xl md:text-4xl font-semibold" data-testid="samples-heading">Sample Reports for Professionals</h2>
        <p className="mt-3 text-muted-foreground max-w-2xl" data-testid="samples-subtext">
          Condensed previews using fictional data. Every completed report follows the same neutral 10-page structure.
        </p>
        <div className="mt-8 grid sm:grid-cols-2 lg:grid-cols-3 gap-5" data-testid="samples-grid">
          {SAMPLE_REPORTS.slice(0, 3).map((s) => <SampleCard key={s.key} s={s} />)}
        </div>
        <div className="mt-8">
          <Link to="/samples" data-testid="samples-view-all-link">
            <Button variant="outline" data-testid="samples-view-all-btn">View All Sample Reports</Button>
          </Link>
        </div>
      </section>

      <ListedProsTeaser />

      <section id="subjects" className="border-y border-border bg-white/70 py-16" data-testid="subjects-section">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-semibold" data-testid="subjects-heading">Available Joint Report Subjects</h2>
          <p className="mt-3 text-muted-foreground max-w-2xl">Choose one focused subject, or select several for a Complete Alignment Report.</p>
          <div className="mt-8 grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {SUBJECTS.map((s) => (
              <Link key={s.slug} to={s.key ? `/samples/${s.key}` : "/samples"} data-testid={`subject-card-${s.slug}`}
                className={`bg-white rounded-xl border p-4 flex items-center gap-3 hover:shadow-md hover:-translate-y-0.5 transition-[transform,box-shadow] duration-200 ${s.danger ? "border-red-300" : "border-border"}`}>
                <s.icon className={`h-6 w-6 shrink-0 ${s.danger ? "text-red-700" : "text-brand-purple"}`} />
                <span className="text-sm font-semibold">{s.title}</span>
              </Link>
            ))}
          </div>
          <p className="mt-4 text-xs text-red-900 bg-red-50 border border-red-200 rounded-md p-3 max-w-3xl" data-testid="safety-note">
            Family-violence safety screening uses a separate, safety-sensitive process. Individual responses go only to the designated professional and are never exchanged between the parties.
          </p>
        </div>
      </section>

      <section id="confidentiality" className="max-w-6xl mx-auto px-6 py-16 grid md:grid-cols-2 gap-10 items-start" data-testid="confidentiality-section">
        <div>
          <div className="flex items-center gap-3">
            <Lock className="h-7 w-7 text-brand-purple" />
            <h2 className="text-3xl md:text-4xl font-semibold" data-testid="confidentiality-heading">Professional control. Parent privacy.</h2>
          </div>
          <ul className="mt-6 space-y-3">
            {CONTROL_POINTS.map((p) => (
              <li key={p} className="flex items-start gap-2.5 text-sm">
                <CheckCircle2 className="h-4 w-4 text-brand-teal shrink-0 mt-0.5" /> {p}
              </li>
            ))}
          </ul>
          <p className="mt-5 text-sm text-muted-foreground">
            Read the full <Link to="/privacy" className="text-primary font-medium hover:underline" data-testid="confidentiality-privacy-link">Confidentiality &amp; Privacy Notice</Link>.
          </p>
        </div>
        <div className="bg-align-yellow/10 border border-align-yellow/40 rounded-xl p-6" data-testid="parent-notice">
          <p className="font-semibold">Are you a parent?</p>
          <p className="text-sm text-muted-foreground mt-2">
            Individual parent reflections happen in the <a href="https://sacoparentsapp.online" target="_blank" rel="noreferrer" className="text-primary font-medium hover:underline">SA CoParents App</a>.
            Joint reports are started by your professional — you participate through the secure invitation they send you.
          </p>
          <p className="mt-6 font-semibold">Ready to start a case?</p>
          <Link to="/auth?mode=register" className="inline-block mt-3" data-testid="pro-join-link">
            <Button className="gap-2" data-testid="pro-join-btn">Create a Free Professional Account <ArrowRight className="h-4 w-4" /></Button>
          </Link>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 pb-12" data-testid="pro-disclaimer-section">
        <div className="bg-secondary/50 border border-border rounded-lg p-5 text-sm text-muted-foreground" data-testid="pro-disclaimer">
          <strong className="text-foreground">Professional-use disclaimer.</strong> SA CoParents Align is an educational,
          organizational, and mediation-preparation platform. It does not provide legal advice, therapy, medical advice,
          custody evaluations, psychological diagnoses, or recommendations about which parent is better.
        </div>
      </section>

      <footer className="border-t border-border py-8" data-testid="landing-footer">
        <div className="max-w-6xl mx-auto px-6 flex flex-wrap items-center justify-between gap-4">
          <p className="text-xs text-muted-foreground leading-relaxed max-w-4xl" data-testid="footer-disclaimer">
            Reports are conversation starters intended to support child-focused professional work and are not
            determinations of fact, parental fitness, or the best interests of a child.
          </p>
          <BrandLogo size="text-xl" />
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-muted-foreground">
            <Link to="/privacy" className="hover:text-foreground" data-testid="footer-privacy-link">Privacy Policy</Link>
            <Link to="/legal/terms" className="hover:text-foreground" data-testid="footer-terms-link">Terms of Use</Link>
            <Link to="/legal/professional-use" className="hover:text-foreground" data-testid="footer-pro-use-link">Professional-Use Agreement</Link>
            <Link to="/methodology" className="hover:text-foreground" data-testid="footer-methodology-link">Methodology</Link>
            <Link to="/legal/data-retention" className="hover:text-foreground" data-testid="footer-retention-link">Data Retention</Link>
            <Link to="/legal/accessibility" className="hover:text-foreground" data-testid="footer-accessibility-link">Accessibility</Link>
            <Link to="/legal/safety-resources" className="hover:text-foreground" data-testid="footer-safety-link">Safety Resources</Link>
            <Link to="/legal/contact" className="hover:text-foreground" data-testid="footer-contact-link">Contact SA CoParents</Link>
            <Link to="/resources" className="hover:text-foreground" data-testid="footer-resources-link">Professional Resources</Link>
            <a href="https://sacoparentsapp.online" target="_blank" rel="noreferrer" className="hover:text-foreground" data-testid="footer-app-link">SA CoParents App</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
