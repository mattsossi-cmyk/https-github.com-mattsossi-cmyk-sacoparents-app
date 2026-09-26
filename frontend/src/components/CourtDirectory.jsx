import { useEffect, useState } from "react";
import { BookUser, CheckCircle2, Clock } from "lucide-react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { PortalCard } from "@/components/JudgePortal";

const fmt = (s) => (s ? String(s).slice(0, 10) : null);

export function CourtDirectory() {
  const [data, setData] = useState(null);
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  useEffect(() => { if (open && !data) api.get("/court-dashboard/providers").then((r) => setData(r.data)).catch(() => setData({ providers: [] })); }, [open, data]);
  const list = (data?.providers || []).filter((p) => !q || `${p.name} ${p.specialty} ${p.organization}`.toLowerCase().includes(q.toLowerCase()));
  const groups = list.reduce((acc, p) => { (acc[p.specialty || "Other"] ||= []).push(p); return acc; }, {});
  return (
    <div className="mb-6" data-testid="court-directory">
      <PortalCard title="Resource Provider Directory" testId="court-directory-card" action={<Button size="sm" variant="ghost" onClick={() => setOpen((v) => !v)} data-testid="court-directory-toggle">{open ? "Hide" : "Browse"}</Button>}>
        <p className="text-sm text-muted-foreground flex items-start gap-2"><BookUser className="h-4 w-4 mt-0.5 shrink-0" /> Read-only list of the parenting facilitators, evaluators, supervised-exchange and safety resources professionals reference in their reports, with the date each listing's contact details were last verified.</p>
        {open && (
          <div className="mt-4">
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search name, specialty or organization" className="h-9 w-full max-w-sm rounded-md border border-input px-3 text-sm" data-testid="court-directory-search" />
            {!data ? <p className="mt-3 text-sm text-muted-foreground">Loading…</p> : Object.keys(groups).length === 0 ? <p className="mt-3 text-sm text-muted-foreground" data-testid="court-directory-empty">No providers match.</p> : Object.entries(groups).map(([spec, items]) => (
              <div key={spec} className="mt-4">
                <p className="text-xs font-bold uppercase tracking-widest text-brand-purple">{spec}</p>
                <ul className="mt-2 grid gap-2 md:grid-cols-2">
                  {items.map((p) => (
                    <li key={p.id} className="rounded-lg border border-border bg-white p-3 text-sm" data-testid={`court-provider-${p.id}`}>
                      <p className="font-semibold">{p.name}</p>
                      {p.organization && <p className="text-muted-foreground">{p.organization}</p>}
                      <p className="mt-1 text-xs">{[p.phone, p.email].filter(Boolean).join(" · ")}{p.website && <> · <a href={/^https?:/.test(p.website) ? p.website : `https://${p.website}`} target="_blank" rel="noreferrer" className="text-brand-purple underline break-all">{p.website}</a></>}</p>
                      <p className={`mt-2 flex items-center gap-1 text-[11px] ${fmt(p.last_verified_at) ? (p.contact_verified ? "text-align-green" : "text-amber-700") : "text-muted-foreground"}`} data-testid={`court-provider-verified-${p.id}`}>
                        {fmt(p.last_verified_at) ? <><CheckCircle2 className="h-3.5 w-3.5" /> Contact details {p.contact_verified ? "verified" : "checked"} {fmt(p.last_verified_at)}</> : <><Clock className="h-3.5 w-3.5" /> Not yet verified</>}
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
            {data?.note && <p className="mt-4 text-[11px] italic text-muted-foreground" data-testid="court-directory-note">{data.note}</p>}
          </div>
        )}
      </PortalCard>
    </div>
  );
}
