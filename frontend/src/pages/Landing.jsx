import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Users, ShieldAlert, HeartPulse, GraduationCap,
  Brain, Scale, MessagesSquare, ArrowRight, Heart, HeartHandshake, Lightbulb,
} from "lucide-react";
import { BrandLogo } from "@/components/Brand";

const POSTER_IMG = "https://customer-assets-cm19k8pv.emergentagent.net/job_align-report/artifacts/yyfhtbqg_ChatGPT%20Image%20Sep%201%2C%202026%2C%2005_47_45%20PM.png";

const TYPES = [
  { icon: Users, title: "General Co-Parenting" },
  { icon: MessagesSquare, title: "Communication" },
  { icon: ShieldAlert, title: "High-Conflict" },
  { icon: ShieldAlert, title: "IPV / Family Violence Safety" },
  { icon: HeartPulse, title: "Medical Needs" },
  { icon: GraduationCap, title: "Educational Needs" },
  { icon: Brain, title: "Psychological / Behavioral" },
  { icon: Scale, title: "Preparing for Court" },
];

const PAGES = [
  "Joint Alignment Overview", "Your Child at the Center", "Where You Align",
  "Where Your Perspectives Differ", "What Might Your Child Need?", "Options & Resources",
  "Questions for Parent Conversation", "Professional Conversation Guide",
  "Parent Action Plan", "Joint Alignment Summary",
];

