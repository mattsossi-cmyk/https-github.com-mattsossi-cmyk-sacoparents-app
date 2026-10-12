import { useEffect, useState } from "react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

export const IndividualSummaries = ({ rid, testId = "individual-summaries" }) => {
  const [d, setD] = useState(null);
  const [s, setS] = useState({ a: {}, b: {} });
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.get(`/joint/reports/${rid}/individual-summaries`).then((r) => { setD(r.data); setS({ a: {}, b: {}, ...r.data.summaries }); }).catch(() => {}); }, [rid]);
  if (!d) return null;
  const save = async () => {
    setBusy(true);
    try { const r = await api.put(`/joint/reports/${rid}/individual-summaries`, s); setS({ a: {}, b: {}, ...r.data.summaries }); toast.success("Topic summaries saved"); }
    catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  return (
    <div className="mt-6 rounded-lg border border-border bg-secondary/30 p-4" data-testid={testId}>
      <p className="text-sm font-semibold">Individual Perspective Reports — topic summaries</p>
      <p className="mt-1 text-xs text-muted-foreground">Optional. Write one neutral line per topic for each parent. Used only in the Individual Perspective Reports packet format; where blank, the report prints "Perspective provided" or "Not provided". Each parent's section never references the other parent.</p>
      <div className="mt-3 grid gap-4 md:grid-cols-2">
        {["a", "b"].map((role) => (
          <div key={role} data-testid={`${testId}-${role}`}>
            <p className="text-xs font-bold uppercase tracking-widest text-brand-purple">{d.parents[role]}</p>
            {d.topics.map((t) => (
              <label key={t.key} className="mt-2 block text-xs"><span className="font-medium">{t.area}</span>
                <input value={s[role]?.[t.key] || ""} maxLength={240} onChange={(e) => setS({ ...s, [role]: { ...s[role], [t.key]: e.target.value } })} className="mt-1 h-9 w-full rounded-md border border-input bg-white px-2 text-sm" data-testid={`${testId}-${role}-${t.key}`} />
              </label>
            ))}
          </div>
        ))}
      </div>
      <Button size="sm" className="mt-3" onClick={save} disabled={busy} data-testid={`${testId}-save`}>{busy ? "Saving…" : "Save topic summaries"}</Button>
    </div>
  );
};
