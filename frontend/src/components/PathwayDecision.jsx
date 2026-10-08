import { useState } from "react";
import { toast } from "sonner";
import { Route } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

export function PathwayDecision({ rid, role, pathway, onChange }) {
  const [choice, setChoice] = useState(pathway.suggested.pathway);
  const [busy, setBusy] = useState(false);
  const dec = pathway.decision;
  const act = async (action) => {
    setBusy(true);
    try { const { data } = await api.put(`/joint/reports/${rid}/safety-pathway/${role}`, { action, pathway: action === "change" ? choice : undefined }); onChange(data); toast.success(action === "dismiss" ? "Suggestion dismissed" : `Pathway confirmed: ${data.label}`); } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  return (
    <div className="rounded-lg border border-[#3D1A78]/25 bg-white p-4 space-y-3" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }} data-testid="pathway-decision">
      <p className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-widest text-[#3D1A78]"><Route className="h-3.5 w-3.5" /> Safety pathway — suggested flag, you decide</p>
      <p className="text-sm"><span className="font-semibold" data-testid="pathway-suggested-label">{pathway.suggested.label}</span>
        {pathway.suggested.triggered_labels?.length > 0 && <span className="text-xs text-muted-foreground" data-testid="pathway-triggered"> · triggered by: {pathway.suggested.triggered_labels.join(", ")}</span>}</p>
      <p className="text-xs text-muted-foreground">{pathway.note}</p>
      {dec && <p className={`rounded-md p-2 text-xs ${dec.status === "confirmed" ? "bg-[#3D1A78]/10 text-[#3D1A78]" : "bg-secondary text-muted-foreground"}`} data-testid="pathway-decision-status">
        {dec.status === "confirmed" ? `Confirmed: ${dec.label || dec.confirmed}` : "Suggestion dismissed — no pathway shown in the report"} · {new Date(dec.at).toLocaleString()}</p>}
      <div className="flex flex-wrap items-center gap-2">
        <Button size="sm" disabled={busy} onClick={() => act("confirm")} className="bg-[#3D1A78] hover:bg-[#3D1A78]/90" data-testid="pathway-confirm-btn">Confirm suggestion</Button>
        <select value={choice} onChange={(e) => setChoice(e.target.value)} className="h-9 rounded-md border border-input bg-white px-2 text-xs" data-testid="pathway-change-select">
          {pathway.options.map((o) => <option key={o.key} value={o.key}>{o.label}</option>)}
        </select>
        <Button size="sm" variant="outline" disabled={busy} onClick={() => act("change")} data-testid="pathway-change-btn">Confirm selected</Button>
        <Button size="sm" variant="ghost" disabled={busy} onClick={() => act("dismiss")} data-testid="pathway-dismiss-btn">Dismiss</Button>
      </div>
    </div>
  );
}
