import { useEffect, useState } from "react";
import { Ban, FileLock2, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { api } from "../lib/api";

const PILL = {
  waiting: ["Not opened yet", "bg-[#F1EEF7] text-[#3D1A78]"],
  opened: ["Opened", "bg-[#E6F4EC] text-[#1F5C3B]"],
  expired: ["Expired", "bg-[#FFF6E5] text-[#8A5B00]"],
  cancelled: ["Cancelled", "bg-[#FCE3DC] text-[#9A3A23]"],
};
const pillKey = (d) => (d.status !== "ready" ? d.status : d.opened_at ? "opened" : "waiting");
const day = (iso) => new Date(iso).toLocaleDateString(undefined, { dateStyle: "medium" });

export function SecureDocsSent() {
  const [docs, setDocs] = useState(null);
  const [busy, setBusy] = useState(null);
  const load = () => api.get("/secure-docs/sent").then((r) => setDocs(r.data)).catch(() => setDocs([]));
  useEffect(() => { load(); }, []);

  const cancel = async (d) => {
    if (!window.confirm(`Cancel this document for ${d.recipient_email}? They won't be able to open it.`)) return;
    setBusy(d.doc_id);
    try { await api.post(`/secure-docs/sent/${d.doc_id}/cancel`); toast.success("Document cancelled."); await load(); }
    catch { toast.error("Couldn't cancel the document."); }
    finally { setBusy(null); }
  };

  if (!docs || docs.length === 0) return null;
  return (
    <section className="mt-8 rounded-3xl border border-[#E5E0EE] bg-white p-5 sm:p-6" data-testid="secure-docs-sent">
      <h2 className="text-sm font-semibold text-[#1A1330] flex items-center gap-2"><FileLock2 size={15} className="text-[#3D1A78]" /> Documents you sent securely</h2>
      <p className="text-[12px] text-[#4B4567] mt-1">Emails never carry the file. The person opens it here with a one-time code, until the link expires or you cancel it.</p>
      <ul className="mt-4 divide-y divide-[#EEE8F7]" data-testid="secure-docs-sent-list">
        {docs.map((d) => {
          const [label, cls] = PILL[pillKey(d)];
          return (
            <li key={d.doc_id} className="py-3 flex flex-wrap items-center justify-between gap-2" data-testid={`secure-doc-row-${d.doc_id}`}>
              <div className="min-w-0 flex-1">
                <div className="text-[13px] font-semibold text-[#1A1330] break-words">{d.label}</div>
                <div className="text-[11px] text-[#857E9C] break-words">
                  To {d.recipient_email} · Sent {day(d.created_at)} · Link ends {day(d.expires_at)}
                </div>
              </div>
              <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${cls}`} data-testid={`secure-doc-status-${d.doc_id}`}>{label}</span>
              {d.status === "ready" && (
                <button type="button" onClick={() => cancel(d)} disabled={busy === d.doc_id}
                  className="inline-flex items-center gap-1 rounded-full border border-[#F5D0C5] text-[#9A3A23] hover:bg-[#FCE3DC] bg-white px-3 py-1 text-[11px] font-semibold disabled:opacity-50"
                  data-testid={`secure-doc-cancel-${d.doc_id}`}>
                  {busy === d.doc_id ? <Loader2 size={10} className="animate-spin" /> : <Ban size={11} />} Cancel
                </button>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
