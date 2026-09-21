import { useEffect, useState } from "react";
import { toast } from "sonner";
import { BookUser, Pencil, Plus, Trash2 } from "lucide-react";
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
  return (
    <section className="mt-10" data-testid="admin-providers">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h2 className="text-2xl font-semibold flex items-center gap-2"><BookUser className="h-6 w-6 text-brand-purple" /> Resource Provider Directory</h2>
        <Button size="sm" onClick={() => setEdit({ ...EMPTY })} data-testid="provider-add-btn"><Plus className="h-4 w-4 mr-1" /> Add provider</Button>
      </div>
      <p className="text-sm text-muted-foreground mt-1">Providers listed here appear in the Legal Lens resource checklists; ticking one auto-fills the provider name, specialty and contact into the report.</p>
      {edit && !edit.id && <div className="mt-4"><ProviderForm value={edit} onChange={setEdit} onSave={save} onCancel={() => setEdit(null)} saving={saving} /></div>}
      <ul className="mt-4 space-y-2" data-testid="provider-list">
        {items.map((p) => (
          <li key={p.id} className="rounded-lg border border-border bg-white p-3" data-testid={`provider-row-${p.id}`}>
            {edit?.id === p.id ? <ProviderForm value={edit} onChange={setEdit} onSave={save} onCancel={() => setEdit(null)} saving={saving} /> : (
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex-1 min-w-[200px]">
                  <p className="font-semibold">{p.name}{p.degrees && <span className="font-normal">, {p.degrees}</span>}{!p.active && <span className="ml-2 rounded-full bg-secondary px-2 py-0.5 text-xs font-normal">inactive</span>}</p>
                  <p className="text-sm text-muted-foreground">{[p.specialty, p.organization, p.phone, p.email, p.website].filter(Boolean).join(" · ") || "No details yet"}</p>
                  <p className="text-xs text-brand-purple mt-0.5">Lists: {(p.lists || []).join(", ")}</p>
                </div>
                <Button size="sm" variant="outline" onClick={() => setEdit({ ...EMPTY, ...p })} data-testid={`provider-edit-${p.id}`}><Pencil className="h-4 w-4" /></Button>
                <Button size="sm" variant="ghost" onClick={() => remove(p)} data-testid={`provider-delete-${p.id}`}><Trash2 className="h-4 w-4 text-destructive" /></Button>
              </div>
            )}
          </li>
        ))}
        {items.length === 0 && <li className="text-sm text-muted-foreground" data-testid="provider-empty">No providers yet.</li>}
      </ul>
    </section>
  );
}
