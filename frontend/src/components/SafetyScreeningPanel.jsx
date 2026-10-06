import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { ShieldCheck, Lock } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

export function SafetyScreeningPanel({ rid }) {
  const [d, setD] = useState(null);
  const load = () => api.get(`/joint/reports/${rid}/safety-screening`).then((r) => setD(r.data)).catch(() => setD(null));
  useEffect(() => { load(); }, [rid]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!d) return null;
  const assign = async (role, version) => { try { await api.put(`/joint/reports/${rid}/safety-screening/assign`, { role, version }); toast.success(`Version ${version} assigned`); load(); } catch (e) { toast.error(formatApiError(e)); } };
  const mine = d.my_role ? d.roles[d.my_role] : null;
  return (
    <div className="mt-5 pt-4 border-t border-border" data-testid="safety-screening-panel">
      <p className="flex items-center gap-1.5 text-sm font-semibold"><ShieldCheck className="h-4 w-4 text-brand-purple" /> Private safety screening <span className="text-xs font-normal text-muted-foreground">— screening questions, not a diagnostic tool</span></p>
      {mine && !d.is_professional && (
        <div className="mt-2 text-sm" data-testid="safety-screening-mine">
          {mine.received ? <p data-testid="safety-screening-mine-done">Your screening was received privately. Only your professional can see your answers.</p>
            : (mine.version || mine.choice_needed) ? <Link to={`/joint/${rid}/safety-screening`}><Button size="sm" variant="outline" data-testid="safety-screening-start-btn">Complete my private safety screening</Button></Link>
            : <p className="text-muted-foreground" data-testid="safety-screening-mine-unassigned">Your professional will assign your screening shortly.</p>}
        </div>
      )}
      {d.is_professional && (
        <div className="mt-2 grid gap-2 sm:grid-cols-2">
          {["a", "b"].map((role) => { const s = d.roles[role]; return (
            <div key={role} className={`rounded-md border p-3 text-sm ${s.tier === 3 ? "border-amber-300 bg-amber-50" : "border-border bg-white"}`} data-testid={`safety-screening-${role}`}>
              <p className="font-semibold">{s.name}</p>
              <p className="text-xs" data-testid={`safety-screening-${role}-status`}>{s.received ? `Received · ${s.version_label} · ${(s.completed_at || "").slice(0, 10)}` : "Not Received"}</p>
              {s.received && <p className="text-xs font-medium" data-testid={`safety-screening-${role}-tier`}>{s.tier_label}</p>}
              {!s.received && s.reminded_at && <p className="text-[11px] text-amber-800" data-testid={`safety-screening-${role}-reminded`}>Reminder sent {new Date(s.reminded_at).toLocaleDateString()} · no response yet</p>}
              {!s.received && !s.reminded_at && <p className="text-[11px] text-muted-foreground" data-testid={`safety-screening-${role}-not-reminded`}>No reminder sent yet (automatic nudge 7 days after joining)</p>}
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <label className="text-xs text-muted-foreground">Version
                  <select value={s.version || ""} onChange={(e) => assign(role, e.target.value)} className={`ml-1 h-7 rounded-md border px-1 text-xs ${s.needs_assignment ? "border-amber-400 bg-amber-50" : "border-input bg-white"}`} data-testid={`safety-screening-${role}-version`}>
                    <option value="" disabled>{s.needs_assignment ? "Assign a version…" : "—"}</option>
                    {Object.entries(d.versions).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
                  </select>
                </label>
                {s.needs_assignment && <span className="text-[11px] text-amber-800" data-testid={`safety-screening-${role}-needs-assignment`}>Gender not recorded — assign a version, or the parent may choose on their intro screen.</span>}
                {s.chosen_by_parent && <span className="text-[11px] text-muted-foreground" data-testid={`safety-screening-${role}-chosen`}>Chosen by parent</span>}
                {s.received && <Link to={`/joint/${rid}/safety-screening/${role}`} className="inline-flex items-center gap-1 text-xs font-semibold text-brand-purple hover:underline" data-testid={`safety-screening-${role}-view`}><Lock className="h-3 w-3" /> View responses (logged)</Link>}
              </div>
            </div>); })}
        </div>
      )}
      <p className="mt-2 text-[11px] text-muted-foreground">{d.scale_note}</p>
    </div>
  );
}
