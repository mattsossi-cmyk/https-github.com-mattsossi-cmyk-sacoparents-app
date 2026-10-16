import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Lock, Eye, FileText, Heart, Scale, ShieldAlert } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { BrandLogo } from "@/components/Brand";
import { QuickExitBar } from "@/components/QuickExit";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";

const ICONS = [Lock, Eye, FileText, Heart, Scale];

const Item = ({ p, i }) => {
  const Icon = ICONS[i] || Lock;
  return (
    <li className="flex gap-4 rounded-2xl border border-[#3D1A78]/10 bg-white p-4 shadow-sm sm:p-5" data-testid={`privacy-point-${i + 1}`}>
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[#3D1A78]/10 text-[#3D1A78]" aria-hidden="true"><Icon className="h-5 w-5" /></span>
      <div className="min-w-0">
        <p className="text-sm font-bold md:text-base" data-testid={`privacy-point-${i + 1}-heading`}>{p.heading}</p>
        <p className="mt-1 text-sm leading-relaxed text-slate-600" data-testid={`privacy-point-${i + 1}-body`}>{p.body}</p>
      </div>
    </li>
  );
};

export default function PrivacyNotice() {
  const navigate = useNavigate();
  const { user, refresh } = useAuth();
  const [n, setN] = useState(null);
  const [ok, setOk] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.get("/privacy-notice").then((r) => setN(r.data.notice)).catch((e) => toast.error(formatApiError(e))); }, []);
  const go = async () => {
    setBusy(true);
    try {
      await api.post("/privacy-notice/accept", { version: n.version, acknowledged: ok });
      await refresh();
      navigate(sessionStorage.getItem("post-privacy-redirect") || (user?.role === "parent" ? "/start-with-safety" : "/dashboard"), { replace: true });
      sessionStorage.removeItem("post-privacy-redirect");
    } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  if (!n) return <div className="min-h-screen bg-[#f6f3fb]" data-testid="privacy-loading"><QuickExitBar /></div>;
  return (
    <div className="min-h-screen bg-[#f6f3fb] font-jakarta text-slate-900" data-testid="privacy-notice-page">
      <QuickExitBar />
      <a href="#privacy-main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-14 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2">Skip to content</a>
      <header className="bg-[#ece6f7]" data-testid="privacy-banner">
        <div className="mx-auto flex max-w-2xl flex-col items-center px-4 pb-8 pt-10 text-center sm:px-6">
          <BrandLogo size="text-3xl" />
          <h1 className="mt-5 text-4xl font-bold tracking-tight text-[#3D1A78] sm:text-5xl" data-testid="privacy-banner-heading">{n.banner_heading}</h1>
          <p className="mt-2 text-base font-semibold text-[#3D1A78]/80 md:text-lg" data-testid="privacy-tagline">{n.tagline}</p>
        </div>
      </header>
      <main id="privacy-main" className="mx-auto max-w-2xl px-4 py-8 sm:px-6" tabIndex={-1}>
        <h2 className="text-2xl font-bold text-[#3D1A78] sm:text-3xl" data-testid="privacy-title">{n.title}</h2>
        <p className="mt-1 text-sm font-semibold text-slate-700 md:text-base" data-testid="privacy-subhead">{n.subhead}</p>
        <p className="mt-3 text-sm text-slate-600" data-testid="privacy-intro">{n.intro}</p>
        <ol className="mt-6 space-y-3" data-testid="privacy-points">{n.points.map((p, i) => <Item key={p.heading} p={p} i={i} />)}</ol>
        <section className="mt-6 rounded-2xl border-2 border-amber-400 bg-amber-50 p-4 sm:p-5" aria-labelledby="privacy-legal-heading" data-testid="privacy-legal">
          <p id="privacy-legal-heading" className="flex items-center gap-2 text-sm font-bold text-amber-900 md:text-base"><ShieldAlert className="h-4 w-4" aria-hidden="true" /> {n.legal_heading}</p>
          <p className="mt-1 text-sm leading-relaxed text-amber-900/90" data-testid="privacy-legal-text">{n.legal}</p>
        </section>
        <label htmlFor="privacy-ack" className="mt-6 flex cursor-pointer items-start gap-3 rounded-2xl border border-[#3D1A78]/20 bg-white p-4 hover:bg-[#3D1A78]/5">
          <Checkbox id="privacy-ack" checked={ok} onCheckedChange={(v) => setOk(v === true)} className="mt-0.5 border-[#3D1A78] data-[state=checked]:bg-[#3D1A78]" data-testid="privacy-ack-checkbox" />
          <span className="text-sm font-medium">{n.checkbox}</span>
        </label>
        <Button onClick={go} disabled={!ok || busy} aria-disabled={!ok || busy} className="mt-5 h-12 w-full rounded-full bg-[#3D1A78] text-base font-bold hover:bg-[#2f1460] disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-[#3D1A78] focus-visible:ring-offset-2" data-testid="privacy-continue-btn">{n.continue}</Button>
        <p className="mt-4 text-center text-[11px] text-slate-500" data-testid="privacy-version">Notice version {n.version}</p>
        {/* PLACEHOLDER (hidden until the pages exist): footer links to Privacy Policy, Confidentiality, Sharing & Consent come from n.footer_links, which is intentionally empty. */}
        {n.footer_links?.length > 0 && (
          <nav className="mt-2 flex flex-wrap justify-center gap-x-4 gap-y-1 text-xs" aria-label="Privacy documents" data-testid="privacy-footer-links">
            {n.footer_links.map((l) => <a key={l.href} href={l.href} className="font-medium text-[#3D1A78] hover:underline">{l.label}</a>)}
          </nav>
        )}
      </main>
    </div>
  );
}
