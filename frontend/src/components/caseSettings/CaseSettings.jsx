import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { Info, ListChecks } from "lucide-react";

import { useCaseSettings } from "../../lib/useCaseSettings";

// Same words for both parents; no reason is ever shown.
function Banner({ settings, className = "" }) {
  if (!settings?.banner) return null;
  return (
    <div role="note" data-testid="case-settings-banner" className={`flex items-start gap-2.5 rounded-xl border border-[#D9D3EA] bg-white/90 px-4 py-3 text-sm text-[#3B3552] ${className}`}>
      <Info size={16} className="mt-0.5 shrink-0 text-[#5B4A8A]" aria-hidden="true" />
      <p>
        <span data-testid="case-settings-banner-text">{settings.banner}</span>{" "}
        <Link to="/case-settings" data-testid="case-settings-banner-link" className="font-semibold text-[#3D1A78] underline underline-offset-2">
          What does this mean?
        </Link>
      </p>
    </div>
  );
}

function PlanOptionsCard({ settings }) {
  const navigate = useNavigate();
  if (!settings?.plan_options) return null;
  return (
    <section data-testid="plan-options-card" className="rounded-2xl border border-purple-200 bg-white p-4 shadow-sm flex items-start gap-3">
      <span className="shrink-0 w-10 h-10 rounded-xl bg-purple-100 text-[#4a2574] grid place-items-center" aria-hidden="true">
        <ListChecks size={18} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-slate-900" data-testid="plan-options-card-text">
          Your professional has set up your parenting plan options.
        </p>
        <button
          type="button"
          onClick={() => navigate("/plan-options")}
          data-testid="plan-options-card-button"
          className="mt-3 inline-flex items-center rounded-full bg-[#4a2574] px-4 py-2 text-xs font-bold text-white transition-colors hover:bg-[#3a1d5c]"
        >
          View options
        </button>
      </div>
    </section>
  );
}

export function CaseSettingsBanner({ className = "" }) {
  return <Banner settings={useCaseSettings()} className={className} />;
}

// Home screen: one settings read for both the banner and the options card.
export function CaseHomeNotices() {
  const settings = useCaseSettings();
  return (
    <>
      <Banner settings={settings} />
      <PlanOptionsCard settings={settings} />
    </>
  );
}
