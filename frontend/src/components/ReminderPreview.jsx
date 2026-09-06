import { useState } from "react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";

export function ReminderPreviewButton({ iid, label, testId }) {
  const [open, setOpen] = useState(false);
  const [preview, setPreview] = useState(null);
  const [sending, setSending] = useState(false);

  const openPreview = async () => {
    setPreview(null);
    setOpen(true);
    try {
      const { data } = await api.get(`/joint/invitations/${iid}/reminder-preview`);
      setPreview(data);
    } catch (e) {
      setOpen(false);
      toast.error(formatApiError(e));
    }
  };

  const send = async () => {
    setSending(true);
    try {
      await api.post(`/joint/invitations/${iid}/resend`);
      toast.success("Reminder sent");
      setOpen(false);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      <Button size="sm" variant="outline" onClick={openPreview} data-testid={testId}>{label}</Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-2xl" data-testid={`reminder-preview-modal-${iid}`}>
          <DialogHeader>
            <DialogTitle data-testid={`reminder-preview-title-${iid}`}>Preview reminder email</DialogTitle>
            <DialogDescription>This is exactly what will be sent to the parent.</DialogDescription>
          </DialogHeader>
          {!preview ? (
            <p className="text-sm text-muted-foreground py-8 text-center" data-testid={`reminder-preview-loading-${iid}`}>Loading preview…</p>
          ) : (
            <div className="space-y-3">
              <div className="text-sm space-y-1">
                <p data-testid={`reminder-preview-to-${iid}`}><span className="font-semibold">To:</span> {preview.to}</p>
                <p data-testid={`reminder-preview-subject-${iid}`}><span className="font-semibold">Subject:</span> {preview.subject}</p>
              </div>
              <iframe
                title="Reminder email preview"
                srcDoc={preview.html}
                className="w-full h-80 border border-border rounded-md bg-white"
                data-testid={`reminder-preview-frame-${iid}`}
              />
            </div>
          )}
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setOpen(false)} data-testid={`reminder-preview-cancel-${iid}`}>Cancel</Button>
            <Button onClick={send} disabled={!preview || sending} data-testid={`reminder-preview-send-${iid}`}>
              {sending ? "Sending…" : "Send Reminder"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
