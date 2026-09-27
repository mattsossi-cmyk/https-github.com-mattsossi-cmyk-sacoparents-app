import { useEffect, useState } from "react";
import { Mail } from "lucide-react";
import api from "@/lib/api";

const STYLE = { green: "bg-align-green/15 text-align-green border-align-green/30", amber: "bg-amber-100 text-amber-800 border-amber-300", red: "bg-red-100 text-red-800 border-red-300" };

export const SenderStatusBadge = () => {
  const [s, setS] = useState(null);
  useEffect(() => { api.get("/admin/email-status").then((r) => setS(r.data)).catch(() => {}); }, []);
  if (!s) return null;
  const detail = s.failed_invites ? ` · ${s.failed_invites} invitation${s.failed_invites > 1 ? "s" : ""} not delivered` : "";
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold ${STYLE[s.level]}`} title={s.last_send?.email_error || ""} data-testid="sender-status-badge" data-level={s.level}>
      <span className={`h-2 w-2 rounded-full ${s.level === "green" ? "bg-align-green" : s.level === "amber" ? "bg-amber-500" : "bg-red-600"}`} />
      <Mail className="h-3.5 w-3.5" /> {s.label}{detail}
    </span>
  );
};
