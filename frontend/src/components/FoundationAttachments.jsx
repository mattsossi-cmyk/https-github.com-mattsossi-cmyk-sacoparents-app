import { useEffect, useRef, useState } from "react";
import { FileUp, Paperclip, Trash2 } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

const fmt = (n) => (n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`);

export function FoundationAttachments() {
  const [files, setFiles] = useState([]);
  const [busy, setBusy] = useState(false);
  const input = useRef(null);
  const load = () => api.get("/foundation/mine/attachments").then((r) => setFiles(r.data.files)).catch(() => {});
  useEffect(() => { load(); }, []);
  const upload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) { toast.error("File too large (10 MB max)"); return; }
    setBusy(true);
    const fd = new FormData();
    fd.append("file", file);
    try { const { data } = await api.post("/foundation/mine/attachments", fd, { headers: { "Content-Type": "multipart/form-data" } }); setFiles((x) => [...x, data]); toast.success("Document attached"); }
    catch (err) { toast.error(formatApiError(err)); } finally { setBusy(false); e.target.value = ""; }
  };
  const remove = async (id) => { try { await api.delete(`/foundation/mine/attachments/${id}`); setFiles((x) => x.filter((f) => f.id !== id)); } catch (err) { toast.error(formatApiError(err)); } };
  return (
    <section className="rounded-lg border border-border bg-white p-4" data-testid="foundation-attachments">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-2 text-sm font-bold text-[#2f174f]"><Paperclip className="h-4 w-4" /> Supporting documents <span className="text-xs font-normal text-muted-foreground">(PDF, JPG, PNG · 10 MB · up to 10)</span></p>
        <input ref={input} type="file" accept="application/pdf,image/jpeg,image/png,image/webp" className="hidden" onChange={upload} data-testid="foundation-attach-input" />
        <Button type="button" size="sm" variant="outline" onClick={() => input.current?.click()} disabled={busy} data-testid="foundation-attach-btn"><FileUp className="h-4 w-4 mr-1" /> {busy ? "Uploading…" : "Attach document"}</Button>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">Private to you and the professional on a case you share your statement into. Never shown to the other parent.</p>
      {files.length > 0 && (
        <ul className="mt-3 space-y-1" data-testid="foundation-attachment-list">
          {files.map((f) => (
            <li key={f.id} className="flex items-center justify-between gap-2 rounded-md border border-border px-3 py-1.5 text-sm" data-testid={`foundation-attachment-${f.id}`}>
              <a href={`${process.env.REACT_APP_BACKEND_URL}/api/files/${f.id}`} target="_blank" rel="noreferrer" className="truncate text-brand-purple underline">{f.original_filename}</a>
              <span className="flex items-center gap-2 text-xs text-muted-foreground">{fmt(f.size || 0)}<button type="button" onClick={() => remove(f.id)} aria-label="Remove" data-testid={`foundation-attachment-remove-${f.id}`}><Trash2 className="h-4 w-4 hover:text-destructive" /></button></span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function CaseAttachments({ rid }) {
  const [files, setFiles] = useState(null);
  useEffect(() => { api.get(`/joint/reports/${rid}/attachments`).then((r) => setFiles(r.data.files)).catch(() => setFiles([])); }, [rid]);
  if (!files?.length) return null;
  return (
    <div className="mt-4 rounded-md border border-border bg-[#faf8fd] p-3" data-testid="case-attachments">
      <p className="text-xs font-bold uppercase tracking-widest text-brand-purple flex items-center gap-1"><Paperclip className="h-3.5 w-3.5" /> Parent-attached documents</p>
      <ul className="mt-2 space-y-1 text-sm">
        {files.map((f) => <li key={f.id} data-testid={`case-attachment-${f.id}`}><span className="text-xs font-semibold uppercase text-muted-foreground mr-2">Parent {f.side.toUpperCase()}</span><a href={`${process.env.REACT_APP_BACKEND_URL}/api/files/${f.id}?case=${rid}`} target="_blank" rel="noreferrer" className="text-brand-purple underline">{f.original_filename}</a> <span className="text-xs text-muted-foreground">{fmt(f.size || 0)}</span></li>)}
      </ul>
    </div>
  );
}
