import { useEffect, useState } from "react";
import { FileText } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

export function PendingCredentialActions({ pro, onAccepted }) {
  const [files, setFiles] = useState(null);
  useEffect(() => { api.get(`/admin/professionals/${pro.id}/credentials`).then((r) => setFiles(r.data.files)).catch(() => setFiles([])); }, [pro.id]);
  const request = async () => { try { const { data } = await api.post(`/admin/professionals/${pro.id}/request-credentials`); toast[data.ok ? "success" : "warning"](data.ok ? `Credential request emailed to ${pro.email}` : "Saved, but the email could not be sent"); } catch (e) { toast.error(formatApiError(e)); } };
  const accept = async () => { try { await api.post(`/admin/accept-professional/${pro.id}`); toast.success(`${pro.name} accepted — credentials marked verified`); onAccepted(pro.id); } catch (e) { toast.error(formatApiError(e)); } };
  return (
    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs" data-testid={`pending-credentials-${pro.id}`}>
      <span className="flex items-center gap-1 text-muted-foreground"><FileText className="h-3.5 w-3.5" /> Credential documents:</span>
      {files === null ? "…" : files.length === 0 ? <span className="text-amber-700" data-testid={`pending-no-files-${pro.id}`}>none uploaded</span> : files.map((f) => <a key={f.id} href={`${process.env.REACT_APP_BACKEND_URL}/api/credential-files/${f.id}`} target="_blank" rel="noreferrer" className="text-brand-purple underline" data-testid={`pending-file-${f.id}`}>{f.original_filename}</a>)}
      {pro.profile?.credential_type && <span className="rounded-full bg-muted px-2 py-0.5">{pro.profile.credential_type}</span>}
      {pro.profile?.zip && <span className="rounded-full bg-muted px-2 py-0.5">ZIP {pro.profile.zip}</span>}
      <Button size="sm" variant="outline" className="h-7" onClick={request} data-testid={`request-credentials-btn-${pro.id}`}>Request credentials</Button>
      <Button size="sm" className="h-7 bg-align-green hover:bg-align-green/90" onClick={accept} data-testid={`accept-pro-btn-${pro.id}`}>Accept (approve + verify)</Button>
    </div>
  );
}
