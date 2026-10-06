import { useEffect, useState } from "react";
import { BookOpen, ExternalLink } from "lucide-react";
import api from "@/lib/api";
import { PortalCard } from "@/components/JudgePortal";
import { Distinctions, SixQuestions, SourceLegend } from "@/components/ReportFraming";

export function JudgeReportGuide({ packetId }) {
  const [g, setG] = useState(null);
  const [pages, setPages] = useState(null);
  const [open, setOpen] = useState(Boolean(packetId));
  useEffect(() => { api.get("/court-dashboard/report-guide").then((r) => setG(r.data)).catch(() => {}); }, []);
  useEffect(() => { if (packetId) api.get(`/court-dashboard/packets/${packetId}/legal-report-sections`).then((r) => setPages(r.data.pages)).catch(() => setPages({})); }, [packetId]);
  if (!g) return null;
  const pdf = packetId ? `${process.env.REACT_APP_BACKEND_URL}/api/court-dashboard/packets/${packetId}/legal-report.pdf?inline=1` : null;
  return (
    <PortalCard title="How to read the Professional Report" testId="judge-report-guide" action={<button type="button" onClick={() => setOpen((v) => !v)} className="text-xs font-medium text-brand-purple hover:underline" data-testid="judge-report-guide-toggle">{open ? "Hide" : "Show guide"}</button>}>
      <p className="text-sm text-muted-foreground flex items-start gap-2"><BookOpen className="h-4 w-4 mt-0.5 shrink-0 text-brand-purple" /> {g.intro}</p>
      {open && (
        <>
          <div className="mt-3 space-y-3">
            <SixQuestions compact testId="judge-six-questions" />
            <SourceLegend testId="judge-source-legend" />
          </div>
          {pdf && <p className="mt-3 text-xs text-brand-purple" data-testid="judge-report-guide-jump-hint">Click a section to open the attached report at that page.</p>}
          <ol className="mt-3 space-y-1.5">
            {g.sections.map((s) => {
              const page = pages?.[s.n];
              const body = <span><span className="font-semibold">{s.title}</span>{s.question && <span className="ml-1 text-muted-foreground italic">({s.question})</span>} — {s.what} <span className="text-amber-800">Guardrail: {s.guardrail}</span></span>;
              return (
                <li key={s.n} className="flex items-start gap-2 text-xs" data-testid={`judge-report-guide-${s.n}`}>
                  <span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-purple text-[10px] font-bold text-white">{s.n}</span>
                  {pdf && page ? <a href={`${pdf}#page=${page}`} target="_blank" rel="noreferrer" className="hover:underline inline-flex items-start gap-1" data-testid={`judge-report-guide-jump-${s.n}`}>{body}<span className="shrink-0 text-brand-purple whitespace-nowrap">p.{page} <ExternalLink className="inline h-3 w-3" /></span></a> : body}
                </li>
              );
            })}
          </ol>
          <p className="mt-3 rounded-md bg-teal-50 p-2 text-xs text-teal-900" data-testid="judge-report-guide-scale">{g.scale}</p>
          <p className="mt-4 text-xs font-bold uppercase tracking-widest text-brand-purple">Four distinctions to keep in mind</p>
          <div className="mt-2"><Distinctions testId="judge-distinctions" /></div>
        </>
      )}
    </PortalCard>
  );
}
