import { ArrowRight } from "lucide-react";

const STEPS = [["ALIGN", "Understand the situation", "bg-brand-purple"], ["FOCUS", "Identify child needs", "bg-brand-teal"], ["RESOLVE", "Explore pathways", "bg-brand-blue"], ["AGREE", "Build next steps", "bg-brand-purple"]];
const Blank = () => <span className="inline-block w-full max-w-xs border-b border-muted-foreground/60 align-baseline">&nbsp;</span>;

export const ReportCover = ({ pro = {}, testId = "report-cover" }) => (
  <section className="space-y-6 rounded-lg border border-border bg-white p-5 sm:p-8" data-testid={testId}>
    <div className="rounded-lg bg-gradient-to-r from-brand-purple to-brand-blue px-6 py-6 text-center text-white">
      <h1 className="font-display text-2xl sm:text-3xl font-bold">Professional Alignment Report</h1>
      <p className="mt-2 text-sm">Understanding Differences. Identifying Alignment. Meeting the Needs of the Child.</p>
      <p className="mt-3 text-xs opacity-90">Prepared for: Court • Attorneys • Mediators • Parent Facilitators • Other Authorized Professionals</p>
    </div>
    <div>
      <h2 className="text-lg font-bold text-brand-purple">Professional Information</h2>
      <dl className="mt-2 divide-y divide-border rounded-md border border-border text-sm" data-testid={`${testId}-contact`}>
        {[["Professional Name", pro.name], ["Email", pro.email], ["Phone", pro.phone], ["Office / Mailing Address", pro.address]].map(([k, v]) => (
          <div key={k} className="grid grid-cols-[minmax(0,10rem)_1fr] gap-3 px-3 py-2"><dt className="font-semibold">{k}</dt><dd className="whitespace-pre-line text-muted-foreground">{v || <Blank />}</dd></div>
        ))}
      </dl>
    </div>
    <div>
      <h2 className="text-lg font-bold text-brand-purple">Purpose</h2>
      <div className="mt-2 grid gap-3 sm:grid-cols-[12rem_1fr] rounded-md bg-[#f3edfb] p-4 text-sm"><p className="font-bold uppercase tracking-wide text-brand-purple">From Differences to Direction</p><p>This report helps professionals understand <strong>where the parents align</strong>, <strong>where perspectives differ</strong>, <strong>what the child may need</strong>, and <strong>what options, resources, and resolution pathways may help</strong>.</p></div>
      <div className="mt-3 grid gap-3 sm:grid-cols-[12rem_1fr] rounded-md bg-[#e8f7f7] p-4 text-sm"><p className="font-bold uppercase tracking-wide text-teal-700">The SA CoParents Approach</p><p>The goal is not to determine which parent is right. The goal is to understand the co-parenting situation, keep the child's needs at the center, and identify constructive pathways toward resolution and agreement.</p></div>
    </div>
    <ol className="flex flex-wrap items-center justify-center gap-2" data-testid={`${testId}-steps`}>
      {STEPS.map(([t, sub, bg], i) => (
        <li key={t} className="flex items-center gap-2">
          <div className={`w-32 rounded-md px-2 py-3 text-center text-white ${bg}`}><p className="text-sm font-bold">{t}</p><p className="text-[11px] font-semibold leading-tight">{sub}</p></div>
          {i < 3 && <ArrowRight className="h-5 w-5 text-brand-purple" />}
        </li>
      ))}
    </ol>
  </section>
);
