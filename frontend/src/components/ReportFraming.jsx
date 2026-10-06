import { HelpCircle, ShieldCheck } from "lucide-react";

export const SIX_QUESTIONS = [
  ["What did each parent report?", [3, 4]], ["Where are they aligned?", [2, 5]], ["Where do their perspectives differ?", [5]],
  ["What child-focused issues need attention?", [6]], ["What options and resources are available?", [7]], ["What conflict-resolution pathway could be considered?", [8]],
];
export const QUESTION_OF_SECTION = { 1: "Case record", 2: "Q2 · Where are they aligned?", 3: "Q1 · What did each parent report?", 4: "Q1 · What did each parent report?",
  5: "Q2 & Q3 · Where are they aligned — and where do their perspectives differ?", 6: "Q4 · What child-focused issues need attention?", 7: "Q5 · What options and resources are available?",
  8: "Q6 · What conflict-resolution pathway could be considered?", 9: "Professional Statement · agreement-building analysis", 10: "Professional Statement · the professional's own observation", 11: "Professional Statement · court summary" };
export const SOURCE_OF_SECTION = { 1: "professional", 2: "system", 3: "parent", 4: "parent", 5: "system", 6: "professional", 7: "professional", 8: "professional", 9: "professional", 10: "professional", 11: "professional" };
export const SOURCE_LEGEND = [
  ["parent", "Parent-reported information", "What a parent said about their own experience, summarised neutrally. Not verified, not a finding."],
  ["system", "System-generated comparison", "Align lines up the two accounts side by side. It shows alignment and difference; it does not decide who is right."],
  ["ai", "AI-assisted draft", "Wording first drafted by an AI aid at the professional's request, then reviewed and owned by the professional."],
  ["professional", "Professional observation", "The professional's own observation, analysis and plan — the only opinion in this report."],
];
export const DISTINCTIONS = [
  ["Assessment", "finding", "A self-assessment records what a parent reports. It does not establish what happened."],
  ["Difference in perspective", "fact determination", "Two accounts can differ without either being false. This report does not resolve which is accurate."],
  ["AI summary", "professional opinion", "AI drafts only organise wording. Every judgment in this report is the professional's, after review."],
  ["Professional report", "court determination", "This report informs; it does not recommend custody, assess credibility, diagnose, or decide."],
];
export const LEGEND_CLS = { parent: "border-align-blue/40 bg-align-blue/10 text-align-blue", system: "border-brand-purple/30 bg-brand-purple/10 text-brand-purple", ai: "border-align-yellow bg-align-yellow/25 text-yellow-900", professional: "border-align-green/40 bg-align-green/10 text-green-900" };

export function SixQuestions({ anchor, compact = false, testId = "six-questions" }) {
  return (
    <div className={`rounded-lg border border-brand-purple/25 bg-white ${compact ? "p-3" : "p-4 sm:p-5"}`} data-testid={testId}>
      <p className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-widest text-brand-purple"><HelpCircle className="h-3.5 w-3.5" /> This report answers six questions</p>
      <ol className="mt-2 grid gap-1.5 sm:grid-cols-2">
        {SIX_QUESTIONS.map(([q, secs], i) => (
          <li key={q} className="flex items-start gap-2 text-sm" data-testid={`${testId}-${i + 1}`}>
            <span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-purple text-[10px] font-bold text-white">Q{i + 1}</span>
            <span>{q} <span className="text-xs text-muted-foreground">— {secs.map((n) => anchor ? <a key={n} href={`#${anchor(n)}`} className="text-brand-purple hover:underline">§{n} </a> : <span key={n}>§{n} </span>)}</span></span>
          </li>
        ))}
      </ol>
      <p className="mt-3 flex items-start gap-2 rounded-md border-l-4 border-align-green bg-align-green/10 p-2 text-sm" data-testid={`${testId}-statement`}>
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-green-900" /><span><strong>Then — clearly separated — the Professional Statement</strong> <span className="text-xs text-muted-foreground">(§9–11): the professional's own observation, analysis and court summary.</span></span>
      </p>
    </div>
  );
}

export function SourceLegend({ testId = "source-legend" }) {
  return (
    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4" data-testid={testId}>
      {SOURCE_LEGEND.map(([k, label, desc]) => (
        <div key={k} className={`rounded-md border p-2.5 ${LEGEND_CLS[k]}`} data-testid={`${testId}-${k}`}>
          <p className="text-[11px] font-bold uppercase tracking-wide">{label}</p>
          <p className="mt-1 text-xs text-foreground/80">{desc}</p>
        </div>
      ))}
    </div>
  );
}

export function Distinctions({ dark = false, testId = "distinctions" }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" data-testid={testId}>
      {DISTINCTIONS.map(([a, b, note], i) => (
        <div key={a} className={`rounded-xl border p-4 ${dark ? "border-white/20 bg-white/10 text-white" : "border-border bg-white"}`} data-testid={`${testId}-${i + 1}`}>
          <p className="text-sm font-extrabold leading-snug"><span>{a}</span> <span className={`mx-1 text-lg ${dark ? "text-align-yellow" : "text-orange-600"}`}>≠</span> <span>{b}</span></p>
          <p className={`mt-2 text-xs leading-relaxed ${dark ? "text-white/80" : "text-muted-foreground"}`}>{note}</p>
        </div>
      ))}
    </div>
  );
}

export function StatementDivider({ testId = "lens-statement-divider" }) {
  return (
    <div className="rounded-lg bg-align-green px-4 py-3 text-white" data-testid={testId} id="professional-statement">
      <p className="text-sm font-extrabold uppercase tracking-widest">Professional Statement — Sections 9 to 11</p>
      <p className="mt-1 text-xs text-white/85">From here on, the words are the professional's own observation and analysis — separate from parent-reported information (§3–4) and the system-generated comparison (§2, §5).</p>
    </div>
  );
}
