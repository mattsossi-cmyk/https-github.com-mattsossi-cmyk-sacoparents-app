import { useEffect, useState } from "react";
import { toast } from "sonner";
import { FileSignature, Download, Lock, ShieldCheck } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { CaseProgress } from "@/components/CaseProgress";

const FIELDS = [
  ["role_basis", "Role and basis of involvement", "How you came to facilitate this matter (court referral, appointment, parties' agreement) and your professional role."],
  ["process_summary", "Process completed by the parents", "What each parent completed independently and how the Joint Alignment Report was produced."],
  ["observations", "Observations of alignment and differences", "Neutral observations from the report and any facilitated conversation. Use both parents' own framing where possible."],
  ["safety_considerations", "Safety considerations (optional)", "Any safety-related process notes in neutral language. Leave blank if none."],
  ["next_steps", "Recommended next steps for facilitation", "Facilitation steps only — no recommendations about conservatorship or possession."],
];

export function ProfessionalStatement({ rid, canSubmit, onStageChange }) {
  const [data, setData] = useState(null);
  const [st, setSt] = useState({});
  const [busy, setBusy] = useState(false);
  const [attest, setAttest] = useState(false);

  const load = () => { api.get(`/joint/reports/${rid}/professional-statement`).then((r) => { setData(r.data); setSt(r.data.statement); onStageChange?.(r.data.stage); }).catch(() => {}); };
  useEffect(() => { load(); }, [rid]);

  const save = async (status) => {
    setBusy(true);
    try {
      const { data: d } = await api.put(`/joint/reports/${rid}/professional-statement`, { ...st, status });
      setSt(d.statement); setData((x) => ({ ...x, statement: d.statement, stage: d.stage })); onStageChange?.(d.stage);
      toast.success(status === "ready" ? "Professional Statement marked ready" : "Draft saved");
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };
  const submit = async () => {
    if (!window.confirm("Submit the Joint Report and Professional Statement to the court? Both documents will be locked, timestamped and placed in the Judge Portal.")) return;
    setBusy(true);
    try {
      const { data: d } = await api.post(`/joint/reports/${rid}/submit-to-court`, { attest });
      toast.success(`Submitted to court — version ${d.submission.version} locked`);
      setAttest(false); load();
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  if (!data) return null;
  const court = data.court;
  const ready = st.status === "ready";
  const subs = data.submissions || [];
  const submittable = court?.judge_email && canSubmit && ready;
  return (
    <section className="bg-white border border-border rounded-lg p-6 md:col-span-2" data-testid="professional-statement-section">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold flex items-center gap-2"><FileSignature className="h-4 w-4" /> Professional Assessment Statement</h2>
          <p className="text-sm text-muted-foreground mt-1">Your letterhead statement to accompany the Joint Report. Neutral facilitation language only; the system blocks custody recommendations.</p>
        </div>
        {court?.judge_email && <div className="text-right text-xs text-muted-foreground" data-testid="statement-court-info"><p className="font-semibold text-foreground">{court.court_name || "Court"}</p><p>Cause No. {court.cause_number} · {court.judge_name}</p></div>}
      </div>
      <CaseProgress stage={data.stage} />
      <div className="mt-5 grid gap-4">
        {FIELDS.map(([k, label, hint]) => (
          <label key={k} className="block text-sm">
            <span className="font-medium">{label}</span>
            <span className="block text-xs text-muted-foreground">{hint}</span>
            <Textarea value={st[k] || ""} onChange={(e) => setSt({ ...st, [k]: e.target.value })} className="mt-1.5 min-h-[88px]" disabled={subs.length > 0 && ready && false} data-testid={`statement-${k}`} />
          </label>
        ))}
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Button size="sm" variant="outline" onClick={() => save("draft")} disabled={busy} data-testid="statement-save-draft-btn">Save draft</Button>
        <Button size="sm" onClick={() => save("ready")} disabled={busy} data-testid="statement-mark-ready-btn">{ready ? "Update & keep ready" : "Mark statement ready"}</Button>
        {st.version && <Button size="sm" variant="ghost" asChild data-testid="statement-pdf-btn"><a href={`${process.env.REACT_APP_BACKEND_URL}/api/joint/reports/${rid}/professional-statement.pdf`} download><Download className="h-4 w-4 mr-1" /> Statement PDF</a></Button>}
        {st.updated_at && <span className="text-xs text-muted-foreground" data-testid="statement-status">{ready ? "Ready" : "Draft"} · v{st.version} · saved {st.updated_at.slice(0, 16).replace("T", " ")}</span>}
      </div>

      {court?.judge_email ? (
        <div className="mt-8 rounded-xl border-2 border-brand-purple/30 bg-brand-purple/5 p-5" data-testid="submit-to-court-box">
          <label className="flex items-start gap-2 text-sm cursor-pointer" data-testid="submit-attest-label">
            <input type="checkbox" checked={attest} onChange={(e) => setAttest(e.target.checked)} className="mt-1" disabled={!submittable} data-testid="submit-attest" />
            <span>{data.attestation_text}</span>
          </label>
          <Button onClick={submit} disabled={!submittable || !attest || busy} className="mt-4 w-full h-14 text-base font-bold tracking-wide bg-brand-purple hover:bg-brand-purple/90 text-white" data-testid="submit-to-court-btn">
            <Lock className="h-5 w-5 mr-2" /> {busy ? "Submitting…" : "SUBMIT JOINT REPORT + PROFESSIONAL STATEMENT TO COURT"}
          </Button>
          {!submittable && <p className="mt-2 text-xs text-muted-foreground" data-testid="submit-blocked-reason">{!canSubmit ? "Both parents must complete their assessments first." : !ready ? "Mark the Professional Statement ready to enable submission." : ""}</p>}
          {subs.length > 0 && (
            <ul className="mt-4 space-y-1.5 text-sm" data-testid="court-submissions-list">
              {subs.map((s) => <li key={s.version} className="flex flex-wrap items-center gap-2 rounded-md bg-white px-3 py-2 border border-border"><ShieldCheck className="h-4 w-4 text-align-green" /><span className="font-semibold">Version {s.version}</span><span className="text-muted-foreground">submitted {s.submitted_at?.slice(0, 16).replace("T", " ")} to {s.court_name || "court"}</span><code className="ml-auto text-[11px] text-muted-foreground">SHA-256 {s.sha256?.slice(0, 16)}…</code></li>)}
            </ul>
          )}
        </div>
      ) : (
        <p className="mt-6 text-xs text-muted-foreground" data-testid="submit-not-court-case">This case was not referred by a court. To share with a judge, use Court Packets below.</p>
      )}
    </section>
  );
}
