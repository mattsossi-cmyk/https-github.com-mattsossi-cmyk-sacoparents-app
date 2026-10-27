import { useState } from "react";
import { Link } from "react-router-dom";
import { Share2, Undo2 } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

export function ShareFoundation({ rid, shared, onShared, onWithdrawn, imported }) {
  const [busy, setBusy] = useState(false);
  const [routed, setRouted] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [deleteHeld, setDeleteHeld] = useState(false);
  const call = async (path, ok, body, after) => {
    setBusy(true);
    try { await api.post(`/joint/reports/${rid}/foundation/${path}`, body); toast.success(ok); after?.(); }
    catch (e) { if (e?.response?.status === 409) setRouted(formatApiError(e)); else toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  const share = () => call("share", "Your Foundation Statement is now part of this case.", undefined, onShared);
  const withdraw = () => call("withdraw", "Your Foundation Statement has been removed from this case.", { delete_held: deleteHeld }, () => { setConfirming(false); onWithdrawn?.(deleteHeld); });
  return (
    <div className="mt-5 pt-4 border-t border-border" data-testid="share-foundation-block">
      <p className="text-sm font-medium">Your Child-Focused Foundation Statement</p>
      {routed && <div className="mt-2 rounded-md border border-[#e0b04a] bg-[#fff7df] p-3 text-sm" data-testid="share-foundation-safety-route"><strong className="text-[#b07d10]">Safety pathway.</strong> {routed}</div>}
      <p className="text-xs text-muted-foreground mt-0.5">{shared ? "Shared into this case — the professional and the Co-Parenting Agreement can use it." : "Share it so the professional sees your goals, priorities and commitments alongside your assessment."}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        <Button size="sm" variant={shared ? "outline" : "default"} onClick={share} disabled={busy} className="gap-1.5" data-testid="share-foundation-btn"><Share2 className="h-3.5 w-3.5" /> {shared ? "Re-share latest version" : "Share my Foundation Statement"}</Button>
        {shared && !confirming && <Button size="sm" variant="ghost" onClick={() => setConfirming(true)} disabled={busy} className="gap-1.5 text-muted-foreground" data-testid="withdraw-foundation-btn"><Undo2 className="h-3.5 w-3.5" /> Withdraw my statement</Button>}
        <Link to="/foundation" className="text-sm text-brand-purple underline self-center" data-testid="share-foundation-edit-link">{shared ? "Edit" : "Write or edit it"}</Link>
      </div>
      {confirming && (
        <div className="mt-3 rounded-md border border-border bg-muted/40 p-3 text-sm" data-testid="withdraw-foundation-confirm">
          <p>Remove your Foundation Statement from this case? The professional and your co-parent will no longer see it in Align. Copies already downloaded, or already in a report submitted to a court, cannot be recalled.</p>
          {imported && (
            <label className="mt-2 flex items-center gap-2 text-xs"><input type="checkbox" checked={deleteHeld} onChange={(e) => setDeleteHeld(e.target.checked)} data-testid="withdraw-delete-held-checkbox" /> Also delete the copy that arrived from the SA CoParents app</label>
          )}
          <div className="mt-3 flex gap-2">
            <Button size="sm" variant="destructive" onClick={withdraw} disabled={busy} data-testid="withdraw-foundation-confirm-btn">Yes, withdraw</Button>
            <Button size="sm" variant="outline" onClick={() => setConfirming(false)} disabled={busy} data-testid="withdraw-foundation-cancel-btn">Cancel</Button>
          </div>
        </div>
      )}
      {imported && !imported.included && (
        <div className="mt-3 rounded-md border border-brand-purple/30 bg-[#f3edfb] p-3 text-sm flex flex-wrap items-center justify-between gap-2" data-testid="share-foundation-import-block">
          <span>A Foundation Statement from the SA CoParents app arrived for you{imported.received_at ? ` on ${imported.received_at.slice(0, 10)}` : ""}. <strong>Nobody in Align can see it until you include it.</strong></span>
          <Button size="sm" variant="outline" onClick={() => call("use-import", "Your statement from the SA CoParents app is now part of this case.", undefined, onShared)} disabled={busy} data-testid="share-foundation-import-btn">Include it in this case</Button>
        </div>
      )}
    </div>
  );
}
