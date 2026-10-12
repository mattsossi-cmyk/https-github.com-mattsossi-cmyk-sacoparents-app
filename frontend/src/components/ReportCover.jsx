import { ArrowRight } from "lucide-react";

const STEPS = [["ALIGN", "Understand the situation", "bg-brand-purple"], ["FOCUS", "Identify child needs", "bg-brand-teal"], ["RESOLVE", "Explore pathways", "bg-brand-blue"], ["AGREE", "Build next steps", "bg-brand-purple"]];
const Blank = () => <span className="inline-block w-full max-w-xs border-b border-muted-foreground/60 align-baseline">&nbsp;</span>;

const ROWS = [["Professional Name", "name"], ["Title", "title"], ["Bar Number", "bar_number"], ["License Number", "license_number"], ["Email", "email"], ["Phone", "phone"], ["Office / Mailing Address", "address"]];

export const ReportCover = ({ pro = {}, testId = "report-cover", imageBase, origin, children }) => (
  <section className="space-y-6 rounded-lg border border-border bg-white p-5 sm:p-8" data-testid={testId}>
    <div className="rounded-lg bg-gradient-to-r from-brand-purple to-brand-blue px-6 py-6 text-center text-white">
      <h1 className="font-display text-2xl sm:text-3xl font-bold">Professional Alignment Report</h1>
      <p className="mt-2 text-sm">Understanding Differences. Identifying Alignment. Meeting the Needs of the Child.</p>
      <p className="mt-3 text-xs opacity-90">Prepared for: Court • Attorneys • Mediators • Parent Facilitators • Other Authorized Professionals</p>
    </div>
    <div>
      <div className="flex items-start justify-between gap-4">
        <h2 className="text-lg font-bold text-brand-purple">Professional Information</h2>
        {imageBase && pro.images && <div className="flex gap-2" data-testid={`${testId}-images`}>{["firm_logo", "headshot"].filter((s) => pro.images[s]).map((s) => <img key={s} src={`${imageBase}/${s}`} alt={s === "headshot" ? "Professional headshot" : "Firm logo"} className="h-16 w-16 rounded-md border border-border object-contain bg-white" data-testid={`${testId}-image-${s}`} />)}</div>}
      </div>
      <dl className="mt-2 divide-y divide-border rounded-md border border-border text-sm" data-testid={`${testId}-contact`}>
        {ROWS.map(([k, f]) => (
          <div key={k} className="grid grid-cols-[minmax(0,10rem)_1fr] gap-3 px-3 py-2"><dt className="font-semibold">{k}</dt><dd className="whitespace-pre-line text-muted-foreground" data-testid={`${testId}-${f}`}>{pro[f] || <Blank />}</dd></div>
        ))}
      </dl>
      <div className="mt-4 grid gap-6 text-sm sm:grid-cols-2" data-testid={`${testId}-signature`}>
        <div>
          {imageBase && pro.images?.signature ? <img src={`${imageBase}/signature`} alt="Professional signature" className="h-12 object-contain" data-testid={`${testId}-signature-image`} /> : <div className="h-12" />}
          <p className="border-t border-foreground/60 pt-1 text-xs text-muted-foreground">Professional signature — {pro.name || ""}</p>
        </div>
        <div><div className="h-12 flex items-end text-muted-foreground">{pro.submission_date || <Blank />}</div><p className="border-t border-foreground/60 pt-1 text-xs text-muted-foreground">Date of submission</p></div>
      </div>
      {origin?.line && <p className="mt-3 text-xs font-semibold text-brand-purple" data-testid={`${testId}-content-origin`}>{origin.line}</p>}
      {children}
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
