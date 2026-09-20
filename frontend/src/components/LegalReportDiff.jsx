import { useEffect, useState } from "react";
import { GitCompareArrows } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { toast } from "sonner";

export function LegalReportDiff({ rid, versions }) {
  const [from, setFrom] = useState(versions.length > 1 ? versions[versions.length - 2].version : versions[0]?.version);
  const [to, setTo] = useState(versions.length > 1 ? versions[versions.length - 1].version : 0);
  const [d, setD] = useState(null);
  useEffect(() => {
    if (!from) return;
    api.get(`/professional-legal-reports/${rid}/diff`, { params: { from_version: from, to_version: to } }).then((r) => setD(r.data)).catch((e) => toast.error(formatApiError(e)));
  }, [rid, from, to]);
  if (!versions.length) return null;
  const opts = versions.map((v) => <option key={v.version} value={v.version}>v{v.version} · {v.finalized_at?.slice(0, 10)}</option>);
  return (
    <section className="bg-white border border-border rounded-lg p-6" data-testid="legal-diff">
      <h2 className="text-lg font-semibold flex items-center gap-2"><GitCompareArrows className="h-5 w-5 text-brand-purple" /> What changed between versions</h2>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
        <select value={from} onChange={(e) => setFrom(Number(e.target.value))} className="h-9 rounded-md border border-input bg-white px-2" data-testid="legal-diff-from">{opts}</select>
        <span className="text-muted-foreground">→</span>
        <select value={to} onChange={(e) => setTo(Number(e.target.value))} className="h-9 rounded-md border border-input bg-white px-2" data-testid="legal-diff-to"><option value={0}>Current working copy</option>{opts}</select>
        <span className="ml-auto text-xs text-muted-foreground"><span className="rounded bg-green-100 px-1 text-green-900">added</span> <span className="rounded bg-red-100 px-1 line-through text-red-900">removed</span></span>
      </div>
      {d && (d.changes.length === 0 ? <p className="mt-4 text-sm italic text-muted-foreground" data-testid="legal-diff-empty">No differences between these versions.</p> : (
        <div className="mt-4 space-y-4">
          {d.changes.map((c) => (
            <div key={c.key} data-testid={`legal-diff-${c.key}`}>
              <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{c.label}</p>
              {c.kind === "text" ? <p className="mt-1 text-sm leading-relaxed">{c.segments.map((s, i) => s.op === "equal" ? <span key={i}>{s.text} </span> : s.op === "insert" ? <mark key={i} className="rounded bg-green-100 px-0.5 text-green-900">{s.text} </mark> : <del key={i} className="rounded bg-red-100 px-0.5 text-red-900">{s.text} </del>)}</p>
                : <ul className="mt-1 text-sm space-y-0.5">{c.added.map((x) => <li key={`a${x}`} className="rounded bg-green-100 px-1 inline-block mr-1 text-green-900">+ {x}</li>)}{c.removed.map((x) => <li key={`r${x}`} className="rounded bg-red-100 px-1 inline-block mr-1 line-through text-red-900">− {x}</li>)}</ul>}
            </div>
          ))}
        </div>
      ))}
    </section>
  );
}
