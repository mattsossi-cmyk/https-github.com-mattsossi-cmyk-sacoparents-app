import { useEffect, useState } from "react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

const FIELDS = [["pro_role", "Title"], ["bar_number", "Bar Number"], ["license_number", "License Number"], ["phone", "Phone"], ["organization", "Organization / Firm"], ["address", "Street address"], ["city", "City"], ["state", "State"], ["zip", "ZIP"]];

export const ProfileContactForm = ({ onSaved, testId = "profile-contact" }) => {
  const [p, setP] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.get("/me/profile/contact").then((r) => setP(r.data)).catch(() => setP({})); }, []);
  if (!p) return null;
  const save = async () => {
    setBusy(true);
    try { await api.put("/me/profile/contact", p); toast.success("Profile saved — every report cover now uses these details"); onSaved?.(); }
    catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  return (
    <div className="grid gap-3 sm:grid-cols-3" data-testid={testId}>
      {FIELDS.map(([k, l]) => (
        <label key={k} className="block text-sm"><span className="font-medium">{l}</span>
          <input value={p[k] || ""} onChange={(e) => setP({ ...p, [k]: e.target.value })} className="mt-1 h-9 w-full rounded-md border border-input bg-white px-2 text-sm" data-testid={`${testId}-${k}`} />
        </label>
      ))}
      <div className="flex items-end"><Button size="sm" onClick={save} disabled={busy} data-testid={`${testId}-save`}>{busy ? "Saving…" : "Save to my profile"}</Button></div>
    </div>
  );
};
