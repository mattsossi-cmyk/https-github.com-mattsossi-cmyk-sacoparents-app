import { useEffect, useState } from "react";
import { toast } from "sonner";
import { BellRing, CalendarDays } from "lucide-react";
import api, { formatApiError } from "@/lib/api";

const OPTIONS = [
  ["daily", "Daily", "Every morning at 8am Central"],
  ["weekly", "Weekly", "Mondays only"],
  ["off", "Off", "No digest emails"],
];

export function DigestPreference() {
  const [prefs, setPrefs] = useState(null);

  useEffect(() => { api.get("/me/preferences").then((r) => setPrefs(r.data)).catch(() => setPrefs({ digest_frequency: "daily", weekly_summary: true })); }, []);

  const save = async (patch, msg) => {
    const prev = prefs;
    setPrefs({ ...prefs, ...patch });
    try {
      await api.put("/me/preferences", patch);
      toast.success(msg);
    } catch (e) { setPrefs(prev); toast.error(formatApiError(e)); }
  };
  const value = prefs?.digest_frequency;
  const weekly = prefs?.weekly_summary;

  return (
    <div className="bg-white border border-border rounded-lg px-4 py-3 space-y-3" data-testid="digest-preference">
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <div className="flex items-center gap-2 text-sm"><BellRing className="h-4 w-4 text-brand-teal" /><span className="font-medium">Expiring-invitation digest</span></div>
        <div className="flex gap-1.5 flex-wrap" role="radiogroup" aria-label="Digest frequency">
          {OPTIONS.map(([k, label, hint]) => (
            <button key={k} type="button" role="radio" aria-checked={value === k} title={hint} disabled={!prefs}
              onClick={() => value !== k && save({ digest_frequency: k }, k === "off" ? "Expiry digest turned off" : `Expiry digest set to ${k}`)}
              className={`text-xs font-medium rounded-full px-3 py-1.5 border transition-colors ${value === k ? "bg-primary text-white border-primary" : "bg-white border-border hover:border-primary/50"}`}
              data-testid={`digest-option-${k}`}>{label}</button>
          ))}
        </div>
        <p className="text-xs text-muted-foreground sm:ml-auto" data-testid="digest-preference-hint">{OPTIONS.find(([k]) => k === value)?.[2] || "Loading…"}</p>
      </div>
      <div className="flex flex-col sm:flex-row sm:items-center gap-3 border-t border-border pt-3">
        <div className="flex items-center gap-2 text-sm"><CalendarDays className="h-4 w-4 text-brand-teal" /><span className="font-medium">Monday caseload summary</span></div>
        <button type="button" role="switch" aria-checked={!!weekly} disabled={!prefs}
          onClick={() => save({ weekly_summary: !weekly }, !weekly ? "Weekly caseload summary turned on" : "Weekly caseload summary turned off")}
          className={`text-xs font-medium rounded-full px-3 py-1.5 border transition-colors ${weekly ? "bg-primary text-white border-primary" : "bg-white border-border hover:border-primary/50"}`}
          data-testid="weekly-summary-toggle">{weekly ? "On" : "Off"}</button>
        <p className="text-xs text-muted-foreground sm:ml-auto" data-testid="weekly-summary-hint">{weekly ? "Every Monday: status of every active matter" : "No weekly overview email"}</p>
      </div>
    </div>
  );
}
