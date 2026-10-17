import React, { useEffect, useState } from "react";
import { Eye, Send } from "lucide-react";
import { toast } from "sonner";

import { api } from "../lib/api";
import { logError } from "../lib/logger";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "./ui/dialog";
import { Switch } from "./ui/switch";

const TYPES = [
  ["sa", "Self-Assessment"],
  ["checkins", "Practice check-ins & streak"],
  ["cp", "Co-Parenting assessment"],
  ["cn", "Child Needs forms"],
  ["fb", "Foundation Statement"],
];
const ALL_ON = Object.fromEntries(TYPES.map(([k]) => [k, true]));

function TypeSwitches({ types, onToggle }) {
  return (
    <div className="grid sm:grid-cols-2 gap-2">
      {TYPES.map(([k, label]) => (
        <label key={k} className="flex items-center justify-between gap-3 rounded-xl border border-[#E5E0EE] bg-[#FAF8FD] px-3 py-2 text-sm text-[#1A1330] cursor-pointer">
          <span>{label}</span>
          <Switch data-testid={`admin-weekly-note-toggle-${k}`} checked={types[k]} onCheckedChange={(v) => onToggle(k, v)} />
        </label>
      ))}
    </div>
  );
}

// Admin: on-screen preview of the exact weekly note, with a switch per progress type.
export function WeeklyNotePreview() {
  const [open, setOpen] = useState(false);
  const [types, setTypes] = useState(ALL_ON);
  const [note, setNote] = useState(null);
  const [sending, setSending] = useState(false);
  const typesKey = TYPES.map(([k]) => (types[k] ? 1 : 0)).join("");

  useEffect(() => {
    if (!open) return;
    api
      .post("/admin/self-journey-weekly/preview", { types })
      .then(({ data }) => setNote(data))
      .catch((e) => {
        logError("weekly note preview failed", e);
        toast.error("Couldn't load the preview right now.");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, typesKey]);

  const send = async () => {
    setSending(true);
    try {
      const { data } = await api.post("/admin/self-journey-weekly/sample", { types });
      toast.success(`This version was sent to ${data.sent_to}`);
    } catch (e) {
      logError("weekly note preview send failed", e);
      toast.error(e?.response?.data?.detail || "Couldn't send it right now.");
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      <button
        type="button"
        data-testid="admin-weekly-note-preview"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1.5 px-3 py-2 rounded-full border border-[#3D1A78] text-[#3D1A78] hover:bg-[#F3EFFA] text-xs font-semibold transition-colors"
      >
        <Eye size={13} /> Preview note
      </button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent data-testid="admin-weekly-note-preview-dialog" className="max-w-3xl max-h-[92vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Weekly note preview</DialogTitle>
            <DialogDescription>Turn kinds of progress on or off to see exactly how a parent's note changes.</DialogDescription>
          </DialogHeader>
          <TypeSwitches types={types} onToggle={(k, v) => setTypes((t) => ({ ...t, [k]: v }))} />
          {note && !note.html ? (
            <p data-testid="admin-weekly-note-preview-empty" className="rounded-xl border border-dashed border-[#E5E0EE] bg-[#FAF8FD] p-6 text-center text-sm text-[#4B4567]">
              Nothing selected. Parents who made no progress that week don't get a note.
            </p>
          ) : (
            <>
              <div data-testid="admin-weekly-note-preview-subject" className="text-sm text-[#4B4567]">
                <span className="font-semibold text-[#1A1330]">Subject:</span> {note?.subject || "…"}
              </div>
              <iframe
                data-testid="admin-weekly-note-preview-frame"
                title="Weekly note preview"
                sandbox=""
                srcDoc={note?.html || ""}
                className="w-full h-[520px] rounded-xl border border-[#E5E0EE] bg-white"
              />
            </>
          )}
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <span className="text-xs text-[#6E6787]">Links in the preview are switched off.</span>
            <button
              type="button"
              data-testid="admin-weekly-note-preview-send"
              onClick={send}
              disabled={sending || !note?.html}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-[#3D1A78] hover:bg-[#2c1259] text-white text-xs font-semibold disabled:opacity-60 transition-colors"
            >
              <Send size={13} /> {sending ? "Sending…" : `Email me this version${note?.sent_to ? ` (${note.sent_to})` : ""}`}
            </button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
