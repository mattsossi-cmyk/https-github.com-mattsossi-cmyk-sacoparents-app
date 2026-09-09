import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Users, ShieldAlert, HeartPulse, GraduationCap, Brain, Scale, MessagesSquare,
  ArrowRight, FileText, Mail, Eye, BookOpen, CheckCircle2, Lock,
} from "lucide-react";
import { BrandLogo } from "@/components/Brand";
import { SampleCard } from "@/components/SampleCard";
import { SAMPLE_REPORTS } from "@/lib/samples";

const POSTER_IMG = "/align-hero-simple.jpg";
const FLYER_IMG = "/align-pro-poster.png";

const PAGES = [
  "Joint Alignment Overview", "Your Child at the Center", "Where You Align",
  "Where Your Perspectives Differ", "What Might Your Child Need?", "Options & Resources",
  "Questions for Parent Conversation", "Professional Conversation Guide",
  "Parent Action Plan", "Joint Alignment Summary",
];

const SUBJECTS = [
  {
    slug: "general", icon: Users, title: "General Co-Parenting",
    who: "Professionals beginning structured work with any co-parenting pair.",
    compares: "The overall co-parenting relationship: cooperation, communication, decision-making, and the child's day-to-day needs.",
    receives: "A baseline alignment map across the parenting system.",
    uses: "First-session planning, parenting coordination intake.",
  },
  {
    slug: "communication", icon: MessagesSquare, title: "Communication",
    who: "Mediators and therapists addressing how information moves between homes.",
    compares: "How each parent experiences the frequency, tone, and reliability of communication.",
    receives: "Shared and differing views of communication patterns, with neutral options.",
    uses: "Mediation preparation, communication protocols.",
  },
  {
    slug: "high-conflict", icon: ShieldAlert, title: "High-Conflict Parenting",
    who: "Professionals supporting parents with repeated disputes or litigation history.",
    compares: "Where each parent locates the sources of friction, and what each believes would reduce it.",
    receives: "Differences in perspective reframed neutrally, with de-escalation options.",
    uses: "High-conflict mediation, parenting facilitation.",
  },
  {
    slug: "safety", icon: ShieldAlert, title: "IPV and Family-Violence Safety", danger: true,
    who: "Professionals trained in family-violence screening and safety planning.",
    compares: "Each party's safety concerns and required safeguards, provided independently.",
    receives: "A safety-structured summary prepared for the facilitating professional.",
    uses: "Safety screening before any joint process is considered.",
    note: "Requires a separate, safety-sensitive process — it is not automatically appropriate for joint discussion. Individual responses are shared with the designated professional, never exchanged between the parties.",
  },
  {
    slug: "medical", icon: HeartPulse, title: "Medical Needs",
    who: "Professionals helping parents coordinate a child's care.",
    compares: "Each parent's understanding of the child's medical needs, providers, and pending decisions.",
    receives: "Alignment and differences on care, with decision options.",
    uses: "Medical decision-making discussions, care protocols.",
  },
  {
    slug: "educational", icon: GraduationCap, title: "Educational Needs",
    who: "Professionals supporting school-related decisions.",
    compares: "Each parent's view of the child's educational needs, school communication, and supports.",
    receives: "Shared priorities and points needing discussion about schooling.",
    uses: "Education planning, school-choice discussions.",
  },
  {
    slug: "psychological", icon: Brain, title: "Psychological and Behavioral Needs",
    who: "Therapists and counselors focused on the child's wellbeing.",
    compares: "Each parent's observations of the child's emotional and behavioral needs.",
    receives: "A child-focused comparison of concerns and support options.",
    uses: "Therapeutic co-parenting work, referral discussions.",
  },
  {
    slug: "mediation-court", icon: Scale, title: "Preparation for Mediation or Court",
    who: "Attorneys and mediators preparing for structured negotiation.",
    compares: "Each parent's positions, priorities, and understanding of the issues to be resolved.",
    receives: "A Mediation Statement-style alignment report for session planning.",
    uses: "Mediation preparation, settlement conferences.",
  },
];

const SAMPLE_KEY_BY_SLUG = {
  general: "co_parenting",
  communication: "communication",
  safety: "safety",
  medical: "medical",
  educational: "education",
  psychological: "psychological",
  "mediation-court": "mediation",
};

