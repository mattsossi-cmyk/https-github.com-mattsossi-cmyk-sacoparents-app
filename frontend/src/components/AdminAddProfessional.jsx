import { useState } from "react";
import { toast } from "sonner";
import { UserPlus } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export const PROFESSIONS = ["Mediator", "Parenting Facilitator", "Parenting Coordinator", "Attorney", "Counselor / Therapist", "Custody Evaluator", "Other"];
const EMPTY = { name: "", email: "", profession: "", degrees: "", phone: "", organization: "" };

export function AdminAddProfessional({ onAdded }) {
  const [open, setOpen] = useState(false);
  const [f, setF] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const upd = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const { data } = await api.post("/admin/professionals", f);
      toast.success(data.invite_sent ? `${data.name} added — invitation sent to ${data.email}` : `${data.name} added, but the invite email could not be sent. Use "Resend invite".`);
      setF(EMPTY); setOpen(false); onAdded?.(data);
    } catch (err) { toast.error(formatApiError(err)); } finally { setSaving(false); }
  };
  if (!open) return <Button size="sm" onClick={() => setOpen(true)} data-testid="admin-add-pro-btn"><UserPlus className="h-4 w-4 mr-1" /> Add professional</Button>;
  return (
    <form onSubmit={submit} className="mt-4 rounded-lg border border-brand-purple/30 bg-brand-purple/5 p-4 space-y-3" data-testid="admin-add-pro-form">
      <p className="text-sm font-semibold">Add an approved professional</p>
      <p className="text-xs text-muted-foreground">The account is created pre-approved and the professional receives an email link to set their password (valid 7 days).</p>
      <div className="grid gap-2 sm:grid-cols-3">
        <label className="text-xs font-medium">Full name *<Input required value={f.name} onChange={upd("name")} className="mt-1 h-8 bg-white" data-testid="add-pro-name" /></label>
        <label className="text-xs font-medium">Email *<Input required type="email" value={f.email} onChange={upd("email")} className="mt-1 h-8 bg-white" data-testid="add-pro-email" /></label>
        <label className="text-xs font-medium">Profession *
          <select required value={f.profession} onChange={upd("profession")} className="mt-1 h-8 w-full rounded-md border border-input bg-white px-2 text-sm" data-testid="add-pro-profession">
            <option value="">Select…</option>{PROFESSIONS.map((p) => <option key={p} value={p}>{p}</option>)}
          </select></label>
        <label className="text-xs font-medium">Degrees / credentials<Input value={f.degrees} onChange={upd("degrees")} placeholder="e.g. JD, LPC-S" className="mt-1 h-8 bg-white" data-testid="add-pro-degrees" /></label>
        <label className="text-xs font-medium">Phone<Input value={f.phone} onChange={upd("phone")} className="mt-1 h-8 bg-white" data-testid="add-pro-phone" /></label>
        <label className="text-xs font-medium">Organization<Input value={f.organization} onChange={upd("organization")} className="mt-1 h-8 bg-white" data-testid="add-pro-organization" /></label>
      </div>
      <div className="flex gap-2">
        <Button type="submit" size="sm" disabled={saving} data-testid="add-pro-submit">{saving ? "Creating…" : "Create account & send invite"}</Button>
        <Button type="button" size="sm" variant="ghost" onClick={() => setOpen(false)} data-testid="add-pro-cancel">Cancel</Button>
      </div>
    </form>
  );
}
