import { useEffect, useState } from "react";
import { toast } from "sonner";
import { X } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

export const SharedProfessionals = ({ rid, refreshKey }) => {
  const [shares, setShares] = useState([]);

  const load = () => api.get(`/joint/reports/${rid}/shares`).then((r) => setShares(r.data)).catch(() => {});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [rid, refreshKey]);

  const stop = async (s) => {
    try {
      await api.delete(`/joint/reports/${rid}/share/${s.id}`);
      toast.success(`Stopped sharing with ${s.name}`);
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  if (!shares.length) return null;
  return (
    <ul className="mt-3 space-y-1.5 max-w-md" data-testid="shared-professionals-list">
      {shares.map((s) => (
        <li key={s.id} className="flex items-center justify-between gap-3 text-sm rounded-md border border-border px-3 py-2" data-testid={`shared-pro-${s.id}`}>
          <span>
            {s.name}
            {s.assigned && <span className="ml-2 text-xs text-muted-foreground" data-testid={`shared-pro-assigned-${s.id}`}>Assigned to your case</span>}
          </span>
          {s.removable ? (
            <Button size="sm" variant="ghost" className="h-7 gap-1 text-xs" onClick={() => stop(s)} data-testid={`stop-sharing-btn-${s.id}`}>
              <X className="h-3.5 w-3.5" /> Stop sharing
            </Button>
          ) : (
            <span className="text-xs text-muted-foreground">Cannot be removed by a parent</span>
          )}
        </li>
      ))}
    </ul>
  );
};