const CLARITY_POINTS = [
  "Where the parents already share common ground",
  "Where their perspectives or priorities differ",
  "What each parent identifies as important for the child",
  "Which subjects require further professional discussion",
  "What options and resources may help the family move forward",
  "What next steps may support a workable agreement",
];

const APPLICATIONS = [
  "Mediation preparation", "Child-focused mediation", "Parenting coordination and facilitation",
  "Therapeutic co-parenting work", "Collaborative family-law meetings", "Settlement conferences",
  "Educational and medical decision-making", "Development of parenting protocols", "Review of child-related concerns",
];

const PARENT_NOTICE_POINTS = [
  "Who invited them",
  "What assessment they are completing",
  "How their information will be used",
  "What information may appear in the joint report",
  "Who may receive or review the report",
  "That the report is not a custody evaluation or determination of truth",
];

const FLOW_STEPS = [
  "Professional creates case", "Professional selects report", "Parents receive secure invitations",
  "Parents respond independently", "Professional generates joint report", "Professional guides discussion",
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-background" data-testid="landing-page">
      <header className="no-print max-w-6xl mx-auto px-6 py-6 flex items-center justify-between gap-4">
        <div data-testid="brand">
          <BrandLogo sub="Professional Joint Reports for Co-Parenting Matters" />
        </div>
        <nav className="hidden lg:flex items-center gap-6 text-sm font-medium" data-testid="main-nav">
          <a href="#how-it-works" className="text-muted-foreground hover:text-foreground" data-testid="nav-how-it-works">How It Works</a>
          <a href="#subjects" className="text-muted-foreground hover:text-foreground" data-testid="nav-joint-reports">Joint Reports</a>
          <a href="#applications" className="text-muted-foreground hover:text-foreground" data-testid="nav-applications">Professional Applications</a>
          <Link to="/samples" className="text-muted-foreground hover:text-foreground" data-testid="nav-sample-report">Sample Reports</Link>
          <Link to="/resources" className="text-muted-foreground hover:text-foreground" data-testid="nav-resources">Professional Resources</Link>
          <Link to="/verify" className="text-muted-foreground hover:text-foreground" data-testid="nav-verify">Verify a Professional</Link>
        </nav>
        <div className="flex items-center gap-3">
          <Link to="/auth" data-testid="nav-login-link">
            <Button variant="ghost" data-testid="nav-login-btn">Sign In</Button>
          </Link>
          <Link to="/auth?mode=register" data-testid="nav-get-started-link">
            <Button data-testid="nav-get-started-btn"><span className="sm:hidden">Get Started</span><span className="hidden sm:inline">Create Professional Account</span></Button>
          </Link>
        </div>
      </header>

      <section className="max-w-6xl mx-auto px-6 pt-10 pb-20 grid md:grid-cols-2 gap-12 items-center" data-testid="hero-section">
        <div className="relative md:order-first">
          <div className="absolute -top-4 -right-4 w-full h-full bg-secondary rounded-xl -z-10" />
          <img
            src={POSTER_IMG}
            alt="SA CoParents Align — For Professionals. Two parent perspectives. One child-focused report."
            className="rounded-xl shadow-xl w-full"
            data-testid="hero-image"
          />
        </div>
        <div className="md:order-last">
          <p className="text-sm uppercase tracking-widest text-primary font-bold mb-4" data-testid="hero-eyebrow">
            SA CoParents Align
          </p>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-brand-purple leading-tight" data-testid="hero-heading">
            Turn Parent Reflection Into Child-Focused Alignment
          </h1>
          <p className="mt-4 text-base md:text-lg text-muted-foreground max-w-xl" data-testid="hero-subtext">
            Invite parents to reflect separately. See where they agree. Identify where they differ.
            Build the conversation around their child's needs.
          </p>
          <p className="mt-3 text-sm text-muted-foreground max-w-xl" data-testid="hero-audience">
            Built for mediators, attorneys, therapists, parenting professionals, and other child-focused practitioners.
          </p>
          <div className="mt-8 flex flex-wrap gap-4">
            <Link to="/auth?mode=register" data-testid="hero-invite-link">
              <Button size="lg" className="gap-2" data-testid="hero-invite-btn">
                Invite Parents <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link to="/auth" data-testid="hero-signin-link">
              <Button size="lg" variant="outline" data-testid="hero-signin-btn">Professional Sign In</Button>
            </Link>
            <Link to="/auth" data-testid="hero-accept-link">
              <Button size="lg" variant="ghost" data-testid="hero-accept-btn">Accept a Parent Invitation</Button>
            </Link>
          </div>
          <p className="mt-6 text-sm font-semibold tracking-wide text-brand-purple" data-testid="hero-journey">
            You invite. Parents reflect. Align compares. You guide.
          </p>
          <p className="mt-6 font-script text-2xl text-brand-purple max-w-xl" data-testid="hero-philosophy">
            Parents Reflect. Professionals Align. Families Build Agreements.
          </p>
        </div>
      </section>

      <section className="bg-brand-purple text-white py-12" data-testid="workflow-strip">
        <div className="max-w-5xl mx-auto px-6">
          <p className="text-xs uppercase tracking-widest font-bold text-white/70">The professional workflow</p>
          <ol className="mt-5 grid grid-cols-2 md:grid-cols-5 gap-4" data-testid="workflow-steps">
            {[
              ["Invite", "You create the case and send each parent a private, secure invitation. Parents never have to exchange codes."],
              ["Assess", "Each parent completes an individual reflection in the SA CoParents App — separately, in their own words."],
              ["Compare", "Align lines up both perspectives and shows where they agree and where they differ, without blame."],
              ["Align", "A neutral Joint Alignment Report frames shared priorities and differences around the child's needs."],
              ["Guide", "You lead the next conversation, mediation, or agreement work with a clear, child-focused map."],
            ].map(([title, body], i) => (
              <li key={title} className="relative bg-white/10 rounded-lg p-4 border border-white/15" data-testid={`workflow-step-${title.toLowerCase()}`}>
                <span className="text-xs font-bold text-white/60">0{i + 1}</span>
                <p className="text-lg font-semibold mt-1">{title}</p>
                <p className="text-xs text-white/80 mt-2 leading-relaxed">{body}</p>
              </li>
            ))}
          </ol>
          <p className="mt-6 text-sm text-white/80 max-w-3xl" data-testid="workflow-note">
            The professional organizes the process from start to finish: you connect the parents, so no one is asked to
            "send the other parent your code."
          </p>
        </div>
      </section>

      <section id="how-it-works" className="border-y border-border bg-white/70 py-16" data-testid="how-it-works">
        <div className="max-w-4xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-semibold" data-testid="platforms-heading">Two Connected Steps. One Child-Focused Process.</h2>
          <div className="mt-8 overflow-x-auto">
            <table className="w-full text-sm border border-border rounded-lg overflow-hidden" data-testid="platforms-table">
              <thead>
                <tr className="bg-secondary/60 text-left">
                  <th className="px-4 py-3 font-semibold">Platform</th>
                  <th className="px-4 py-3 font-semibold">Purpose</th>
                  <th className="px-4 py-3 font-semibold">Primary user</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-t border-border" data-testid="platform-row-app">
                  <td className="px-4 py-3 font-semibold text-brand-teal">SA CoParents App</td>
                  <td className="px-4 py-3">Parent individual assessments and private reflection</td>
                  <td className="px-4 py-3">Parents</td>
                </tr>
                <tr className="border-t border-border" data-testid="platform-row-align">
                  <td className="px-4 py-3 font-semibold text-brand-purple">SA CoParents Align</td>
                  <td className="px-4 py-3">Professional invitations, comparison and joint reports</td>
                  <td className="px-4 py-3">Professionals</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="grid sm:grid-cols-[1fr_auto_1fr] gap-6 items-center mt-10" data-testid="journey-strip">
            <a href="https://sacoparentsapp.online" target="_blank" rel="noreferrer" className="group" data-testid="step-one">
              <div className="bg-white border border-border rounded-xl p-6 text-center shadow-sm group-hover:shadow-md group-hover:-translate-y-0.5 transition-all duration-200 h-full">
                <div className="h-12 w-12 rounded-full bg-brand-teal text-white font-extrabold flex items-center justify-center mx-auto mb-3 text-lg">1</div>
                <p className="font-bold text-brand-teal uppercase tracking-wide text-sm">Step One — Parent Individual Assessment</p>
                <p className="text-sm text-muted-foreground mt-2">Each parent completes a private assessment through the SA CoParents App, describing concerns, observations, priorities, and their understanding of their child's needs.</p>
                <p className="text-xs text-primary mt-2 font-medium">sacoparentsapp.online →</p>
              </div>
            </a>
            <ArrowRight className="h-6 w-6 text-muted-foreground mx-auto rotate-90 sm:rotate-0" />
            <div className="bg-white border-2 border-brand-purple rounded-xl p-6 text-center shadow-sm h-full" data-testid="step-two">
              <div className="h-12 w-12 rounded-full bg-brand-purple text-white font-extrabold flex items-center justify-center mx-auto mb-3 text-lg">2</div>
              <p className="font-bold text-brand-purple uppercase tracking-wide text-sm">Step Two — Professional Joint Report</p>
              <p className="text-sm text-muted-foreground mt-2">You create the case and invite both parents. Align connects their completed assessments and generates a structured Joint Alignment Report to guide mediation, counseling, parenting coordination, or other family-law processes.</p>
              <p className="text-xs text-brand-purple mt-2 font-medium italic">You are here</p>
            </div>
          </div>

          <div className="mt-10 bg-align-yellow/10 border border-align-yellow/40 rounded-lg p-5" data-testid="parent-notice">
            <p className="font-semibold">Are you a parent?</p>
            <p className="text-sm text-muted-foreground mt-1">
              Individual parent assessments begin at <a href="https://sacoparentsapp.online" target="_blank" rel="noreferrer" className="text-primary font-medium hover:underline">SA CoParents App</a>.
              Joint reports are initiated by an authorized professional — parents participate through a secure invitation link or case code.
            </p>
          </div>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 py-16" data-testid="pro-actions">
        <h2 className="text-3xl md:text-4xl font-semibold" data-testid="pro-actions-heading">The professional initiates every case</h2>
        <p className="mt-3 text-muted-foreground max-w-2xl" data-testid="pro-actions-subtext">
          Create a case, select the report, and each parent receives a separate secure invitation.
          Parents respond independently — the system never asks parents to exchange codes themselves.
        </p>
        <div className="mt-8 grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Link to="/auth?mode=register" data-testid="action-create-link">
            <div className="bg-white border border-border rounded-xl p-6 h-full hover:shadow-md hover:-translate-y-0.5 transition-all duration-200">
              <FileText className="h-8 w-8 text-brand-purple mb-3" />
              <p className="font-semibold" data-testid="action-create">Create a Joint Report</p>
            </div>
          </Link>
          <Link to="/auth?mode=register" data-testid="action-invite-link">
            <div className="bg-white border border-border rounded-xl p-6 h-full hover:shadow-md hover:-translate-y-0.5 transition-all duration-200">
              <Mail className="h-8 w-8 text-brand-teal mb-3" />
              <p className="font-semibold" data-testid="action-invite">Invite Parents to Participate</p>
            </div>
          </Link>
          <Link to="/samples" data-testid="action-preview-link">
            <div className="bg-white border border-border rounded-xl p-6 h-full hover:shadow-md hover:-translate-y-0.5 transition-all duration-200">
              <Eye className="h-8 w-8 text-brand-green mb-3" />
              <p className="font-semibold" data-testid="action-preview">Preview Report Formats</p>
            </div>
          </Link>
          <Link to="/resources" data-testid="action-resources-link">
            <div className="bg-white border border-border rounded-xl p-6 h-full hover:shadow-md hover:-translate-y-0.5 transition-all duration-200">
              <BookOpen className="h-8 w-8 text-brand-orange mb-3" />
              <p className="font-semibold" data-testid="action-resources">Access Professional Resources</p>
            </div>
          </Link>
        </div>
        <Link to="/auth" className="inline-block mt-6" data-testid="signin-create-link">
          <Button variant="secondary" size="lg" data-testid="signin-create-btn">Sign In to Create a Joint Report</Button>
        </Link>
        <div className="mt-8 flex flex-wrap items-center gap-2 text-xs text-muted-foreground" data-testid="flow-steps">
          {FLOW_STEPS.map((s, i) => (
            <span key={s} className="flex items-center gap-2">
              <span className="bg-secondary rounded-full px-3 py-1.5 font-medium">{s}</span>
              {i < FLOW_STEPS.length - 1 && <ArrowRight className="h-3.5 w-3.5" />}
            </span>
          ))}
        </div>
      </section>

      <section id="report" className="bg-secondary/60 py-20" data-testid="clarity-section">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-semibold" data-testid="clarity-heading">See the Parenting System More Clearly</h2>
          <p className="mt-3 text-muted-foreground max-w-2xl">
            SA CoParents Align organizes independently provided parent perspectives into a neutral,
            child-focused report. The report helps professionals identify:
          </p>
          <ul className="mt-6 grid sm:grid-cols-2 gap-3 max-w-3xl">
            {CLARITY_POINTS.map((p) => (
              <li key={p} className="flex items-start gap-2.5 text-sm bg-white rounded-md px-4 py-3 border border-border">
                <CheckCircle2 className="h-4 w-4 text-align-green shrink-0 mt-0.5" /> {p}
              </li>
            ))}
          </ul>
          <p className="mt-6 text-sm font-medium max-w-2xl" data-testid="clarity-note">
            The report does not decide which parent is right or wrong. It provides professionals with a clearer
            and more organized starting point for meaningful discussion.
          </p>
          <div className="mt-10">
            <p className="text-xs uppercase tracking-widest text-muted-foreground font-bold mb-3">A universal 10-page report — parents and professionals always know where to look:</p>
            <div className="flex flex-wrap gap-2">
              {PAGES.map((p, i) => (
                <span key={p} className="text-xs bg-white border border-border rounded-full px-3 py-1.5" data-testid={`page-chip-${i}`}>{p}</span>
              ))}
            </div>
            <p className="mt-3 text-xs text-muted-foreground" data-testid="pages-sample-note">
              Sample reports below are condensed; every completed Joint Alignment Report follows this full universal 10-page structure.
            </p>
          </div>
        </div>
      </section>

      <section id="samples" className="border-y border-border bg-white/70 py-20" data-testid="samples-section">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-semibold" data-testid="samples-heading">Sample Reports for Professionals</h2>
          <p className="mt-3 text-muted-foreground max-w-2xl" data-testid="samples-subtext">
            Preview the neutral, child-focused format your clients' reports will follow — alignment,
            differences in perspective, the child's needs, options, and next steps. All samples use fictional data.
          </p>
          <div className="mt-10 grid sm:grid-cols-2 lg:grid-cols-3 gap-5" data-testid="samples-grid">
            {SAMPLE_REPORTS.map((s) => (
              <SampleCard key={s.key} s={s} />
            ))}
          </div>
          <div className="mt-8 text-center">
            <Link to="/samples" data-testid="samples-view-all-link">
              <Button variant="outline" data-testid="samples-view-all-btn">View All Sample Reports</Button>
            </Link>
          </div>
        </div>
      </section>

      <section id="subjects" className="max-w-6xl mx-auto px-6 py-20" data-testid="subjects-section">
        <h2 className="text-3xl md:text-4xl font-semibold" data-testid="subjects-heading">Available Joint Report Subjects</h2>
        <p className="mt-3 text-muted-foreground max-w-2xl">Each report compares the parents' independently provided perspectives within one focused area.</p>
        <div className="mt-10 grid md:grid-cols-2 gap-5">
          {SUBJECTS.map((s) => (
            <div key={s.slug} className={`bg-white rounded-xl border p-6 ${s.danger ? "border-red-300" : "border-border"}`} data-testid={`subject-card-${s.slug}`}>
              <div className="flex items-center gap-3 mb-4">
                <s.icon className={`h-7 w-7 ${s.danger ? "text-red-700" : "text-brand-purple"}`} />
                <h3 className="text-lg font-semibold">{s.title}</h3>
              </div>
              <dl className="space-y-2.5 text-sm">
                <div><dt className="text-xs uppercase tracking-widest text-muted-foreground font-semibold">Who should use it</dt><dd className="mt-0.5">{s.who}</dd></div>
                <div><dt className="text-xs uppercase tracking-widest text-muted-foreground font-semibold">What it compares</dt><dd className="mt-0.5">{s.compares}</dd></div>
                <div><dt className="text-xs uppercase tracking-widest text-muted-foreground font-semibold">What the professional receives</dt><dd className="mt-0.5">{s.receives}</dd></div>
                <div><dt className="text-xs uppercase tracking-widest text-muted-foreground font-semibold">Appropriate professional uses</dt><dd className="mt-0.5">{s.uses}</dd></div>
              </dl>
              {s.note && (
                <p className="mt-4 text-xs bg-red-50 border border-red-200 text-red-900 rounded-md p-3" data-testid="safety-note">{s.note}</p>
              )}
              <Link to={SAMPLE_KEY_BY_SLUG[s.slug] ? `/samples/${SAMPLE_KEY_BY_SLUG[s.slug]}` : "/samples"} className="inline-block mt-4" data-testid={`view-sample-${s.slug}`}>
                <Button variant="outline" size="sm">{SAMPLE_KEY_BY_SLUG[s.slug] ? "View Sample Report" : "View Report Examples"}</Button>
              </Link>
            </div>
          ))}
        </div>
      </section>

      <section id="applications" className="border-y border-border bg-white/70 py-20" data-testid="applications-section">
        <div className="max-w-4xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-semibold" data-testid="applications-heading">Designed to Complement Professional Judgment</h2>
          <p className="mt-3 text-muted-foreground">SA CoParents Align can provide a structured starting point for:</p>
          <ul className="mt-6 grid sm:grid-cols-2 gap-3">
            {APPLICATIONS.map((a) => (
              <li key={a} className="flex items-start gap-2.5 text-sm bg-white rounded-md px-4 py-3 border border-border">
                <CheckCircle2 className="h-4 w-4 text-brand-teal shrink-0 mt-0.5" /> {a}
              </li>
            ))}
          </ul>
          <p className="mt-6 text-sm italic text-muted-foreground max-w-2xl" data-testid="applications-disclaimer">
            SA CoParents Align does not replace professional judgment, legal advice, psychological evaluation,
            safety assessment, or individualized case management.
          </p>
        </div>
      </section>

      <section id="confidentiality" className="max-w-4xl mx-auto px-6 py-20" data-testid="confidentiality-section">
        <div className="flex items-center gap-3">
          <Lock className="h-7 w-7 text-brand-purple" />
          <h2 className="text-3xl md:text-4xl font-semibold" data-testid="confidentiality-heading">Professional Control and Purposeful Sharing</h2>
        </div>
        <p className="mt-4 text-muted-foreground">
          Parents provide their perspectives independently. The professional manages the invitation and report
          process. Parents receive clear notice explaining:
        </p>
        <ul className="mt-6 space-y-2">
          {PARENT_NOTICE_POINTS.map((p) => (
            <li key={p} className="flex items-start gap-2.5 text-sm">
              <CheckCircle2 className="h-4 w-4 text-brand-purple shrink-0 mt-0.5" /> {p}
            </li>
          ))}
        </ul>
        <p className="mt-6 text-sm text-muted-foreground">
          Professionals should obtain appropriate authorization before sharing a report outside the identified
          professional process. Read the full <Link to="/privacy" className="text-primary font-medium hover:underline" data-testid="confidentiality-privacy-link">Confidentiality &amp; Privacy Notice</Link>.
        </p>
      </section>

      <section className="max-w-4xl mx-auto px-6 py-20" data-testid="leadership-section">
        <h2 className="text-3xl md:text-4xl font-semibold" data-testid="leadership-heading">Created for the Professionals Who Guide Families</h2>
        <p className="mt-4 text-muted-foreground leading-relaxed max-w-2xl">
          SA CoParents Align was developed from family-law and mediation experience to help professionals
          organize parent perspectives before beginning difficult child-related conversations. The platform
          is designed to support informed professional dialogue, identify areas requiring attention, and help
          families move from competing positions toward child-focused decisions.
        </p>
        <ul className="mt-6 space-y-2 text-sm">
          <li className="flex items-start gap-2.5"><CheckCircle2 className="h-4 w-4 text-brand-teal shrink-0 mt-0.5" /> <span><strong>Who it's for:</strong> mediators, family-law attorneys, therapists and counselors, parenting coordinators and facilitators, collaborative and court-appointed professionals.</span></li>
          <li className="flex items-start gap-2.5"><CheckCircle2 className="h-4 w-4 text-brand-teal shrink-0 mt-0.5" /> <span><strong>The problem it addresses:</strong> professionals too often begin with two competing narratives and no organized common ground. Align structures each parent's independent perspective before the first joint conversation.</span></li>
          <li className="flex items-start gap-2.5"><CheckCircle2 className="h-4 w-4 text-brand-teal shrink-0 mt-0.5" /> <span><strong>"Authorized professional":</strong> the practitioner who created the case and invited the parents. They control invitations, timing, and report access; parents participate only through that professional's secure invitation.</span></li>
          <li className="flex items-start gap-2.5"><CheckCircle2 className="h-4 w-4 text-brand-teal shrink-0 mt-0.5" /> <span><strong>Parent platform:</strong> parent individual assessments and private reflection happen in the <a href="https://sacoparentsapp.online" target="_blank" rel="noreferrer" className="text-primary hover:underline">SA CoParents App</a> (sacoparentsapp.online) — Align is the professional counterpart.</span></li>
        </ul>
      </section>

      <section className="max-w-4xl mx-auto px-6 py-12" data-testid="pro-disclaimer-section">
        <div className="bg-secondary/50 border border-border rounded-lg p-6 text-sm text-muted-foreground" data-testid="pro-disclaimer">
          <strong className="text-foreground">Professional-use disclaimer.</strong> SA CoParents Align is an
          educational, organizational, and mediation-preparation platform. It does not provide legal advice,
          therapy, medical advice, custody evaluations, psychological diagnoses, or recommendations about
          which parent is better. Reports are intended to support informed professional conversations and
          child-focused decision-making.
        </div>
        <p className="mt-4 text-sm text-muted-foreground italic max-w-3xl" data-testid="philosophy-line">
          Start with individual reflection. Discover shared understanding. Identify differences without
          assigning blame. Provide options and resources. Build alignment around the child's needs.
          Use alignment as the foundation for agreement.
        </p>
      </section>

      <section id="invitation" className="bg-secondary/60 py-20" data-testid="professionals-invite">
        <div className="max-w-4xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-semibold" data-testid="invite-heading">Help Parents Find Alignment Before Agreement</h2>
          <p className="mt-4 text-muted-foreground leading-relaxed">
            Parents often enter mediation, counseling, or the legal process with very different understandings
            of their child, their parenting relationship, and the problem they are trying to solve.
            SA CoParents Align helps professionals begin with better-organized information.
          </p>
          <p className="mt-4 text-muted-foreground leading-relaxed">
            Rather than beginning with "Which parent is right?" the process begins with more constructive questions:
          </p>
          <ul className="mt-4 space-y-2">
            {["Where are these parents already aligned?", "Where do their perspectives differ?", "What does their child need from them next?"].map((q) => (
              <li key={q} className="flex items-start gap-2.5 text-sm font-medium">
                <CheckCircle2 className="h-4 w-4 text-align-green shrink-0 mt-0.5" /> {q}
              </li>
            ))}
          </ul>
          <p className="mt-4 text-muted-foreground leading-relaxed">
            The professional remains at the center of the process — providing context, exercising judgment,
            managing safety concerns, and helping the parents determine appropriate next steps.
          </p>
          <p className="mt-6 font-script text-2xl text-brand-purple" data-testid="invite-mantra">
            Reflect Individually. Understand Together. Align Around the Child. Build Agreement.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/auth?mode=register" data-testid="pro-join-link">
              <Button size="lg" className="gap-2" data-testid="pro-join-btn">Create a Free Professional Account <ArrowRight className="h-4 w-4" /></Button>
            </Link>
            <Link to="/samples" data-testid="sample-mediation-link">
              <Button size="lg" variant="outline" data-testid="sample-mediation-btn">Browse Sample Reports</Button>
            </Link>
          </div>
          <div className="mt-10 max-w-md" data-testid="pro-flyer">
            <img src={FLYER_IMG} alt="SA CoParents Align for Professionals — shareable overview" className="rounded-xl shadow-md w-full" />
            <p className="mt-2 text-xs text-muted-foreground text-center">Shareable overview — feel free to forward to colleagues.</p>
          </div>
        </div>
      </section>

      <footer className="border-t border-border py-8" data-testid="landing-footer">
        <div className="max-w-6xl mx-auto px-6 flex flex-wrap items-center justify-between gap-4">
          <p className="text-xs text-muted-foreground leading-relaxed max-w-4xl" data-testid="footer-disclaimer">
            SA CoParents Align is an educational and professional-support platform. It does not provide legal
            advice, therapy, medical advice, custody evaluations, psychological diagnoses, or emergency services.
            Reports are conversation starters intended to support child-focused professional work and are not
            determinations of fact, parental fitness, or the best interests of a child.
          </p>
          <BrandLogo size="text-xl" />
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-muted-foreground">
            <Link to="/privacy" className="hover:text-foreground" data-testid="footer-privacy-link">Privacy Policy</Link>
            <Link to="/legal/terms" className="hover:text-foreground" data-testid="footer-terms-link">Terms of Use</Link>
            <Link to="/legal/professional-use" className="hover:text-foreground" data-testid="footer-pro-use-link">Professional-Use Agreement</Link>
            <Link to="/legal/methodology" className="hover:text-foreground" data-testid="footer-methodology-link">Methodology</Link>
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
