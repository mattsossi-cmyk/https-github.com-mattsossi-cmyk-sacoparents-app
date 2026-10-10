import React, { useCallback, useEffect, useState } from "react";
import { Link2, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { api } from "../../lib/api";
import { AlignLinkCode } from "./AlignLinkCode";
import { AlignReadHistory } from "./AlignReadHistory";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "../ui/alert-dialog";

const when = (iso) => new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });

function UnlinkButton({ busy, onConfirm }) {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <button type="button" data-testid="align-unlink-button" disabled={busy} className="shrink-0 rounded-full border border-[#E5C9C2] text-[#9A3A23] bg-white px-4 py-2 text-xs font-bold hover:bg-[#FDF3F0] disabled:opacity-60">
          {busy ? <Loader2 size={12} className="animate-spin" /> : "Unlink Align"}
        </button>
      </AlertDialogTrigger>
      <AlertDialogContent data-testid="align-unlink-dialog">
        <AlertDialogHeader>
          <AlertDialogTitle>Unlink SA CoParents Align?</AlertDialogTitle>
          <AlertDialogDescription>
            Align will stop being able to read your Situation Snapshot, Foundation Statement and Special Needs summaries
            straight away. Anything Align already saved stays on Align. To link again you&rsquo;ll need a new code.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel data-testid="align-unlink-cancel">Keep linked</AlertDialogCancel>
          <AlertDialogAction data-testid="align-unlink-confirm" onClick={onConfirm} className="bg-[#9A3A23] hover:bg-[#7E2E1B]">
            Unlink
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

// Account card: is SA CoParents Align linked, when it last read anything, and an Unlink button.
export default function AlignLinkCard() {
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/integrations/align-link");
      setStatus(data);
      return data;
    } catch {
      setStatus((s) => s || { linked: false, recent_reads: [] });
      return null;
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  const unlink = async () => {
    setBusy(true);
    try {
      const { data } = await api.delete("/integrations/align-link");
      setStatus(data);
      toast.success("Align is unlinked. It can no longer read your account.");
    } catch {
      toast.error("Couldn't unlink right now. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="align-link-card" className="rounded-2xl border border-[#E5E0EE] bg-white p-4 sm:p-5">
      <div className="flex items-start gap-3">
      <div className="shrink-0 h-9 w-9 rounded-full grid place-items-center bg-[#F5F1FB] text-[#3D1A78]">
        <Link2 size={15} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78]">SA CoParents Align</div>
        <div data-testid="align-link-state" className="text-sm font-semibold text-[#1A1330] mt-0.5">
          {!status ? "Checking..." : status.linked ? `Linked since ${when(status.linked_at)}` : "Not linked"}
        </div>
        <p className="text-xs text-[#4B4567] mt-1 leading-relaxed">
          {status?.linked
            ? "Align can read your Situation Snapshot, Foundation Statement and Special Needs summaries."
            : "Align can't read anything from your account. It only can after you link with a code."}
          {status?.last_read_at && (
            <span data-testid="align-link-last-read"> Last read {when(status.last_read_at)}.</span>
          )}
        </p>
      </div>
      </div>
      <div className="mt-3 flex flex-wrap items-start gap-2 sm:pl-12">
        <AlignLinkCode onPoll={load} />
        {status?.linked && <UnlinkButton busy={busy} onConfirm={unlink} />}
      </div>
      {status && <AlignReadHistory reads={status.recent_reads || []} />}
    </div>
  );
}
