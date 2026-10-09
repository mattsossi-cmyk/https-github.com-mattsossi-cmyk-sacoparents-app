import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { ShieldCheck, Lock, Scale } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { BrandLogo } from "@/components/Brand";
import { QuickExitBar } from "@/components/QuickExit";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";

export default function PrivacyNotice() {
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [n, setN] = useState(null);
  const [ok, setOk] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.get("/privacy-notice").then((r) => setN(r.data.notice)).catch((e) => toast.error(formatApiError(e))); }, []);
  const go = async () => {
    setBusy(true);
    try { await api.post("/privacy-notice/accept", { version: n.version, acknowledged: ok }); await refresh(); navigate(sessionStorage.getItem("post-privacy-redirect") || "/dashboard", { replace: true }); sessionStorage.removeItem("post-privacy-redirect"); } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  if (!n) return <div className="min-h-screen bg-[#f6f3fb]" data-testid="privacy-loading"><QuickExitBar /></div>;
  return (
    <div className="min-h-screen bg-[#f6f3fb] font-jakarta text-slate-900" data-testid="privacy-notice-page">
      <QuickExitBar />
      <main className="mx-auto max-w-2xl px-4 py-10 sm:px-6">
        <div className="flex flex-col items-center text-center"><BrandLogo size="text-3xl" sub={n.tagline} /></div>
        <section className="mt-8 rounded-2xl border border-[#3D1A78]/15 bg-white p-6 shadow-sm sm:p-8" aria-labelledby="privacy-title">
          <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-[#3D1A78]/10 text-[#3D1A78]" aria-hidden="true"><ShieldCheck className="h-6 w-6" /></span>
          <h1 id="privacy-title" className="mt-4 text-4xl font-bold tracking-tight text-[#3D1A78] sm:text-5xl" data-testid="privacy-title">{n.title}</h1>
          <p className="mt-2 text-base font-semibold text-[#3D1A78]/80 md:text-lg" data-testid="privacy-subhead">{n.subhead}</p>
          <p className="mt-4 text-sm text-slate-700" data-testid="privacy-intro">{n.intro}</p>
          <ol className="mt-6 space-y-4" data-testid="privacy-points">
            {n.points.map((p, i) => (
              <li key={p.heading} className="flex gap-3" data-testid={`privacy-point-${i + 1}`}>
                <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#3D1A78] text-xs font-bold text-white" aria-hidden="true">{i + 1}</span>
                <div><p className="text-sm font-bold">{p.heading}</p><p className="mt-1 text-sm text-slate-600">{p.body}</p></div>
              </li>
            ))}
          </ol>
          <div className="mt-6 rounded-xl border-l-4 border-amber-500 bg-amber-50 p-4" data-testid="privacy-legal">
            <p className="flex items-center gap-2 text-sm font-bold text-amber-900"><Scale className="h-4 w-4" aria-hidden="true" /> {n.legal_heading}</p>
            <p className="mt-1 text-sm text-amber-900/90">{n.legal}</p>
          </div>
          <label htmlFor="privacy-ack" className="mt-6 flex cursor-pointer items-start gap-3 rounded-xl border border-[#3D1A78]/20 p-4 hover:bg-[#3D1A78]/5">
            <Checkbox id="privacy-ack" checked={ok} onCheckedChange={(v) => setOk(v === true)} className="mt-0.5 border-[#3D1A78] data-[state=checked]:bg-[#3D1A78]" data-testid="privacy-ack-checkbox" />
            <span className="text-sm font-medium">{n.checkbox}</span>
          </label>
          <Button onClick={go} disabled={!ok || busy} className="mt-5 h-12 w-full rounded-full bg-[#3D1A78] text-base font-bold hover:bg-[#2f1460] disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-[#3D1A78] focus-visible:ring-offset-2" data-testid="privacy-continue-btn">{n.continue}</Button>
          <p className="mt-4 flex items-center gap-1.5 text-[11px] text-slate-500"><Lock className="h-3 w-3" aria-hidden="true" /> Notice version {n.version}. {/* TODO(placeholder): footer links to Privacy Policy, Confidentiality, and Sharing & Consent will appear here once those pages exist. */}</p>
        </section>
      </main>
    </div>
  );
}
