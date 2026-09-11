import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { toast } from "sonner";
import { ShieldCheck } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { BrandLogo } from "@/components/Brand";
import { PacketViewer } from "@/components/PacketViewer";

const KEY = (t) => `court-access-${t}`;

export default function CourtPacket() {
  const { token } = useParams();
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);
  const [code, setCode] = useState("");
  const [access, setAccess] = useState(() => sessionStorage.getItem(KEY(token)) || "");
  const [packet, setPacket] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get(`/court/${token}/preview`).then((r) => setPreview(r.data)).catch((e) => setError(formatApiError(e)));
  }, [token]);

  useEffect(() => {
    if (!access) return;
    api.get(`/court/${token}`, { headers: { "X-Court-Access": access } })
      .then((r) => setPacket(r.data))
      .catch(() => { sessionStorage.removeItem(KEY(token)); setAccess(""); });
  }, [token, access]);

  const unlock = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/court/${token}/unlock`, { code: code.trim() });
      sessionStorage.setItem(KEY(token), data.access);
      setAccess(data.access);
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  if (error) return <Shell><p className="text-destructive" data-testid="court-error">{error}</p></Shell>;
  if (!preview) return <Shell><p className="text-muted-foreground" data-testid="court-loading">Loading…</p></Shell>;
  if (preview.state !== "active") {
    return <Shell><div data-testid="court-unavailable"><h1 className="text-2xl font-semibold">This Court Packet is {preview.state}</h1><p className="mt-2 text-muted-foreground">Please contact {preview.professional_name} to request a new packet.</p></div></Shell>;
  }

  if (!packet) {
    return (
      <Shell>
        <div className="max-w-md" data-testid="court-unlock">
          <p className="text-xs uppercase tracking-widest text-accent font-semibold">Court Packet</p>
          <h1 className="text-2xl font-semibold mt-1">{preview.court_name || "For the Court"}</h1>
          <p className="mt-1 text-sm text-muted-foreground">Prepared by {preview.professional_name}{preview.cause_number ? ` · Cause No. ${preview.cause_number}` : ""} · Addressed to {preview.judge_name}</p>
          <p className="mt-6 text-sm">Enter the 6-digit access code that was emailed to you separately.</p>
          <div className="mt-3 flex gap-2">
            <Input value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))} inputMode="numeric" placeholder="000000" className="h-11 text-lg tracking-[0.4em] font-semibold" data-testid="court-code-input" />
            <Button onClick={unlock} disabled={busy || code.length !== 6} className="h-11" data-testid="court-unlock-btn">{busy ? "Checking…" : "Open packet"}</Button>
          </div>
          <p className="mt-6 text-xs text-muted-foreground flex items-center gap-1.5"><ShieldCheck className="h-3.5 w-3.5" /> Read-only. Every opening and download is logged for the professional. Access expires {preview.expires_at?.slice(0, 10)}.</p>
          <p className="mt-4 text-xs text-muted-foreground">Judges and court staff can also <a href="/auth?mode=register&court=1" className="text-primary hover:underline" data-testid="court-account-link">create a court account</a> to see every packet in one dashboard.</p>
        </div>
      </Shell>
    );
  }

  return (
    <Shell wide>
      <PacketViewer packet={packet} setPacket={setPacket}
        downloadHref={`${process.env.REACT_APP_BACKEND_URL}/api/court/${token}/pdf?access=${encodeURIComponent(access)}`}
        respondFn={(body) => api.post(`/court/${token}/respond`, body, { headers: { "X-Court-Access": access } })} />
    </Shell>
  );
}

function Shell({ children, wide }) {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-white"><div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between"><BrandLogo size="text-xl" /><span className="text-xs text-muted-foreground">Court access</span></div></header>
      <main className={`${wide ? "max-w-5xl" : "max-w-3xl"} mx-auto px-6 py-10`}>{children}</main>
    </div>
  );
}
