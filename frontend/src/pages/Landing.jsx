import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Users, MessageSquare, ShieldAlert, HeartPulse, GraduationCap,
  Brain, Scale, MessagesSquare, ArrowRight, FileText,
} from "lucide-react";

const HERO_IMG = "https://images.unsplash.com/photo-1519226135464-df5a9dbcd2a5?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2MzR8MHwxfHNlYXJjaHw0fHxjaGlsZCUyMHBsYXlpbmclMjBwZWFjZWZ1bCUyMG5hdHVyZXxlbnwwfHx8fDE3ODgyMDE0Mzd8MA&ixlib=rb-4.1.0&q=85";
const STONES_IMG = "https://images.unsplash.com/photo-1532009877282-3340270e0529?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzZ8MHwxfHNlYXJjaHwzfHxiYWxhbmNlZCUyMHN0b25lcyUyMHplbnxlbnwwfHx8fDE3ODgyMDE0MzZ8MA&ixlib=rb-4.1.0&q=85";

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

export default function Landing() {
  return (
    <div className="min-h-screen bg-background" data-testid="landing-page">
      <header className="no-print max-w-6xl mx-auto px-6 py-6 flex items-center justify-between">
        <div className="flex items-center gap-2" data-testid="brand">
          <FileText className="h-6 w-6 text-primary" />
          <span className="font-display text-2xl font-semibold text-primary">SA CoParents</span>
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
          <p className="text-sm uppercase tracking-widest text-accent font-semibold mb-4" data-testid="hero-eyebrow">
            Alignment Before Agreement
          </p>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-semibold text-foreground leading-tight" data-testid="hero-heading">
            Two perspectives. One child at the center.
          </h1>
          <p className="mt-6 text-base md:text-lg text-muted-foreground max-w-xl" data-testid="hero-subtext">
            SA CoParents combines both parents' perspectives into a structured 10-page Joint Alignment
            Report — showing where you align, where your perspectives differ, and what your child may need.
          </p>
          <div className="mt-8 flex flex-wrap gap-4">
            <Link to="/auth" data-testid="hero-cta-link">
              <Button size="lg" className="gap-2" data-testid="hero-cta-btn">
                Start a Joint Assessment <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link to="/auth" data-testid="hero-demo-link">
              <Button size="lg" variant="outline" data-testid="hero-demo-btn">Try the demo report</Button>
            </Link>
          </div>
          <p className="mt-8 text-sm text-muted-foreground italic max-w-xl" data-testid="hero-philosophy">
            "We value the parenting system by how well it supports the child, not by how friendly the adults appear."
          </p>
        </div>
        <div className="relative">
          <div className="absolute -top-6 -left-6 w-40 h-40 bg-secondary rounded-lg -z-10" />
          <img
            src={HERO_IMG}
            alt="Child playing peacefully in nature"
            className="rounded-lg shadow-xl object-cover w-full h-[420px]"
            data-testid="hero-image"
          />
          <img
            src={STONES_IMG}
            alt="Balanced stones representing alignment"
            className="absolute -bottom-8 -left-8 w-40 h-40 object-cover rounded-lg shadow-lg border-4 border-white hidden md:block"
            data-testid="hero-image-secondary"
          />
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
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" />
            <span className="font-display text-xl font-semibold text-primary">SA CoParents</span>
          </div>
          <p className="text-sm text-muted-foreground" data-testid="footer-note">
            Educational resource. Not legal, medical, or psychological advice.
          </p>
        </div>
      </footer>
    </div>
  );
}
