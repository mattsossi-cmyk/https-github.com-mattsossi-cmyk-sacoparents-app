import { useState } from "react";
import { Link } from "react-router-dom";
import { Share2 } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

export function ShareFoundation({ rid, shared, onShared }) {
  const [busy, setBusy] = useState(false);
  const share = async () => {
    setBusy(true);
    try { await api.post(`/joint/reports/${rid}/foundation/share`); toast.success("Your Foundation Statement is now part of this case."); onShared?.(); }
    catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  return (
    <div className="mt-5 pt-4 border-t border-border" data-testid="share-foundation-block">
      <p className="text-sm font-medium">Your Child-Focused Foundation Statement</p>
      <p className="text-xs text-muted-foreground mt-0.5">{shared ? "Shared into this case — the professional and the Co-Parenting Agreement can use it." : "Share it so the professional sees your goals, priorities and commitments alongside your assessment."}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        <Button size="sm" variant={shared ? "outline" : "default"} onClick={share} disabled={busy} className="gap-1.5" data-testid="share-foundation-btn"><Share2 className="h-3.5 w-3.5" /> {shared ? "Re-share latest version" : "Share my Foundation Statement"}</Button>
        <Link to="/foundation" className="text-sm text-brand-purple underline self-center" data-testid="share-foundation-edit-link">{shared ? "Edit" : "Write or edit it"}</Link>
      </div>
    </div>
  );
}
