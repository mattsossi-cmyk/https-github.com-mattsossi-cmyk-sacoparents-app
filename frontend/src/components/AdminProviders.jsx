import { useEffect, useState } from "react";
import { toast } from "sonner";
import { BookUser, Download, History, Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";
import { ProviderHistory } from "@/components/ProviderHistory";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const EMPTY = { name: "", degrees: "", specialty: "", organization: "", phone: "", email: "", website: "", lists: ["individual", "joint"], active: true };
const FIELDS = [["name", "Name *"], ["degrees", "Degrees / credentials (e.g. LPC, JD)"], ["specialty", "Specialty"], ["organization", "Organization"], ["phone", "Phone"], ["email", "Email"], ["website", "Website"]];

function ProviderForm({ value, onChange, onSave, onCancel, saving }) {
  const toggle = (l) => onChange({ ...value, lists: value.lists.includes(l) ? value.lists.filter((x) => x !== l) : [...value.lists, l] });
  return (
    <div className="rounded-lg border border-brand-purple/30 bg-brand-purple/5 p-4 space-y-3" data-testid="provider-form">
      <div className="grid gap-2 sm:grid-cols-3">{FIELDS.map(([k, l]) => <label key={k} className="text-xs font-medium">{l}<Input value={value[k]} onChange={(e) => onChange({ ...value, [k]: e.target.value })} className="mt-1 h-8 bg-white" data-testid={`provider-${k}`} /></label>)}</div>
      <div className="flex flex-wrap items-center gap-4 text-sm">
        <span className="text-xs font-medium">Appears in:</span>
        {["individual", "joint"].map((l) => <label key={l} className="flex items-center gap-1.5 capitalize"><input type="checkbox" checked={value.lists.includes(l)} onChange={() => toggle(l)} data-testid={`provider-list-${l}`} />{l} resources</label>)}
        <label className="flex items-center gap-1.5"><input type="checkbox" checked={value.active} onChange={(e) => onChange({ ...value, active: e.target.checked })} data-testid="provider-active" />Active</label>
      </div>
      <div className="flex gap-2"><Button size="sm" onClick={onSave} disabled={saving || !value.name.trim()} data-testid="provider-save-btn">Save provider</Button><Button size="sm" variant="ghost" onClick={onCancel} data-testid="provider-cancel-btn">Cancel</Button></div>
    </div>
  );
}

export function AdminProviders() {
  const [items, setItems] = useState([]);
  const [edit, setEdit] = useState(null);
  const [saving, setSaving] = useState(false);
  const load = () => api.get("/admin/providers").then((r) => setItems(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);
  const save = async () => {
    setSaving(true);
    try {
      if (edit.id) await api.put(`/admin/providers/${edit.id}`, edit); else await api.post("/admin/providers", edit);
      toast.success(`${edit.name} saved`); setEdit(null); load();
    } catch (e) { toast.error(formatApiError(e)); } finally { setSaving(false); }
  };
  const remove = async (p) => {
    if (!window.confirm(`Remove ${p.name} from the provider directory?`)) return;
    try { await api.delete(`/admin/providers/${p.id}`); toast.success("Provider removed"); load(); } catch (e) { toast.error(formatApiError(e)); }
  };
  const [verifying, setVerifying] = useState(null);
  const verify = async (p) => {
    setVerifying(p.id);
    try { await api.post(`/research/providers/${p.id}/verify`); toast.success(`${p.name} checked against live web results`); load(); }
    catch (e) { toast.error(formatApiError(e)); } finally { setVerifying(null); }
  };
  const applyVerification = async (p) => {
    try { const { data } = await api.post(`/research/providers/${p.id}/apply-verification`); toast.success(Object.keys(data.updated).length ? `Updated ${Object.keys(data.updated).join(", ")}` : "Nothing to update"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const isStale = (p) => !p.last_verified_at || (Date.now() - new Date(p.last_verified_at).getTime()) > 90 * 86400000;
  const stale = items.filter((p) => p.active !== false && isStale(p));
  const [checkingAll, setCheckingAll] = useState(false);
  const [historyFor, setHistoryFor] = useState(null);
  const checkAll = async () => {
    setCheckingAll(true);
    let ok = 0;
    for (const p of stale) { try { setVerifying(p.id); await api.post(`/research/providers/${p.id}/verify`); ok += 1; } catch { /* continue */ } }
    setVerifying(null); setCheckingAll(false); load(); toast.success(`Checked ${ok} of ${stale.length} stale provider${stale.length === 1 ? "" : "s"}`);
  };
  return (
    <section className="mt-10" data-testid="admin-providers">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h2 className="text-2xl font-semibold flex items-center gap-2"><BookUser className="h-6 w-6 text-brand-purple" /> Resource Provider Directory</h2>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" asChild data-testid="provider-export-csv-btn"><a href={`${process.env.REACT_APP_BACKEND_URL}/api/admin/providers/export.csv`} download><Download className="h-4 w-4 mr-1" /> Export CSV</a></Button>
          {stale.length > 0 && <Button size="sm" variant="outline" onClick={checkAll} disabled={checkingAll} data-testid="provider-check-all-btn"><RefreshCw className={`h-4 w-4 mr-1 ${checkingAll ? "animate-spin" : ""}`} /> {checkingAll ? "Checking…" : `Check all stale (${stale.length})`}</Button>}
          <Button size="sm" onClick={() => setEdit({ ...EMPTY })} data-testid="provider-add-btn"><Plus className="h-4 w-4 mr-1" /> Add provider</Button>
        </div>
      </div>
      <p className="text-sm text-muted-foreground mt-1">Providers listed here appear in the Legal Lens resource checklists; ticking one auto-fills the provider name, specialty and contact into the report.</p>
      {edit && !edit.id && <div className="mt-4"><ProviderForm value={edit} onChange={setEdit} onSave={save} onCancel={() => setEdit(null)} saving={saving} /></div>}
      <ul className="mt-4 space-y-2" data-testid="provider-list">
        {items.map((p) => (
          <li key={p.id} className="rounded-lg border border-border bg-white p-3" data-testid={`provider-row-${p.id}`}>
            {edit?.id === p.id ? <ProviderForm value={edit} onChange={setEdit} onSave={save} onCancel={() => setEdit(null)} saving={saving} /> : (
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex-1 min-w-[200px]">
                  <p className="font-semibold">{p.name}{p.degrees && <span className="font-normal">, {p.degrees}</span>}{!p.active && <span className="ml-2 rounded-full bg-secondary px-2 py-0.5 text-xs font-normal">inactive</span>}{isStale(p) && <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800" title="Not freshness-checked in the last 90 days" data-testid={`provider-stale-${p.id}`}>{p.last_verified_at ? "stale check" : "never checked"}</span>}</p>
                  <p className="text-sm text-muted-foreground">{[p.specialty, p.organization, p.phone, p.email, p.website].filter(Boolean).join(" · ") || "No details yet"}</p>
                  <p className="text-xs text-brand-purple mt-0.5">Lists: {(p.lists || []).join(", ")}</p>
                </div>
                <Button size="sm" variant="outline" onClick={() => setEdit({ ...EMPTY, ...p })} data-testid={`provider-edit-${p.id}`}><Pencil className="h-4 w-4" /></Button>
                <Button size="sm" variant="outline" onClick={() => verify(p)} disabled={verifying === p.id} title="Re-verify phone & website via Perplexity" data-testid={`provider-verify-${p.id}`}><RefreshCw className={`h-4 w-4 ${verifying === p.id ? "animate-spin" : ""}`} /></Button>
                <Button size="sm" variant={historyFor === p.id ? "secondary" : "outline"} onClick={() => setHistoryFor((h) => (h === p.id ? null : p.id))} title="Freshness history" data-testid={`provider-history-btn-${p.id}`}><History className="h-4 w-4" /></Button>
                <Button size="sm" variant="ghost" onClick={() => remove(p)} data-testid={`provider-delete-${p.id}`}><Trash2 className="h-4 w-4 text-destructive" /></Button>
              </div>
            )}
            {p.verification && edit?.id !== p.id && (
              <div className="mt-2 rounded-md border border-teal-200 bg-[#f4fbfb] p-2 text-xs" data-testid={`provider-verification-${p.id}`}>
                <p className="font-semibold text-teal-700">Freshness check · {String(p.verification.checked_at || "").slice(0, 10)}</p>
                {Object.entries(p.verification.checks || {}).map(([k, c]) => <p key={k} data-testid={`provider-verification-${p.id}-${k}`}><span className="capitalize">{k}</span>: {c.match ? <span className="text-align-green font-semibold">matches</span> : c.found ? <span className="text-amber-700 font-semibold">differs</span> : <span className="text-muted-foreground">not found</span>}{c.found && !c.match && <> — found <strong>{c.found}</strong> (directory: {c.directory || "—"})</>}</p>)}
                {p.verification.summary && <p className="mt-1 text-muted-foreground line-clamp-3">{p.verification.summary}</p>}
                {Object.values(p.verification.checks || {}).some((c) => c.found && !c.match) && <Button size="sm" variant="outline" className="mt-1 h-7" onClick={() => applyVerification(p)} data-testid={`provider-verification-apply-${p.id}`}>Apply found values</Button>}
              </div>
            )}
            {historyFor === p.id && <ProviderHistory providerId={p.id} refreshKey={`${p.last_verified_at}-${p.updated_at}`} />}
          </li>
        ))}
        {items.length === 0 && <li className="text-sm text-muted-foreground" data-testid="provider-empty">No providers yet.</li>}
      </ul>
    </section>
  );
}
