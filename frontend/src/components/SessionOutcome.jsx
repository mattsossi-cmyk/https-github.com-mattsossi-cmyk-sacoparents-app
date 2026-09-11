import { useEffect, useState } from "react";
import { toast } from "sonner";
import { CheckSquare, Square } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export function SessionOutcome({ rid, steps, initial, onSaved }) {
  const [chosen, setChosen] = useState(initial?.chosen_steps || []);
  const [summary, setSummary] = useState(initial?.summary || "");
  const [saving, setSaving] = useState(false);

  useEffect(() => { setChosen(initial?.chosen_steps || []); setSummary(initial?.summary || ""); }, [initial]);

  const toggle = (s) => setChosen((c) => (c.includes(s) ? c.filter((x) => x !== s) : [...c, s]));
  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.put(`/joint/reports/${rid}/session-outcome`, { chosen_steps: chosen, summary });
      toast.success("Session outcome saved to the case record");
      onSaved?.(data.session_outcome);
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setSaving(false); }
  };

  const all = Array.from(new Set([...(steps || []), ...chosen]));
  return (
    <section className="bg-white border border-border rounded-lg p-6 md:col-span-2" data-testid="session-outcome-section">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold" data-testid="session-outcome-heading">Post-Session Outcome</h2>
        {initial?.recorded_at && <span className="text-xs text-muted-foreground" data-testid="session-outcome-recorded">Last saved {initial.recorded_at.slice(0, 16).replace("T", " ")}</span>}
      </div>
      <p className="text-sm text-muted-foreground mt-1">Tick the next steps the parents chose together. Saved to the case record and lifecycle log — never shown to parents.</p>
      <ul className="mt-4 grid sm:grid-cols-2 gap-2" data-testid="session-outcome-steps">
        {all.map((s) => {
          const on = chosen.includes(s);
          return (
            <li key={s}>
              <button type="button" onClick={() => toggle(s)} aria-pressed={on} className={`w-full flex items-start gap-2.5 rounded-md border px-3 py-2.5 text-left text-sm transition-colors ${on ? "border-align-green bg-align-green/10" : "border-border hover:border-primary/40"}`} data-testid={`session-outcome-step-${all.indexOf(s)}`}>
                {on ? <CheckSquare className="h-4 w-4 shrink-0 mt-0.5 text-align-green" /> : <Square className="h-4 w-4 shrink-0 mt-0.5 text-muted-foreground" />}
                <span>{s}</span>
              </button>
            </li>
          );
        })}
      </ul>
      <Textarea value={summary} onChange={(e) => setSummary(e.target.value)} placeholder="Optional: what the parents agreed to try before the next session…" className="mt-4 min-h-[80px]" data-testid="session-outcome-summary" />
      <div className="mt-3 flex items-center gap-3">
        <Button size="sm" onClick={save} disabled={saving} data-testid="session-outcome-save-btn">{saving ? "Saving…" : "Save outcome"}</Button>
        <span className="text-xs text-muted-foreground" data-testid="session-outcome-count">{chosen.length} step{chosen.length === 1 ? "" : "s"} chosen</span>
      </div>
    </section>
  );
}
