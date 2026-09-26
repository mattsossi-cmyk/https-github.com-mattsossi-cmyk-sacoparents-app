import { useState } from "react";
import { toast } from "sonner";
import { MapPin } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export const ProZipPrompt = () => {
  const { user, refresh } = useAuth();
  const [zip, setZip] = useState("");
  const [busy, setBusy] = useState(false);
  if (!user || user.approved === false || user.profile?.zip) return null;

  const save = async () => {
    if (!/^\d{5}(-\d{4})?$/.test(zip.trim())) { toast.error("Enter a 5-digit ZIP code"); return; }
    setBusy(true);
    try { await api.put("/me/profile/zip", { zip: zip.trim() }); toast.success("ZIP saved — courts can now find you as a nearby professional"); await refresh(); }
    catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };
  return (
    <div className="mb-6 flex flex-wrap items-center gap-3 rounded-lg border border-brand-purple/30 bg-brand-purple/5 p-4" data-testid="pro-zip-prompt">
      <MapPin className="h-5 w-5 shrink-0 text-brand-purple" />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold">Add your practice ZIP code</p>
        <p className="text-xs text-muted-foreground">Judges referring a case sort professionals by distance from the parties' ZIP. Without one, you appear under "Location not listed".</p>
      </div>
      <div className="flex items-center gap-2">
        <Input placeholder="ZIP" value={zip} onChange={(e) => setZip(e.target.value)} inputMode="numeric" maxLength={10} className="h-9 w-[110px]" data-testid="pro-zip-input" />
        <Button onClick={save} disabled={busy} size="sm" className="bg-brand-purple hover:bg-brand-purple/90 text-white" data-testid="pro-zip-save-btn">{busy ? "Saving…" : "Save"}</Button>
      </div>
    </div>
  );
};
