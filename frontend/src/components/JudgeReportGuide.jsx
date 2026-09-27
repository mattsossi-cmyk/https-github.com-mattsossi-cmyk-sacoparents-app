import { useEffect, useState } from "react";
import { BookOpen } from "lucide-react";
import api from "@/lib/api";
import { PortalCard } from "@/components/JudgePortal";

export function JudgeReportGuide() {
  const [g, setG] = useState(null);
  const [open, setOpen] = useState(false);
  useEffect(() => { api.get("/court-dashboard/report-guide").then((r) => setG(r.data)).catch(() => {}); }, []);
  if (!g) return null;
  return (
    <PortalCard title="How to read the Professional Report" testId="judge-report-guide" action={<button type="button" onClick={() => setOpen((v) => !v)} className="text-xs font-medium text-brand-purple hover:underline" data-testid="judge-report-guide-toggle">{open ? "Hide" : "Show guide"}</button>}>
      <p className="text-sm text-muted-foreground flex items-start gap-2"><BookOpen className="h-4 w-4 mt-0.5 shrink-0 text-brand-purple" /> {g.intro}</p>
      {open && (
        <>
          <ol className="mt-3 space-y-1.5">
            {g.sections.map((s) => (
              <li key={s.n} className="flex items-start gap-2 text-xs" data-testid={`judge-report-guide-${s.n}`}>
                <span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-purple text-[10px] font-bold text-white">{s.n}</span>
                <span><span className="font-semibold">{s.title}</span> — {s.what} <span className="text-amber-800">Guardrail: {s.guardrail}</span></span>
              </li>
            ))}
          </ol>
          <p className="mt-3 rounded-md bg-teal-50 p-2 text-xs text-teal-900" data-testid="judge-report-guide-scale">{g.scale}</p>
        </>
      )}
    </PortalCard>
  );
}
