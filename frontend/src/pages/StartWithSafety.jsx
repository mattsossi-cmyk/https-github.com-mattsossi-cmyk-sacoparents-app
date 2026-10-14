import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { HeartHandshake } from "lucide-react";
import api from "@/lib/api";
import { QuickExitBar } from "@/components/QuickExit";
import { CrisisResourcesButton } from "@/components/CrisisResources";
import { BrandLogo } from "@/components/Brand";
import { SAFETY_HUB_BODY, SAFETY_HUB_SKIP, SAFETY_HUB_TITLE, SAFETY_BANNER_BEGIN } from "@/content/safetyEntry";

export const SEEN_KEY = "align-start-with-safety-seen";

export default function StartWithSafety() {
  const navigate = useNavigate();
  const [s, setS] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    api.get("/me/safety-entry").then((r) => {
      if (!r.data?.applies || r.data.status !== "not_started") { sessionStorage.setItem(SEEN_KEY, "1"); navigate("/dashboard", { replace: true }); return; }
      setS(r.data);
    }).catch(() => { sessionStorage.setItem(SEEN_KEY, "1"); navigate("/dashboard", { replace: true }); });
  }, [navigate]);
  const begin = () => { sessionStorage.setItem(SEEN_KEY, "1"); navigate(s.report_id ? `/joint/${s.report_id}/safety-screening` : "/dashboard"); };
  const skip = async () => {
    setBusy(true);
    try { if (s.report_id) await api.post(`/joint/reports/${s.report_id}/safety-screening/skip`); } catch { /* status only; never block the parent */ }
    sessionStorage.setItem(SEEN_KEY, "1");
    navigate("/dashboard", { replace: true });
  };
  if (!s) return <div className="min-h-screen bg-[#f6f3fb]" data-testid="start-safety-loading" />;
  return (
    <div className="min-h-screen bg-[#f6f3fb] font-jakarta text-slate-900" data-testid="start-with-safety-page">
      <QuickExitBar variant="red" label="Confidential Assessment Area" />
      <header className="border-b border-[#3D1A78]/10 bg-white"><div className="mx-auto flex max-w-2xl items-center justify-between px-4 py-4 sm:px-6"><BrandLogo size="text-xl" /><CrisisResourcesButton /></div></header>
      <main className="mx-auto max-w-2xl px-4 py-10 sm:px-6">
        <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#3D1A78] text-white" aria-hidden="true"><HeartHandshake className="h-7 w-7" /></span>
        <h1 className="mt-5 text-3xl font-bold tracking-tight text-[#3D1A78] sm:text-4xl" data-testid="start-safety-title">{SAFETY_HUB_TITLE}</h1>
        <p className="mt-3 text-base leading-relaxed text-slate-700" data-testid="start-safety-body">{SAFETY_HUB_BODY}</p>
        {!s.has_case && <p className="mt-3 text-sm text-slate-600" data-testid="start-safety-no-case">The check-in opens once you have accepted an invitation to a case. You can continue to your home screen now.</p>}
        <div className="mt-8 flex flex-wrap gap-3">
          {s.has_case && <button type="button" onClick={begin} className="rounded-full bg-[#3D1A78] px-7 py-3 text-base font-bold text-white transition-colors hover:bg-[#2f1460]" data-testid="start-safety-begin-btn">{SAFETY_BANNER_BEGIN}</button>}
          <button type="button" onClick={skip} disabled={busy} className="rounded-full border border-[#3D1A78]/40 px-7 py-3 text-base font-semibold text-[#3D1A78] transition-colors hover:bg-[#3D1A78]/5 disabled:opacity-50" data-testid="start-safety-skip-btn">{s.has_case ? SAFETY_HUB_SKIP : "Continue"}</button>
        </div>
        <p className="mt-6 text-xs text-slate-500" data-testid="start-safety-footnote">Optional. Nothing is required to take part in your case. Every question can be skipped.</p>
      </main>
    </div>
  );
}
