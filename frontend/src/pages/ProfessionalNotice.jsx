import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { ShieldAlert } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";

export default function ProfessionalNotice() {
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [n, setN] = useState(null);
  const [ok, setOk] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.get("/professional-notice").then((r) => setN(r.data.notice)).catch((e) => toast.error(formatApiError(e))); }, []);
  const go = async () => {
    setBusy(true);
    try {
      await api.post("/professional-notice/accept", { version: n.version, acknowledged: ok });
      await refresh();
      navigate(sessionStorage.getItem("post-pro-notice-redirect") || "/dashboard", { replace: true });
      sessionStorage.removeItem("post-pro-notice-redirect");
    } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  if (!n) return <div className="min-h-screen bg-[#f6f3fb]" data-testid="pro-notice-loading" />;
  return (
    <div className="min-h-screen bg-[#f6f3fb] font-jakarta text-slate-900" data-testid="professional-notice-page">
      <header className="bg-[#ece6f7]">
        <div className="mx-auto flex max-w-2xl flex-col items-center px-4 pb-8 pt-10 text-center sm:px-6">
          <BrandLogo size="text-3xl" />
          <p className="mt-4 text-xs font-bold uppercase tracking-widest text-[#3D1A78]/70">{n.brand}</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-[#3D1A78] sm:text-4xl" data-testid="pro-notice-title">{n.title}</h1>
          <p className="mt-2 text-base font-semibold text-[#3D1A78]/80 md:text-lg" data-testid="pro-notice-tagline">{n.tagline}</p>
        </div>
      </header>
      <main className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
        <p className="text-sm leading-relaxed text-slate-700 md:text-base" data-testid="pro-notice-intro">{n.intro}</p>
        <h2 className="mt-6 text-xl font-bold text-[#3D1A78]" data-testid="pro-notice-section-heading">{n.section_heading}</h2>
        <ol className="mt-3 space-y-3" data-testid="pro-notice-points">
          {n.points.map((p, i) => (
            <li key={p.heading} className="rounded-2xl border border-[#3D1A78]/10 bg-white p-4 shadow-sm" data-testid={`pro-notice-point-${i + 1}`}>
              <p className="text-sm font-bold md:text-base">{p.heading}</p>
              <p className="mt-1 text-sm leading-relaxed text-slate-600">{p.body}</p>
            </li>
          ))}
        </ol>
        <section className="mt-6 rounded-2xl border-2 border-[#3D1A78]/40 bg-white p-4 text-center" data-testid="pro-notice-principle">
          <p className="text-xs font-bold uppercase tracking-widest text-[#3D1A78]/70">{n.principle_heading}</p>
          <p className="mt-1 text-base font-bold text-[#3D1A78] md:text-lg">{n.principle}</p>
        </section>
        <p className="mt-6 flex items-center gap-2 text-sm font-bold text-amber-900 md:text-base"><ShieldAlert className="h-4 w-4" aria-hidden="true" /> {n.ack_heading}</p>
        <label htmlFor="pro-ack" className="mt-2 flex cursor-pointer items-start gap-3 rounded-2xl border border-[#3D1A78]/20 bg-white p-4 hover:bg-[#3D1A78]/5">
          <Checkbox id="pro-ack" checked={ok} onCheckedChange={(v) => setOk(v === true)} className="mt-0.5 border-[#3D1A78] data-[state=checked]:bg-[#3D1A78]" data-testid="pro-notice-ack-checkbox" />
          <span className="text-sm font-medium" data-testid="pro-notice-ack-text">{n.checkbox}</span>
        </label>
        <Button onClick={go} disabled={!ok || busy} className="mt-5 h-12 w-full rounded-full bg-[#3D1A78] text-base font-bold hover:bg-[#2f1460] disabled:opacity-50" data-testid="pro-notice-continue-btn">{n.continue}</Button>
        <p className="mt-4 text-center text-[11px] text-slate-500" data-testid="pro-notice-version">Notice version {n.version}</p>
      </main>
    </div>
  );
}
