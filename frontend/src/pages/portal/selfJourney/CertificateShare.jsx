import React, { useState } from "react";
import { ProSeeLink } from "../../../components/privacy/ProSeeLink";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "../../../components/ui/dialog";
import { api } from "../../../lib/api";

const btn = "px-5 py-2.5 rounded-md text-sm font-semibold transition-colors disabled:opacity-50";

function RecipientList({ recipients, onPick }) {
  if (recipients === null) return <p data-testid="cert-share-loading" className="text-sm text-slate-500"><i className="fa-solid fa-spinner fa-spin mr-1.5"></i>Loading…</p>;
  if (!recipients.length) {
    return (
      <div data-testid="cert-share-empty" className="rounded-lg bg-[#FBF9FC] border border-[#E2E8F0] p-4 text-sm text-slate-600">
        <p>There's no one to send it to yet. Invite your mediator or attorney first. Once they accept, they'll show up here.</p>
        <Link to="/share/professional" data-testid="cert-share-invite-link" className="inline-block mt-3 font-bold text-[#4A154B] underline underline-offset-2">
          Share with a Professional
        </Link>
      </div>
    );
  }
  return (
    <div className="space-y-2">
      {recipients.map((r) => (
        <button key={r.recipient_id} type="button" data-testid={`cert-share-recipient-${r.recipient_id}`} onClick={() => onPick(r)} className="w-full flex items-center justify-between gap-3 text-left rounded-lg border-2 border-[#E2E8F0] bg-white hover:border-[#611663] px-3.5 py-2.5 transition-colors">
          <span className="min-w-0">
            <span className="block text-sm font-bold text-slate-900">{r.name}</span>
            <span className="block text-[0.75rem] text-slate-500 break-words">{r.role_label} · {r.email}</span>
          </span>
          <i className="fa-solid fa-paper-plane text-[#611663]"></i>
        </button>
      ))}
    </div>
  );
}

// "Share certificate": tap a person → "Send to X (Role)?" → sent. No typed addresses.
export function CertificateShare({ defaultName, onSent }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [recipients, setRecipients] = useState(null);
  const [picked, setPicked] = useState(null);
  const [busy, setBusy] = useState(false);

  const start = () => {
    setName(defaultName || "");
    setPicked(null);
    setRecipients(null);
    setOpen(true);
    api.get("/journey-summary/certificate/recipients").then(({ data }) => setRecipients(data)).catch(() => setRecipients([]));
  };
  const send = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/journey-summary/certificate/send", { recipient_id: picked.recipient_id, name: name.trim() });
      toast.success(`Certificate sent to ${data.name}.`);
      setOpen(false);
      onSent?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Couldn't send right now. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <button type="button" data-testid="door-self-certificate-share-btn" onClick={start} className="shrink-0 rounded-full bg-white/15 hover:bg-white/25 border border-white/40 text-white text-[0.8125rem] font-bold px-4 py-2 transition-colors">
        <i className="fa-solid fa-paper-plane mr-1.5"></i>Share certificate
      </button>
      <Dialog open={open} onOpenChange={(v) => !busy && setOpen(v)}>
        <DialogContent data-testid="cert-share-dialog" className="max-w-md max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-[#4a1d7a]">{picked ? `Send to ${picked.name} (${picked.role_label})?` : "Share your certificate"}</DialogTitle>
            <DialogDescription>{picked ? `${picked.email} gets a private link with a one-time code to open it (no file in the email). Replies come back to you.` : "Tap who should get it."}</DialogDescription>
          </DialogHeader>
          <ProSeeLink testid="cert-share-pros-see-link" className="text-[12.5px] -mt-1" />
          {picked ? (
            <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 pt-1">
              <button type="button" data-testid="cert-share-back" onClick={() => setPicked(null)} disabled={busy} className={`${btn} bg-[#F4EEF5] hover:bg-[#E2D6E5] text-[#4A154B]`}>
                Back
              </button>
              <button type="button" data-testid="cert-share-send" onClick={send} disabled={busy} className={`${btn} bg-[#4a1d7a] hover:bg-[#35145a] text-white`}>
                {busy ? <i className="fa-solid fa-spinner fa-spin"></i> : "Send now"}
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="block text-[0.75rem] font-bold text-slate-700 mb-1" htmlFor="cert-share-name">
                  Name on the certificate
                </label>
                <input id="cert-share-name" data-testid="cert-share-name-input" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} className="w-full border border-slate-300 rounded-md px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400" />
              </div>
              <RecipientList recipients={recipients} onPick={(r) => (name.trim() ? setPicked(r) : toast.error("Please enter the name to print."))} />
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
