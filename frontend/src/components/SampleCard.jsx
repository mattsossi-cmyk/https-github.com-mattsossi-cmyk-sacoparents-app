import { useState } from "react";
import { Link } from "react-router-dom";
import { Download, Eye, Mail, ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { samplePdfUrl } from "@/lib/samples";
import { Button } from "@/components/ui/button";

export function SampleCard({ s }) {
  const [showEmail, setShowEmail] = useState(false);
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);

  const send = async (e) => {
    e.preventDefault();
    if (!email.trim()) return;
    setSending(true);
    try {
      await api.post(s.emailEndpoint || `/joint/sample/${s.key}/email`, { email: email.trim() });
      toast.success(`Sample "${s.label}" sent to ${email.trim()}`);
      setEmail("");
      setShowEmail(false);
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setSending(false);
    }
  };

  return (
    <div className={`bg-white border rounded-lg p-6 flex flex-col ${s.safety ? "border-red-300" : "border-border"}`} data-testid={`sample-card-${s.key}`}>
      {s.safety && (
        <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-red-700 mb-3" data-testid={`sample-card-safety-badge-${s.key}`}>
          <ShieldAlert className="h-3.5 w-3.5" /> Professional-mediated preview
        </span>
      )}
      {s.tag && <span className="text-xs font-bold uppercase tracking-widest text-teal-700 mb-2" data-testid={`sample-card-tag-${s.key}`}>{s.tag}</span>}
      <h3 className="text-lg font-bold" data-testid={`sample-card-title-${s.key}`}>{s.label}</h3>
      <p className="text-sm text-muted-foreground mt-2 flex-1">{s.blurb}</p>
      <div className="flex gap-2 mt-5">
        <Link to={s.to || `/samples/${s.key}`} className="flex-1" data-testid={`sample-view-link-${s.key}`}>
          <Button variant="outline" size="sm" className="w-full gap-2" data-testid={`sample-view-btn-${s.key}`}>
            <Eye className="h-4 w-4" /> View
          </Button>
        </Link>
        <Button size="sm" className="flex-1 gap-2" asChild data-testid={`sample-download-btn-${s.key}`}>
          <a href={s.pdf || samplePdfUrl(s.key)} download>
            <Download className="h-4 w-4" /> PDF
          </a>
        </Button>
        <Button
          variant="outline" size="sm" className="gap-1.5" title="Email this sample"
          onClick={() => setShowEmail((v) => !v)} data-testid={`sample-email-btn-${s.key}`}
        >
          <Mail className="h-4 w-4" />
        </Button>
      </div>
      {showEmail && (
        <form onSubmit={send} className="mt-3 flex gap-2" data-testid={`sample-email-form-${s.key}`}>
          <input
            type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
            placeholder="name@example.com"
            className="flex-1 min-w-0 border border-border rounded-md px-3 py-1.5 text-sm bg-background focus:outline-none focus:ring-1 focus:ring-primary"
            data-testid={`sample-email-input-${s.key}`}
          />
          <Button size="sm" type="submit" disabled={sending} data-testid={`sample-email-send-${s.key}`}>
            {sending ? "Sending…" : "Send"}
          </Button>
        </form>
      )}
    </div>
  );
}
