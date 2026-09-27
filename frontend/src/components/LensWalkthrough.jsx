import { useEffect, useState } from "react";
import { HelpCircle, ShieldCheck, X } from "lucide-react";
import api from "@/lib/api";

const KEY = "lens-walkthrough-open";

export function SectionGuide({ ns, guides }) {
  const items = (guides || []).filter((x) => ns.includes(x.n));
  const [open, setOpen] = useState(false);
  if (!items.length) return null;
  const key = ns.join("-");
  return (
    <div className="mb-2" data-testid={`lens-guide-${key}`}>
      <button type="button" onClick={() => setOpen((v) => !v)} className="inline-flex items-center gap-1 text-xs font-medium text-brand-purple hover:underline" data-testid={`lens-guide-toggle-${key}`}>
        <HelpCircle className="h-3.5 w-3.5" /> {open ? "Hide guide" : "How to complete this section"}
      </button>
      {open && items.map((g) => (
        <div key={g.n} className="mt-2 rounded-md border border-brand-purple/20 bg-[#f8f4fc] p-3 text-xs leading-relaxed" data-testid={`lens-guide-body-${g.n}`}>
          <p className="font-semibold text-brand-purple">PDF section {g.n} · {g.title}</p>
          <p className="mt-1"><span className="font-semibold">What this section is:</span> {g.what}</p>
          <p className="mt-1"><span className="font-semibold">How to complete it:</span> {g.how}</p>
          <p className="mt-1 flex items-start gap-1 text-amber-800"><ShieldCheck className="h-3.5 w-3.5 mt-0.5 shrink-0" /><span><span className="font-semibold">Neutrality guardrail:</span> {g.guardrail}</span></p>
        </div>
      ))}
    </div>
  );
}

export function useWalkthrough(caseId) {
  const [guides, setGuides] = useState([]);
  useEffect(() => { if (caseId) api.get(`/cases/${caseId}/professional-report/walkthrough`).then((r) => setGuides(r.data)).catch(() => {}); }, [caseId]);
  return guides;
}

export function WalkthroughOverview({ guides, done, anchor }) {
  const [open, setOpen] = useState(() => localStorage.getItem(KEY) !== "0");
  const toggle = () => { localStorage.setItem(KEY, open ? "0" : "1"); setOpen(!open); };
  if (!guides?.length) return null;
  const finished = guides.filter((g) => done?.(g.n)).length;
  return (
    <section className="rounded-lg border border-brand-purple/30 bg-white p-4" data-testid="lens-walkthrough">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-semibold text-brand-purple">Report walk-through <span className="ml-2 rounded-full bg-brand-purple/10 px-2 py-0.5 text-[11px]" data-testid="lens-walkthrough-progress">{finished}/{guides.length} sections have content</span></p>
        <button type="button" onClick={toggle} className="text-xs text-muted-foreground hover:text-foreground" data-testid="lens-walkthrough-toggle">{open ? <X className="h-4 w-4" /> : "Show"}</button>
      </div>
      {open && (
        <ol className="mt-3 grid gap-1.5 sm:grid-cols-2 lg:grid-cols-3">
          {guides.map((g) => (
            <li key={g.n} className="flex items-start gap-2 text-xs" data-testid={`lens-walkthrough-step-${g.n}`}>
              <span className={`mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${done?.(g.n) ? "bg-align-green text-white" : "bg-brand-purple text-white"}`}>{done?.(g.n) ? "✓" : g.n}</span>
              <a href={`#${anchor ? anchor(g.n) : ""}`} className="hover:underline"><span className="font-medium">{g.title}</span> <span className="text-muted-foreground">— {g.what}</span></a>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
