import React, { useState } from "react";
import { toast } from "sonner";

import { COMM_SHARE_QUESTION, setCommShare } from "../../lib/commShare";
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../ui/alert-dialog";

const BTN = "rounded-full px-4 py-2 text-sm font-bold disabled:opacity-60";

// Asked once after Communication Style is saved. Skip = nothing sent; the Account page switch changes it later.
export function CommShareCard({ open, onDone }) {
  const [busy, setBusy] = useState(false);
  const choose = async (share) => {
    setBusy(true);
    try {
      await setCommShare(share);
      toast.success(share ? "Shared privately with your assigned professional on Align." : "Kept private to your account.");
    } catch {
      toast.error("Couldn't save your choice. You can set it later on your Account page.");
    } finally {
      setBusy(false);
      onDone();
    }
  };
  return (
    <AlertDialog open={open}>
      <AlertDialogContent data-testid="comm-share-card">
        <AlertDialogHeader>
          <AlertDialogTitle data-testid="comm-share-question">{COMM_SHARE_QUESTION}</AlertDialogTitle>
          <AlertDialogDescription>
            The 4 answers are your 3 choices above and the message you pasted. You can change this any time on your Account page.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter className="gap-2">
          <button type="button" data-testid="comm-share-skip" disabled={busy} onClick={onDone}
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
