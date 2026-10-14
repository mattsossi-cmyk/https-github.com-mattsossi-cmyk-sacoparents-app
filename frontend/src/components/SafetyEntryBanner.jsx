import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { LogOut, ShieldCheck } from "lucide-react";
import api from "@/lib/api";
import { quickExit } from "@/components/QuickExit";
import { SAFETY_BANNER_BEGIN, SAFETY_BANNER_SMALL, SAFETY_BANNER_TEXT } from "@/content/safetyEntry";

export const SafetyEntryBanner = () => {
  const navigate = useNavigate();
  const [s, setS] = useState(null);
  useEffect(() => { api.get("/me/safety-entry").then((r) => setS(r.data)).catch(() => setS(null)); }, []);
  if (!s?.applies) return null;
  const target = s.report_id ? `/joint/${s.report_id}/safety-screening` : "/start-with-safety";
  if (s.status !== "not_started") {
    return (
      <div className="font-jakarta border-b border-[#3D1A78]/15 bg-[#f6f3fb]" data-testid="safety-entry-link">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-2 text-xs sm:px-6">
          <button type="button" onClick={() => navigate(target)} className="flex items-center gap-1.5 font-semibold text-[#3D1A78] underline-offset-2 hover:underline" data-testid="safety-entry-link-btn"><ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" /> {SAFETY_BANNER_SMALL}</button>
          <button type="button" onClick={quickExit} className="flex items-center gap-1 text-[#3D1A78]/80 hover:text-[#3D1A78]" data-testid="safety-entry-quick-exit"><LogOut className="h-3.5 w-3.5" aria-hidden="true" /> Quick Exit</button>
        </div>
      </div>
    );
  }
  return (
    <section className="font-jakarta bg-[#3D1A78] text-white" role="region" aria-label="Start with Safety" data-testid="safety-entry-banner">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <p className="flex items-center gap-2 text-sm font-semibold md:text-base" data-testid="safety-entry-banner-text"><ShieldCheck className="h-5 w-5 shrink-0" aria-hidden="true" /> {s.text || SAFETY_BANNER_TEXT}</p>
        <div className="flex items-center gap-2">
          <button type="button" onClick={() => navigate(target)} className="rounded-full bg-white px-5 py-2 text-sm font-bold text-[#3D1A78] transition-colors hover:bg-[#ece6f7] focus-visible:outline focus-visible:outline-2 focus-visible:outline-white" data-testid="safety-entry-begin-btn">{SAFETY_BANNER_BEGIN}</button>
          <button type="button" onClick={quickExit} className="flex items-center gap-1.5 rounded-full border border-white/60 px-4 py-2 text-sm font-semibold transition-colors hover:bg-white/10" data-testid="safety-entry-quick-exit"><LogOut className="h-4 w-4" aria-hidden="true" /> Quick Exit</button>
        </div>
      </div>
    </section>
  );
};
