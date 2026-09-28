import { Link } from "react-router-dom";
import { Mail, GitCompare, FileOutput } from "lucide-react";

const CTA = ({ n, to, icon: Icon, title, desc, tint, onTrigger, trigger, testId }) => (
  <Link to={to} onMouseEnter={() => onTrigger?.(trigger, "hover")} onClick={() => onTrigger?.(trigger, "click")}
    className={`group block rounded-xl border-2 bg-white p-5 transition-[transform,box-shadow,border-color] hover:-translate-y-0.5 hover:shadow-lg ${tint.border}`} data-testid={testId}>
    <div className="flex items-center gap-3">
      <span className={`inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-bold text-white ${tint.badge}`}>{n}</span>
      <span className={`rounded-md p-2 ${tint.icon}`}><Icon className="h-5 w-5" /></span>
    </div>
    <p className="mt-4 text-base font-bold uppercase tracking-wide">{title}</p>
    <p className="mt-1 text-sm text-muted-foreground">{desc}</p>
  </Link>
);

export const ProHero = ({ reviewTo, reportTo, onTrigger }) => (
  <section className="space-y-8" data-testid="pro-hero">
    <div className="rounded-2xl border border-border bg-white p-6 sm:p-10">
      <h1 className="font-display text-3xl sm:text-4xl lg:text-5xl font-bold text-brand-purple leading-tight" data-testid="pro-hero-title">Two Parents. Two Perspectives. One Child-Focused Picture.</h1>
      <p className="mt-4 max-w-3xl text-base text-muted-foreground" data-testid="pro-hero-text">SA CoParents Align helps professionals bring parents' individual assessments together to identify areas of alignment, differences in perspective, child-focused needs, options and resources, and potential pathways for resolving parenting conflict.</p>
    </div>
    <div className="grid gap-4 md:grid-cols-3" data-testid="primary-cta-bar">
      <CTA n={1} to="/joint/new" icon={Mail} title="Invite Parents" desc="Send assessment links to Parent A & Parent B." trigger="invite" onTrigger={onTrigger} testId="cta-invite-parents"
        tint={{ border: "border-brand-teal/40 hover:border-brand-teal", badge: "bg-brand-teal", icon: "bg-[#e8f7f7] text-teal-700" }} />
      <CTA n={2} to={reviewTo} icon={GitCompare} title="Review Joint Report" desc="View the alignment overlay and where perspectives differ." trigger="review" onTrigger={onTrigger} testId="cta-review-joint"
        tint={{ border: "border-brand-purple/40 hover:border-brand-purple", badge: "bg-brand-purple", icon: "bg-[#f3edfb] text-brand-purple" }} />
      <CTA n={3} to={reportTo} icon={FileOutput} title="Create Prof. Report" desc="Export the court / mediation decision-support report." trigger="report" onTrigger={onTrigger} testId="cta-create-report"
        tint={{ border: "border-brand-blue/40 hover:border-brand-blue", badge: "bg-brand-blue", icon: "bg-[#eaf4fb] text-brand-blue" }} />
    </div>
  </section>
);
