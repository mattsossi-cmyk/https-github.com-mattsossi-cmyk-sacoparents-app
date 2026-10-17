import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Contact, ImagePlus, Trash2 } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const FIELDS = [["phone", "Phone"], ["organization", "Firm / Organization"], ["address", "Office / Mailing Address"], ["city", "City"], ["state", "State"], ["zip", "ZIP"]];
const SLOTS = [["headshot", "Headshot"], ["firm_logo", "Court / Firm Logo"], ["signature", "Signature (prints on the certification page when finalized)"]];

const ImageSlot = ({ slot, label, has, onChange }) => {
  const [busy, setBusy] = useState(false);
  const [v, setV] = useState(0);
  const upload = async (file) => {
    if (!file) return;
    setBusy(true);
    const fd = new FormData(); fd.append("file", file);
    try { await api.post(`/me/profile/image/${slot}`, fd); toast.success(`${label} saved`); setV((x) => x + 1); await onChange(); }
    catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  const remove = async () => { setBusy(true); try { await api.delete(`/me/profile/image/${slot}`); await onChange(); } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); } };
  return (
    <div className="flex items-center gap-3 rounded-md border border-border p-2" data-testid={`cover-image-${slot}`}>
      <div className="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-md bg-secondary">
        {has ? <img src={`${process.env.REACT_APP_BACKEND_URL}/api/me/profile/image/${slot}?v=${v}`} alt={label} className="h-full w-full object-contain" data-testid={`cover-image-${slot}-img`} /> : <ImagePlus className="h-5 w-5 text-muted-foreground" />}
      </div>
      <div className="min-w-0 flex-1"><p className="text-sm font-semibold">{label}</p><p className="text-xs text-muted-foreground">JPG/PNG/WebP · max 2 MB · prints on the report cover</p></div>
      <label className="cursor-pointer rounded-md border border-input px-2 py-1 text-xs font-semibold hover:bg-secondary" data-testid={`cover-image-${slot}-upload`}>{busy ? "…" : has ? "Replace" : "Upload"}<input type="file" accept="image/jpeg,image/png,image/webp" className="hidden" disabled={busy} onChange={(e) => upload(e.target.files?.[0])} /></label>
      {has && <button type="button" onClick={remove} disabled={busy} className="rounded-md p-1 text-destructive hover:bg-destructive/10" aria-label={`Remove ${label}`} data-testid={`cover-image-${slot}-remove`}><Trash2 className="h-4 w-4" /></button>}
    </div>
  );
};

export const ProContactCard = () => {
  const { user, refresh } = useAuth();
  const unlinkGoogle = async () => {
    try { await api.delete("/auth/google/link"); await refresh(); toast.success("Google sign-in unlinked — password sign-in still works"); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const p = user?.profile || {};
  const [form, setForm] = useState({});
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => { setForm(Object.fromEntries(FIELDS.map(([k]) => [k, p[k] || ""]))); }, [user]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!user || user.approved === false) return null;
  const missing = FIELDS.filter(([k]) => !p[k]).length;
  const save = async (e) => {
    e.preventDefault(); setBusy(true);
    try { await api.put("/me/profile/contact", form); toast.success("Report cover contact saved"); await refresh(); setOpen(false); }
    catch (err) { toast.error(formatApiError(err)); } finally { setBusy(false); }
  };
  return (
    <section className="rounded-lg border border-border bg-white p-4" data-testid="pro-contact-card">
      <div className="flex flex-wrap items-center gap-3">
        <Contact className="h-5 w-5 shrink-0 text-brand-purple" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold">Report Cover Contact</p>
          <p className="text-xs text-muted-foreground" data-testid="pro-contact-summary">{missing ? `${missing} field${missing > 1 ? "s" : ""} missing — the report cover prints blank lines until filled in.` : [p.organization, p.address, [p.city, p.state].filter(Boolean).join(", "), p.zip, p.phone].filter(Boolean).join(" · ")}</p>
        </div>
        <Button size="sm" variant="outline" onClick={() => setOpen((o) => !o)} data-testid="pro-contact-toggle">{open ? "Close" : "Edit"}</Button>
      </div>
      {user?.google_linked_at && (
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs" data-testid="google-linked-row">
          <span className="inline-flex items-center gap-1 rounded-full border border-border bg-secondary/60 px-2 py-0.5 font-semibold" data-testid="google-linked-badge"><span className="h-2 w-2 rounded-full bg-[#34A853]" /> Google linked</span>
          <span className="text-muted-foreground">since {String(user.google_linked_at).slice(0, 10)} · you can sign in with Google or your password</span>
          <button type="button" className="text-muted-foreground underline hover:text-foreground" onClick={unlinkGoogle} data-testid="google-unlink-btn">Unlink</button>
        </div>
      )}
      {open && (
        <form onSubmit={save} className="mt-4 space-y-4">
          <div className="grid gap-3 sm:grid-cols-3">{FIELDS.map(([k, l]) => <label key={k} className={`block text-sm ${k === "address" || k === "organization" ? "sm:col-span-2" : ""}`}><span className="font-medium">{l}</span><Input value={form[k] || ""} onChange={(e) => setForm({ ...form, [k]: e.target.value })} className="mt-1 h-9" data-testid={`pro-contact-${k}`} /></label>)}</div>
          <div className="grid gap-3 sm:grid-cols-2">{SLOTS.map(([s, l]) => <ImageSlot key={s} slot={s} label={l} has={!!p.images?.[s]} onChange={refresh} />)}</div>
          <Button type="submit" size="sm" disabled={busy} className="bg-brand-purple text-white hover:bg-brand-purple/90" data-testid="pro-contact-save">{busy ? "Saving…" : "Save contact details"}</Button>
        </form>
      )}
    </section>
  );
};
