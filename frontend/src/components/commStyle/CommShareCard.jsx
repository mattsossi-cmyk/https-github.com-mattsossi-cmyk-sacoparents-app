import React, { useState } from "react";
import { toast } from "sonner";

import { COMM_SHARE_QUESTION, COMM_SHARE_REASK, clearCommShare, setCommShare } from "../../lib/commShare";
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../ui/alert-dialog";

const BTN = "rounded-full px-4 py-2 text-sm font-bold disabled:opacity-60";

// Asked once after Communication Style is saved (or again after a wording change). Skip = nothing sent.
export function CommShareCard({ open, hasSample, reask = false, onDone }) {
  const [busy, setBusy] = useState(false);
  const choose = async (share) => {
    setBusy(true);
    try {
      await setCommShare(share);
      toast.success(share ? "Shared with SACOparentsAlign, for your assigned professionals only." : "Kept private to your account.");
    } catch {
      toast.error("Couldn't save your choice. You can set it later on your Account page.");
    } finally {
      setBusy(false);
      onDone();
    }
  };
  const skip = async () => {
    if (reask) await clearCommShare().catch(() => {});
    onDone();
  };
  return (
    <AlertDialog open={open}>
      <AlertDialogContent data-testid="comm-share-card">
        <AlertDialogHeader>
          <AlertDialogTitle data-testid="comm-share-question">{COMM_SHARE_QUESTION}</AlertDialogTitle>
          <AlertDialogDescription data-testid="comm-share-what">
            {reask ? (
              <>{COMM_SHARE_REASK} The 4 answers are your 3 Communication Style choices and the optional message box.</>
            ) : (
              <>The 4 answers are your 3 choices above and {hasSample ? "the message you pasted" : "the optional message box, which you left empty"}.</>
            )}{" "}
            You can change this any time on your Account page.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter className="gap-2">
          <button type="button" data-testid="comm-share-skip" disabled={busy} onClick={skip}
                  className={`${BTN} text-[#4B4567] hover:bg-[#F5F1FB]`}>Skip for now</button>
          <button type="button" data-testid="comm-share-no" disabled={busy} onClick={() => choose(false)}
                  className={`${BTN} border border-[#E5E0EE] bg-white text-[#1A1330] hover:bg-[#F5F1FB]`}>No, keep private</button>
          <button type="button" data-testid="comm-share-yes" disabled={busy} onClick={() => choose(true)}
                  className={`${BTN} bg-[#3D1A78] text-white hover:bg-[#2E1260]`}>Yes, share</button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
