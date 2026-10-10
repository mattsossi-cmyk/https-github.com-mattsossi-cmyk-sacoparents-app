import { Link } from "react-router-dom";
import { Mail, ClipboardList, GitCompare, Scale, FileOutput, Gavel } from "lucide-react";

const Action = ({ n, to, icon: Icon, title, desc, count, countLabel, tint, danger, onTrigger, trigger, testId }) => (
  <Link to={to} onMouseEnter={() => onTrigger?.(trigger, "hover")} onClick={() => onTrigger?.(trigger, "click")}
    className={`group flex flex-col rounded-2xl border-2 bg-white p-5 transition-[transform,box-shadow,border-color] hover:-translate-y-0.5 hover:shadow-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-purple ${danger ? "border-red-400" : tint.border}`}
    aria-label={`${title}${count != null ? `, ${count} ${countLabel}` : ""}`} data-testid={testId}>
    <div className="flex items-center justify-between gap-3">
      <div className="flex items-center gap-3">
        <span className={`inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white ${tint.badge}`}>{n}</span>
        <span className={`rounded-md p-2 ${tint.icon}`}><Icon className="h-5 w-5" aria-hidden="true" /></span>
      </div>
      {count != null && (
        <span className={`whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-bold ${danger ? "bg-red-600 text-white" : count > 0 ? "bg-brand-purple text-white" : "bg-secondary text-muted-foreground"}`} data-testid={`${testId}-count`}>{count} {countLabel}</span>
      )}
    </div>
    <p className="mt-4 text-base font-bold uppercase tracking-wide">{title}</p>
    <p className="mt-1 text-sm text-muted-foreground">{desc}</p>
  </Link>
);

const TINT = {
  teal: { border: "border-brand-teal/40 hover:border-brand-teal", badge: "bg-brand-teal", icon: "bg-[#e8f7f7] text-teal-700" },
  purple: { border: "border-brand-purple/40 hover:border-brand-purple", badge: "bg-brand-purple", icon: "bg-[#f3edfb] text-brand-purple" },
  blue: { border: "border-brand-blue/40 hover:border-brand-blue", badge: "bg-brand-blue", icon: "bg-[#eaf4fb] text-brand-blue" },
  amber: { border: "border-amber-400/50 hover:border-amber-500", badge: "bg-amber-600", icon: "bg-amber-50 text-amber-700" },
};

export const ProHero = ({ counts, reviewTo, reportTo, onTrigger }) => {
  const c = counts || {};
  return (
    <section className="space-y-8" data-testid="pro-hero">
      <div className="rounded-2xl border border-border bg-white p-6 sm:p-10">
        <p className="text-xs font-bold uppercase tracking-widest text-brand-purple">Professional Dashboard</p>
        <h1 className="mt-2 font-display text-2xl sm:text-3xl font-bold text-brand-purple leading-snug" data-testid="pro-hero-title">
          SA CoParents Align helps professionals understand each parent's perspective, identify the child's needs, and organize information for safer, more informed decisions.
        </h1>
        <p className="mt-4 text-sm text-muted-foreground" data-testid="pro-hero-text">Five steps, in order. Counts update as parents complete their part.</p>
      </div>
      <ol className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5" data-testid="primary-cta-bar" aria-label="Workflow actions">
        <li><Action n={1} to="/joint/new" icon={Mail} title="Invite Parents" desc="Open a case and send each parent a private assessment link." count={c.awaitingParents} countLabel="awaiting" tint={TINT.teal} trigger="invite" onTrigger={onTrigger} testId="cta-invite-parents" /></li>
        <li><Action n={2} to={reviewTo} icon={ClipboardList} title="Review Assessments" desc="See which parent has completed, and the private safety screening status." count={c.assessmentsIn} countLabel="received" tint={TINT.purple} trigger="review" onTrigger={onTrigger} testId="cta-review-assessments" /></li>
        <li><Action n={3} to={reviewTo} icon={GitCompare} title="Joint Report" desc="Where the two perspectives align and where they differ." count={c.jointReady} countLabel="ready" tint={TINT.purple} trigger="review" onTrigger={onTrigger} testId="cta-joint-report" /></li>
        <li><Action n={4} to={reportTo} icon={Scale} title="Legal Lens Review" desc="Review the Six Questions, label sources, and add your professional statement." count={c.lensReady} countLabel="to review" tint={TINT.blue} trigger="report" onTrigger={onTrigger} testId="cta-legal-lens" /></li>
        <li><Action n={5} to="#court-referrals" icon={FileOutput} title="Court Report" desc={c.overdue > 0 ? `${c.overdue} hearing${c.overdue === 1 ? "" : "s"} within 7 days with nothing submitted.` : "Freeze and submit the court packet to the referring judge."} count={c.overdue > 0 ? c.overdue : c.courtPending} countLabel={c.overdue > 0 ? "overdue" : "pending"} danger={c.overdue > 0} tint={TINT.blue} trigger="report" onTrigger={onTrigger} testId="cta-court-report" /></li>
      </ol>
      <Link to="#court-referrals" className="flex flex-col gap-3 rounded-2xl border-2 border-amber-400/50 bg-amber-50/40 p-5 transition-colors hover:border-amber-500 sm:flex-row sm:items-center sm:justify-between focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500" data-testid="cta-judge-portal">
        <div className="flex items-center gap-3">
          <span className="rounded-md bg-amber-100 p-2 text-amber-800"><Gavel className="h-5 w-5" aria-hidden="true" /></span>
          <div><p className="text-base font-bold uppercase tracking-wide">Judge Portal &amp; Referrals</p><p className="text-sm text-muted-foreground">Court-ordered matters arrive here as referrals from the Judicial Portal. Accept one to start at step 1.</p></div>
        </div>
        <span className={`self-start rounded-full px-2.5 py-1 text-xs font-bold sm:self-center ${c.referrals > 0 ? "bg-amber-600 text-white" : "bg-white text-muted-foreground"}`} data-testid="cta-judge-portal-count">{c.referrals || 0} new</span>
      </Link>
    </section>
  );
};
