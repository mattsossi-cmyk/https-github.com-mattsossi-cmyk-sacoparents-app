import { useEffect, useRef, useState } from "react";
import { FileUp, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

export function CredentialUpload({ user }) {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const input = useRef(null);
  const load = () => api.get("/me/credentials").then((r) => setData(r.data)).catch(() => setData({ files: [] }));
  useEffect(() => { load(); }, []);
  const upload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    const fd = new FormData(); fd.append("file", file);
    try { await api.post("/me/credentials", fd, { headers: { "Content-Type": "multipart/form-data" } }); toast.success("Credential uploaded — our team will review it"); load(); }
    catch (err) { toast.error(formatApiError(err)); } finally { setBusy(false); e.target.value = ""; }
  };
  if (!data) return null;
  const verified = user?.verification_level === "credentials_verified";
  if (verified && data.files.length === 0) return null;
  return (
    <section id="credentials" className={`rounded-lg border p-5 mb-6 ${verified ? "border-border bg-white" : "border-align-yellow/40 bg-align-yellow/10"}`} data-testid="credential-upload-section">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div><p className="font-semibold flex items-center gap-2"><ShieldCheck className="h-4 w-4" /> {verified ? "Your credentials are verified" : "Credential verification"}</p>
          {!verified && <p className="text-sm text-muted-foreground mt-1">{data.requested_at ? "SA CoParents Align has requested a copy of your license or certification." : "Upload a copy of your license or certification (PDF or image) to speed up acceptance."}</p>}</div>
        <input ref={input} type="file" accept="application/pdf,image/jpeg,image/png,image/webp" className="hidden" onChange={upload} data-testid="credential-file-input" />
        <Button size="sm" onClick={() => input.current?.click()} disabled={busy} data-testid="credential-upload-btn"><FileUp className="h-4 w-4 mr-1" /> {busy ? "Uploading…" : "Upload credential"}</Button>
      </div>
      {data.files.length > 0 && <ul className="mt-3 text-sm space-y-1" data-testid="credential-file-list">{data.files.map((f) => <li key={f.id} data-testid={`credential-file-${f.id}`}><a href={`${process.env.REACT_APP_BACKEND_URL}/api/credential-files/${f.id}`} target="_blank" rel="noreferrer" className="text-brand-purple underline">{f.original_filename}</a> <span className="text-xs text-muted-foreground">· {String(f.created_at).slice(0, 10)}</span></li>)}</ul>}
    </section>
  );
}