const PILLARS = [
  { icon: Heart, label: "REFLECT", color: "text-brand-purple", bg: "bg-brand-purple", desc: "Each parent's perspective matters." },
  { icon: HeartHandshake, label: "ALIGN", color: "text-brand-teal", bg: "bg-brand-teal", desc: "Discover areas of shared understanding." },
  { icon: MessagesSquare, label: "COMMUNICATE", color: "text-brand-green", bg: "bg-brand-green", desc: "Identify differences without blame." },
  { icon: Lightbulb, label: "CO-PARENT", color: "text-brand-orange", bg: "bg-brand-orange", desc: "Access options and resources together." },
  { icon: Users, label: "THRIVE", color: "text-brand-blue", bg: "bg-brand-blue", desc: "Build a strong foundation for your child's future." },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-background" data-testid="landing-page">
      <header className="no-print max-w-6xl mx-auto px-6 py-6 flex items-center justify-between">
        <div data-testid="brand">
          <BrandLogo sub="Step Two" />
        </div>
        <div className="flex items-center gap-3">
          <Link to="/auth" data-testid="nav-login-link">
            <Button variant="ghost" data-testid="nav-login-btn">Sign in</Button>
          </Link>
          <Link to="/auth" data-testid="nav-get-started-link">
            <Button data-testid="nav-get-started-btn">Get started</Button>
          </Link>
        </div>
      </header>

      <section className="max-w-6xl mx-auto px-6 pt-10 pb-20 grid md:grid-cols-2 gap-12 items-center">
        <div>
          <p className="text-sm uppercase tracking-widest text-primary font-bold mb-4" data-testid="hero-eyebrow">
            Align • Communicate • Thrive
          </p>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-brand-purple leading-tight" data-testid="hero-heading">
            The SA CoParents <span className="font-script text-brand-teal font-normal">Difference</span>
          </h1>
          <p className="mt-4 text-lg font-semibold text-foreground" data-testid="hero-tagline">
            A better way to co-parent. A better future for your child.
          </p>
          <p className="mt-4 text-base md:text-lg text-muted-foreground max-w-xl" data-testid="hero-subtext">
            SA CoParents combines both parents' perspectives into a structured 10-page Joint Alignment
            Report — showing where you align, where your perspectives differ, and what your child may need.
          </p>
          <div className="mt-8 flex flex-wrap gap-4">
            <Link to="/auth" data-testid="hero-cta-link">
              <Button size="lg" className="gap-2" data-testid="hero-cta-btn">
                Start a Joint Assessment <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </div>
          <p className="mt-8 font-script text-2xl text-brand-purple max-w-xl" data-testid="hero-philosophy">
            Starting with alignment, ending with agreement.
          </p>
        </div>
        <div className="relative">
          <div className="absolute -top-4 -left-4 w-full h-full bg-secondary rounded-xl -z-10" />
          <img
            src={POSTER_IMG}
            alt="The SA CoParents Difference — Joint Alignment Report"
            className="rounded-xl shadow-xl w-full"
            data-testid="hero-image"
          />
        </div>
      </section>

      <section className="border-y border-border bg-white/70 py-16" data-testid="pillars-section">
        <div className="max-w-6xl mx-auto px-6 grid grid-cols-2 md:grid-cols-5 gap-8">
          {PILLARS.map((p) => (
            <div key={p.label} className="text-center" data-testid={`pillar-${p.label.toLowerCase()}`}>
              <div className={`h-24 w-24 md:h-28 md:w-28 rounded-full ${p.bg} flex items-center justify-center mx-auto shadow-lg hover:scale-105 transition-transform duration-200`}>
                <p.icon className="h-10 w-10 md:h-12 md:w-12 text-white" />
              </div>
              <p className={`mt-4 text-sm font-extrabold tracking-wide ${p.color}`}>{p.label}</p>
              <p className="mt-1.5 text-xs text-muted-foreground leading-snug max-w-[180px] mx-auto">{p.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-secondary/60 py-20">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-semibold" data-testid="pages-heading">A universal 10-page report</h2>
          <p className="mt-3 text-muted-foreground max-w-2xl" data-testid="pages-subtext">
            Every report is visually familiar. Page 3 always shows alignment, Page 4 always shows
            differences, Page 5 focuses on the child — parents and professionals always know where to look.
          </p>
          <div className="mt-10 grid sm:grid-cols-2 lg:grid-cols-5 gap-4" data-testid="pages-grid">
            {PAGES.map((p, i) => (
              <div
                key={p}
                className="bg-white rounded-lg border border-border p-5 hover:-translate-y-0.5 hover:shadow-md transition-[transform,box-shadow] duration-200"
                data-testid={`page-card-${i + 1}`}
              >
                <span className="font-display text-3xl text-accent font-semibold">{i + 1}</span>
                <p className="mt-2 text-sm font-medium leading-snug">{p}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-20">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-semibold" data-testid="types-heading">Eight specialized assessments</h2>
          <p className="mt-3 text-muted-foreground max-w-2xl" data-testid="types-subtext">
            The architecture stays the same. The questions and analysis change.
          </p>
          <div className="mt-10 grid sm:grid-cols-2 lg:grid-cols-4 gap-4" data-testid="types-grid">
            {TYPES.map((t) => (
              <div
                key={t.title}
                className="bg-white rounded-lg border border-border p-6 flex items-start gap-4 hover:-translate-y-0.5 hover:shadow-md transition-[transform,box-shadow] duration-200"
                data-testid={`type-card-${t.title.toLowerCase().replace(/[^a-z]+/g, "-")}`}
              >
                <t.icon className="h-6 w-6 text-primary shrink-0 mt-0.5" />
                <p className="text-sm font-medium">{t.title}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="border-t border-border py-10">
        <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <BrandLogo size="text-xl" />
            <p className="mt-1 text-xs uppercase tracking-widest text-primary font-bold" data-testid="footer-tagline">
              Align • Communicate • Thrive
            </p>
          </div>
          <div className="md:text-right">
            <p className="text-sm text-muted-foreground" data-testid="footer-note">
              Educational resource. Not legal, medical, or psychological advice.
            </p>
            <p className="text-xs text-muted-foreground mt-1" data-testid="footer-site">sacoparentsapp.online</p>
            <Link to="/privacy" className="block text-xs text-primary mt-2 hover:underline" data-testid="footer-privacy-link">
              Privacy, Confidentiality &amp; Notice Provision
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
