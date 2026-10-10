import React, { useState } from "react";
import { toast } from "sonner";

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "../../../components/ui/dialog";
import { api } from "../../../lib/api";

const btn = "px-5 py-2.5 rounded-md text-sm font-semibold transition-colors disabled:opacity-50";

async function errorText(e) {
  try {
    return JSON.parse(await e.response.data.text()).detail;
  } catch {
    return null;
  }
}

// "Download certificate" button + dialog to confirm how the parent's name is printed.
export function CertificateButton({ defaultName }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);

  const download = async () => {
    setBusy(true);
    try {
      const res = await api.post("/journey-summary/certificate", { name: name.trim() }, { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = "SA_CoParents_Individual_Journey_Certificate.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
      toast.success("Your certificate is downloading.");
      setOpen(false);
    } catch (e) {
      toast.error((await errorText(e)) || "Couldn't build your certificate right now. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <button
        type="button"
        data-testid="door-self-certificate-btn"
        onClick={() => {
          setName(defaultName || "");
          setOpen(true);
        }}
        className="shrink-0 rounded-full bg-white hover:bg-purple-50 text-[#4a1d7a] text-[13px] font-bold px-4 py-2 transition-colors"
      >
        <i className="fa-solid fa-award mr-1.5"></i>Download certificate
      </button>
      <Dialog open={open} onOpenChange={(v) => !busy && setOpen(v)}>
        <DialogContent data-testid="certificate-dialog" className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-[#4a1d7a]">Individual Journey certificate</DialogTitle>
            <DialogDescription>Check how your name should be printed, then download.</DialogDescription>
          </DialogHeader>
          <label className="block text-[12px] font-bold text-slate-700" htmlFor="certificate-name">
            Name on the certificate
          </label>
          <input
            id="certificate-name"
            data-testid="certificate-name-input"
            value={name}
            maxLength={80}
            onChange={(e) => setName(e.target.value)}
            className="w-full border border-slate-300 rounded-md px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400"
          />
          <p className="text-[11px] text-slate-500 leading-relaxed">
            A certificate of completion for the self-guided SA CoParents Individual Journey. It is not a court-approved parenting course certificate and not legal advice.
          </p>
          <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 pt-1">
            <button type="button" data-testid="certificate-cancel" onClick={() => setOpen(false)} disabled={busy} className={`${btn} bg-[#F4EEF5] hover:bg-[#E2D6E5] text-[#4A154B]`}>
              Cancel
            </button>
            <button type="button" data-testid="certificate-download" onClick={download} disabled={busy || !name.trim()} className={`${btn} bg-[#4a1d7a] hover:bg-[#35145a] text-white`}>
              {busy ? <i className="fa-solid fa-spinner fa-spin"></i> : "Download PDF"}
            </button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
