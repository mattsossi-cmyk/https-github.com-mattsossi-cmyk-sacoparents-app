import { useState } from "react";
import { Link } from "react-router-dom";
import { Share2 } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

export function ShareFoundation({ rid, shared, onShared, imported }) {
  const [busy, setBusy] = useState(false);
  const [routed, setRouted] = useState("");
  const call = async (path, ok) => {
    setBusy(true);
    try { await api.post(`/joint/reports/${rid}/foundation/${path}`); toast.success(ok); onShared?.(); }
    catch (e) { if (e?.response?.status === 409) setRouted(formatApiError(e)); else toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  const share = () => call("share", "Your Foundation Statement is now part of this case.");
  return (
    <div className="mt-5 pt-4 border-t border-border" data-testid="share-foundation-block">
      <p className="text-sm font-medium">Your Child-Focused Foundation Statement</p>
      {routed && <div className="mt-2 rounded-md border border-[#e0b04a] bg-[#fff7df] p-3 text-sm" data-testid="share-foundation-safety-route"><strong className="text-[#b07d10]">Safety pathway.</strong> {routed}</div>}
      <p className="text-xs text-muted-foreground mt-0.5">{shared ? "Shared into this case — the professional and the Co-Parenting Agreement can use it." : "Share it so the professional sees your goals, priorities and commitments alongside your assessment."}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        <Button size="sm" variant={shared ? "outline" : "default"} onClick={share} disabled={busy} className="gap-1.5" data-testid="share-foundation-btn"><Share2 className="h-3.5 w-3.5" /> {shared ? "Re-share latest version" : "Share my Foundation Statement"}</Button>
        <Link to="/foundation" className="text-sm text-brand-purple underline self-center" data-testid="share-foundation-edit-link">{shared ? "Edit" : "Write or edit it"}</Link>
      </div>
      {imported && !imported.included && (
        <div className="mt-3 rounded-md border border-brand-purple/30 bg-[#f3edfb] p-3 text-sm flex flex-wrap items-center justify-between gap-2" data-testid="share-foundation-import-block">
          <span>A Foundation Statement from the SA CoParents app arrived for you{imported.received_at ? ` on ${imported.received_at.slice(0, 10)}` : ""}. <strong>Nobody in Align can see it until you include it.</strong></span>
          <Button size="sm" variant="outline" onClick={() => call("use-import", "Your statement from the SA CoParents app is now part of this case.")} disabled={busy} data-testid="share-foundation-import-btn">Include it in this case</Button>
        </div>
      )}
    </div>
  );
}
