import React from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import StartWithSafetyBanner from "../components/startWithSafety/StartWithSafetyBanner";
import CoparentingBuilderReferral from "../components/startWithSafety/CoparentingBuilderReferral";
import { SafetyFirstBanner } from "../components/caseSettings/SafetyFirstBanner";
import { ALIGN_SITE_URL, BUILDER_PATH, quickExitAction } from "./portal/JourneyShell";
import { useParallelStatus } from "./portal/selfJourney/useParallelDone";

// The dashboard's "Private check-in" step: banner, check-in button, hotlines, then the builder card.
export default function StartWithSafetyPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const ppStatus = useParallelStatus(user?.user_id, false);
  return (
    <div className="min-h-screen bg-[#f7f4fd] pb-16" data-testid="start-with-safety-page">
      <header className="sticky top-0 z-10 bg-white border-b border-[#f1ecfc] px-4 py-2.5 flex items-center justify-between gap-3">
        <Link to="/dashboard" data-testid="sws-page-home" className="min-h-[44px] inline-flex items-center gap-1 text-sm font-bold text-[#3d1f80]">
          <i className="fa-solid fa-arrow-left" aria-hidden="true"></i> Home
        </Link>
        <button
          type="button"
          onClick={quickExitAction}
          data-testid="sws-page-quick-exit"
          className="min-h-[44px] px-4 rounded-full bg-[#b42318] text-white text-[0.95rem] font-bold"
        >
          Quick Exit <span aria-hidden="true">✕</span>
        </button>
      </header>
      <main className="max-w-md mx-auto px-4 py-4 space-y-4">
        <StartWithSafetyBanner />
        <SafetyFirstBanner alignUrl={ALIGN_SITE_URL} onQuickExit={quickExitAction} />
        <CoparentingBuilderReferral
          builderUrl={BUILDER_PATH}
          progress={ppStatus}
          onOpen={(e) => {
            e.preventDefault();
            navigate(BUILDER_PATH);
          }}
        />
      </main>
    </div>
  );
}
