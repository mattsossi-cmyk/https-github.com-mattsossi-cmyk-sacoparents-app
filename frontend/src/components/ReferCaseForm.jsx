import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Send } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

const EMPTY = { professional_id: "", cause_number: "", court_name: "", child_initials: "", parent_a_name: "", parent_a_email: "", parent_b_name: "", parent_b_email: "", note: "", subject: "co_parenting", hearing_date: "", requested_reports: ["co_parenting"] };

const REPORT_TYPES = [
  ["co_parenting", "Co-Parenting Joint Report"], ["education", "Educational Joint Report"], ["medical", "Medical Joint Report"],
  ["psychological", "Psychological Joint Report"], ["agreement", "Co-Parenting Agreement"], ["family_violence", "Family Violence / Safety Assessment"],
];

export function ReferCaseForm({ defaultCourt, onCreated }) {
  const [pros, setPros] = useState([]);
  const [form, setForm] = useState({ ...EMPTY, court_name: defaultCourt || "" });
  const [busy, setBusy] = useState(false);
  const [q, setQ] = useState("");

  useEffect(() => { api.get("/court-dashboard/professionals").then((r) => setPros(r.data)).catch(() => {}); }, []);

  const send = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/court-dashboard/referrals", form);
      toast.success(`Referred Cause No. ${data.cause_number} to ${data.professional_name}`);
      setForm({ ...EMPTY, court_name: defaultCourt || "" }); onCreated?.(data);
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  const shown = pros.filter((p) => !q || `${p.name} ${p.pro_role} ${p.organization} ${p.city}`.toLowerCase().includes(q.toLowerCase()));
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const toggleReport = (k) => setForm((f) => {
    const next = f.requested_reports.includes(k) ? f.requested_reports.filter((x) => x !== k) : [...f.requested_reports, k];
    const first = next.find((x) => !["agreement", "family_violence"].includes(x)) || (next.includes("family_violence") ? "safety" : "co_parenting");
    return { ...f, requested_reports: next, subject: first };
  });
  return (
    <section className="bg-white border-2 border-brand-purple/30 rounded-xl p-6" data-testid="refer-case-form">
      <h2 className="text-lg font-semibold flex items-center gap-2"><Send className="h-4 w-4 text-brand-purple" /> Refer Case to Professional</h2>
      <p className="text-sm text-muted-foreground mt-1">The professional invites both parents, guides the process, and submits the Joint Report with a Professional Statement back to you. The court never contacts parents through Align.</p>
      <div className="mt-5 grid sm:grid-cols-2 gap-3">
        <Input placeholder="Cause number *" value={form.cause_number} onChange={set("cause_number")} data-testid="refer-cause-number" />
        <Input placeholder="Court" value={form.court_name} onChange={set("court_name")} data-testid="refer-court-name" />
        <Input placeholder="Child initials (e.g. E.T.)" value={form.child_initials} onChange={set("child_initials")} data-testid="refer-child-initials" />
        <fieldset className="sm:col-span-2 rounded-md border border-input bg-white p-3" data-testid="refer-report-types">
          <legend className="px-1 text-xs font-bold uppercase tracking-wider text-muted-foreground">Reports requested from the professional</legend>
          <div className="grid gap-1.5 sm:grid-cols-3">
            {REPORT_TYPES.map(([k, l]) => (
              <label key={k} className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.requested_reports.includes(k)} onChange={() => toggleReport(k)} data-testid={`refer-report-${k}`} />
                {l}
              </label>
            ))}
          </div>
          <p className="mt-2 text-xs text-muted-foreground">The professional sends the matching assessments to both parents and returns each Joint Report with a Professional Statement.</p>
        </fieldset>
        <Input placeholder="Parent A name (optional)" value={form.parent_a_name} onChange={set("parent_a_name")} data-testid="refer-parent-a-name" />
        <Input placeholder="Parent A email (optional)" value={form.parent_a_email} onChange={set("parent_a_email")} data-testid="refer-parent-a-email" />
        <Input placeholder="Parent B name (optional)" value={form.parent_b_name} onChange={set("parent_b_name")} data-testid="refer-parent-b-name" />
        <Input placeholder="Parent B email (optional)" value={form.parent_b_email} onChange={set("parent_b_email")} data-testid="refer-parent-b-email" />
        <label className="flex items-center gap-2 text-sm text-muted-foreground sm:col-span-2"><span className="shrink-0">Hearing date (optional — reminders go out one week before if not yet submitted)</span><Input type="date" value={form.hearing_date} onChange={set("hearing_date")} className="h-10 max-w-[200px]" data-testid="refer-hearing-date" /></label>
      </div>
      <Textarea placeholder="Note to the professional (scope, deadlines)…" value={form.note} onChange={set("note")} className="mt-3 min-h-[70px]" data-testid="refer-note" />
      <div className="mt-4">
        <div className="flex items-center justify-between gap-3"><p className="text-sm font-medium">Choose an approved professional *</p><Input placeholder="Search name, role, city…" value={q} onChange={(e) => setQ(e.target.value)} className="h-8 max-w-[220px] text-xs" data-testid="refer-pro-search" /></div>
        <ul className="mt-2 max-h-56 overflow-y-auto divide-y divide-border rounded-md border border-border" data-testid="refer-pro-list">
          {shown.length === 0 && <li className="px-3 py-3 text-sm text-muted-foreground">No approved professionals match.</li>}
          {shown.map((p) => (
            <li key={p.id}>
              <button type="button" onClick={() => setForm({ ...form, professional_id: p.id })} className={`w-full text-left px-3 py-2 text-sm flex items-center justify-between gap-2 ${form.professional_id === p.id ? "bg-brand-purple/10" : "hover:bg-secondary/60"}`} data-testid={`refer-pro-option-${p.id}`}>
                <span><span className="font-medium">{p.name}</span> <span className="text-muted-foreground">· {[p.pro_role, p.organization, [p.city, p.state].filter(Boolean).join(", ")].filter(Boolean).join(" · ")}</span></span>
                {p.credentials_verified && <span className="text-[10px] font-semibold text-accent shrink-0">VERIFIED</span>}
              </button>
            </li>
          ))}
        </ul>
      </div>
      <Button onClick={send} disabled={busy || !form.professional_id || !form.cause_number.trim() || form.requested_reports.length === 0} className="mt-4 bg-brand-purple hover:bg-brand-purple/90 text-white" data-testid="refer-submit-btn">{busy ? "Sending…" : "Send referral"}</Button>
    </section>
  );
}
