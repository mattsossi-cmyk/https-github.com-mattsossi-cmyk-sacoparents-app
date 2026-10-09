import React, { useState } from "react";
import { toast } from "sonner";

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "../../../components/ui/dialog";
import { api } from "../../../lib/api";
import { NEEDS_ART } from "../selfJourney/selfJourneyArt";
import { ConfirmStep, FormTicks, ProviderPicker } from "./ShareProviderSteps";

const ORDER = NEEDS_ART.items.map((i) => i.key);
const btnCls = "px-5 py-2.5 rounded-md text-sm font-semibold transition-colors disabled:opacity-50";

// "Send to a provider" button + dialog: pick an accepted professional, tick completed forms, confirm, send.
export function SendToProvider({ completedAt, defaultKeys = [], onSent, testid, className }) {
  const completed = ORDER.filter((k) => completedAt?.[k]);
  const [open, setOpen] = useState(false);
  const [providers, setProviders] = useState(null);
  const [pickedId, setPickedId] = useState(null);
  const [keys, setKeys] = useState([]);
  const [step, setStep] = useState("pick");
  const [sending, setSending] = useState(false);
  if (!completed.length) return null;

  const start = () => {
    setOpen(true);
    setStep("pick");
    setKeys(defaultKeys.filter((k) => completed.includes(k)));
    setProviders(null);
    api
      .get("/child-needs/providers")
      .then(({ data }) => {
        setProviders(data);
        setPickedId(data.length === 1 ? data[0].provider_id : null);
      })
      .catch(() => setProviders([]));
  };
  const toggle = (k) => setKeys((s) => (s.includes(k) ? s.filter((x) => x !== k) : [...s, k]));
  const all = () => setKeys((s) => (completed.every((k) => s.includes(k)) ? [] : completed));
  const provider = providers?.find((p) => p.provider_id === pickedId);
  const ordered = ORDER.filter((k) => keys.includes(k));

  const send = async () => {
    setSending(true);
    try {
      const { data } = await api.post("/child-needs/share", { provider_id: pickedId, categories: ordered });
      toast.success(`Sent to ${data.provider_name}.`);
      setOpen(false);
      onSent?.(data);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Couldn't send right now. Please try again.");
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      <button type="button" data-testid={testid} onClick={start} className={className}>
        <i className="fa-solid fa-paper-plane mr-1.5"></i>Send to a provider
      </button>
      <Dialog open={open} onOpenChange={(v) => !sending && setOpen(v)}>
        <DialogContent data-testid="share-provider-dialog" className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-[#4A154B]">{step === "pick" ? "Send to a provider" : "Check before you send"}</DialogTitle>
            <DialogDescription>{step === "pick" ? "Pick a professional who accepted your invitation, then tick the forms to include." : "This is exactly what will be emailed."}</DialogDescription>
          </DialogHeader>
          {step === "pick" ? (
            <div className="space-y-5">
              <ProviderPicker providers={providers} pickedId={pickedId} onPick={setPickedId} />
              {providers?.length > 0 && <FormTicks completed={completed} picked={keys} onToggle={toggle} onAll={all} />}
            </div>
          ) : (
            <ConfirmStep provider={provider} keys={ordered} />
          )}
          <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 pt-2">
            <button type="button" data-testid="share-provider-back" onClick={() => (step === "pick" ? setOpen(false) : setStep("pick"))} disabled={sending} className={`${btnCls} bg-[#F4EEF5] hover:bg-[#E2D6E5] text-[#4A154B]`}>
              {step === "pick" ? "Cancel" : "Back"}
            </button>
            {step === "pick" ? (
              <button type="button" data-testid="share-provider-continue" onClick={() => setStep("confirm")} disabled={!provider || !ordered.length} className={`${btnCls} bg-[#4A154B] hover:bg-[#350D36] text-white`}>
                Continue
              </button>
            ) : (
              <button type="button" data-testid="share-provider-send" onClick={send} disabled={sending} className={`${btnCls} bg-[#4A154B] hover:bg-[#350D36] text-white`}>
                {sending ? <i className="fa-solid fa-spinner fa-spin"></i> : "Send now"}
              </button>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
