import React, { useState } from "react";
import { Link } from "react-router-dom";
import { LifeBuoy, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";

import AppShell from "../components/AppShell";
import { AdminGate, useAdminGet } from "../components/AdminGate";
import { api } from "../lib/api";
import { US_STATES, stateName } from "../lib/usStates";

const EMPTY = { state: "TX", name: "", phone: "", text: "", url: "", description: "" };
const FIELDS = [["name", "Name"], ["phone", "Phone"], ["text", "Text line (e.g. Text START to 88788)"], ["url", "Website (https://…)"]];
const input = "w-full rounded-lg border border-[#D9D3EA] bg-white px-3 py-2 text-sm";

function ServiceForm({ value, onChange, onSubmit, onCancel, busy }) {
  const set = (k) => (e) => onChange({ ...value, [k]: e.target.value });
  return (
    <form onSubmit={onSubmit} className="card-soft p-5 grid gap-3" data-testid="admin-help-form">
      <select value={value.state} onChange={set("state")} className={input} data-testid="admin-help-state">
        {US_STATES.map(([c, n]) => <option key={c} value={c}>{n}</option>)}
      </select>
      {FIELDS.map(([k, label]) => (
        <input key={k} value={value[k] || ""} onChange={set(k)} placeholder={label} aria-label={label} className={input} data-testid={`admin-help-${k}`} required={k === "name"} />
      ))}
      <textarea value={value.description || ""} onChange={set("description")} placeholder="Short description" aria-label="Short description" rows={2} className={input} data-testid="admin-help-description" />
      <div className="flex gap-2">
        <button type="submit" disabled={busy} className="btn-gradient px-5 disabled:opacity-50" data-testid="admin-help-save">{value.id ? "Save changes" : "Add service"}</button>
        {value.id && <button type="button" onClick={onCancel} className="text-sm underline" data-testid="admin-help-cancel">Cancel</button>}
      </div>
    </form>
  );
}

function ServiceRow({ s, onEdit, onDelete }) {
  return (
    <li className="flex items-start justify-between gap-3 py-3 border-t border-[#F0EDF6]" data-testid={`admin-help-row-${s.id}`}>
      <div className="min-w-0">
        <p className="text-sm font-semibold text-[#1A1330]">{s.name}</p>
        <p className="text-xs text-[#857E9C]">{[stateName(s.state), s.phone, s.text, s.url].filter(Boolean).join(" · ")}</p>
      </div>
      <div className="flex gap-2 shrink-0">
        <button type="button" onClick={() => onEdit(s)} aria-label="Edit" data-testid={`admin-help-edit-${s.id}`} className="p-1.5 rounded hover:bg-slate-100"><Pencil size={14} /></button>
        <button type="button" onClick={() => onDelete(s)} aria-label="Delete" data-testid={`admin-help-delete-${s.id}`} className="p-1.5 rounded hover:bg-rose-50 text-rose-700"><Trash2 size={14} /></button>
      </div>
    </li>
  );
}

export default function AdminHelpServices() {
  const { data, err, reload } = useAdminGet("/admin/help-services");
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    const { id, ...body } = form;
    try {
      await (id ? api.put(`/admin/help-services/${id}`, body) : api.post("/admin/help-services", body));
      toast.success(id ? "Service updated." : "Service added.");
      setForm(EMPTY);
      reload();
    } catch (er) {
      toast.error(er?.response?.data?.detail?.[0]?.msg || "Couldn't save. Check the fields.");
    } finally {
      setBusy(false);
    }
  };
  const remove = async (s) => {
    if (!window.confirm(`Delete "${s.name}"?`)) return;
    await api.delete(`/admin/help-services/${s.id}`).catch(() => toast.error("Couldn't delete."));
    reload();
  };
  return (
    <AdminGate tp="admin-help" err={err}>
      <AppShell>
        <div className="max-w-3xl mx-auto px-1 py-6 space-y-6" data-testid="admin-help-page">
          <div>
            <div className="text-[11px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] inline-flex items-center gap-2"><LifeBuoy size={12} /> Get help page</div>
            <h1 className="font-serif text-4xl text-[#1A1330] mt-2">Local services by state</h1>
            <p className="text-sm text-[#4B4567] mt-2">Shown on <Link to="/help" className="underline">Get help</Link> when a visitor picks their state.</p>
          </div>
          <ServiceForm value={form} onChange={setForm} onSubmit={submit} onCancel={() => setForm(EMPTY)} busy={busy} />
          <ul className="card-soft px-5 py-2" data-testid="admin-help-list">
            {(data?.services || []).map((s) => (
              <ServiceRow key={s.id} s={s} onEdit={(x) => setForm({ ...EMPTY, ...x })} onDelete={remove} />
            ))}
            {data && !data.services.length && <li className="py-3 text-sm text-[#857E9C]">No services yet.</li>}
          </ul>
        </div>
      </AppShell>
    </AdminGate>
  );
}
